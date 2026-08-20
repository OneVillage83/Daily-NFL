"""Daily NFL external-provider acquisition boundary."""

from daily_nfl.providers.contracts import (
    AcquisitionRequest,
    CostClass,
    DatasetKind,
    NormalizedAcquisition,
    PointInTimeFidelity,
    ProviderAdapter,
    ProviderCapability,
    ProviderDescriptor,
    ProviderPayload,
)
from daily_nfl.providers.nflverse import (
    NFLVERSE_DESCRIPTOR,
    NflverseAdapter,
    UnsupportedDatasetError,
)
from daily_nfl.providers.raw_store import (
    FileSystemRawEvidenceStore,
    RawEvidenceArtifact,
    RawEvidenceCollisionError,
    RawEvidenceStore,
    evidence_id_for,
    sha256_bytes,
)
from daily_nfl.providers.registry import ProviderRegistrationError, ProviderRegistry
from daily_nfl.providers.service import AcquisitionService, StoredAcquisition

__all__ = [
    "AcquisitionRequest",
    "AcquisitionService",
    "CostClass",
    "DatasetKind",
    "FileSystemRawEvidenceStore",
    "NFLVERSE_DESCRIPTOR",
    "NflverseAdapter",
    "NormalizedAcquisition",
    "PointInTimeFidelity",
    "ProviderAdapter",
    "ProviderCapability",
    "ProviderDescriptor",
    "ProviderPayload",
    "ProviderRegistrationError",
    "ProviderRegistry",
    "RawEvidenceArtifact",
    "RawEvidenceCollisionError",
    "RawEvidenceStore",
    "StoredAcquisition",
    "UnsupportedDatasetError",
    "evidence_id_for",
    "sha256_bytes",
]
