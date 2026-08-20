from datetime import UTC, datetime
from pathlib import Path

import pytest

from daily_nfl.domain import AvailabilityConfidence, AvailabilityMethod
from daily_nfl.providers import (
    AcquisitionRequest,
    AcquisitionService,
    DatasetKind,
    FileSystemRawEvidenceStore,
    NflverseAdapter,
    ProviderPayload,
    RawEvidenceCollisionError,
    evidence_id_for,
    sha256_bytes,
)


def _payload(content: bytes = b'{"game":"fixture"}') -> ProviderPayload:
    observed = datetime(2026, 8, 20, 20, 0, tzinfo=UTC)
    return ProviderPayload(
        content=content,
        content_type="application/json; charset=utf-8",
        source_uri="fixture://pbp",
        observed_at=observed,
        available_at=observed,
        availability_method=AvailabilityMethod.OUR_OBSERVATION_TIME,
        availability_confidence=AvailabilityConfidence.HIGH,
        provider_schema_version="fixture-v1",
    )


def test_sha256_and_evidence_identity_are_reproducible() -> None:
    content = b"same evidence"
    digest = sha256_bytes(content)

    assert digest == sha256_bytes(content)
    assert evidence_id_for("nflverse", DatasetKind.PLAY_BY_PLAY, digest) == evidence_id_for(
        "nflverse", DatasetKind.PLAY_BY_PLAY, digest
    )
    assert evidence_id_for("other", DatasetKind.PLAY_BY_PLAY, digest) != evidence_id_for(
        "nflverse", DatasetKind.PLAY_BY_PLAY, digest
    )


def test_filesystem_store_is_content_addressed_and_idempotent(tmp_path: Path) -> None:
    store = FileSystemRawEvidenceStore(tmp_path / "raw")
    payload = _payload()

    first = store.put("nflverse", DatasetKind.PLAY_BY_PLAY, payload)
    second = store.put("nflverse", DatasetKind.PLAY_BY_PLAY, payload)

    assert first == second
    assert first.sha256 == sha256_bytes(payload.content)
    assert first.size_bytes == len(payload.content)
    assert first.relative_path.suffix == ".raw"
    assert (store.root / first.relative_path).read_bytes() == payload.content


def test_store_rejects_unsafe_provider_identifier(tmp_path: Path) -> None:
    store = FileSystemRawEvidenceStore(tmp_path / "raw")

    with pytest.raises(ValueError, match="filesystem-safe"):
        store.put("../escape", DatasetKind.SCHEDULE, _payload())


def test_store_refuses_to_overwrite_tampered_evidence(tmp_path: Path) -> None:
    store = FileSystemRawEvidenceStore(tmp_path / "raw")
    payload = _payload()
    artifact = store.put("nflverse", DatasetKind.SCHEDULE, payload)
    object_path = store.root / artifact.relative_path
    object_path.write_bytes(b"tampered")

    with pytest.raises(RawEvidenceCollisionError, match="collision"):
        store.put("nflverse", DatasetKind.SCHEDULE, payload)

    assert object_path.read_bytes() == b"tampered"


def test_acquisition_service_pairs_and_persists_every_raw_asset(tmp_path: Path) -> None:
    payloads = (_payload(b"season-2025"), _payload(b"season-2026"))
    request = AcquisitionRequest(dataset=DatasetKind.PLAY_BY_PLAY, seasons=(2025, 2026))
    adapter = NflverseAdapter(loader=lambda _: payloads)
    store = FileSystemRawEvidenceStore(tmp_path / "raw")
    service = AcquisitionService(raw_store=store)

    acquired = service.acquire(adapter, request)

    assert acquired.descriptor.provider_id == "nflverse"
    assert acquired.request == request
    assert len(acquired.evidence) == 2
    for payload, evidence in zip(payloads, acquired.evidence, strict=True):
        assert evidence.payload is payload
        assert evidence.ingested_at >= payload.observed_at
        assert (store.root / evidence.artifact.relative_path).read_bytes() == payload.content
