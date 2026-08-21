from datetime import UTC, datetime, timedelta

import pytest

from daily_nfl.domain import (
    AvailabilityConfidence,
    AvailabilityMethod,
    GameId,
)
from daily_nfl.pit import (
    AvailabilityEvidence,
    IndefensibleAvailabilityError,
    PITHorizon,
    PITInputKind,
    PITInputRef,
    PITObservation,
    PITPolicy,
    PITSelectionConflictError,
    PredictionCutoff,
    derive_knowledge_timestamp,
    is_input_eligible,
    select_latest_as_of,
)


def _cutoff(horizon: PITHorizon = PITHorizon.T_90M) -> PredictionCutoff:
    return PredictionCutoff.from_horizon(
        game_id=GameId("gam_fixture"),
        kickoff=datetime(2026, 9, 10, 20, 20, tzinfo=UTC),
        horizon=horizon,
    )


def _input(
    input_id: str,
    available_at: datetime,
    *,
    payload_sha256: str = "a" * 64,
    method: AvailabilityMethod = AvailabilityMethod.SOURCE_TIMESTAMP,
    confidence: AvailabilityConfidence = AvailabilityConfidence.HIGH,
) -> PITInputRef:
    return PITInputRef(
        input_kind=PITInputKind.INJURY,
        input_id=input_id,
        available_at=available_at,
        availability_method=method,
        availability_confidence=confidence,
        source_table="fixture_observations",
        observed_at=available_at,
        ingested_at=available_at + timedelta(seconds=1),
        payload_sha256=payload_sha256,
    )


def test_standard_horizon_derives_exact_prediction_cutoff() -> None:
    cutoff = _cutoff(PITHorizon.T_15M)

    assert cutoff.prediction_time == datetime(2026, 9, 10, 20, 5, tzinfo=UTC)
    assert cutoff.prediction_time < cutoff.kickoff


def test_source_timestamp_has_priority_for_defensible_availability() -> None:
    source = datetime(2026, 9, 9, 15, 0, tzinfo=UTC)
    observed = source + timedelta(hours=2)
    knowledge = derive_knowledge_timestamp(
        AvailabilityEvidence(
            source_timestamp=source,
            observed_at=observed,
            ingested_at=observed + timedelta(seconds=1),
        )
    )

    assert knowledge.available_at == source
    assert knowledge.availability_method is AvailabilityMethod.SOURCE_TIMESTAMP
    assert knowledge.availability_confidence is AvailabilityConfidence.HIGH


def test_strict_availability_fails_when_historical_time_is_indefensible() -> None:
    with pytest.raises(IndefensibleAvailabilityError, match="no defensible"):
        derive_knowledge_timestamp(AvailabilityEvidence(), strict=True)


def test_permissive_backfill_can_record_ingestion_but_marks_it_unknown_low() -> None:
    ingested = datetime(2026, 8, 21, 6, 0, tzinfo=UTC)
    knowledge = derive_knowledge_timestamp(
        AvailabilityEvidence(ingested_at=ingested),
        strict=False,
    )

    assert knowledge.available_at == ingested
    assert knowledge.availability_method is AvailabilityMethod.UNKNOWN
    assert knowledge.availability_confidence is AvailabilityConfidence.LOW


def test_strict_policy_rejects_unknown_and_inferred_low_confidence() -> None:
    cutoff = _cutoff()
    unknown = _input(
        "unknown",
        cutoff.prediction_time - timedelta(hours=1),
        method=AvailabilityMethod.UNKNOWN,
        confidence=AvailabilityConfidence.LOW,
    )
    inferred = _input(
        "inferred",
        cutoff.prediction_time - timedelta(hours=1),
        method=AvailabilityMethod.INFERRED_REPORT_DATE,
        confidence=AvailabilityConfidence.LOW,
    )

    assert not is_input_eligible(unknown, cutoff, PITPolicy())
    assert not is_input_eligible(inferred, cutoff, PITPolicy())


def test_game_day_information_is_eligible_when_available_before_cutoff() -> None:
    cutoff = _cutoff(PITHorizon.T_15M)
    report = _input("late-report", cutoff.prediction_time - timedelta(minutes=2))

    assert is_input_eligible(report, cutoff, PITPolicy())


def test_selector_hides_later_correction_until_it_becomes_available() -> None:
    cutoff = _cutoff()
    old = PITObservation(
        logical_key="player:fixture:status",
        input_ref=_input("old", cutoff.prediction_time - timedelta(hours=3)),
        value="QUESTIONABLE",
    )
    corrected = PITObservation(
        logical_key="player:fixture:status",
        input_ref=_input("corrected", cutoff.prediction_time + timedelta(minutes=10)),
        value="OUT",
    )

    selected = select_latest_as_of((old, corrected), cutoff=cutoff)

    assert len(selected) == 1
    assert selected[0].value == "QUESTIONABLE"


def test_selector_uses_correction_after_later_cutoff() -> None:
    original_cutoff = _cutoff()
    later_cutoff = PredictionCutoff(
        game_id=original_cutoff.game_id,
        kickoff=original_cutoff.kickoff,
        prediction_time=original_cutoff.prediction_time + timedelta(minutes=30),
    )
    old = PITObservation(
        logical_key="player:fixture:status",
        input_ref=_input("old", original_cutoff.prediction_time - timedelta(hours=3)),
        value="QUESTIONABLE",
    )
    corrected = PITObservation(
        logical_key="player:fixture:status",
        input_ref=_input("corrected", original_cutoff.prediction_time + timedelta(minutes=10)),
        value="OUT",
    )

    selected = select_latest_as_of((old, corrected), cutoff=later_cutoff)

    assert selected[0].value == "OUT"


def test_equally_ranked_conflicting_revisions_fail_closed() -> None:
    cutoff = _cutoff()
    available = cutoff.prediction_time - timedelta(hours=1)
    first = PITObservation(
        logical_key="same-key",
        input_ref=_input("a", available, payload_sha256="a" * 64),
        value="A",
    )
    second = PITObservation(
        logical_key="same-key",
        input_ref=_input("b", available, payload_sha256="b" * 64),
        value="B",
    )

    with pytest.raises(PITSelectionConflictError, match="equally ranked"):
        select_latest_as_of((first, second), cutoff=cutoff)
