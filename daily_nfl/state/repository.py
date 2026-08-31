"""SQLite persistence for deterministic, sealed M7 state snapshots."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import Any

from daily_nfl.domain import StateSnapshotId
from daily_nfl.pit import PITInputRef
from daily_nfl.state.contracts import StateSnapshotEnvelope
from daily_nfl.state.snapshot import (
    _iso,
    canonical_state_json,
    state_input_payload,
    verify_state_snapshot_identity,
)


class StateSnapshotConflictError(RuntimeError):
    """Raised when stored state disagrees with a deterministic snapshot manifest."""


def _parse_db_time(value: object) -> datetime:
    text = str(value)
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise StateSnapshotConflictError("stored state snapshot timestamp is not timezone-aware")
    return parsed.astimezone(UTC)


def state_snapshot_is_sealed(
    connection: sqlite3.Connection,
    snapshot_id: StateSnapshotId | str,
) -> bool:
    row = connection.execute(
        "SELECT 1 FROM state_snapshot_seals WHERE snapshot_id = ?",
        (str(snapshot_id),),
    ).fetchone()
    return row is not None


def require_state_snapshot_sealed(
    connection: sqlite3.Connection,
    snapshot_id: StateSnapshotId | str,
) -> None:
    if not state_snapshot_is_sealed(connection, snapshot_id):
        raise StateSnapshotConflictError(
            f"state snapshot {str(snapshot_id)!r} is missing or unsealed"
        )


def _semantic_row_values[
    PayloadT
](snapshot: StateSnapshotEnvelope[PayloadT]) -> tuple[object, ...]:
    return (
        str(snapshot.snapshot_id),
        snapshot.state_type.value,
        snapshot.subject_type.value,
        snapshot.subject_id,
        str(snapshot.team_season_id) if snapshot.team_season_id is not None else None,
        str(snapshot.game_id) if snapshot.game_id is not None else None,
        _iso(snapshot.as_of),
        snapshot.calculation_contract,
        snapshot.model_version,
        canonical_state_json(snapshot.state_payload),
        canonical_state_json(snapshot.uncertainty),
        canonical_state_json(snapshot.coverage),
        snapshot.payload_sha256,
        snapshot.pit_validation.value,
        len(snapshot.input_observations),
        len(snapshot.input_state_snapshot_ids),
    )


def _insert_row_values[
    PayloadT
](snapshot: StateSnapshotEnvelope[PayloadT]) -> tuple[object, ...]:
    return (*_semantic_row_values(snapshot), _iso(snapshot.created_at))


def _input_row_values(snapshot_id: StateSnapshotId, input_ref: PITInputRef) -> tuple[object, ...]:
    payload = state_input_payload(input_ref)
    return (
        str(snapshot_id),
        payload["input_kind"],
        payload["input_id"],
        payload["source_table"],
        payload["evidence_id"],
        payload["evidence_observation_id"],
        payload["provider_id"],
        payload["provider_revision"],
        payload["provider_schema_version"],
        payload["parser_version"],
        payload["subject_game_id"],
        payload["available_at"],
        payload["availability_method"],
        payload["availability_confidence"],
        payload["effective_at"],
        payload["published_at"],
        payload["observed_at"],
        payload["ingested_at"],
        payload["source_game_kickoff"],
        payload["market_quote_at"],
        payload["season_complete_at"],
        payload["payload_sha256"],
        payload["raw_sha256"],
    )


def _ordered_input_rows[
    PayloadT
](snapshot: StateSnapshotEnvelope[PayloadT]) -> list[tuple[object, ...]]:
    ordered = sorted(
        snapshot.input_observations,
        key=lambda input_ref: (
            input_ref.input_kind.value,
            input_ref.source_table,
            input_ref.input_id,
        ),
    )
    return [_input_row_values(snapshot.snapshot_id, input_ref) for input_ref in ordered]


def _ordered_dependency_rows[
    PayloadT
](snapshot: StateSnapshotEnvelope[PayloadT]) -> list[tuple[str, str]]:
    return [
        (str(snapshot.snapshot_id), str(parent_id))
        for parent_id in sorted(snapshot.input_state_snapshot_ids, key=str)
    ]


def _validate_parent_dependencies[
    PayloadT
](connection: sqlite3.Connection, snapshot: StateSnapshotEnvelope[PayloadT]) -> None:
    for parent_id in snapshot.input_state_snapshot_ids:
        row = connection.execute(
            """
            SELECT parent.as_of, seal.snapshot_id
            FROM state_snapshots parent
            LEFT JOIN state_snapshot_seals seal
              ON seal.snapshot_id = parent.snapshot_id
            WHERE parent.snapshot_id = ?
            """,
            (str(parent_id),),
        ).fetchone()
        if row is None or row[1] is None:
            raise StateSnapshotConflictError(
                f"state dependency parent {str(parent_id)!r} must exist and be sealed"
            )
        if _parse_db_time(row[0]) > snapshot.as_of.astimezone(UTC):
            raise StateSnapshotConflictError(
                f"state dependency parent {str(parent_id)!r} is later than child as_of"
            )


def _verify_existing_snapshot[
    PayloadT
](
    connection: sqlite3.Connection,
    snapshot: StateSnapshotEnvelope[PayloadT],
    existing: sqlite3.Row | tuple[Any, ...],
) -> None:
    require_state_snapshot_sealed(connection, snapshot.snapshot_id)
    if tuple(existing) != _semantic_row_values(snapshot):
        raise StateSnapshotConflictError(
            f"stored state snapshot {str(snapshot.snapshot_id)!r} conflicts with manifest"
        )

    stored_inputs = connection.execute(
        """
        SELECT snapshot_id, input_kind, input_id, source_table, evidence_id,
               evidence_observation_id, provider_id, provider_revision,
               provider_schema_version, parser_version, subject_game_id,
               available_at, availability_method, availability_confidence,
               effective_at, published_at, observed_at, ingested_at,
               source_game_kickoff, market_quote_at, season_complete_at,
               payload_sha256, raw_sha256
        FROM state_snapshot_inputs
        WHERE snapshot_id = ?
        ORDER BY input_kind, source_table, input_id
        """,
        (str(snapshot.snapshot_id),),
    ).fetchall()
    if [tuple(row) for row in stored_inputs] != _ordered_input_rows(snapshot):
        raise StateSnapshotConflictError(
            f"stored state snapshot {str(snapshot.snapshot_id)!r} has conflicting inputs"
        )

    stored_dependencies = connection.execute(
        """
        SELECT snapshot_id, parent_snapshot_id
        FROM state_snapshot_dependencies
        WHERE snapshot_id = ?
        ORDER BY parent_snapshot_id
        """,
        (str(snapshot.snapshot_id),),
    ).fetchall()
    if [tuple(row) for row in stored_dependencies] != _ordered_dependency_rows(snapshot):
        raise StateSnapshotConflictError(
            f"stored state snapshot {str(snapshot.snapshot_id)!r} has conflicting dependencies"
        )


def record_state_snapshot[
    PayloadT
](connection: sqlite3.Connection, snapshot: StateSnapshotEnvelope[PayloadT]) -> None:
    """Persist one deterministic snapshot and exact membership atomically/idempotently."""

    verify_state_snapshot_identity(snapshot)
    existing = connection.execute(
        """
        SELECT snapshot_id, state_type, subject_type, subject_id,
               team_season_id, game_id, as_of, calculation_contract,
               model_version, state_payload_json, uncertainty_json,
               coverage_json, payload_sha256, pit_validation,
               input_count, dependency_count
        FROM state_snapshots
        WHERE snapshot_id = ?
        """,
        (str(snapshot.snapshot_id),),
    ).fetchone()
    if existing is not None:
        _verify_existing_snapshot(connection, snapshot, existing)
        return

    _validate_parent_dependencies(connection, snapshot)

    connection.execute("SAVEPOINT record_state_snapshot")
    try:
        connection.execute(
            """
            INSERT INTO state_snapshots(
                snapshot_id,
                state_type,
                subject_type,
                subject_id,
                team_season_id,
                game_id,
                as_of,
                calculation_contract,
                model_version,
                state_payload_json,
                uncertainty_json,
                coverage_json,
                payload_sha256,
                pit_validation,
                input_count,
                dependency_count,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            _insert_row_values(snapshot),
        )
        connection.executemany(
            """
            INSERT INTO state_snapshot_inputs(
                snapshot_id,
                input_kind,
                input_id,
                source_table,
                evidence_id,
                evidence_observation_id,
                provider_id,
                provider_revision,
                provider_schema_version,
                parser_version,
                subject_game_id,
                available_at,
                availability_method,
                availability_confidence,
                effective_at,
                published_at,
                observed_at,
                ingested_at,
                source_game_kickoff,
                market_quote_at,
                season_complete_at,
                payload_sha256,
                raw_sha256
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            _ordered_input_rows(snapshot),
        )
        connection.executemany(
            """
            INSERT INTO state_snapshot_dependencies(snapshot_id, parent_snapshot_id)
            VALUES (?, ?)
            """,
            _ordered_dependency_rows(snapshot),
        )
        connection.execute(
            "INSERT INTO state_snapshot_seals(snapshot_id) VALUES (?)",
            (str(snapshot.snapshot_id),),
        )
        connection.execute("RELEASE SAVEPOINT record_state_snapshot")
    except BaseException:
        connection.execute("ROLLBACK TO SAVEPOINT record_state_snapshot")
        connection.execute("RELEASE SAVEPOINT record_state_snapshot")
        raise
