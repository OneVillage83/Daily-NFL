"""Compatibility boundary for certified M6 normalization persistence.

Canonical-row helper implementation lives in ``persistence_core``. Public write
operations lazily delegate to ``certified_persistence`` so direct imports of this
historical module cannot bypass M3/M5 acquisition-observation provenance checks.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from daily_nfl.domain import KnowledgeTimestamp
from daily_nfl.normalization.contracts import NormalizedPlayBundle
from daily_nfl.normalization.persistence_core import NormalizedPlayConflictError


@dataclass(frozen=True, slots=True)
class NormalizationProvenance:
    """Compatibility form of the certified exact-acquisition provenance contract."""

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
    import daily_nfl.normalization.certified_persistence as certified_persistence

    return certified_persistence.normalized_play_observation_id(
        evidence_id=evidence_id,
        evidence_observation_id=evidence_observation_id,
        provider_id=provider_id,
        provider_play_id=provider_play_id,
        provider_revision=provider_revision,
    )


def serialize_normalized_play(bundle: NormalizedPlayBundle) -> tuple[str, str]:
    import daily_nfl.normalization.certified_persistence as certified_persistence

    return certified_persistence.serialize_normalized_play(bundle)


def record_normalized_play(
    connection: sqlite3.Connection,
    bundle: NormalizedPlayBundle,
    provenance: NormalizationProvenance,
) -> None:
    import daily_nfl.normalization.certified_persistence as certified_persistence

    certified_persistence.record_normalized_play(
        connection,
        bundle,
        certified_persistence.NormalizationProvenance(
            observation_id=provenance.observation_id,
            knowledge=provenance.knowledge,
            evidence_id=provenance.evidence_id,
            evidence_observation_id=provenance.evidence_observation_id,
            provider_revision=provenance.provider_revision,
        ),
    )


__all__ = [
    "NormalizationProvenance",
    "NormalizedPlayConflictError",
    "normalized_play_observation_id",
    "record_normalized_play",
    "serialize_normalized_play",
]
