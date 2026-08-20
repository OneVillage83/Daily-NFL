"""Point-in-time knowledge primitives shared by NFL domain observations."""

from dataclasses import dataclass
from datetime import datetime

from daily_nfl.domain.enums import AvailabilityConfidence, AvailabilityMethod


@dataclass(frozen=True, slots=True)
class KnowledgeTimestamp:
    """The four clocks needed to reason about historical information safely.

    `available_at` is the earliest defensible time a model could have known the
    datum. It is intentionally explicit rather than inferred ad hoc downstream.
    """

    available_at: datetime
    effective_at: datetime | None = None
    published_at: datetime | None = None
    observed_at: datetime | None = None
    ingested_at: datetime | None = None
    availability_method: AvailabilityMethod = AvailabilityMethod.UNKNOWN
    availability_confidence: AvailabilityConfidence = AvailabilityConfidence.LOW

    def __post_init__(self) -> None:
        timestamps = (
            self.available_at,
            self.effective_at,
            self.published_at,
            self.observed_at,
            self.ingested_at,
        )
        for timestamp in timestamps:
            if timestamp is not None and timestamp.tzinfo is None:
                raise ValueError("Knowledge timestamps must be timezone-aware")

    def is_available_by(self, cutoff: datetime) -> bool:
        if cutoff.tzinfo is None:
            raise ValueError("cutoff must be timezone-aware")
        return self.available_at <= cutoff
