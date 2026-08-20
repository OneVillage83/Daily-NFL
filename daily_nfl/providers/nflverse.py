"""Initial nflverse/nflreadpy provider boundary.

The concrete nflreadpy loader is intentionally injected. M3 freezes the
provider contract before binding Daily NFL to a particular nflreadpy API
surface or dataset shape.
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


NflverseLoader = Callable[[AcquisitionRequest], ProviderPayload]


NFLVERSE_DESCRIPTOR = ProviderDescriptor(
    provider_id="nflverse",
    name="nflverse / nflreadpy",
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
    """Provider adapter whose concrete loader is supplied at the integration edge."""

    loader: NflverseLoader
    descriptor: ProviderDescriptor = NFLVERSE_DESCRIPTOR

    def acquire(self, request: AcquisitionRequest) -> ProviderPayload:
        if self.descriptor.capability_for(request.dataset) is None:
            raise UnsupportedDatasetError(
                f"nflverse adapter does not declare support for {request.dataset.value}"
            )
        return self.loader(request)
