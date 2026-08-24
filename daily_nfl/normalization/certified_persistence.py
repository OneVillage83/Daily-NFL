"""Certified M6 persistence boundary for canonical normalized play observations.

This module composes the provisional canonical-row identity helpers with the
M3/M5 acquisition-observation provenance contract. New M6 writes are atomic and
must identify the exact raw acquisition observation that supported normalization.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass

from daily_nfl.domain import KnowledgeTimestamp
from daily_nfl.normalization.contracts import NormalizedPlayBundle
from daily_nfl.normalization.persistence import (
    NormalizedPlayConflictError,
    _ensure_canonical_rows,
    _iso,
)

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


def _payload(bundle: NormalizedPlayBundle) -> dict[str, object]:
    pre = bundle.pre_play_state
    result = bundle.result
    physical = result.physical_outcome
    after = bundle.state_after
    return {
        "contract_version": "NFL_CANONICAL_PLAY_V1",
        "game_id": str(bundle.game_id),
        "canonical_sequence": bundle.canonical_sequence,
        "drive_sequence": bundle.drive_sequence,
        "possession_sequence": bundle.possession_sequence,
        "provider_id": bundle.provider_id,
        "provider_play_id": bundle.provider_play_id,
        "provider_drive_id": bundle.provider_drive_id,
        "description": bundle.description,
        "pre_play_state": {
            "play_id": str(pre.play_id),
            "previous_play_id": (
                str(pre.previous_play_id) if pre.previous_play_id is not None else None
            ),
            "drive_id": str(pre.drive_id) if pre.drive_id is not None else None,
            "possession_id": str(pre.possession.possession_id),
            "possession_segment_id": (
                str(pre.possession_segment_id)
                if pre.possession_segment_id is not None
                else None
            ),
            "offense_team_season_id": str(pre.possession.offense_team_season_id),
            "defense_team_season_id": str(pre.possession.defense_team_season_id),
            "period": pre.period.number,
            "is_overtime": pre.period.is_overtime,
            "clock_seconds_remaining": pre.clock_seconds_remaining,
            "play_clock_seconds_remaining": pre.play_clock_seconds_remaining,
            "down": pre.down,
            "distance": pre.distance,
            "yards_to_goal": pre.yards_to_goal,
            "home_score": pre.home_score,
            "away_score": pre.away_score,
            "home_timeouts_remaining": pre.home_timeouts_remaining,
            "away_timeouts_remaining": pre.away_timeouts_remaining,
            "kickoff_state": pre.kickoff_state,
            "try_state": pre.try_state,
            "two_minute_state": pre.two_minute_state,
            "overtime_state": pre.overtime_state,
            "offensive_personnel": pre.offensive_personnel,
            "defensive_personnel": pre.defensive_personnel,
            "offensive_formation": pre.offensive_formation,
            "defensive_front": pre.defensive_front,
            "coverage_shell": pre.coverage_shell,
            "motion": pre.motion,
            "shift": pre.shift,
            "shotgun": pre.shotgun,
            "no_huddle": pre.no_huddle,
            "weather_snapshot_id": pre.weather_snapshot_id,
            "surface_state_id": pre.surface_state_id,
        },
        "execution": {
            "primary_play_type": bundle.execution.primary_play_type.value,
            "modifiers": sorted(modifier.value for modifier in bundle.execution.modifiers),
            "semantic_label": bundle.execution.semantic_label,
        },
        "events": [
            {
                "play_event_id": str(event.play_event_id),
                "sequence": event.sequence,
                "event_type": event.event_type.value,
                "player_id": str(event.player_id) if event.player_id is not None else None,
                "team_season_id": (
                    str(event.team_season_id) if event.team_season_id is not None else None
                ),
                "detail": event.detail,
            }
            for event in bundle.events
        ],
        "participation": [
            {
                "participation_id": str(item.participation_id),
                "player_id": str(item.player_id),
                "team_season_id": str(item.team_season_id),
                "side": item.side.value,
                "role": item.role,
                "on_field": item.on_field,
            }
            for item in bundle.participation
        ],
        "penalties": [
            {
                "penalty_id": str(penalty.penalty_id),
                "team_season_id": str(penalty.team_season_id),
                "player_id": str(penalty.player_id) if penalty.player_id is not None else None,
                "penalty_type": penalty.penalty_type,
                "disposition": penalty.disposition.value,
                "yards": penalty.yards,
                "automatic_first_down": penalty.automatic_first_down,
                "loss_of_down": penalty.loss_of_down,
                "nullifies_play": penalty.nullifies_play,
                "enforcement_spot": penalty.enforcement_spot,
            }
            for penalty in bundle.penalties
        ],
        "result": {
            "official_yards_gained": result.official_yards_gained,
            "first_down": result.first_down,
            "touchdown": result.touchdown,
            "safety": result.safety,
            "completion": result.completion,
            "interception": result.interception,
            "sack": result.sack,
            "fumble": result.fumble,
            "fumble_lost": result.fumble_lost,
            "possession_changed": result.possession_changed,
            "score_change": result.score_change,
            "no_play": result.no_play,
            "kick_result": result.kick_result,
            "physical_outcome": (
                None
                if physical is None
                else {
                    "yards_gained": physical.yards_gained,
                    "first_down": physical.first_down,
                    "touchdown": physical.touchdown,
                    "safety": physical.safety,
                    "completion": physical.completion,
                    "interception": physical.interception,
                    "sack": physical.sack,
                    "fumble": physical.fumble,
                    "fumble_lost": physical.fumble_lost,
                    "possession_changed": physical.possession_changed,
                    "score_change": physical.score_change,
                }
            ),
        },
        "state_after": (
            None
            if after is None
            else {
                "next_possession_id": (
                    str(after.next_possession.possession_id)
                    if after.next_possession is not None
                    else None
                ),
                "offense_team_season_id": (
                    str(after.next_possession.offense_team_season_id)
                    if after.next_possession is not None
                    else None
                ),
                "defense_team_season_id": (
                    str(after.next_possession.defense_team_season_id)
                    if after.next_possession is not None
                    else None
                ),
                "period": after.period.number,
                "is_overtime": after.period.is_overtime,
                "clock_seconds_remaining": after.clock_seconds_remaining,
                "down": after.down,
                "distance": after.distance,
                "yards_to_goal": after.yards_to_goal,
                "home_score": after.home_score,
                "away_score": after.away_score,
                "drive_continues": after.drive_continues,
            }
        ),
    }


def serialize_normalized_play(bundle: NormalizedPlayBundle) -> tuple[str, str]:
    """Serialize every canonical M6 field that is safe to persist downstream."""

    payload_json = json.dumps(_payload(bundle), sort_keys=True, separators=(",", ":"))
    return payload_json, hashlib.sha256(payload_json.encode()).hexdigest()


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
    participation_rows = connection.execute(
        """
        SELECT observation_id, participation_id, evidence_id,
               evidence_observation_id, provider_id, provider_revision
        FROM participation_observations
        WHERE play_id = ? AND evidence_observation_id = ?
        ORDER BY observation_id
        """,
        (str(bundle.pre_play_state.play_id), provenance.evidence_observation_id),
    ).fetchall()
    expected_participation = sorted(
        (
            _participation_observation_id(provenance.observation_id, sequence),
            str(item.participation_id),
            provenance.evidence_id,
            provenance.evidence_observation_id,
            bundle.provider_id,
            provenance.provider_revision,
        )
        for sequence, item in enumerate(bundle.participation, start=1)
    )
    if [tuple(row) for row in participation_rows] != expected_participation:
        raise NormalizedPlayConflictError(
            "stored participation observations do not match normalized play membership"
        )

    penalty_rows = connection.execute(
        """
        SELECT observation_id, penalty_id, evidence_id,
               evidence_observation_id, provider_id, provider_revision
        FROM penalty_observations
        WHERE play_id = ? AND evidence_observation_id = ?
        ORDER BY observation_id
        """,
        (str(bundle.pre_play_state.play_id), provenance.evidence_observation_id),
    ).fetchall()
    expected_penalties = sorted(
        (
            _penalty_observation_id(provenance.observation_id, sequence),
            str(item.penalty_id),
            provenance.evidence_id,
            provenance.evidence_observation_id,
            bundle.provider_id,
            provenance.provider_revision,
        )
        for sequence, item in enumerate(bundle.penalties, start=1)
    )
    if [tuple(row) for row in penalty_rows] != expected_penalties:
        raise NormalizedPlayConflictError(
            "stored penalty observations do not match normalized play membership"
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
                observation_id,
                participation_id,
                play_id,
                player_id,
                team_season_id,
                evidence_id,
                evidence_observation_id,
                provider_id,
                side,
                role,
                on_field,
                effective_at,
                published_at,
                observed_at,
                ingested_at,
                available_at,
                availability_method,
                availability_confidence,
                provider_revision
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
                observation_id,
                penalty_id,
                play_id,
                team_season_id,
                player_id,
                evidence_id,
                evidence_observation_id,
                provider_id,
                penalty_type,
                disposition,
                yards,
                automatic_first_down,
                loss_of_down,
                nullifies_play,
                enforcement_spot,
                effective_at,
                published_at,
                observed_at,
                ingested_at,
                available_at,
                availability_method,
                availability_confidence,
                provider_revision
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
                observation_id,
                play_id,
                evidence_id,
                evidence_observation_id,
                provider_id,
                provider_play_id,
                provider_revision,
                normalized_payload_json,
                normalized_sha256,
                effective_at,
                published_at,
                observed_at,
                ingested_at,
                available_at,
                availability_method,
                availability_confidence
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
