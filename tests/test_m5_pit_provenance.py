from datetime import UTC, datetime, timedelta

from daily_nfl.domain import AvailabilityConfidence, AvailabilityMethod, GameId
from daily_nfl.pit import (
    PITInputKind,
    PITInputRef,
    PITLeakageCode,
    PredictionCutoff,
    find_leakage,
)


def test_raw_backed_input_requires_acquisition_observation_and_provider() -> None:
    kickoff = datetime(2026, 9, 10, 20, 20, tzinfo=UTC)
    cutoff = PredictionCutoff(
        game_id=GameId("gam_fixture"),
        kickoff=kickoff,
        prediction_time=kickoff - timedelta(hours=1),
    )
    input_ref = PITInputRef(
        input_kind=PITInputKind.INJURY,
        input_id="raw-backed",
        available_at=cutoff.prediction_time - timedelta(minutes=5),
        availability_method=AvailabilityMethod.SOURCE_TIMESTAMP,
        availability_confidence=AvailabilityConfidence.HIGH,
        source_table="fixture",
        evidence_id="evidence-1",
        payload_sha256="a" * 64,
    )

    codes = {
        violation.code
        for violation in find_leakage((input_ref,), cutoff=cutoff)
    }

    assert PITLeakageCode.MISSING_REQUIRED_CONTEXT in codes


def test_raw_backed_input_with_acquisition_provenance_passes_generic_checks() -> None:
    kickoff = datetime(2026, 9, 10, 20, 20, tzinfo=UTC)
    cutoff = PredictionCutoff(
        game_id=GameId("gam_fixture"),
        kickoff=kickoff,
        prediction_time=kickoff - timedelta(hours=1),
    )
    input_ref = PITInputRef(
        input_kind=PITInputKind.INJURY,
        input_id="raw-backed",
        available_at=cutoff.prediction_time - timedelta(minutes=5),
        availability_method=AvailabilityMethod.SOURCE_TIMESTAMP,
        availability_confidence=AvailabilityConfidence.HIGH,
        source_table="fixture",
        evidence_id="evidence-1",
        evidence_observation_id="reo-1",
        provider_id="fixture-provider",
        payload_sha256="a" * 64,
    )

    assert find_leakage((input_ref,), cutoff=cutoff) == ()
