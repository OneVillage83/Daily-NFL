"""Exact-byte acquisition for selected nflverse-data release assets."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.request import Request, urlopen

from daily_nfl.domain import AvailabilityConfidence, AvailabilityMethod
from daily_nfl.providers.contracts import AcquisitionRequest, DatasetKind, ProviderPayload

NFLVERSE_RELEASE_BASE = "https://github.com/nflverse/nflverse-data/releases/download"


class UnsupportedRawAssetMappingError(ValueError):
    """Raised when M3 has not yet mapped a dataset to immutable upstream assets."""


@dataclass(frozen=True, slots=True)
class NflverseAsset:
    dataset: DatasetKind
    url: str
    season: int | None = None


def resolve_nflverse_assets(request: AcquisitionRequest) -> tuple[NflverseAsset, ...]:
    """Resolve a logical acquisition to exact upstream release assets."""
    if request.dataset is DatasetKind.SCHEDULE:
        return (
            NflverseAsset(
                dataset=request.dataset,
                url=f"{NFLVERSE_RELEASE_BASE}/schedules/games.parquet",
            ),
        )

    if request.dataset is DatasetKind.PLAY_BY_PLAY:
        if not request.seasons:
            raise ValueError("play-by-play raw acquisition requires explicit seasons")
        if any(season < 1999 for season in request.seasons):
            raise ValueError("nflverse play-by-play is available from the 1999 season")
        return tuple(
            NflverseAsset(
                dataset=request.dataset,
                season=season,
                url=(
                    f"{NFLVERSE_RELEASE_BASE}/pbp/"
                    f"play_by_play_{season}.parquet"
                ),
            )
            for season in request.seasons
        )

    raise UnsupportedRawAssetMappingError(
        f"exact raw-asset mapping is not implemented for {request.dataset.value}"
    )


@dataclass(frozen=True, slots=True)
class NflverseHttpLoader:
    """Download exact nflverse release bytes without parsing them first."""

    user_agent: str = "Daily-NFL/0.1 raw-evidence-acquisition"
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        if not self.user_agent.strip():
            raise ValueError("user_agent cannot be blank")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

    def __call__(self, request: AcquisitionRequest) -> tuple[ProviderPayload, ...]:
        return tuple(self._download(asset) for asset in resolve_nflverse_assets(request))

    def _download(self, asset: NflverseAsset) -> ProviderPayload:
        request = Request(
            asset.url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "application/octet-stream, application/vnd.apache.parquet, */*",
            },
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310
            content = response.read()
            content_type = response.headers.get_content_type() or "application/octet-stream"

        observed_at = datetime.now(UTC)
        return ProviderPayload(
            content=content,
            content_type=content_type,
            source_uri=asset.url,
            observed_at=observed_at,
            available_at=observed_at,
            availability_method=AvailabilityMethod.OUR_OBSERVATION_TIME,
            availability_confidence=AvailabilityConfidence.HIGH,
        )
