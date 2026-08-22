import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from daily_nfl.persistence import SCHEMA_VERSION, apply_migrations, open_database
from daily_nfl.persistence.migrations import MIGRATIONS
from daily_nfl.providers import (
    NFLVERSE_DESCRIPTOR,
    AcquisitionRequest,
    AcquisitionService,
    DatasetKind,
    FileSystemRawEvidenceStore,
    ProviderDescriptor,
    ProviderPayload,
    UnsupportedProviderCapabilityError,
    capability_id_for,
)


def _apply_through_v4(connection: sqlite3.Connection) -> None:
    for migration in MIGRATIONS:
        if migration.version > 4:
            break
        escaped_name = migration.name.replace("'", "''")
        connection.executescript(
            "BEGIN IMMEDIATE;\n"
            f"{migration.sql}\n"
            "INSERT INTO schema_migrations(version, name) "
            f"VALUES ({migration.version}, '{escaped_name}');\n"
            "COMMIT;"
        )


def test_v5_migration_preserves_certified_m2_raw_evidence(tmp_path: Path) -> None:
    database = tmp_path / "m2-to-m3.db"

    with open_database(database) as connection:
        _apply_through_v4(connection)
        connection.execute(
            """
            INSERT INTO providers(provider_id, name, provider_type)
            VALUES ('legacy-provider', 'Legacy Provider', 'TEST')
            """
        )
        connection.execute(
            """
            INSERT INTO raw_evidence(
                evidence_id, provider_id, endpoint_category, content_type,
                sha256, object_path, ingested_at, available_at,
                availability_method, availability_confidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "legacy-evidence",
                "legacy-provider",
                "SCHEDULE",
                "application/octet-stream",
                "abc123",
                "legacy/schedule/abc123.raw",
                "2026-08-20T20:00:01Z",
                "2026-08-20T20:00:00Z",
                "OUR_OBSERVATION_TIME",
                "HIGH",
            ),
        )
        connection.commit()

        assert apply_migrations(connection) == SCHEMA_VERSION
        raw = connection.execute(
            "SELECT provider_id, sha256, object_path FROM raw_evidence WHERE evidence_id = ?",
            ("legacy-evidence",),
        ).fetchone()
        tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }

    assert raw is not None
    assert tuple(raw) == (
        "legacy-provider",
        "abc123",
        "legacy/schedule/abc123.raw",
    )
    assert {
        "provider_capability_snapshots",
        "raw_evidence_observations",
    }.issubset(tables)


def test_capability_snapshot_identity_changes_with_material_metadata() -> None:
    schedule = NFLVERSE_DESCRIPTOR.capability_for(DatasetKind.SCHEDULE)
    pbp = NFLVERSE_DESCRIPTOR.capability_for(DatasetKind.PLAY_BY_PLAY)

    assert schedule is not None
    assert pbp is not None
    first = capability_id_for("nflverse", schedule)
    second = capability_id_for("nflverse", schedule)
    other_dataset = capability_id_for("nflverse", pbp)

    assert first == second
    assert first != other_dataset


def test_acquisition_service_rejects_undeclared_capability_before_provider_call(
    tmp_path: Path,
) -> None:
    calls: list[AcquisitionRequest] = []

    class Adapter:
        descriptor = ProviderDescriptor(
            provider_id="empty",
            name="Empty",
            provider_type="TEST",
            parser_version="v1",
        )

        def acquire(self, request: AcquisitionRequest) -> tuple[ProviderPayload, ...]:
            calls.append(request)
            observed = datetime(2026, 8, 20, 20, 0, tzinfo=UTC)
            raise AssertionError(f"provider should not be called at {observed.isoformat()}")

    service = AcquisitionService(FileSystemRawEvidenceStore(tmp_path / "raw"))

    with pytest.raises(UnsupportedProviderCapabilityError, match="does not declare"):
        service.acquire(Adapter(), AcquisitionRequest(dataset=DatasetKind.SCHEDULE))

    assert calls == []
