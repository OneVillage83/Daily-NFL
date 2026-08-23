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
    select_latest_bitemporal_as_of,
)


def _cutoff(horizon: PITHorizon = PITHorizon.T_90M) -> PredictionCutoff:
    return PredictionCutoff.from_horizon(
        game_id=GameId("gam_fixture"),
        kickoff=datetime(2026, 9, 13, 20, 20, tzinfo=UTC),
        horizon=horizon,
    )


def _input(
    input_id: str,
    available_at: datetime,
    *,
    payload_sha256: str = "a" * 64,
    method: AvailabilityMethod = AvailabilityMethod.SOURCE_TIMESTAMP,
    confidence: AvailabilityConfidence = AvailabilityConfidence.HIGH,
    observed_at: datetime | None = None,
    ingested_at: datetime | None = None,
    effective_at: datetime | None = None,
) -> PITInputRef:
    observed = observed_at or available_at
    ingested = ingested_at or observed + timedelta(seconds=1)
    return PITInputRef(
        input_kind=PITInputKind.INJURY,
        input_id=input_id,
        available_at=available_at,
        availability_method=method,
        availability_confidence=confidence,
        source_table="fixture_observations",
        effective_at=effective_at,
        observed_at=observed,
        ingested_at=ingested,
        payload_sha256=payload_sha256,
    )


def test_standard_horizon_derives_exact_prediction_cutoff() -> None:
    cutoff = _cutoff(PITHorizon.T_15M)

    assert cutoff.prediction_time == datetime(2026, 9, 13, 20, 5, tzinfo=UTC)
    assert cutoff.prediction_time < cutoff.kickoff


def test_earliest_high_confidence_availability_evidence_wins() -> None:
    archived = datetime(2026, 9, 9, 14, 0, tzinfo=UTC)
    source = archived + timedelta(hours=1)
    observed = source + timedelta(hours=2)
    knowledge = derive_knowledge_timestamp(
        AvailabilityEvidence(
            source_timestamp=source,
            archived_release_time=archived,
            observed_at=observed,
            ingested_at=observed + timedelta(seconds=1),
        )
    )

    assert knowledge.available_at == archived
    assert knowledge.availability_method is AvailabilityMethod.ARCHIVED_RELEASE_TIME
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


def test_inferred_report_date_is_medium_but_requires_explicit_policy_opt_in() -> None:
    cutoff = _cutoff()
    inferred_at = cutoff.prediction_time - timedelta(hours=1)
    knowledge = derive_knowledge_timestamp(
        AvailabilityEvidence(inferred_report_date=inferred_at)
    )
    inferred = _input(
        "inferred",
        knowledge.available_at,
        method=knowledge.availability_method,
        confidence=knowledge.availability_confidence,
    )

    assert knowledge.availability_confidence is AvailabilityConfidence.MEDIUM
    assert not is_input_eligible(inferred, cutoff, PITPolicy())
    assert is_input_eligible(
        inferred,
        cutoff,
        PITPolicy(allow_inferred_report_date=True),
    )


def test_strict_policy_rejects_unknown_low_confidence() -> None:
    cutoff = _cutoff()
    unknown = _input(
        "unknown",
        cutoff.prediction_time - timedelta(hours=1),
        method=AvailabilityMethod.UNKNOWN,
        confidence=AvailabilityConfidence.LOW,
    )

    assert not is_input_eligible(unknown, cutoff, PITPolicy())


def test_sunday_game_day_information_is_eligible_before_cutoff() -> None:
    cutoff = _cutoff(PITHorizon.T_15M)
    report = _input("late-report", cutoff.prediction_time - timedelta(minutes=2))

    assert cutoff.kickoff.weekday() == 6
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


def test_same_knowledge_conflict_fails_even_when_observed_later() -> None:
    cutoff = _cutoff()
    available = cutoff.prediction_time - timedelta(hours=1)
    original = PITObservation(
        logical_key="same-key",
        input_ref=_input(
            "original",
            available,
            payload_sha256="a" * 64,
            observed_at=available,
        ),
        value="A",
    )
    retrospective_correction = PITObservation(
        logical_key="same-key",
        input_ref=_input(
            "retrospective",
            available,
            payload_sha256="b" * 64,
            observed_at=available + timedelta(days=100),
            ingested_at=available + timedelta(days=100, seconds=1),
        ),
        value="B",
    )

    with pytest.raises(PITSelectionConflictError, match="same knowledge timestamp"):
        select_latest_as_of((original, retrospective_correction), cutoff=cutoff)


def test_same_knowledge_duplicate_payload_is_deterministic() -> None:
    cutoff = _cutoff()
    available = cutoff.prediction_time - timedelta(hours=1)
    first = PITObservation(
        logical_key="same-key",
        input_ref=_input("b", available, payload_sha256="a" * 64),
        value="same",
    )
    second = PITObservation(
        logical_key="same-key",
        input_ref=_input(
            "a",
            available,
            payload_sha256="a" * 64,
            observed_at=available + timedelta(minutes=1),
        ),
        value="same",
    )

    selected = select_latest_as_of((first, second), cutoff=cutoff)

    assert selected[0].input_ref.input_id == "a"


def test_bitemporal_selector_excludes_known_future_effective_state() -> None:
    cutoff = _cutoff()
    old = PITObservation(
        logical_key="player:fixture:status",
        input_ref=_input(
            "old",
            cutoff.prediction_time - timedelta(hours=3),
            payload_sha256="a" * 64,
            effective_at=cutoff.prediction_time - timedelta(days=1),
        ),
        value="ACTIVE",
    )
    announced_future = PITObservation(
        logical_key="player:fixture:status",
        input_ref=_input(
            "future-effective",
            cutoff.prediction_time - timedelta(hours=1),
            payload_sha256="b" * 64,
            effective_at=cutoff.prediction_time + timedelta(hours=1),
        ),
        value="RELEASED",
    )

    knowledge_only = select_latest_as_of((old, announced_future), cutoff=cutoff)
    bitemporal = select_latest_bitemporal_as_of((old, announced_future), cutoff=cutoff)

    assert knowledge_only[0].value == "RELEASED"
    assert bitemporal[0].value == "ACTIVE"


def test_bitemporal_selector_fails_if_effective_time_is_missing() -> None:
    cutoff = _cutoff()
    observation = PITObservation(
        logical_key="player:fixture:status",
        input_ref=_input("missing-effective", cutoff.prediction_time - timedelta(hours=1)),
        value="ACTIVE",
    )

    with pytest.raises(PITSelectionConflictError, match="requires effective_at"):
        select_latest_bitemporal_as_of((observation,), cutoff=cutoff)
