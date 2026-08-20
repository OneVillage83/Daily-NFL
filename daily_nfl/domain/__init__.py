"""Provider-neutral Daily NFL domain contracts.

This package describes football concepts. Provider adapters and persistence
layers may populate these objects, but they must not redefine their semantics.
"""

from daily_nfl.domain.enums import (
    AvailabilityConfidence,
    AvailabilityMethod,
    GameResultType,
    GameStatus,
    ParticipationSide,
    PenaltyDisposition,
    PlayDesignModifier,
    PlayEventType,
    PlayType,
    SeasonPhase,
)
from daily_nfl.domain.game import Game, GameResult, RulesetVersion, SeasonWeek
from daily_nfl.domain.identity import Franchise, Person, Player, TeamSeason
from daily_nfl.domain.ids import (
    DriveId,
    EventId,
    FranchiseId,
    GameId,
    PersonId,
    PlayerId,
    PlayEventId,
    PlayId,
    PossessionId,
    TeamSeasonId,
    VenueId,
)
from daily_nfl.domain.play import (
    Participation,
    Penalty,
    Period,
    PlayEvent,
    PlayExecution,
    PlayResult,
    PlayStateAfter,
    Possession,
    PrePlayState,
)
from daily_nfl.domain.temporal import KnowledgeTimestamp

__all__ = [
    "AvailabilityConfidence",
    "AvailabilityMethod",
    "DriveId",
    "EventId",
    "Franchise",
    "FranchiseId",
    "Game",
    "GameId",
    "GameResult",
    "GameResultType",
    "GameStatus",
    "KnowledgeTimestamp",
    "Participation",
    "ParticipationSide",
    "Penalty",
    "PenaltyDisposition",
    "Period",
    "Person",
    "PersonId",
    "PlayDesignModifier",
    "PlayEvent",
    "PlayEventId",
    "PlayEventType",
    "PlayExecution",
    "PlayId",
    "PlayResult",
    "PlayStateAfter",
    "PlayType",
    "Player",
    "PlayerId",
    "Possession",
    "PossessionId",
    "PrePlayState",
    "RulesetVersion",
    "SeasonPhase",
    "SeasonWeek",
    "TeamSeason",
    "TeamSeasonId",
    "VenueId",
]
