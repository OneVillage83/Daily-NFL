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
from daily_nfl.normalization.nflverse_extract import (
    NflverseRowExtractionError,
    extract_nflverse_play_record,
)
from daily_nfl.normalization.persistence import (
    NormalizationProvenance,
    NormalizedPlayConflictError,
    normalized_play_observation_id,
    record_normalized_play,
    serialize_normalized_play,
)

__all__ = [
    "NflverseGameContext",
    "NflversePlayRecord",
    "NflverseRowExtractionError",
    "NormalizationProvenance",
    "NormalizedPlayBundle",
    "NormalizedPlayConflictError",
    "PlayNormalizationError",
    "ProviderPenaltyRecord",
    "classify_play_type",
    "extract_nflverse_play_record",
    "normalize_nflverse_play",
    "normalized_play_observation_id",
    "record_normalized_play",
    "serialize_normalized_play",
]
