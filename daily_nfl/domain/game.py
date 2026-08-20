"""Canonical game-level football contracts."""

from dataclasses import dataclass
from datetime import datetime

from daily_nfl.domain.enums import GameResultType, GameStatus, SeasonPhase
from daily_nfl.domain.ids import EventId, GameId, TeamSeasonId, VenueId


@dataclass(frozen=True, slots=True)
class SeasonWeek:
    season: int
    phase: SeasonPhase
    week: int

    def __post_init__(self) -> None:
        if self.season < 1920:
            raise ValueError("season is outside the supported NFL era")
        if self.week < 1:
            raise ValueError("week must be positive")


@dataclass(frozen=True, slots=True)
class RulesetVersion:
    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("ruleset version cannot be blank")


@dataclass(frozen=True, slots=True)
class Game:
    """A scheduled/played NFL event without final outcome truth.

    Final scores and winner/tie truth deliberately live in `GameResult` so a
    pregame Game object cannot accidentally carry postgame labels.
    """

    game_id: GameId
    event_id: EventId
    season_week: SeasonWeek
    ruleset_version: RulesetVersion
    home_team_season_id: TeamSeasonId
    away_team_season_id: TeamSeasonId
    venue_id: VenueId
    scheduled_kickoff: datetime
    status: GameStatus = GameStatus.SCHEDULED
    actual_kickoff: datetime | None = None
    neutral_site: bool = False

    def __post_init__(self) -> None:
        if self.home_team_season_id == self.away_team_season_id:
            raise ValueError("home and away teams must differ")
        if self.scheduled_kickoff.tzinfo is None:
            raise ValueError("scheduled_kickoff must be timezone-aware")
        if self.actual_kickoff is not None and self.actual_kickoff.tzinfo is None:
            raise ValueError("actual_kickoff must be timezone-aware")


@dataclass(frozen=True, slots=True)
class GameResult:
    """Canonical football truth, independent of sportsbook settlement rules."""

    game_id: GameId
    home_points_final: int
    away_points_final: int
    home_points_regulation: int | None = None
    away_points_regulation: int | None = None
    overtime_played: bool = False

    def __post_init__(self) -> None:
        point_values = (
            self.home_points_final,
            self.away_points_final,
            self.home_points_regulation,
            self.away_points_regulation,
        )
        if any(value is not None and value < 0 for value in point_values):
            raise ValueError("football scores cannot be negative")

    @property
    def result_type(self) -> GameResultType:
        if self.home_points_final > self.away_points_final:
            return GameResultType.HOME_WIN
        if self.home_points_final < self.away_points_final:
            return GameResultType.AWAY_WIN
        return GameResultType.TIE

    @property
    def margin(self) -> int:
        return self.home_points_final - self.away_points_final

    @property
    def total(self) -> int:
        return self.home_points_final + self.away_points_final
