"""Deterministic immutable manifests for historical PIT feature inputs."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime

from daily_nfl.pit.contracts import (
    DEFAULT_PIT_POLICY,
    PITFeatureSnapshotSpec,
    PITFeatureScalar,
    PITInputRef,
    PITPolicy,
    PITValidationResult,
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


def _parse_db_time(value: object | None) -> datetime | None:
    if value is None:
        return None
    text = str(value)
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise PITSnapshotConflictError("stored actual kickoff is not timezone-aware")
    return parsed.astimezone(UTC)


def _feature_values_payload(spec: PITFeatureSnapshotSpec) -> dict[str, PITFeatureScalar]:
    return {
        feature.name: feature.value
        for feature in sorted(spec.feature_values, key=lambda feature: feature.name)
    }


def _coverage_payload(spec: PITFeatureSnapshotSpec) -> dict[str, object]:
    present = len(spec.feature_values)
    missing = len(spec.missing_features)
    expected = present + missing
    coverage_fraction = 1.0 if expected == 0 else present / expected
    return {
        "expected_feature_count": expected,
        "missing_feature_count": missing,
        "present_feature_count": present,
        "coverage_fraction": coverage_fraction,
    }


def _input_payload(input_ref: PITInputRef) -> dict[str, object]:
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


@dataclass(frozen=True, slots=True)
class PITSnapshotManifest:
    snapshot_id: str
    manifest_sha256: str
    cutoff: PredictionCutoff
    policy_version: str
    feature_spec: PITFeatureSnapshotSpec
    validation_result: PITValidationResult
    inputs: tuple[PITInputRef, ...]

    def __post_init__(self) -> None:
        if len(self.manifest_sha256) != 64:
            raise ValueError("manifest_sha256 must be a SHA-256 hex digest")
        if any(
            character not in "0123456789abcdefABCDEF"
            for character in self.manifest_sha256
        ):
            raise ValueError("manifest_sha256 must be a SHA-256 hex digest")
        if self.snapshot_id != f"pit_{self.manifest_sha256}":
            raise ValueError("snapshot_id must equal pit_ plus manifest_sha256")
        if not self.policy_version.strip():
            raise ValueError("policy_version cannot be blank")
        if self.validation_result is not PITValidationResult.PASS:
            raise ValueError("persistable PIT snapshot manifests must have validation PASS")


def build_snapshot_manifest(
    *,
    cutoff: PredictionCutoff,
    inputs: tuple[PITInputRef, ...],
    feature_spec: PITFeatureSnapshotSpec,
    policy: PITPolicy = DEFAULT_PIT_POLICY,
) -> PITSnapshotManifest:
    """Validate and hash the exact information/feature set available at a cutoff."""

    assert_no_leakage(inputs, cutoff=cutoff, policy=policy)
    identities = [(input_ref.input_kind, input_ref.input_id) for input_ref in inputs]
    if len(identities) != len(set(identities)):
        raise ValueError("PIT snapshot inputs cannot contain duplicate identities")
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
    feature_values = _feature_values_payload(feature_spec)
    coverage = _coverage_payload(feature_spec)
    missing_features = sorted(feature_spec.missing_features)
    payload = {
        "game_id": str(cutoff.game_id),
        "kickoff": _iso(cutoff.kickoff),
        "prediction_time": _iso(cutoff.prediction_time),
        "horizon": cutoff.horizon.value if cutoff.horizon is not None else None,
        "policy_version": policy.version,
        "feature_contract": feature_spec.feature_contract,
        "feature_version": feature_spec.feature_version,
        "feature_values": feature_values,
        "coverage_report": coverage,
        "missing_features": missing_features,
        "pit_validation_result": PITValidationResult.PASS.value,
        "inputs": [_input_payload(input_ref) for input_ref in ordered_inputs],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(encoded).hexdigest()
    return PITSnapshotManifest(
        snapshot_id=f"pit_{digest}",
        manifest_sha256=digest,
        cutoff=cutoff,
        policy_version=policy.version,
        feature_spec=feature_spec,
        validation_result=PITValidationResult.PASS,
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
        manifest.feature_spec.feature_contract,
        manifest.feature_spec.feature_version,
        json.dumps(
            _feature_values_payload(manifest.feature_spec),
            sort_keys=True,
            separators=(",", ":"),
        ),
        json.dumps(
            _coverage_payload(manifest.feature_spec),
            sort_keys=True,
            separators=(",", ":"),
        ),
        json.dumps(sorted(manifest.feature_spec.missing_features), separators=(",", ":")),
        manifest.validation_result.value,
        len(manifest.inputs),
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
        payload["evidence_observation_id"],
        payload["provider_id"],
        payload["provider_revision"],
        payload["provider_schema_version"],
        payload["parser_version"],
        payload["raw_sha256"],
    )


def _is_sealed(connection: sqlite3.Connection, snapshot_id: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM pit_snapshot_seals WHERE snapshot_id = ?",
        (snapshot_id,),
    ).fetchone()
    return row is not None


def _validate_retrospective_kickoff_boundary(
    connection: sqlite3.Connection,
    manifest: PITSnapshotManifest,
) -> None:
    rows = connection.execute(
        """
        SELECT DISTINCT actual_kickoff
        FROM schedule_observations
        WHERE game_id = ? AND actual_kickoff IS NOT NULL
        """,
        (str(manifest.cutoff.game_id),),
    ).fetchall()
    actual_kickoffs = {
        parsed
        for row in rows
        if (parsed := _parse_db_time(row[0])) is not None
    }
    if len(actual_kickoffs) > 1:
        raise PITSnapshotConflictError(
            "conflicting retrospective actual_kickoff truth prevents PIT snapshot sealing"
        )
    if not actual_kickoffs:
        return
    actual_kickoff = next(iter(actual_kickoffs))
    prediction_time = manifest.cutoff.prediction_time.astimezone(UTC)
    if prediction_time >= actual_kickoff:
        raise PITSnapshotConflictError(
            "pregame PIT prediction_time cannot be at or after actual kickoff"
        )


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
               season_complete_at, payload_sha256, evidence_observation_id,
               provider_id, provider_revision, provider_schema_version,
               parser_version, raw_sha256
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

    _validate_retrospective_kickoff_boundary(connection, manifest)
    existing = connection.execute(
        """
        SELECT snapshot_id, game_id, prediction_time, kickoff, horizon,
               policy_version, manifest_sha256, feature_contract,
               feature_version, feature_values_json, coverage_report_json,
               missing_features_json, pit_validation_result, input_count
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
                manifest_sha256,
                feature_contract,
                feature_version,
                feature_values_json,
                coverage_report_json,
                missing_features_json,
                pit_validation_result,
                input_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                payload_sha256,
                evidence_observation_id,
                provider_id,
                provider_revision,
                provider_schema_version,
                parser_version,
                raw_sha256
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
