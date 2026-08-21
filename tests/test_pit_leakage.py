from datetime import UTC, datetime, timedelta

from daily_nfl.domain import AvailabilityConfidence, AvailabilityMethod, GameId
from daily_nfl.pit import (
    PITInputKind,
    PITInputRef,
    PITLeakageCode,
    PredictionCutoff,
    find_leakage,
)


def _cutoff() -> PredictionCutoff:
    return PredictionCutoff(
        game_id=GameId("gam_current"),
        kickoff=datetime(2026, 9, 10, 20, 20, tzinfo=UTC),
        prediction_time=datetime(2026, 9, 10, 18, 50, tzinfo=UTC),
    )


def _input(
    input_id: str,
    kind: PITInputKind,
    *,
    available_at: datetime | None = None,
    subject_game_id: GameId | None = None,
    method: AvailabilityMethod = AvailabilityMethod.SOURCE_TIMESTAMP,
    market_quote_at: datetime | None = None,
    source_game_kickoff: datetime | None = None,
    season_complete_at: datetime | None = None,
) -> PITInputRef:
    cutoff = _cutoff()
    return PITInputRef(
        input_kind=kind,
        input_id=input_id,
        available_at=available_at or cutoff.prediction_time - timedelta(minutes=5),
        availability_method=method,
        availability_confidence=AvailabilityConfidence.HIGH,
        source_table="fixture_source",
        subject_game_id=subject_game_id,
        market_quote_at=market_quote_at,
        source_game_kickoff=source_game_kickoff,
        season_complete_at=season_complete_at,
    )


def _codes(*inputs: PITInputRef) -> set[PITLeakageCode]:
    return {violation.code for violation in find_leakage(tuple(inputs), cutoff=_cutoff())}


def test_post_cutoff_injury_depth_and_forecast_are_rejected() -> None:
    after = _cutoff().prediction_time + timedelta(seconds=1)

    for kind in (
        PITInputKind.INJURY,
        PITInputKind.DEPTH_CHART,
        PITInputKind.WEATHER_FORECAST,
    ):
        assert PITLeakageCode.SOURCE_AFTER_CUTOFF in _codes(
            _input(f"late-{kind.value}", kind, available_at=after)
        )


def test_current_game_final_score_stats_and_plays_are_rejected() -> None:
    game_id = _cutoff().game_id

    for kind in (
        PITInputKind.CURRENT_GAME_RESULT,
        PITInputKind.CURRENT_GAME_STAT,
        PITInputKind.CURRENT_GAME_PLAY,
    ):
        assert PITLeakageCode.CURRENT_GAME_OUTCOME in _codes(
            _input(f"outcome-{kind.value}", kind, subject_game_id=game_id)
        )


def test_actual_weather_cannot_replace_current_game_forecast() -> None:
    codes = _codes(
        _input(
            "actual-weather",
            PITInputKind.WEATHER_ACTUAL,
            subject_game_id=_cutoff().game_id,
        )
    )

    assert PITLeakageCode.ACTUAL_WEATHER_FOR_CURRENT_GAME in codes


def test_later_market_quote_is_rejected_even_if_mislabeled_available_early() -> None:
    cutoff = _cutoff()
    codes = _codes(
        _input(
            "closing-line",
            PITInputKind.MARKET_QUOTE,
            market_quote_at=cutoff.prediction_time + timedelta(minutes=20),
        )
    )

    assert PITLeakageCode.LATER_MARKET_QUOTE in codes


def test_future_opponent_game_information_is_rejected() -> None:
    cutoff = _cutoff()
    codes = _codes(
        _input(
            "future-game",
            PITInputKind.FUTURE_GAME,
            source_game_kickoff=cutoff.prediction_time + timedelta(days=1),
        )
    )

    assert PITLeakageCode.FUTURE_GAME_INFORMATION in codes


def test_end_of_season_aggregate_is_rejected_midseason() -> None:
    cutoff = _cutoff()
    codes = _codes(
        _input(
            "season-final",
            PITInputKind.SEASON_FINAL_AGGREGATE,
            season_complete_at=cutoff.prediction_time + timedelta(days=100),
        )
    )

    assert PITLeakageCode.END_OF_SEASON_INFORMATION in codes


def test_indefensible_provider_correction_is_rejected() -> None:
    codes = _codes(
        _input(
            "correction",
            PITInputKind.PROVIDER_CORRECTION,
            method=AvailabilityMethod.UNKNOWN,
        )
    )

    assert PITLeakageCode.INDEFENSIBLE_AVAILABILITY in codes
    assert PITLeakageCode.LATE_PROVIDER_CORRECTION in codes


def test_legitimate_pre_cutoff_inputs_pass() -> None:
    cutoff = _cutoff()
    inputs = (
        _input("injury", PITInputKind.INJURY),
        _input("forecast", PITInputKind.WEATHER_FORECAST, subject_game_id=cutoff.game_id),
        _input(
            "market",
            PITInputKind.MARKET_QUOTE,
            market_quote_at=cutoff.prediction_time - timedelta(minutes=1),
        ),
    )

    assert find_leakage(inputs, cutoff=cutoff) == ()
