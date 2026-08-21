"""Provider-neutral football play normalization for Daily NFL."""

from daily_nfl.normalization.contracts import (
    NflverseGameContext,
    NflversePlayRecord,
    NormalizedPlayBundle,
    ProviderPenaltyRecord,
)
from daily_nfl.normalization.nflverse import (
    PlayNormalizationError,
    classify_play_type,
    normalize_nflverse_play,
)

__all__ = [
    "NflverseGameContext",
    "NflversePlayRecord",
    "NormalizedPlayBundle",
    "PlayNormalizationError",
    "ProviderPenaltyRecord",
    "classify_play_type",
    "normalize_nflverse_play",
]
