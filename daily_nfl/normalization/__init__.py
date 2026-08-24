"""Provider-neutral football play normalization for Daily NFL."""

from daily_nfl.normalization.certified_persistence import (
    NormalizationProvenance,
    NormalizedPlayConflictError,
    normalized_play_observation_id,
    record_normalized_play,
    serialize_normalized_play,
)
from daily_nfl.normalization.contracts import (
    NflverseGameContext,
    NflversePlayRecord,
    NormalizedPlayBundle,
    ProviderParticipantRecord,
    ProviderPenaltyRecord,
)
from daily_nfl.normalization.drive import DriveNormalizationError, normalize_drive
from daily_nfl.normalization.nflverse import (
    PlayNormalizationError,
    classify_play_type,
    normalize_nflverse_play,
)
from daily_nfl.normalization.nflverse_extract import (
    NflverseRowExtractionError,
    extract_nflverse_play_record,
)

__all__ = [
    "DriveNormalizationError",
    "NflverseGameContext",
    "NflversePlayRecord",
    "NflverseRowExtractionError",
    "NormalizationProvenance",
    "NormalizedPlayBundle",
    "NormalizedPlayConflictError",
    "PlayNormalizationError",
    "ProviderParticipantRecord",
    "ProviderPenaltyRecord",
    "classify_play_type",
    "extract_nflverse_play_record",
    "normalize_drive",
    "normalize_nflverse_play",
    "normalized_play_observation_id",
    "record_normalized_play",
    "serialize_normalized_play",
]
