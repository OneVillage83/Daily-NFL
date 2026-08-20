"""Raw-first acquisition orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from daily_nfl.providers.contracts import (
    AcquisitionRequest,
    ProviderAdapter,
    ProviderDescriptor,
    ProviderPayload,
)
from daily_nfl.providers.raw_store import RawEvidenceArtifact, RawEvidenceStore


@dataclass(frozen=True, slots=True)
class StoredAcquisition:
    descriptor: ProviderDescriptor
    request: AcquisitionRequest
    payload: ProviderPayload
    artifact: RawEvidenceArtifact


@dataclass(frozen=True, slots=True)
class AcquisitionService:
    raw_store: RawEvidenceStore

    def acquire(self, provider: ProviderAdapter, request: AcquisitionRequest) -> StoredAcquisition:
        payload = provider.acquire(request)
        artifact = self.raw_store.put(provider.descriptor.provider_id, request.dataset, payload)
        return StoredAcquisition(
            descriptor=provider.descriptor,
            request=request,
            payload=payload,
            artifact=artifact,
        )
