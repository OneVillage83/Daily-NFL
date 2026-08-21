"""Raw-first acquisition orchestration."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime

from daily_nfl.providers.contracts import (
    AcquisitionRequest,
    ProviderAdapter,
    ProviderDescriptor,
    ProviderPayload,
)
from daily_nfl.providers.raw_store import RawEvidenceArtifact, RawEvidenceStore, sha256_bytes


class UnsupportedProviderCapabilityError(ValueError):
    """Raised before acquisition when a provider did not declare the requested dataset."""


def _utc_timestamp_key(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("observation identity timestamps must be timezone-aware")
    return value.astimezone(UTC).isoformat(timespec="microseconds")


def evidence_observation_id_for(
    evidence_id: str,
    source_uri: str | None,
    observed_at: datetime,
) -> str:
    """Derive identity for one observation of an immutable raw content object."""

    if not evidence_id.strip():
        raise ValueError("evidence_id cannot be blank")
    payload = "\0".join(
        (evidence_id, source_uri or "", _utc_timestamp_key(observed_at))
    ).encode()
    return f"reo_{hashlib.sha256(payload).hexdigest()}"


@dataclass(frozen=True, slots=True)
class StoredEvidence:
    payload: ProviderPayload
    artifact: RawEvidenceArtifact
    ingested_at: datetime

    def __post_init__(self) -> None:
        if self.ingested_at.tzinfo is None or self.ingested_at.utcoffset() is None:
            raise ValueError("ingested_at must be timezone-aware")
        if self.ingested_at < self.payload.observed_at:
            raise ValueError("ingested_at cannot precede observed_at")
        if self.artifact.sha256 != sha256_bytes(self.payload.content):
            raise ValueError("stored artifact checksum does not match provider payload")
        if self.artifact.size_bytes != len(self.payload.content):
            raise ValueError("stored artifact size does not match provider payload")
        if self.artifact.content_type != self.payload.content_type:
            raise ValueError("stored artifact content_type does not match provider payload")

    @property
    def evidence_observation_id(self) -> str:
        return evidence_observation_id_for(
            self.artifact.evidence_id,
            self.payload.source_uri,
            self.payload.observed_at,
        )


@dataclass(frozen=True, slots=True)
class StoredAcquisition:
    descriptor: ProviderDescriptor
    request: AcquisitionRequest
    evidence: tuple[StoredEvidence, ...]

    def __post_init__(self) -> None:
        if not self.evidence:
            raise ValueError("stored acquisition requires at least one raw evidence object")
        if self.descriptor.capability_for(self.request.dataset) is None:
            raise UnsupportedProviderCapabilityError(
                f"provider {self.descriptor.provider_id!r} does not declare "
                f"{self.request.dataset.value}"
            )
        for item in self.evidence:
            if item.artifact.provider_id != self.descriptor.provider_id:
                raise ValueError("stored artifact provider does not match acquisition provider")
            if item.artifact.dataset is not self.request.dataset:
                raise ValueError("stored artifact dataset does not match acquisition request")


@dataclass(frozen=True, slots=True)
class AcquisitionService:
    raw_store: RawEvidenceStore

    def acquire(self, provider: ProviderAdapter, request: AcquisitionRequest) -> StoredAcquisition:
        descriptor = provider.descriptor
        if descriptor.capability_for(request.dataset) is None:
            raise UnsupportedProviderCapabilityError(
                f"provider {descriptor.provider_id!r} does not declare {request.dataset.value}"
            )

        payloads = provider.acquire(request)
        evidence = tuple(
            StoredEvidence(
                payload=payload,
                artifact=self.raw_store.put(
                    descriptor.provider_id,
                    request.dataset,
                    payload,
                ),
                ingested_at=datetime.now(UTC),
            )
            for payload in payloads
        )
        return StoredAcquisition(
            descriptor=descriptor,
            request=request,
            evidence=evidence,
        )
