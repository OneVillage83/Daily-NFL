"""Raw-first acquisition orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from daily_nfl.providers.contracts import (
    AcquisitionRequest,
    ProviderAdapter,
    ProviderDescriptor,
    ProviderPayload,
)
from daily_nfl.providers.raw_store import RawEvidenceArtifact, RawEvidenceStore


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


@dataclass(frozen=True, slots=True)
class StoredAcquisition:
    descriptor: ProviderDescriptor
    request: AcquisitionRequest
    evidence: tuple[StoredEvidence, ...]

    def __post_init__(self) -> None:
        if not self.evidence:
            raise ValueError("stored acquisition requires at least one raw evidence object")


@dataclass(frozen=True, slots=True)
class AcquisitionService:
    raw_store: RawEvidenceStore

    def acquire(self, provider: ProviderAdapter, request: AcquisitionRequest) -> StoredAcquisition:
        payloads = provider.acquire(request)
        evidence = tuple(
            StoredEvidence(
                payload=payload,
                artifact=self.raw_store.put(
                    provider.descriptor.provider_id,
                    request.dataset,
                    payload,
                ),
                ingested_at=datetime.now(UTC),
            )
            for payload in payloads
        )
        return StoredAcquisition(
            descriptor=provider.descriptor,
            request=request,
            evidence=evidence,
        )
