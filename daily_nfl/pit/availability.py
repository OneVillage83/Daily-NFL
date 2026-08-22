"""Defensible historical availability derivation for PIT reconstruction."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from daily_nfl.domain import (
    AvailabilityConfidence,
    AvailabilityMethod,
    KnowledgeTimestamp,
)


class IndefensibleAvailabilityError(ValueError):
    """Raised when a historical availability time cannot be defended."""


@dataclass(frozen=True, slots=True)
class AvailabilityEvidence:
    source_timestamp: datetime | None = None
    archived_release_time: datetime | None = None
    observed_at: datetime | None = None
    ingested_at: datetime | None = None
    inferred_report_date: datetime | None = None
    effective_at: datetime | None = None
    published_at: datetime | None = None

    def __post_init__(self) -> None:
        for value, label in (
            (self.source_timestamp, "source_timestamp"),
            (self.archived_release_time, "archived_release_time"),
            (self.observed_at, "observed_at"),
            (self.ingested_at, "ingested_at"),
            (self.inferred_report_date, "inferred_report_date"),
            (self.effective_at, "effective_at"),
            (self.published_at, "published_at"),
        ):
            if value is not None and (value.tzinfo is None or value.utcoffset() is None):
                raise ValueError(f"{label} must be timezone-aware")
        if (
            self.observed_at is not None
            and self.ingested_at is not None
            and self.ingested_at < self.observed_at
        ):
            raise ValueError("ingested_at cannot precede observed_at")


def derive_knowledge_timestamp(
    evidence: AvailabilityEvidence,
    *,
    strict: bool = True,
) -> KnowledgeTimestamp:
    """Derive the earliest defensible historical availability clock.

    F-4 defines source/publication timestamps, archived release times, and our
    own observation time as high-confidence evidence when they are genuinely
    available. When more than one such clock exists, the earliest defensible
    public/observed clock is the knowledge boundary. Inferred report dates are
    medium-confidence evidence and remain excluded by the default strict PIT
    policy unless explicitly authorized by the caller.
    """

    high_confidence: list[tuple[datetime, AvailabilityMethod]] = []
    if evidence.source_timestamp is not None:
        high_confidence.append(
            (evidence.source_timestamp, AvailabilityMethod.SOURCE_TIMESTAMP)
        )
    if evidence.published_at is not None:
        high_confidence.append((evidence.published_at, AvailabilityMethod.SOURCE_TIMESTAMP))
    if evidence.archived_release_time is not None:
        high_confidence.append(
            (evidence.archived_release_time, AvailabilityMethod.ARCHIVED_RELEASE_TIME)
        )
    if evidence.observed_at is not None:
        high_confidence.append(
            (evidence.observed_at, AvailabilityMethod.OUR_OBSERVATION_TIME)
        )

    available_at: datetime | None = None
    method = AvailabilityMethod.UNKNOWN
    confidence = AvailabilityConfidence.LOW

    if high_confidence:
        method_priority = {
            AvailabilityMethod.SOURCE_TIMESTAMP: 0,
            AvailabilityMethod.ARCHIVED_RELEASE_TIME: 1,
            AvailabilityMethod.OUR_OBSERVATION_TIME: 2,
        }
        available_at, method = min(
            high_confidence,
            key=lambda candidate: (candidate[0], method_priority[candidate[1]]),
        )
        confidence = AvailabilityConfidence.HIGH
    elif evidence.inferred_report_date is not None:
        available_at = evidence.inferred_report_date
        method = AvailabilityMethod.INFERRED_REPORT_DATE
        confidence = AvailabilityConfidence.MEDIUM
    elif evidence.ingested_at is not None and not strict:
        available_at = evidence.ingested_at

    if available_at is None:
        raise IndefensibleAvailabilityError(
            "no defensible historical availability time can be derived"
        )

    if evidence.observed_at is not None and available_at > evidence.observed_at:
        raise IndefensibleAvailabilityError(
            "derived available_at cannot be later than our observation time"
        )
    if evidence.ingested_at is not None and available_at > evidence.ingested_at:
        raise IndefensibleAvailabilityError(
            "derived available_at cannot be later than ingestion time"
        )

    return KnowledgeTimestamp(
        available_at=available_at,
        effective_at=evidence.effective_at,
        published_at=evidence.published_at,
        observed_at=evidence.observed_at,
        ingested_at=evidence.ingested_at,
        availability_method=method,
        availability_confidence=confidence,
    )
