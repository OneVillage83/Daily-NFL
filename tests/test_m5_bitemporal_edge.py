from datetime import UTC, datetime, timedelta

from daily_nfl.domain import AvailabilityConfidence, AvailabilityMethod, GameId
from daily_nfl.pit import (
    PITInputKind,
    PITInputRef,
    PITObservation,
    PredictionCutoff,
    select_latest_bitemporal_as_of,
)


def _ref(
    input_id: str,
    *,
    available_at: datetime,
    effective_at: datetime,
    payload: str,
) -> PITInputRef:
    return PITInputRef(
        input_kind=PITInputKind.INJURY,
        input_id=input_id,
        available_at=available_at,
        availability_method=AvailabilityMethod.SOURCE_TIMESTAMP,
        availability_confidence=AvailabilityConfidence.HIGH,
        source_table="fixture",
        effective_at=effective_at,
        observed_at=available_at,
        ingested_at=available_at + timedelta(seconds=1),
        payload_sha256=payload * 64,
    )


def test_late_correction_to_older_state_cannot_displace_newer_effective_state() -> None:
    kickoff = datetime(2026, 9, 10, 20, 20, tzinfo=UTC)
    cutoff = PredictionCutoff(
        game_id=GameId("gam_fixture"),
        kickoff=kickoff,
        prediction_time=kickoff - timedelta(hours=1),
    )
    monday = kickoff - timedelta(days=3)
    tuesday = kickoff - timedelta(days=2)
    newer_state = PITObservation(
        logical_key="player:status",
        input_ref=_ref(
            "tuesday-state",
            available_at=kickoff - timedelta(hours=4),
            effective_at=tuesday,
            payload="b",
        ),
        value="ACTIVE",
    )
    late_monday_correction = PITObservation(
        logical_key="player:status",
        input_ref=_ref(
            "monday-correction",
            available_at=kickoff - timedelta(hours=2),
            effective_at=monday,
            payload="c",
        ),
        value="QUESTIONABLE",
    )

    selected = select_latest_bitemporal_as_of(
        (newer_state, late_monday_correction),
        cutoff=cutoff,
    )

    assert len(selected) == 1
    assert selected[0].input_ref.input_id == "tuesday-state"
    assert selected[0].value == "ACTIVE"
