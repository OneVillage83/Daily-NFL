"""Initial nflverse provider boundary.

The concrete loader is injected. Daily NFL acquires exact upstream artifacts
before parsing them, while nflreadpy remains a schema/API reference and later
parity-validation tool rather than the owner of raw evidence.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from daily_nfl.providers.contracts import (
    AcquisitionRequest,
    CostClass,
    DatasetKind,
    PointInTimeFidelity,
    ProviderCapability,
    ProviderDescriptor,
    ProviderPayload,
)


class UnsupportedDatasetError(ValueError):
    """Raised when an adapter is asked for a dataset it did not declare."""


NflverseLoader = Callable[[AcquisitionRequest], tuple[ProviderPayload, ...]]


NFLVERSE_DESCRIPTOR = ProviderDescriptor(
    provider_id="nflverse",
    name="nflverse / nflreadpy ecosystem",
    provider_type="OPEN_SOURCE_FOUNDATION",
    parser_version="NFLVERSE_ADAPTER_V1",
    capabilities=tuple(
        ProviderCapability(
            dataset=dataset,
            point_in_time_fidelity=PointInTimeFidelity.UNKNOWN,
            cadence="UPSTREAM_DEFINED",
            license_class="UPSTREAM_DATASET_TERMS",
            cost_class=CostClass.FREE,
        )
        for dataset in (
            DatasetKind.SCHEDULE,
            DatasetKind.PLAY_BY_PLAY,
            DatasetKind.ROSTER,
            DatasetKind.PARTICIPATION,
            DatasetKind.PLAYER_STATS,
            DatasetKind.TEAM_STATS,
            DatasetKind.INJURY,
            DatasetKind.DEPTH_CHART,
        )
    ),
)


@dataclass(frozen=True, slots=True)
class NflverseAdapter:
    """Provider adapter whose concrete raw loader lives at the integration edge."""

    loader: NflverseLoader
    descriptor: ProviderDescriptor = NFLVERSE_DESCRIPTOR

    def acquire(self, request: AcquisitionRequest) -> tuple[ProviderPayload, ...]:
        if self.descriptor.capability_for(request.dataset) is None:
            raise UnsupportedDatasetError(
                f"nflverse adapter does not declare support for {request.dataset.value}"
            )
        payloads = self.loader(request)
        if not payloads:
            raise ValueError("provider loader returned no raw payloads")
        return payloads
