from datetime import UTC, datetime, timedelta

from daily_nfl.domain import AvailabilityConfidence, AvailabilityMethod, GameId
from daily_nfl.pit import (
    PITInputKind,
    PITInputRef,
    PITLeakageCode,
    PredictionCutoff,
    find_leakage,
)


def test_future_season_week_label_is_always_rejected_from_historical_snapshot() -> None:
    kickoff = datetime(2026, 9, 10, 20, 20, tzinfo=UTC)
    cutoff = PredictionCutoff(
        game_id=GameId("gam_fixture"),
        kickoff=kickoff,
        prediction_time=kickoff - timedelta(hours=1),
    )
    input_ref = PITInputRef(
        input_kind=PITInputKind.FUTURE_SEASON_WEEK_LABEL,
        input_id="future-week-label",
        available_at=cutoff.prediction_time - timedelta(minutes=5),
        availability_method=AvailabilityMethod.SOURCE_TIMESTAMP,
        availability_confidence=AvailabilityConfidence.HIGH,
        source_table="deliberate_leak_fixture",
        payload_sha256="a" * 64,
    )

    codes = {
        violation.code
        for violation in find_leakage((input_ref,), cutoff=cutoff)
    }

    assert PITLeakageCode.FUTURE_GAME_INFORMATION in codes
