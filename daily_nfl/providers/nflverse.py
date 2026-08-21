"""Initial nflverse provider boundary.

The concrete loader is injected. Daily NFL acquires exact upstream artifacts
before parsing them, while nflreadpy remains a schema/API reference and parity
validation tool rather than the owner of raw evidence.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from daily_nfl.providers.contracts import (
    AcquisitionRequest,
    CostClass,
    DatasetKind,
    HistoricalAvailability,
    PointInTimeFidelity,
    ProviderCapability,
    ProviderDescriptor,
    ProviderPayload,
    ReliabilityTier,
)


class UnsupportedDatasetError(ValueError):
    """Raised when an adapter is asked for a dataset it did not declare."""


NflverseLoader = Callable[[AcquisitionRequest], tuple[ProviderPayload, ...]]

_NFLVERSE_DATA_LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
_NFLVERSE_ATTRIBUTION = "nflverse"


NFLVERSE_DESCRIPTOR = ProviderDescriptor(
    provider_id="nflverse",
    name="nflverse / nflreadpy ecosystem",
    provider_type="OPEN_SOURCE_FOUNDATION",
    parser_version="NFLVERSE_ADAPTER_V1",
    capabilities=(
        ProviderCapability(
            dataset=DatasetKind.SCHEDULE,
            point_in_time_fidelity=PointInTimeFidelity.PARTIAL,
            cadence="UPSTREAM_AUTOMATION",
            license_class="CREATIVE_COMMONS_ATTRIBUTION",
            cost_class=CostClass.FREE,
            earliest_season=1999,
            entity_coverage=("GAME", "TEAM", "VENUE"),
            field_coverage=(
                "SCHEDULE_STATE",
                "TEAM_ASSIGNMENT",
                "VENUE_CONTEXT",
                "GAME_RESULT",
            ),
            expected_latency="UPSTREAM_AUTOMATION",
            historical_availability=HistoricalAvailability.ARCHIVAL,
            reliability_tier=ReliabilityTier.TIER_1,
            reliability_note="Community-maintained nflverse-data release artifact",
            license_id="CC-BY-4.0",
            license_url=_NFLVERSE_DATA_LICENSE_URL,
            attribution_required=True,
            attribution_text=_NFLVERSE_ATTRIBUTION,
        ),
        ProviderCapability(
            dataset=DatasetKind.PLAY_BY_PLAY,
            point_in_time_fidelity=PointInTimeFidelity.PARTIAL,
            cadence="DAILY_IN_SEASON",
            license_class="CREATIVE_COMMONS_ATTRIBUTION",
            cost_class=CostClass.FREE,
            earliest_season=1999,
            entity_coverage=("GAME", "DRIVE", "PLAY", "PLAYER", "TEAM"),
            field_coverage=(
                "PLAY_STATE",
                "PLAY_EXECUTION",
                "PLAY_RESULT",
                "PENALTY",
                "PARTICIPATION_HINTS",
            ),
            expected_latency="PROCESSED_DAILY_IN_SEASON",
            historical_availability=HistoricalAvailability.ARCHIVAL,
            reliability_tier=ReliabilityTier.TIER_1,
            reliability_note="Community-maintained nflverse-data release artifact",
            license_id="CC-BY-4.0",
            license_url=_NFLVERSE_DATA_LICENSE_URL,
            attribution_required=True,
            attribution_text=_NFLVERSE_ATTRIBUTION,
        ),
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
