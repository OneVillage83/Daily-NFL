from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from daily_nfl.domain import AvailabilityConfidence, AvailabilityMethod
from daily_nfl.persistence import apply_migrations, open_database
from daily_nfl.providers import (
    AcquisitionRequest,
    AcquisitionService,
    DatasetKind,
    FileSystemRawEvidenceStore,
    NFLVERSE_DESCRIPTOR,
    NflverseAdapter,
    ProviderDescriptor,
    ProviderMetadataConflictError,
    ProviderPayload,
    StoredAcquisition,
    record_provider,
    record_stored_acquisition,
)


def _payload(observed_at: datetime) -> ProviderPayload:
    return ProviderPayload(
        content=b"same-upstream-bytes",
        content_type="application/octet-stream",
        source_uri="https://example.test/games.parquet",
        observed_at=observed_at,
        available_at=observed_at,
        availability_method=AvailabilityMethod.OUR_OBSERVATION_TIME,
        availability_confidence=AvailabilityConfidence.HIGH,
        provider_schema_version="fixture-v1",
    )


def _acquire(tmp_path: Path, payload: ProviderPayload) -> StoredAcquisition:
    request = AcquisitionRequest(dataset=DatasetKind.SCHEDULE)
    adapter = NflverseAdapter(loader=lambda _: (payload,))
    service = AcquisitionService(FileSystemRawEvidenceStore(tmp_path / "raw"))
    return service.acquire(adapter, request)


def test_stored_acquisition_records_provider_and_raw_evidence(tmp_path: Path) -> None:
    database = tmp_path / "daily-nfl.db"
    observed = datetime(2026, 8, 20, 20, 0, tzinfo=UTC)
    acquisition = _acquire(tmp_path, _payload(observed))

    with open_database(database) as connection:
        apply_migrations(connection)
        record_stored_acquisition(connection, acquisition)
        connection.commit()

        provider = connection.execute(
            "SELECT name, parser_version FROM providers WHERE provider_id = ?",
            ("nflverse",),
        ).fetchone()
        evidence = connection.execute(
            """
            SELECT endpoint_category, sha256, object_path, observed_at, available_at
            FROM raw_evidence
            """
        ).fetchone()

    assert provider is not None
    assert provider[0] == NFLVERSE_DESCRIPTOR.name
    assert provider[1] == NFLVERSE_DESCRIPTOR.parser_version
    assert evidence is not None
    assert evidence[0] == DatasetKind.SCHEDULE.value
    assert evidence[1] == acquisition.evidence[0].artifact.sha256
    assert str(evidence[2]).endswith(".raw")
    assert evidence[3] == "2026-08-20T20:00:00Z"
    assert evidence[4] == "2026-08-20T20:00:00Z"


def test_same_content_can_be_reobserved_without_duplicate_raw_row(tmp_path: Path) -> None:
    database = tmp_path / "daily-nfl.db"
    first_observed = datetime(2026, 8, 20, 20, 0, tzinfo=UTC)
    second_observed = first_observed + timedelta(hours=1)
    first = _acquire(tmp_path, _payload(first_observed))
    second = _acquire(tmp_path, _payload(second_observed))

    assert first.evidence[0].artifact.evidence_id == second.evidence[0].artifact.evidence_id

    with open_database(database) as connection:
        apply_migrations(connection)
        record_stored_acquisition(connection, first)
        record_stored_acquisition(connection, second)
        connection.commit()

        row = connection.execute(
            "SELECT COUNT(*), MIN(observed_at) FROM raw_evidence"
        ).fetchone()

    assert row is not None
    assert row[0] == 1
    assert row[1] == "2026-08-20T20:00:00Z"


def test_provider_id_cannot_be_reused_for_different_provider(tmp_path: Path) -> None:
    database = tmp_path / "daily-nfl.db"
    conflicting = ProviderDescriptor(
        provider_id="nflverse",
        name="Not nflverse",
        provider_type=NFLVERSE_DESCRIPTOR.provider_type,
        parser_version="v1",
    )

    with open_database(database) as connection:
        apply_migrations(connection)
        record_provider(connection, NFLVERSE_DESCRIPTOR)

        with pytest.raises(ProviderMetadataConflictError, match="different provider"):
            record_provider(connection, conflicting)
