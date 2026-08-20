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
    payloads: tuple[ProviderPayload, ...]
    artifacts: tuple[RawEvidenceArtifact, ...]

    def __post_init__(self) -> None:
        if not self.payloads or not self.artifacts:
            raise ValueError("stored acquisition requires raw payloads and artifacts")
        if len(self.payloads) != len(self.artifacts):
            raise ValueError("raw payload and artifact counts must match")


@dataclass(frozen=True, slots=True)
class AcquisitionService:
    raw_store: RawEvidenceStore

    def acquire(self, provider: ProviderAdapter, request: AcquisitionRequest) -> StoredAcquisition:
        payloads = provider.acquire(request)
        artifacts = tuple(
            self.raw_store.put(provider.descriptor.provider_id, request.dataset, payload)
            for payload in payloads
        )
        return StoredAcquisition(
            descriptor=provider.descriptor,
            request=request,
            payloads=payloads,
            artifacts=artifacts,
        )
