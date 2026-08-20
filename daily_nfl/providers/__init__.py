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
from daily_nfl.providers.metadata import (
    ProviderMetadataConflictError,
    RawEvidenceMetadataConflictError,
    record_provider,
    record_stored_acquisition,
)
from daily_nfl.providers.nflverse import (
    NFLVERSE_DESCRIPTOR,
    NflverseAdapter,
    UnsupportedDatasetError,
)
from daily_nfl.providers.nflverse_http import (
    NFLVERSE_RELEASE_BASE,
    NflverseAsset,
    NflverseHttpLoader,
    UnsupportedRawAssetMappingError,
    resolve_nflverse_assets,
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
from daily_nfl.providers.service import AcquisitionService, StoredAcquisition, StoredEvidence

__all__ = [
    "AcquisitionRequest",
    "AcquisitionService",
    "CostClass",
    "DatasetKind",
    "FileSystemRawEvidenceStore",
    "NFLVERSE_DESCRIPTOR",
    "NFLVERSE_RELEASE_BASE",
    "NflverseAdapter",
    "NflverseAsset",
    "NflverseHttpLoader",
    "NormalizedAcquisition",
    "PointInTimeFidelity",
    "ProviderAdapter",
    "ProviderCapability",
    "ProviderDescriptor",
    "ProviderMetadataConflictError",
    "ProviderPayload",
    "ProviderRegistrationError",
    "ProviderRegistry",
    "RawEvidenceArtifact",
    "RawEvidenceCollisionError",
    "RawEvidenceMetadataConflictError",
    "RawEvidenceStore",
    "StoredAcquisition",
    "StoredEvidence",
    "UnsupportedDatasetError",
    "UnsupportedRawAssetMappingError",
    "evidence_id_for",
    "record_provider",
    "record_stored_acquisition",
    "resolve_nflverse_assets",
    "sha256_bytes",
]
