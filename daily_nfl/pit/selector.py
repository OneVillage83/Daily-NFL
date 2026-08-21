"""Fail-closed eligibility and as-of selection for historical observations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from daily_nfl.domain import AvailabilityConfidence, AvailabilityMethod
from daily_nfl.pit.contracts import PITInputRef, PITPolicy, PredictionCutoff


class PITSelectionConflictError(RuntimeError):
    """Raised when equally ranked historical revisions disagree."""


ConfidenceRank = {
    AvailabilityConfidence.LOW: 1,
    AvailabilityConfidence.MEDIUM: 2,
    AvailabilityConfidence.HIGH: 3,
}


@dataclass(frozen=True, slots=True)
class PITObservation[T]:
    logical_key: str
    input_ref: PITInputRef
    value: T

    def __post_init__(self) -> None:
        if not self.logical_key.strip():
            raise ValueError("logical_key cannot be blank")


def is_input_eligible(
    input_ref: PITInputRef,
    cutoff: PredictionCutoff,
    policy: PITPolicy,
) -> bool:
    if input_ref.available_at > cutoff.prediction_time:
        return False
    if (
        input_ref.availability_method is AvailabilityMethod.UNKNOWN
        and not policy.allow_unknown_method
    ):
        return False
    if (
        input_ref.availability_method is AvailabilityMethod.INFERRED_REPORT_DATE
        and not policy.allow_inferred_report_date
    ):
        return False
    return ConfidenceRank[input_ref.availability_confidence] >= ConfidenceRank[
        policy.minimum_confidence
    ]


def _rank(input_ref: PITInputRef) -> tuple[datetime, datetime, datetime]:
    minimum = datetime.min.replace(tzinfo=input_ref.available_at.tzinfo)
    return (
        input_ref.available_at,
        input_ref.observed_at or minimum,
        input_ref.ingested_at or minimum,
    )


def select_latest_as_of[T](
    observations: tuple[PITObservation[T], ...],
    *,
    cutoff: PredictionCutoff,
    policy: PITPolicy = PITPolicy(),
) -> tuple[PITObservation[T], ...]:
    """Select the latest eligible revision for each logical observation key."""

    eligible = [
        observation
        for observation in observations
        if is_input_eligible(observation.input_ref, cutoff, policy)
    ]
    grouped: dict[str, list[PITObservation[T]]] = {}
    for observation in eligible:
        grouped.setdefault(observation.logical_key, []).append(observation)

    selected: list[PITObservation[T]] = []
    for logical_key in sorted(grouped):
        candidates = grouped[logical_key]
        top_rank = max(_rank(candidate.input_ref) for candidate in candidates)
        top = [candidate for candidate in candidates if _rank(candidate.input_ref) == top_rank]
        payload_hashes = {candidate.input_ref.payload_sha256 for candidate in top}
        if len(top) > 1 and len(payload_hashes) > 1:
            raise PITSelectionConflictError(
                f"conflicting equally ranked PIT revisions for logical key {logical_key!r}"
            )
        selected.append(min(top, key=lambda candidate: candidate.input_ref.input_id))

    return tuple(selected)
