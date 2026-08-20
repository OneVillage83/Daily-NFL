from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from daily_nfl.providers import (
    AcquisitionRequest,
    DatasetKind,
    NflverseHttpLoader,
    UnsupportedRawAssetMappingError,
    resolve_nflverse_assets,
)


def test_schedule_resolves_to_canonical_release_asset() -> None:
    assets = resolve_nflverse_assets(AcquisitionRequest(dataset=DatasetKind.SCHEDULE))

    assert len(assets) == 1
    assert assets[0].season is None
    assert assets[0].url.endswith("/schedules/games.parquet")


def test_multi_season_pbp_resolves_one_raw_asset_per_season() -> None:
    assets = resolve_nflverse_assets(
        AcquisitionRequest(dataset=DatasetKind.PLAY_BY_PLAY, seasons=(2024, 2025))
    )

    assert [asset.season for asset in assets] == [2024, 2025]
    assert assets[0].url.endswith("/pbp/play_by_play_2024.parquet")
    assert assets[1].url.endswith("/pbp/play_by_play_2025.parquet")


def test_pbp_requires_explicit_supported_seasons() -> None:
    with pytest.raises(ValueError, match="requires explicit seasons"):
        resolve_nflverse_assets(AcquisitionRequest(dataset=DatasetKind.PLAY_BY_PLAY))

    with pytest.raises(ValueError, match="available from the 1999 season"):
        resolve_nflverse_assets(
            AcquisitionRequest(dataset=DatasetKind.PLAY_BY_PLAY, seasons=(1998,))
        )


def test_unmapped_dataset_fails_closed() -> None:
    with pytest.raises(UnsupportedRawAssetMappingError, match="not implemented"):
        resolve_nflverse_assets(AcquisitionRequest(dataset=DatasetKind.INJURY))


def test_http_loader_returns_exact_response_bytes_without_parsing() -> None:
    response = MagicMock()
    response.__enter__.return_value = response
    response.read.return_value = b"raw-parquet-bytes"
    response.headers.get_content_type.return_value = "application/octet-stream"

    before = datetime.now(UTC)
    with patch("daily_nfl.providers.nflverse_http.urlopen", return_value=response):
        payloads = NflverseHttpLoader().acquire(
            AcquisitionRequest(dataset=DatasetKind.SCHEDULE)
        ) if False else NflverseHttpLoader()(AcquisitionRequest(dataset=DatasetKind.SCHEDULE))
    after = datetime.now(UTC)

    assert len(payloads) == 1
    payload = payloads[0]
    assert payload.content == b"raw-parquet-bytes"
    assert payload.source_uri is not None
    assert payload.source_uri.endswith("/schedules/games.parquet")
    assert before <= payload.observed_at <= after
    assert payload.available_at == payload.observed_at
