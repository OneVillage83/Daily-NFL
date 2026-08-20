"""Content-addressed immutable raw evidence storage."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from daily_nfl.providers.contracts import DatasetKind, ProviderPayload


class RawEvidenceCollisionError(RuntimeError):
    """Raised if an existing content-addressed object does not match its digest."""


@dataclass(frozen=True, slots=True)
class RawEvidenceArtifact:
    evidence_id: str
    provider_id: str
    dataset: DatasetKind
    sha256: str
    relative_path: Path
    size_bytes: int
    content_type: str


@runtime_checkable
class RawEvidenceStore(Protocol):
    def put(
        self,
        provider_id: str,
        dataset: DatasetKind,
        payload: ProviderPayload,
    ) -> RawEvidenceArtifact: ...


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def evidence_id_for(provider_id: str, dataset: DatasetKind, content_sha256: str) -> str:
    identity = f"{provider_id}\0{dataset.value}\0{content_sha256}".encode()
    return hashlib.sha256(identity).hexdigest()


def _suffix_for(content_type: str) -> str:
    normalized = content_type.partition(";")[0].strip().lower()
    return {
        "application/json": ".json",
        "application/x-ndjson": ".ndjson",
        "text/csv": ".csv",
        "application/csv": ".csv",
        "application/parquet": ".parquet",
        "application/vnd.apache.parquet": ".parquet",
    }.get(normalized, ".bin")


def _validate_provider_id(provider_id: str) -> None:
    if not provider_id.strip():
        raise ValueError("provider_id cannot be blank")
    if provider_id in {".", ".."} or any(character in provider_id for character in ("/", "\\")):
        raise ValueError("provider_id must be a filesystem-safe identifier")


@dataclass(frozen=True, slots=True)
class FileSystemRawEvidenceStore:
    root: Path

    def put(
        self,
        provider_id: str,
        dataset: DatasetKind,
        payload: ProviderPayload,
    ) -> RawEvidenceArtifact:
        _validate_provider_id(provider_id)
        digest = sha256_bytes(payload.content)
        relative_path = (
            Path(provider_id)
            / dataset.value.lower()
            / f"{digest}{_suffix_for(payload.content_type)}"
        )
        object_path = self.root / relative_path
        object_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with object_path.open("xb") as handle:
                handle.write(payload.content)
        except FileExistsError:
            existing = object_path.read_bytes()
            if sha256_bytes(existing) != digest or existing != payload.content:
                raise RawEvidenceCollisionError(
                    f"raw evidence collision at content-addressed path {object_path}"
                ) from None

        return RawEvidenceArtifact(
            evidence_id=evidence_id_for(provider_id, dataset, digest),
            provider_id=provider_id,
            dataset=dataset,
            sha256=digest,
            relative_path=relative_path,
            size_bytes=len(payload.content),
            content_type=payload.content_type,
        )
