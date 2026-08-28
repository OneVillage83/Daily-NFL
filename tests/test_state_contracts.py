from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from daily_nfl.domain import (
    AvailabilityConfidence,
    AvailabilityMethod,
    GameId,
    StateSnapshotId,
    TeamSeasonId,
)
from daily_nfl.pit import PITInputKind, PITInputRef, PITValidationResult
from daily_nfl.state import (
    StateCoverage,
    StateSnapshotEnvelope,
    StateSubjectType,
    StateType,
    StateUncertainty,
)


AS_OF = datetime(2026, 9, 13, 16, 0, tzinfo=UTC)
CREATED_AT = datetime(2026, 9, 13, 16, 1, tzinfo=UTC)
DEFAULT_SNAPSHOT_ID = StateSnapshotId("state-1")


def _input_ref(
    *,
    input_id: str = "obs-1",
    available_at: datetime | None = None,
) -> PITInputRef:
    return PITInputRef(
        input_kind=PITInputKind.OTHER,
        input_id=input_id,
        available_at=available_at or AS_OF - timedelta(minutes=1),
        availability_method=AvailabilityMethod.SOURCE_TIMESTAMP,
        availability_confidence=AvailabilityConfidence.HIGH,
        source_table="test_observations",
    )


def _coverage() -> StateCoverage:
    return StateCoverage(
        expected_fields=("quality", "style"),
        present_fields=("quality",),
        missing_fields=("style",),
    )


def _envelope(
    *,
    snapshot_id: StateSnapshotId = DEFAULT_SNAPSHOT_ID,
    as_of: datetime = AS_OF,
    inputs: tuple[PITInputRef, ...] = (),
    dependencies: tuple[StateSnapshotId, ...] = (),
    pit_validation: PITValidationResult = PITValidationResult.PASS,
    payload_sha256: str = "a" * 64,
) -> StateSnapshotEnvelope[tuple[str, ...]]:
    return StateSnapshotEnvelope(
        snapshot_id=snapshot_id,
        state_type=StateType.TEAM,
        subject_type=StateSubjectType.TEAM_SEASON,
        subject_id="team-season-1",
        team_season_id=TeamSeasonId("team-season-1"),
        game_id=GameId("game-1"),
        as_of=as_of,
        calculation_contract="NFL_TEAM_STATE_V1",
        model_version="team-state-baseline-v1",
        state_payload=("quality", "style"),
        uncertainty=StateUncertainty(),
        coverage=_coverage(),
        input_observations=inputs,
        input_state_snapshot_ids=dependencies,
        payload_sha256=payload_sha256,
        pit_validation=pit_validation,
        created_at=CREATED_AT,
    )


def test_state_coverage_tracks_exact_partition_and_fraction() -> None:
    coverage = _coverage()
    assert coverage.coverage_fraction == 0.5

    empty = StateCoverage(expected_fields=(), present_fields=(), missing_fields=())
    assert empty.coverage_fraction == 1.0


def test_state_coverage_rejects_non_partitioned_fields() -> None:
    with pytest.raises(ValueError, match="exactly partition"):
        StateCoverage(
            expected_fields=("quality", "style"),
            present_fields=("quality",),
            missing_fields=(),
        )

    with pytest.raises(ValueError, match="both present and missing"):
        StateCoverage(
            expected_fields=("quality",),
            present_fields=("quality",),
            missing_fields=("quality",),
        )


def test_state_snapshot_envelope_accepts_pit_safe_inputs() -> None:
    envelope = _envelope(inputs=(_input_ref(),))
    assert envelope.state_type is StateType.TEAM
    assert envelope.input_observations[0].input_id == "obs-1"


def test_state_snapshot_envelope_rejects_naive_as_of() -> None:
    with pytest.raises(ValueError, match="as_of must be timezone-aware"):
        _envelope(as_of=datetime(2026, 9, 13, 16, 0))


def test_state_snapshot_envelope_rejects_post_as_of_input() -> None:
    with pytest.raises(ValueError, match="available after snapshot as_of"):
        _envelope(
            inputs=(
                _input_ref(
                    available_at=AS_OF + timedelta(seconds=1),
                ),
            )
        )


def test_state_snapshot_envelope_rejects_duplicate_observation_inputs() -> None:
    duplicate = _input_ref()
    with pytest.raises(ValueError, match="observation inputs cannot repeat"):
        _envelope(inputs=(duplicate, duplicate))


def test_state_snapshot_envelope_rejects_duplicate_dependencies() -> None:
    dependency = StateSnapshotId("state-parent")
    with pytest.raises(ValueError, match="dependencies cannot repeat"):
        _envelope(dependencies=(dependency, dependency))


def test_state_snapshot_envelope_rejects_self_dependency() -> None:
    snapshot_id = StateSnapshotId("state-self")
    with pytest.raises(ValueError, match="cannot depend on itself"):
        _envelope(snapshot_id=snapshot_id, dependencies=(snapshot_id,))


def test_state_snapshot_envelope_requires_valid_payload_sha256() -> None:
    with pytest.raises(ValueError, match="SHA-256"):
        _envelope(payload_sha256="not-a-digest")


def test_state_snapshot_envelope_requires_pit_pass() -> None:
    with pytest.raises(ValueError, match="PIT validation PASS"):
        _envelope(pit_validation=PITValidationResult.FAIL)
