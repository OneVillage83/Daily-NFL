"""Deterministic construction and identity verification for M7 state snapshots."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any, cast

from daily_nfl.domain import GameId, StateSnapshotId, TeamSeasonId
from daily_nfl.pit import PITInputRef, PITValidationResult
from daily_nfl.state.contracts import (
    StateCoverage,
    StateSnapshotEnvelope,
    StateSubjectType,
    StateType,
)
from daily_nfl.state.uncertainty import StateUncertainty


class StateSnapshotIdentityError(ValueError):
    """Raised when a snapshot's deterministic identity does not match its content."""


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("state snapshot timestamps must be timezone-aware")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _json_default(value: object) -> object:
    if isinstance(value, datetime):
        return _iso(value)
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(cast(Any, value))
    raise TypeError(f"unsupported state JSON value: {type(value).__name__}")


def canonical_state_json(value: object) -> str:
    """Serialize state content deterministically and reject non-finite floats."""

    return json.dumps(
        value,
        default=_json_default,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def state_input_payload(input_ref: PITInputRef) -> dict[str, object]:
    """Return the M5-compatible provenance payload used by the state ledger."""

    return {
        "input_kind": input_ref.input_kind.value,
        "input_id": input_ref.input_id,
        "source_table": input_ref.source_table,
        "evidence_id": input_ref.evidence_id,
        "evidence_observation_id": input_ref.evidence_observation_id,
        "provider_id": input_ref.provider_id,
        "provider_revision": input_ref.provider_revision,
        "provider_schema_version": input_ref.provider_schema_version,
        "parser_version": input_ref.parser_version,
        "subject_game_id": (
            str(input_ref.subject_game_id) if input_ref.subject_game_id is not None else None
        ),
        "available_at": _iso(input_ref.available_at),
        "availability_method": input_ref.availability_method.value,
        "availability_confidence": input_ref.availability_confidence.value,
        "effective_at": _iso(input_ref.effective_at),
        "published_at": _iso(input_ref.published_at),
        "observed_at": _iso(input_ref.observed_at),
        "ingested_at": _iso(input_ref.ingested_at),
        "source_game_kickoff": _iso(input_ref.source_game_kickoff),
        "market_quote_at": _iso(input_ref.market_quote_at),
        "season_complete_at": _iso(input_ref.season_complete_at),
        "payload_sha256": input_ref.payload_sha256,
        "raw_sha256": input_ref.raw_sha256,
    }


def _payload_sha256(state_payload: object) -> str:
    encoded = canonical_state_json(state_payload).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _manifest_payload[
    PayloadT
](snapshot: StateSnapshotEnvelope[PayloadT]) -> dict[str, object]:
    return {
        "state_type": snapshot.state_type.value,
        "subject_type": snapshot.subject_type.value,
        "subject_id": snapshot.subject_id,
        "team_season_id": (
            str(snapshot.team_season_id) if snapshot.team_season_id is not None else None
        ),
        "game_id": str(snapshot.game_id) if snapshot.game_id is not None else None,
        "as_of": _iso(snapshot.as_of),
        "calculation_contract": snapshot.calculation_contract,
        "model_version": snapshot.model_version,
        "state_payload": snapshot.state_payload,
        "uncertainty": snapshot.uncertainty,
        "coverage": snapshot.coverage,
        "payload_sha256": snapshot.payload_sha256,
        "pit_validation": snapshot.pit_validation.value,
        "input_observations": [
            state_input_payload(input_ref) for input_ref in snapshot.input_observations
        ],
        "input_state_snapshot_ids": [
            str(snapshot_id) for snapshot_id in snapshot.input_state_snapshot_ids
        ],
    }


def _snapshot_id_from_manifest(manifest: dict[str, object]) -> StateSnapshotId:
    encoded = canonical_state_json(manifest).encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()
    return StateSnapshotId(f"state_{digest}")


def verify_state_snapshot_identity[
    PayloadT
](snapshot: StateSnapshotEnvelope[PayloadT]) -> None:
    """Fail closed if payload hash or deterministic snapshot ID was forged/mutated."""

    expected_payload_sha256 = _payload_sha256(snapshot.state_payload)
    if snapshot.payload_sha256 != expected_payload_sha256:
        raise StateSnapshotIdentityError("state payload SHA-256 does not match state payload")
    expected_snapshot_id = _snapshot_id_from_manifest(_manifest_payload(snapshot))
    if snapshot.snapshot_id != expected_snapshot_id:
        raise StateSnapshotIdentityError(
            "state snapshot ID does not match deterministic semantic manifest"
        )


def build_state_snapshot[
    PayloadT
](
    *,
    state_type: StateType,
    subject_type: StateSubjectType,
    subject_id: str,
    team_season_id: TeamSeasonId | None,
    game_id: GameId | None,
    as_of: datetime,
    calculation_contract: str,
    model_version: str,
    state_payload: PayloadT,
    uncertainty: StateUncertainty,
    coverage: StateCoverage,
    input_observations: tuple[PITInputRef, ...] = (),
    parent_snapshots: tuple[StateSnapshotEnvelope[Any], ...] = (),
    created_at: datetime,
) -> StateSnapshotEnvelope[PayloadT]:
    """Build a content-addressed snapshot from exact PIT inputs and parent states."""

    ordered_inputs = tuple(
        sorted(
            input_observations,
            key=lambda input_ref: (
                input_ref.input_kind.value,
                input_ref.source_table,
                input_ref.input_id,
            ),
        )
    )
    ordered_parents = tuple(
        sorted(parent_snapshots, key=lambda parent: str(parent.snapshot_id))
    )
    parent_ids = [str(parent.snapshot_id) for parent in ordered_parents]
    if len(parent_ids) != len(set(parent_ids)):
        raise ValueError("state snapshot parent states cannot repeat")
    for parent in ordered_parents:
        verify_state_snapshot_identity(parent)
        if parent.as_of > as_of:
            raise ValueError("state snapshot parent cannot be later than child as_of")

    payload_sha256 = _payload_sha256(state_payload)
    provisional = StateSnapshotEnvelope(
        snapshot_id=StateSnapshotId("state_provisional"),
        state_type=state_type,
        subject_type=subject_type,
        subject_id=subject_id,
        team_season_id=team_season_id,
        game_id=game_id,
        as_of=as_of,
        calculation_contract=calculation_contract,
        model_version=model_version,
        state_payload=state_payload,
        uncertainty=uncertainty,
        coverage=coverage,
        input_observations=ordered_inputs,
        input_state_snapshot_ids=tuple(parent.snapshot_id for parent in ordered_parents),
        payload_sha256=payload_sha256,
        pit_validation=PITValidationResult.PASS,
        created_at=created_at,
    )
    snapshot_id = _snapshot_id_from_manifest(_manifest_payload(provisional))
    snapshot = StateSnapshotEnvelope(
        snapshot_id=snapshot_id,
        state_type=state_type,
        subject_type=subject_type,
        subject_id=subject_id,
        team_season_id=team_season_id,
        game_id=game_id,
        as_of=as_of,
        calculation_contract=calculation_contract,
        model_version=model_version,
        state_payload=state_payload,
        uncertainty=uncertainty,
        coverage=coverage,
        input_observations=ordered_inputs,
        input_state_snapshot_ids=tuple(parent.snapshot_id for parent in ordered_parents),
        payload_sha256=payload_sha256,
        pit_validation=PITValidationResult.PASS,
        created_at=created_at,
    )
    verify_state_snapshot_identity(snapshot)
    return snapshot
