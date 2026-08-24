"""Certified M6 persistence boundary for canonical normalized play observations."""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass

from daily_nfl.domain import KnowledgeTimestamp
from daily_nfl.normalization.contracts import NormalizedPlayBundle
from daily_nfl.normalization.persistence_core import (
    NormalizedPlayConflictError,
    _ensure_canonical_rows,
    _iso,
)
from daily_nfl.normalization.serialization import serialize_normalized_play

_SAVEPOINT = "m6_normalized_play_write"


@dataclass(frozen=True, slots=True)
class NormalizationProvenance:
    """Exact historical evidence supporting one normalized provider play row."""

    observation_id: str
    knowledge: KnowledgeTimestamp
    evidence_id: str
    evidence_observation_id: str
    provider_revision: str | None = None

    def __post_init__(self) -> None:
        for value, label in (
            (self.observation_id, "observation_id"),
            (self.evidence_id, "evidence_id"),
            (self.evidence_observation_id, "evidence_observation_id"),
        ):
            if not value.strip():
                raise ValueError(f"{label} cannot be blank")
        if self.provider_revision is not None and not self.provider_revision.strip():
            raise ValueError("provider_revision cannot be blank when present")
        if self.knowledge.ingested_at is None:
            raise ValueError("normalized observations require ingested_at")


def normalized_play_observation_id(
    *,
    evidence_id: str,
    evidence_observation_id: str,
    provider_id: str,
    provider_play_id: str,
    provider_revision: str | None = None,
) -> str:
    """Derive identity from content, acquisition, provider row, and revision."""

    values = (
        evidence_id,
        evidence_observation_id,
        provider_id,
        provider_play_id,
    )
    if any(not value.strip() for value in values):
        raise ValueError("normalization observation identity fields cannot be blank")
    payload = "|".join((*values, provider_revision or "")).encode()
    return f"pob_{hashlib.sha256(payload).hexdigest()}"


def _participation_observation_id(observation_id: str, sequence: int) -> str:
    digest = hashlib.sha256(f"{observation_id}|participation|{sequence}".encode()).hexdigest()
    return f"pao_{digest}"


def _penalty_observation_id(observation_id: str, sequence: int) -> str:
    digest = hashlib.sha256(f"{observation_id}|penalty|{sequence}".encode()).hexdigest()
    return f"peo_{digest}"


def _validate_acquisition_provenance(
    connection: sqlite3.Connection,
    *,
    bundle: NormalizedPlayBundle,
    provenance: NormalizationProvenance,
) -> None:
    row = connection.execute(
        """
        SELECT evidence_id, provider_id
        FROM raw_evidence_observations
        WHERE evidence_observation_id = ?
        """,
        (provenance.evidence_observation_id,),
    ).fetchone()
    expected = (provenance.evidence_id, bundle.provider_id)
    if row is None or tuple(row) != expected:
        raise NormalizedPlayConflictError(
            "normalization provenance must match the exact raw acquisition observation"
        )


def _verify_existing_children(
    connection: sqlite3.Connection,
    bundle: NormalizedPlayBundle,
    provenance: NormalizationProvenance,
) -> None:
    for sequence, item in enumerate(bundle.participation, start=1):
        observation_id = _participation_observation_id(
            provenance.observation_id,
            sequence,
        )
        row = connection.execute(
            """
            SELECT participation_id, evidence_id, evidence_observation_id,
                   provider_id, provider_revision
            FROM participation_observations
            WHERE observation_id = ?
            """,
            (observation_id,),
        ).fetchone()
        expected = (
            str(item.participation_id),
            provenance.evidence_id,
            provenance.evidence_observation_id,
            bundle.provider_id,
            provenance.provider_revision,
        )
        if row is None or tuple(row) != expected:
            raise NormalizedPlayConflictError(
                "stored participation observation conflicts with normalized membership"
            )

    for sequence, penalty in enumerate(bundle.penalties, start=1):
        observation_id = _penalty_observation_id(provenance.observation_id, sequence)
        row = connection.execute(
            """
            SELECT penalty_id, evidence_id, evidence_observation_id,
                   provider_id, provider_revision
            FROM penalty_observations
            WHERE observation_id = ?
            """,
            (observation_id,),
        ).fetchone()
        expected = (
            str(penalty.penalty_id),
            provenance.evidence_id,
            provenance.evidence_observation_id,
            bundle.provider_id,
            provenance.provider_revision,
        )
        if row is None or tuple(row) != expected:
            raise NormalizedPlayConflictError(
                "stored penalty observation conflicts with normalized membership"
            )


def _insert_participation_observations(
    connection: sqlite3.Connection,
    bundle: NormalizedPlayBundle,
    provenance: NormalizationProvenance,
) -> None:
    knowledge = provenance.knowledge
    for sequence, item in enumerate(bundle.participation, start=1):
        connection.execute(
            """
            INSERT INTO participation_observations(
                observation_id, participation_id, play_id, player_id,
                team_season_id, evidence_id, evidence_observation_id,
                provider_id, side, role, on_field, effective_at, published_at,
                observed_at, ingested_at, available_at, availability_method,
                availability_confidence, provider_revision
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _participation_observation_id(provenance.observation_id, sequence),
                str(item.participation_id),
                str(item.play_id),
                str(item.player_id),
                str(item.team_season_id),
                provenance.evidence_id,
                provenance.evidence_observation_id,
                bundle.provider_id,
                item.side.value,
                item.role,
                int(item.on_field),
                _iso(knowledge.effective_at),
                _iso(knowledge.published_at),
                _iso(knowledge.observed_at),
                _iso(knowledge.ingested_at),
                _iso(knowledge.available_at),
                knowledge.availability_method.value,
                knowledge.availability_confidence.value,
                provenance.provider_revision,
            ),
        )


def _insert_penalty_observations(
    connection: sqlite3.Connection,
    bundle: NormalizedPlayBundle,
    provenance: NormalizationProvenance,
) -> None:
    knowledge = provenance.knowledge
    for sequence, penalty in enumerate(bundle.penalties, start=1):
        connection.execute(
            """
            INSERT INTO penalty_observations(
                observation_id, penalty_id, play_id, team_season_id, player_id,
                evidence_id, evidence_observation_id, provider_id, penalty_type,
                disposition, yards, automatic_first_down, loss_of_down,
                nullifies_play, enforcement_spot, effective_at, published_at,
                observed_at, ingested_at, available_at, availability_method,
                availability_confidence, provider_revision
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _penalty_observation_id(provenance.observation_id, sequence),
                str(penalty.penalty_id),
                str(penalty.play_id),
                str(penalty.team_season_id),
                str(penalty.player_id) if penalty.player_id is not None else None,
                provenance.evidence_id,
                provenance.evidence_observation_id,
                bundle.provider_id,
                penalty.penalty_type,
                penalty.disposition.value,
                penalty.yards,
                int(penalty.automatic_first_down),
                int(penalty.loss_of_down),
                int(penalty.nullifies_play),
                penalty.enforcement_spot,
                _iso(knowledge.effective_at),
                _iso(knowledge.published_at),
                _iso(knowledge.observed_at),
                _iso(knowledge.ingested_at),
                _iso(knowledge.available_at),
                knowledge.availability_method.value,
                knowledge.availability_confidence.value,
                provenance.provider_revision,
            ),
        )


def record_normalized_play(
    connection: sqlite3.Connection,
    bundle: NormalizedPlayBundle,
    provenance: NormalizationProvenance,
) -> None:
    """Atomically persist one certified M6 normalized play observation."""

    _validate_acquisition_provenance(
        connection,
        bundle=bundle,
        provenance=provenance,
    )
    payload_json, payload_sha256 = serialize_normalized_play(bundle)
    connection.execute(f"SAVEPOINT {_SAVEPOINT}")
    try:
        _ensure_canonical_rows(connection, bundle)
        existing = connection.execute(
            """
            SELECT play_id, evidence_id, evidence_observation_id, provider_id,
                   provider_play_id, provider_revision, normalized_payload_json,
                   normalized_sha256
            FROM play_observations
            WHERE observation_id = ?
            """,
            (provenance.observation_id,),
        ).fetchone()
        expected = (
            str(bundle.pre_play_state.play_id),
            provenance.evidence_id,
            provenance.evidence_observation_id,
            bundle.provider_id,
            bundle.provider_play_id,
            provenance.provider_revision,
            payload_json,
            payload_sha256,
        )
        if existing is not None:
            if tuple(existing) != expected:
                raise NormalizedPlayConflictError(
                    "stored normalized play observation conflicts with supplied observation"
                )
            _verify_existing_children(connection, bundle, provenance)
            connection.execute(f"RELEASE SAVEPOINT {_SAVEPOINT}")
            return

        knowledge = provenance.knowledge
        connection.execute(
            """
            INSERT INTO play_observations(
                observation_id, play_id, evidence_id, evidence_observation_id,
                provider_id, provider_play_id, provider_revision,
                normalized_payload_json, normalized_sha256, effective_at,
                published_at, observed_at, ingested_at, available_at,
                availability_method, availability_confidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                provenance.observation_id,
                str(bundle.pre_play_state.play_id),
                provenance.evidence_id,
                provenance.evidence_observation_id,
                bundle.provider_id,
                bundle.provider_play_id,
                provenance.provider_revision,
                payload_json,
                payload_sha256,
                _iso(knowledge.effective_at),
                _iso(knowledge.published_at),
                _iso(knowledge.observed_at),
                _iso(knowledge.ingested_at),
                _iso(knowledge.available_at),
                knowledge.availability_method.value,
                knowledge.availability_confidence.value,
            ),
        )
        _insert_participation_observations(connection, bundle, provenance)
        _insert_penalty_observations(connection, bundle, provenance)
        connection.execute(f"RELEASE SAVEPOINT {_SAVEPOINT}")
    except Exception:
        connection.execute(f"ROLLBACK TO SAVEPOINT {_SAVEPOINT}")
        connection.execute(f"RELEASE SAVEPOINT {_SAVEPOINT}")
        raise


__all__ = [
    "NormalizationProvenance",
    "NormalizedPlayConflictError",
    "normalized_play_observation_id",
    "record_normalized_play",
    "serialize_normalized_play",
]
