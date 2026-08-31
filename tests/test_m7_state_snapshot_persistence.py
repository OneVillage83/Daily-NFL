from __future__ import annotations

import sqlite3
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from daily_nfl.domain import AvailabilityConfidence, AvailabilityMethod, StateSnapshotId
from daily_nfl.persistence import SCHEMA_VERSION, apply_migrations, connect_database
from daily_nfl.persistence.migrations import MIGRATIONS, current_schema_version
from daily_nfl.pit import PITInputKind, PITInputRef
from daily_nfl.state import (
    StateCoverage,
    StateSnapshotConflictError,
    StateSnapshotEnvelope,
    StateSnapshotIdentityError,
    StateSubjectType,
    StateType,
    StateUncertainty,
    build_state_snapshot,
    record_state_snapshot,
    require_state_snapshot_sealed,
    state_snapshot_is_sealed,
    verify_state_snapshot_identity,
)


type TestPayload = dict[str, float | str]

AS_OF = datetime(2026, 9, 13, 16, 0, tzinfo=UTC)
CREATED_AT = AS_OF + timedelta(minutes=1)


def _coverage() -> StateCoverage:
    return StateCoverage(
        expected_fields=("quality", "style"),
        present_fields=("quality", "style"),
        missing_fields=(),
    )


def _input_ref(input_id: str, *, available_at: datetime | None = None) -> PITInputRef:
    return PITInputRef(
        input_kind=PITInputKind.OTHER,
        input_id=input_id,
        available_at=available_at or AS_OF - timedelta(minutes=5),
        availability_method=AvailabilityMethod.SOURCE_TIMESTAMP,
        availability_confidence=AvailabilityConfidence.HIGH,
        source_table="m7_test_observations",
    )


def _snapshot(
    *,
    quality: float = 0.5,
    inputs: tuple[PITInputRef, ...] = (),
    parents: tuple[StateSnapshotEnvelope[TestPayload], ...] = (),
    as_of: datetime = AS_OF,
    created_at: datetime = CREATED_AT,
) -> StateSnapshotEnvelope[TestPayload]:
    return build_state_snapshot(
        state_type=StateType.TEAM,
        subject_type=StateSubjectType.TEAM_SEASON,
        subject_id="team-subject",
        team_season_id=None,
        game_id=None,
        as_of=as_of,
        calculation_contract="NFL_TEAM_STATE_V1",
        model_version="team-state-test-v1",
        state_payload={"quality": quality, "style": "balanced"},
        uncertainty=StateUncertainty(),
        coverage=_coverage(),
        input_observations=inputs,
        parent_snapshots=parents,
        created_at=created_at,
    )


def _migrated_connection() -> sqlite3.Connection:
    connection = connect_database(":memory:")
    apply_migrations(connection)
    return connection


def test_schema_v8_applies_from_fresh_database() -> None:
    connection = _migrated_connection()
    try:
        assert SCHEMA_VERSION == 8
        assert current_schema_version(connection) == 8
        tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        assert {
            "state_snapshots",
            "state_snapshot_inputs",
            "state_snapshot_dependencies",
            "state_snapshot_seals",
        }.issubset(tables)
    finally:
        connection.close()


def test_schema_v8_upgrades_certified_v7_without_rewriting_history() -> None:
    connection = connect_database(":memory:")
    try:
        for migration in MIGRATIONS[:7]:
            connection.executescript(migration.sql)
            connection.execute(
                "INSERT INTO schema_migrations(version, name) VALUES (?, ?)",
                (migration.version, migration.name),
            )
        assert current_schema_version(connection) == 7
        assert apply_migrations(connection) == 8
        rows = connection.execute(
            "SELECT version, name FROM schema_migrations ORDER BY version"
        ).fetchall()
        assert [(int(row[0]), str(row[1])) for row in rows[:7]] == [
            (migration.version, migration.name) for migration in MIGRATIONS[:7]
        ]
        assert str(rows[7][1]) == "m7_state_snapshot_foundation"
    finally:
        connection.close()


def test_snapshot_identity_is_deterministic_across_input_order_and_created_at() -> None:
    first = _snapshot(
        inputs=(_input_ref("b"), _input_ref("a")),
        created_at=CREATED_AT,
    )
    second = _snapshot(
        inputs=(_input_ref("a"), _input_ref("b")),
        created_at=CREATED_AT + timedelta(hours=2),
    )

    assert first.snapshot_id == second.snapshot_id
    assert first.payload_sha256 == second.payload_sha256
    assert [input_ref.input_id for input_ref in first.input_observations] == ["a", "b"]


def test_snapshot_identity_changes_when_semantic_payload_changes() -> None:
    assert _snapshot(quality=0.5).snapshot_id != _snapshot(quality=0.6).snapshot_id


def test_snapshot_identity_verification_rejects_forged_payload_hash() -> None:
    snapshot = _snapshot()
    forged = replace(snapshot, payload_sha256="f" * 64)
    with pytest.raises(StateSnapshotIdentityError, match="payload SHA-256"):
        verify_state_snapshot_identity(forged)


def test_snapshot_builder_rejects_parent_later_than_child() -> None:
    parent = _snapshot(as_of=AS_OF + timedelta(minutes=1))
    with pytest.raises(ValueError, match="parent cannot be later"):
        _snapshot(parents=(parent,))


def test_record_state_snapshot_persists_exact_membership_and_seal() -> None:
    connection = _migrated_connection()
    try:
        parent = _snapshot(quality=0.4, as_of=AS_OF - timedelta(hours=1))
        record_state_snapshot(connection, parent)
        child = _snapshot(inputs=(_input_ref("obs-1"),), parents=(parent,))
        record_state_snapshot(connection, child)

        assert state_snapshot_is_sealed(connection, child.snapshot_id)
        row = connection.execute(
            "SELECT input_count, dependency_count FROM state_snapshots WHERE snapshot_id = ?",
            (str(child.snapshot_id),),
        ).fetchone()
        assert row is not None
        assert (int(row[0]), int(row[1])) == (1, 1)
        dependency_row = connection.execute(
            "SELECT parent_snapshot_id FROM state_snapshot_dependencies WHERE snapshot_id = ?",
            (str(child.snapshot_id),),
        ).fetchone()
        assert dependency_row is not None
        assert str(dependency_row[0]) == str(parent.snapshot_id)
    finally:
        connection.close()


def test_identical_replay_is_idempotent_even_when_created_at_differs() -> None:
    connection = _migrated_connection()
    try:
        first = _snapshot(inputs=(_input_ref("obs-1"),), created_at=CREATED_AT)
        replay = _snapshot(
            inputs=(_input_ref("obs-1"),),
            created_at=CREATED_AT + timedelta(days=1),
        )
        assert first.snapshot_id == replay.snapshot_id

        record_state_snapshot(connection, first)
        record_state_snapshot(connection, replay)

        count_row = connection.execute(
            "SELECT COUNT(*) FROM state_snapshots WHERE snapshot_id = ?",
            (str(first.snapshot_id),),
        ).fetchone()
        assert count_row is not None
        assert int(count_row[0]) == 1
    finally:
        connection.close()


def test_record_rejects_unsealed_dependency_parent() -> None:
    connection = _migrated_connection()
    try:
        parent = _snapshot(quality=0.4, as_of=AS_OF - timedelta(hours=1))
        child = _snapshot(parents=(parent,))
        with pytest.raises(StateSnapshotConflictError, match="exist and be sealed"):
            record_state_snapshot(connection, child)
    finally:
        connection.close()


def test_sealed_snapshot_rejects_late_membership_extension() -> None:
    connection = _migrated_connection()
    try:
        snapshot = _snapshot()
        record_state_snapshot(connection, snapshot)
        with pytest.raises(sqlite3.IntegrityError, match="after sealing"):
            connection.execute(
                """
                INSERT INTO state_snapshot_inputs(
                    snapshot_id, input_kind, input_id, source_table,
                    available_at, availability_method, availability_confidence
                ) VALUES (?, 'OTHER', 'late-member', 'test', ?, 'SOURCE_TIMESTAMP', 'HIGH')
                """,
                (str(snapshot.snapshot_id), AS_OF.isoformat()),
            )
    finally:
        connection.close()


def test_state_ledger_rows_are_append_only() -> None:
    connection = _migrated_connection()
    try:
        snapshot = _snapshot()
        record_state_snapshot(connection, snapshot)
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE state_snapshots SET model_version = 'mutated' WHERE snapshot_id = ?",
                (str(snapshot.snapshot_id),),
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "DELETE FROM state_snapshot_seals WHERE snapshot_id = ?",
                (str(snapshot.snapshot_id),),
            )
    finally:
        connection.close()


def test_unsealed_snapshot_is_not_consumable() -> None:
    connection = _migrated_connection()
    try:
        with pytest.raises(StateSnapshotConflictError, match="missing or unsealed"):
            require_state_snapshot_sealed(connection, StateSnapshotId("missing"))
    finally:
        connection.close()


def test_existing_storage_conflict_fails_closed() -> None:
    connection = _migrated_connection()
    try:
        snapshot = _snapshot()
        record_state_snapshot(connection, snapshot)
        connection.execute("DROP TRIGGER state_snapshots_no_update")
        connection.execute(
            "UPDATE state_snapshots SET model_version = 'tampered' WHERE snapshot_id = ?",
            (str(snapshot.snapshot_id),),
        )
        with pytest.raises(StateSnapshotConflictError, match="conflicts with manifest"):
            record_state_snapshot(connection, snapshot)
    finally:
        connection.close()


def test_cycle_attempt_is_rejected_by_sealed_membership_boundary() -> None:
    connection = _migrated_connection()
    try:
        first = _snapshot(quality=0.4, as_of=AS_OF - timedelta(hours=2))
        record_state_snapshot(connection, first)
        second = _snapshot(
            quality=0.5,
            as_of=AS_OF - timedelta(hours=1),
            parents=(first,),
        )
        record_state_snapshot(connection, second)

        with pytest.raises(sqlite3.IntegrityError, match="after sealing"):
            connection.execute(
                """
                INSERT INTO state_snapshot_dependencies(snapshot_id, parent_snapshot_id)
                VALUES (?, ?)
                """,
                (str(first.snapshot_id), str(second.snapshot_id)),
            )
    finally:
        connection.close()
