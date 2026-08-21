"""Deterministic immutable manifests for historical PIT feature inputs."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime

from daily_nfl.pit.contracts import (
    DEFAULT_PIT_POLICY,
    PITInputRef,
    PITPolicy,
    PredictionCutoff,
)
from daily_nfl.pit.leakage import assert_no_leakage


class PITSnapshotConflictError(RuntimeError):
    """Raised when stored snapshot data disagrees with its deterministic manifest."""


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("snapshot timestamps must be timezone-aware")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _input_payload(input_ref: PITInputRef) -> dict[str, object]:
    return {
        "input_kind": input_ref.input_kind.value,
        "input_id": input_ref.input_id,
        "source_table": input_ref.source_table,
        "evidence_id": input_ref.evidence_id,
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
    }


@dataclass(frozen=True, slots=True)
class PITSnapshotManifest:
    snapshot_id: str
    manifest_sha256: str
    cutoff: PredictionCutoff
    policy_version: str
    inputs: tuple[PITInputRef, ...]

    def __post_init__(self) -> None:
        if not self.snapshot_id.startswith("pit_"):
            raise ValueError("snapshot_id must use the pit_ prefix")
        if len(self.manifest_sha256) != 64:
            raise ValueError("manifest_sha256 must be a SHA-256 hex digest")
        if not self.policy_version.strip():
            raise ValueError("policy_version cannot be blank")


def build_snapshot_manifest(
    *,
    cutoff: PredictionCutoff,
    inputs: tuple[PITInputRef, ...],
    policy: PITPolicy = DEFAULT_PIT_POLICY,
) -> PITSnapshotManifest:
    """Validate and hash the exact information set available at a prediction cutoff."""

    assert_no_leakage(inputs, cutoff=cutoff, policy=policy)
    ordered_inputs = tuple(
        sorted(
            inputs,
            key=lambda input_ref: (
                input_ref.input_kind.value,
                input_ref.source_table,
                input_ref.input_id,
            ),
        )
    )
    payload = {
        "game_id": str(cutoff.game_id),
        "kickoff": _iso(cutoff.kickoff),
        "prediction_time": _iso(cutoff.prediction_time),
        "horizon": cutoff.horizon.value if cutoff.horizon is not None else None,
        "policy_version": policy.version,
        "inputs": [_input_payload(input_ref) for input_ref in ordered_inputs],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(encoded).hexdigest()
    return PITSnapshotManifest(
        snapshot_id=f"pit_{digest}",
        manifest_sha256=digest,
        cutoff=cutoff,
        policy_version=policy.version,
        inputs=ordered_inputs,
    )


def _snapshot_row_values(manifest: PITSnapshotManifest) -> tuple[object, ...]:
    return (
        manifest.snapshot_id,
        str(manifest.cutoff.game_id),
        _iso(manifest.cutoff.prediction_time),
        _iso(manifest.cutoff.kickoff),
        manifest.cutoff.horizon.value if manifest.cutoff.horizon is not None else None,
        manifest.policy_version,
        manifest.manifest_sha256,
    )


def _input_row_values(snapshot_id: str, input_ref: PITInputRef) -> tuple[object, ...]:
    payload = _input_payload(input_ref)
    return (
        snapshot_id,
        payload["input_kind"],
        payload["input_id"],
        payload["source_table"],
        payload["evidence_id"],
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
    )


def _is_sealed(connection: sqlite3.Connection, snapshot_id: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM pit_snapshot_seals WHERE snapshot_id = ?",
        (snapshot_id,),
    ).fetchone()
    return row is not None


def _verify_existing_snapshot(
    connection: sqlite3.Connection,
    manifest: PITSnapshotManifest,
    existing: sqlite3.Row,
) -> None:
    if not _is_sealed(connection, manifest.snapshot_id):
        raise PITSnapshotConflictError(
            f"stored PIT snapshot {manifest.snapshot_id!r} is incomplete/unsealed"
        )
    values = _snapshot_row_values(manifest)
    if tuple(existing) != values:
        raise PITSnapshotConflictError(
            f"stored PIT snapshot {manifest.snapshot_id!r} conflicts with manifest"
        )
    stored_inputs = connection.execute(
        """
        SELECT snapshot_id, input_kind, input_id, source_table, evidence_id,
               subject_game_id, available_at, availability_method,
               availability_confidence, effective_at, published_at,
               observed_at, ingested_at, source_game_kickoff, market_quote_at,
               season_complete_at, payload_sha256
        FROM pit_snapshot_inputs
        WHERE snapshot_id = ?
        ORDER BY input_kind, source_table, input_id
        """,
        (manifest.snapshot_id,),
    ).fetchall()
    expected_inputs = [
        _input_row_values(manifest.snapshot_id, input_ref)
        for input_ref in manifest.inputs
    ]
    if [tuple(row) for row in stored_inputs] != expected_inputs:
        raise PITSnapshotConflictError(
            f"stored PIT snapshot {manifest.snapshot_id!r} has conflicting inputs"
        )


def record_snapshot(
    connection: sqlite3.Connection,
    manifest: PITSnapshotManifest,
) -> None:
    """Persist a validated, sealed manifest idempotently and atomically."""

    existing = connection.execute(
        """
        SELECT snapshot_id, game_id, prediction_time, kickoff, horizon,
               policy_version, manifest_sha256
        FROM pit_snapshots
        WHERE snapshot_id = ?
        """,
        (manifest.snapshot_id,),
    ).fetchone()
    if existing is not None:
        _verify_existing_snapshot(connection, manifest, existing)
        return

    connection.execute("SAVEPOINT record_pit_snapshot")
    try:
        connection.execute(
            """
            INSERT INTO pit_snapshots(
                snapshot_id,
                game_id,
                prediction_time,
                kickoff,
                horizon,
                policy_version,
                manifest_sha256
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            _snapshot_row_values(manifest),
        )
        connection.executemany(
            """
            INSERT INTO pit_snapshot_inputs(
                snapshot_id,
                input_kind,
                input_id,
                source_table,
                evidence_id,
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
                payload_sha256
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                _input_row_values(manifest.snapshot_id, input_ref)
                for input_ref in manifest.inputs
            ],
        )
        connection.execute(
            "INSERT INTO pit_snapshot_seals(snapshot_id) VALUES (?)",
            (manifest.snapshot_id,),
        )
        connection.execute("RELEASE SAVEPOINT record_pit_snapshot")
    except BaseException:
        connection.execute("ROLLBACK TO SAVEPOINT record_pit_snapshot")
        connection.execute("RELEASE SAVEPOINT record_pit_snapshot")
        raise
