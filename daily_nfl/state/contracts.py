"""Provider-neutral common contracts for M7 football state snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from daily_nfl.domain import GameId, StateSnapshotId, TeamSeasonId
from daily_nfl.pit import PITInputRef, PITValidationResult
from daily_nfl.state.uncertainty import StateUncertainty


class StateType(StrEnum):
    INJURY_AVAILABILITY = "INJURY_AVAILABILITY"
    PLAYER = "PLAYER"
    UNIT = "UNIT"
    COACHING = "COACHING"
    TEAM = "TEAM"


class StateSubjectType(StrEnum):
    PLAYER = "PLAYER"
    UNIT = "UNIT"
    UNIT_CONFIGURATION = "UNIT_CONFIGURATION"
    COACHING_REGIME = "COACHING_REGIME"
    TEAM_SEASON = "TEAM_SEASON"


def _require_nonblank(value: str, label: str) -> None:
    if not value.strip():
        raise ValueError(f"{label} cannot be blank")


def _require_aware(value: datetime, label: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(
        character in "0123456789abcdefABCDEF" for character in value
    )


def _validate_field_names(values: tuple[str, ...], label: str) -> None:
    if any(not value.strip() for value in values):
        raise ValueError(f"{label} names cannot be blank")
    if len(values) != len(set(values)):
        raise ValueError(f"{label} names cannot repeat")


@dataclass(frozen=True, slots=True)
class StateCoverage:
    """Exact expected/present/missing field membership for one state build."""

    expected_fields: tuple[str, ...]
    present_fields: tuple[str, ...]
    missing_fields: tuple[str, ...]

    def __post_init__(self) -> None:
        _validate_field_names(self.expected_fields, "expected field")
        _validate_field_names(self.present_fields, "present field")
        _validate_field_names(self.missing_fields, "missing field")
        expected = set(self.expected_fields)
        present = set(self.present_fields)
        missing = set(self.missing_fields)
        if present.intersection(missing):
            raise ValueError("coverage field cannot be both present and missing")
        if present.union(missing) != expected:
            raise ValueError("present and missing fields must exactly partition expected fields")

    @property
    def coverage_fraction(self) -> float:
        if not self.expected_fields:
            return 1.0
        return len(self.present_fields) / len(self.expected_fields)


@dataclass(frozen=True, slots=True)
class StateSnapshotEnvelope[PayloadT]:
    """Immutable semantic envelope shared by every persisted M7 state family.

    M7-B owns deterministic manifest construction, hashing, sealing, and SQLite
    persistence. This contract defines the provider-neutral object those layers
    must persist and reproduce exactly.
    """

    snapshot_id: StateSnapshotId
    state_type: StateType
    subject_type: StateSubjectType
    subject_id: str
    team_season_id: TeamSeasonId | None
    game_id: GameId | None
    as_of: datetime
    calculation_contract: str
    model_version: str
    state_payload: PayloadT
    uncertainty: StateUncertainty
    coverage: StateCoverage
    input_observations: tuple[PITInputRef, ...]
    input_state_snapshot_ids: tuple[StateSnapshotId, ...]
    payload_sha256: str
    pit_validation: PITValidationResult
    created_at: datetime

    def __post_init__(self) -> None:
        _require_nonblank(str(self.snapshot_id), "snapshot_id")
        _require_nonblank(self.subject_id, "subject_id")
        _require_nonblank(self.calculation_contract, "calculation_contract")
        _require_nonblank(self.model_version, "model_version")
        if self.team_season_id is not None:
            _require_nonblank(str(self.team_season_id), "team_season_id")
        if self.game_id is not None:
            _require_nonblank(str(self.game_id), "game_id")
        _require_aware(self.as_of, "as_of")
        _require_aware(self.created_at, "created_at")
        if not _is_sha256(self.payload_sha256):
            raise ValueError("payload_sha256 must be a SHA-256 hex digest")
        if self.pit_validation is not PITValidationResult.PASS:
            raise ValueError("state snapshot envelope requires PIT validation PASS")

        input_identities = [
            (input_ref.input_kind, input_ref.input_id)
            for input_ref in self.input_observations
        ]
        if len(input_identities) != len(set(input_identities)):
            raise ValueError("state snapshot observation inputs cannot repeat")
        for input_ref in self.input_observations:
            if input_ref.available_at > self.as_of:
                raise ValueError("state snapshot input cannot be available after snapshot as_of")

        dependency_ids = [str(snapshot_id) for snapshot_id in self.input_state_snapshot_ids]
        if len(dependency_ids) != len(set(dependency_ids)):
            raise ValueError("state snapshot dependencies cannot repeat")
        if str(self.snapshot_id) in dependency_ids:
            raise ValueError("state snapshot cannot depend on itself")
