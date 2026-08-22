"""Leakage validation for historical pregame snapshots."""

from __future__ import annotations

from daily_nfl.domain import AvailabilityMethod
from daily_nfl.pit.contracts import (
    DEFAULT_PIT_POLICY,
    PITInputKind,
    PITInputRef,
    PITLeakageCode,
    PITLeakageViolation,
    PITPolicy,
    PredictionCutoff,
)
from daily_nfl.pit.selector import is_input_eligible


class PITLeakageError(RuntimeError):
    """Raised when strict PIT validation finds one or more leaked inputs."""

    def __init__(self, violations: tuple[PITLeakageViolation, ...]) -> None:
        self.violations = violations
        codes = ", ".join(violation.code.value for violation in violations)
        super().__init__(f"PIT leakage validation failed: {codes}")


def _append_missing_context(
    violations: list[PITLeakageViolation],
    input_ref: PITInputRef,
    explanation: str,
) -> None:
    violations.append(
        PITLeakageViolation(
            code=PITLeakageCode.MISSING_REQUIRED_CONTEXT,
            input_id=input_ref.input_id,
            explanation=explanation,
        )
    )


def find_leakage(
    inputs: tuple[PITInputRef, ...],
    *,
    cutoff: PredictionCutoff,
    policy: PITPolicy = DEFAULT_PIT_POLICY,
) -> tuple[PITLeakageViolation, ...]:
    violations: list[PITLeakageViolation] = []

    for input_ref in inputs:
        if input_ref.available_at > cutoff.prediction_time:
            violations.append(
                PITLeakageViolation(
                    code=PITLeakageCode.SOURCE_AFTER_CUTOFF,
                    input_id=input_ref.input_id,
                    explanation="input became available after the prediction cutoff",
                )
            )
        elif not is_input_eligible(input_ref, cutoff, policy):
            violations.append(
                PITLeakageViolation(
                    code=PITLeakageCode.INDEFENSIBLE_AVAILABILITY,
                    input_id=input_ref.input_id,
                    explanation="availability method/confidence fails strict PIT policy",
                )
            )

        if policy.require_context_metadata and input_ref.evidence_id is not None:
            if input_ref.evidence_observation_id is None or input_ref.provider_id is None:
                _append_missing_context(
                    violations,
                    input_ref,
                    "raw-backed PIT input requires acquisition observation and provider provenance",
                )

        is_current_game = input_ref.subject_game_id == cutoff.game_id
        if input_ref.input_kind in {
            PITInputKind.CURRENT_GAME_RESULT,
            PITInputKind.CURRENT_GAME_STAT,
            PITInputKind.CURRENT_GAME_PLAY,
        }:
            if policy.require_context_metadata and not is_current_game:
                _append_missing_context(
                    violations,
                    input_ref,
                    "current-game outcome/stat/play input must identify the cutoff game",
                )
            if is_current_game:
                violations.append(
                    PITLeakageViolation(
                        code=PITLeakageCode.CURRENT_GAME_OUTCOME,
                        input_id=input_ref.input_id,
                        explanation=(
                            "current-game outcome/play/stat cannot enter a pregame snapshot"
                        ),
                    )
                )

        if input_ref.input_kind is PITInputKind.WEATHER_ACTUAL:
            if policy.require_context_metadata and input_ref.subject_game_id is None:
                _append_missing_context(
                    violations,
                    input_ref,
                    "actual weather requires subject_game_id under strict PIT policy",
                )
            if is_current_game:
                violations.append(
                    PITLeakageViolation(
                        code=PITLeakageCode.ACTUAL_WEATHER_FOR_CURRENT_GAME,
                        input_id=input_ref.input_id,
                        explanation=(
                            "actual game weather cannot substitute for the prior forecast"
                        ),
                    )
                )

        if input_ref.input_kind is PITInputKind.MARKET_QUOTE:
            if policy.require_context_metadata and input_ref.market_quote_at is None:
                _append_missing_context(
                    violations,
                    input_ref,
                    "market quote requires its quote timestamp under strict PIT policy",
                )
            elif (
                input_ref.market_quote_at is not None
                and input_ref.market_quote_at > cutoff.prediction_time
            ):
                violations.append(
                    PITLeakageViolation(
                        code=PITLeakageCode.LATER_MARKET_QUOTE,
                        input_id=input_ref.input_id,
                        explanation="market quote timestamp is later than the prediction cutoff",
                    )
                )

        if input_ref.input_kind is PITInputKind.FUTURE_GAME:
            if policy.require_context_metadata and input_ref.source_game_kickoff is None:
                _append_missing_context(
                    violations,
                    input_ref,
                    "future/prior game reference requires source_game_kickoff",
                )
            elif (
                input_ref.source_game_kickoff is not None
                and input_ref.source_game_kickoff >= cutoff.prediction_time
            ):
                violations.append(
                    PITLeakageViolation(
                        code=PITLeakageCode.FUTURE_GAME_INFORMATION,
                        input_id=input_ref.input_id,
                        explanation="source game had not occurred by the prediction cutoff",
                    )
                )

        if input_ref.input_kind is PITInputKind.FUTURE_SEASON_WEEK_LABEL:
            violations.append(
                PITLeakageViolation(
                    code=PITLeakageCode.FUTURE_GAME_INFORMATION,
                    input_id=input_ref.input_id,
                    explanation="future season/week labels cannot enter a historical snapshot",
                )
            )

        if input_ref.input_kind is PITInputKind.SEASON_FINAL_AGGREGATE:
            if policy.require_context_metadata and input_ref.season_complete_at is None:
                _append_missing_context(
                    violations,
                    input_ref,
                    "season-final aggregate requires season_complete_at",
                )
            elif (
                input_ref.season_complete_at is not None
                and input_ref.season_complete_at > cutoff.prediction_time
            ):
                violations.append(
                    PITLeakageViolation(
                        code=PITLeakageCode.END_OF_SEASON_INFORMATION,
                        input_id=input_ref.input_id,
                        explanation="end-of-season aggregate was not complete at the cutoff",
                    )
                )

        if input_ref.input_kind is PITInputKind.PROVIDER_CORRECTION:
            if policy.require_context_metadata and (
                input_ref.provider_id is None or input_ref.provider_revision is None
            ):
                _append_missing_context(
                    violations,
                    input_ref,
                    "provider correction requires provider_id and provider_revision",
                )
            if (
                input_ref.available_at > cutoff.prediction_time
                or input_ref.availability_method is AvailabilityMethod.UNKNOWN
            ):
                violations.append(
                    PITLeakageViolation(
                        code=PITLeakageCode.LATE_PROVIDER_CORRECTION,
                        input_id=input_ref.input_id,
                        explanation="provider correction lacks pre-cutoff defensible availability",
                    )
                )

    return tuple(violations)


def assert_no_leakage(
    inputs: tuple[PITInputRef, ...],
    *,
    cutoff: PredictionCutoff,
    policy: PITPolicy = DEFAULT_PIT_POLICY,
) -> None:
    violations = find_leakage(inputs, cutoff=cutoff, policy=policy)
    if violations:
        raise PITLeakageError(violations)
