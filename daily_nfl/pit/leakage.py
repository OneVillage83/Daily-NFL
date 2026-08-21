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

        is_current_game = input_ref.subject_game_id == cutoff.game_id
        if is_current_game and input_ref.input_kind in {
            PITInputKind.CURRENT_GAME_RESULT,
            PITInputKind.CURRENT_GAME_STAT,
            PITInputKind.CURRENT_GAME_PLAY,
        }:
            violations.append(
                PITLeakageViolation(
                    code=PITLeakageCode.CURRENT_GAME_OUTCOME,
                    input_id=input_ref.input_id,
                    explanation="current-game outcome/play/stat cannot enter a pregame snapshot",
                )
            )

        if is_current_game and input_ref.input_kind is PITInputKind.WEATHER_ACTUAL:
            violations.append(
                PITLeakageViolation(
                    code=PITLeakageCode.ACTUAL_WEATHER_FOR_CURRENT_GAME,
                    input_id=input_ref.input_id,
                    explanation="actual game weather cannot substitute for the prior forecast",
                )
            )

        if (
            input_ref.input_kind is PITInputKind.MARKET_QUOTE
            and input_ref.market_quote_at is not None
            and input_ref.market_quote_at > cutoff.prediction_time
        ):
            violations.append(
                PITLeakageViolation(
                    code=PITLeakageCode.LATER_MARKET_QUOTE,
                    input_id=input_ref.input_id,
                    explanation="market quote timestamp is later than the prediction cutoff",
                )
            )

        if (
            input_ref.input_kind is PITInputKind.FUTURE_GAME
            and input_ref.source_game_kickoff is not None
            and input_ref.source_game_kickoff >= cutoff.prediction_time
        ):
            violations.append(
                PITLeakageViolation(
                    code=PITLeakageCode.FUTURE_GAME_INFORMATION,
                    input_id=input_ref.input_id,
                    explanation="source game had not occurred by the prediction cutoff",
                )
            )

        if (
            input_ref.input_kind is PITInputKind.SEASON_FINAL_AGGREGATE
            and input_ref.season_complete_at is not None
            and input_ref.season_complete_at > cutoff.prediction_time
        ):
            violations.append(
                PITLeakageViolation(
                    code=PITLeakageCode.END_OF_SEASON_INFORMATION,
                    input_id=input_ref.input_id,
                    explanation="end-of-season aggregate was not complete at the cutoff",
                )
            )

        if input_ref.input_kind is PITInputKind.PROVIDER_CORRECTION and (
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
