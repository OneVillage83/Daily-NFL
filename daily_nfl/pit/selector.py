"""Fail-closed eligibility and as-of selection for historical observations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from daily_nfl.domain import AvailabilityConfidence, AvailabilityMethod
from daily_nfl.pit.contracts import (
    DEFAULT_PIT_POLICY,
    PITInputRef,
    PITPolicy,
    PredictionCutoff,
)


class PITSelectionConflictError(RuntimeError):
    """Raised when historical revisions cannot be resolved without guessing."""


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


def _select_latest_by_knowledge[T](
    observations: list[PITObservation[T]],
) -> tuple[PITObservation[T], ...]:
    grouped: dict[str, list[PITObservation[T]]] = {}
    for observation in observations:
        grouped.setdefault(observation.logical_key, []).append(observation)

    selected: list[PITObservation[T]] = []
    for logical_key in sorted(grouped):
        candidates = grouped[logical_key]
        latest_available_at = max(candidate.input_ref.available_at for candidate in candidates)
        top = [
            candidate
            for candidate in candidates
            if candidate.input_ref.available_at == latest_available_at
        ]
        if len(top) > 1:
            payload_hashes = {candidate.input_ref.payload_sha256 for candidate in top}
            if None in payload_hashes or len(payload_hashes) > 1:
                raise PITSelectionConflictError(
                    "conflicting PIT revisions share the same knowledge timestamp "
                    f"for logical key {logical_key!r}"
                )
        selected.append(min(top, key=lambda candidate: candidate.input_ref.input_id))

    return tuple(selected)


def select_latest_as_of[T](
    observations: tuple[PITObservation[T], ...],
    *,
    cutoff: PredictionCutoff,
    policy: PITPolicy = DEFAULT_PIT_POLICY,
) -> tuple[PITObservation[T], ...]:
    """Select the latest defensibly known revision for each logical key.

    `observed_at` and `ingested_at` are deliberately not revision tie-breakers.
    If two different payloads claim the same historical knowledge timestamp,
    M5 cannot know which content was available then and therefore fails closed.
    """

    eligible = [
        observation
        for observation in observations
        if is_input_eligible(observation.input_ref, cutoff, policy)
    ]
    return _select_latest_by_knowledge(eligible)


def select_latest_bitemporal_as_of[T](
    observations: tuple[PITObservation[T], ...],
    *,
    cutoff: PredictionCutoff,
    state_time: datetime | None = None,
    policy: PITPolicy = DEFAULT_PIT_POLICY,
) -> tuple[PITObservation[T], ...]:
    """Select state valid in reality and knowable by the prediction cutoff.

    This is the explicit F-4 bitemporal helper. `state_time` defaults to the
    prediction timestamp. Every knowledge-eligible observation passed to this
    state query must carry `effective_at`; otherwise the engine refuses to
    guess its real-world validity interval.
    """

    resolved_state_time = state_time or cutoff.prediction_time
    if resolved_state_time.tzinfo is None or resolved_state_time.utcoffset() is None:
        raise ValueError("state_time must be timezone-aware")

    eligible: list[PITObservation[T]] = []
    for observation in observations:
        if not is_input_eligible(observation.input_ref, cutoff, policy):
            continue
        effective_at = observation.input_ref.effective_at
        if effective_at is None:
            raise PITSelectionConflictError(
                "bitemporal PIT selection requires effective_at for every "
                f"knowledge-eligible observation; missing on {observation.input_ref.input_id!r}"
            )
        if effective_at <= resolved_state_time:
            eligible.append(observation)

    return _select_latest_by_knowledge(eligible)
