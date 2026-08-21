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

    Precedence intentionally favors explicit source/release timestamps, then
    our own observation time. Inferred report dates are weak evidence. If no
    historical availability evidence exists, strict mode fails closed; a
    permissive caller may use ingestion time with UNKNOWN/LOW confidence.
    """

    available_at: datetime | None = None
    method = AvailabilityMethod.UNKNOWN
    confidence = AvailabilityConfidence.LOW

    if evidence.source_timestamp is not None:
        available_at = evidence.source_timestamp
        method = AvailabilityMethod.SOURCE_TIMESTAMP
        confidence = AvailabilityConfidence.HIGH
    elif evidence.archived_release_time is not None:
        available_at = evidence.archived_release_time
        method = AvailabilityMethod.ARCHIVED_RELEASE_TIME
        confidence = AvailabilityConfidence.HIGH
    elif evidence.observed_at is not None:
        available_at = evidence.observed_at
        method = AvailabilityMethod.OUR_OBSERVATION_TIME
        confidence = AvailabilityConfidence.HIGH
    elif evidence.inferred_report_date is not None:
        available_at = evidence.inferred_report_date
        method = AvailabilityMethod.INFERRED_REPORT_DATE
        confidence = AvailabilityConfidence.LOW
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

    return KnowledgeTimestamp(
        available_at=available_at,
        effective_at=evidence.effective_at,
        published_at=evidence.published_at,
        observed_at=evidence.observed_at,
        ingested_at=evidence.ingested_at,
        availability_method=method,
        availability_confidence=confidence,
    )
