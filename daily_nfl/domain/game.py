"""Canonical competition, season, week, game, and result contracts."""

from dataclasses import dataclass
from datetime import datetime

from daily_nfl.domain.enums import GameResultType, GameStatus, SeasonPhase
from daily_nfl.domain.ids import CompetitionId, EventId, GameId, TeamSeasonId, VenueId


def _validate_season(season: int) -> None:
    if season < 1920:
        raise ValueError("season is outside the supported NFL era")


@dataclass(frozen=True, slots=True)
class Season:
    """One competition season in the canonical football hierarchy."""

    competition_id: CompetitionId
    year: int

    def __post_init__(self) -> None:
        _validate_season(self.year)


@dataclass(frozen=True, slots=True)
class Week:
    """Competition-week identity scoped by season phase."""

    season: Season
    phase: SeasonPhase
    number: int

    def __post_init__(self) -> None:
        if self.number < 1:
            raise ValueError("week must be positive")


@dataclass(frozen=True, slots=True)
class SeasonWeek:
    """Compact compatibility reference for season / phase / week.

    The canonical ontology also exposes Season and Week as distinct concepts;
    this compact value remains useful in existing game/persistence boundaries.
    """

    season: int
    phase: SeasonPhase
    week: int

    def __post_init__(self) -> None:
        _validate_season(self.season)
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

    `event_id` is the opaque Daily-Data-Core sporting-event reference. Final
    scores, winner/tie truth, and realized overtime live in GameResult so a
    pregame Game object cannot accidentally carry postgame labels.
    """

    game_id: GameId
    event_id: EventId
    competition_id: CompetitionId
    season_week: SeasonWeek
    ruleset_version: RulesetVersion
    home_team_season_id: TeamSeasonId
    away_team_season_id: TeamSeasonId
    venue_id: VenueId
    scheduled_kickoff: datetime
    status: GameStatus = GameStatus.SCHEDULED
    actual_kickoff: datetime | None = None
    neutral_site: bool = False
    schedule_version: str | None = None

    def __post_init__(self) -> None:
        if self.home_team_season_id == self.away_team_season_id:
            raise ValueError("home and away teams must differ")
        if self.scheduled_kickoff.tzinfo is None:
            raise ValueError("scheduled_kickoff must be timezone-aware")
        if self.actual_kickoff is not None and self.actual_kickoff.tzinfo is None:
            raise ValueError("actual_kickoff must be timezone-aware")
        if self.schedule_version is not None and not self.schedule_version.strip():
            raise ValueError("schedule_version cannot be blank when present")

    @property
    def core_event_id(self) -> EventId:
        """Architecture-native name for the linked Core sporting event."""

        return self.event_id


@dataclass(frozen=True, slots=True)
class GameResult:
    """Canonical football truth, independent of sportsbook settlement rules."""

    game_id: GameId
    home_points_final: int
    away_points_final: int
    home_points_regulation: int | None = None
    away_points_regulation: int | None = None
    overtime_played: bool = False
    final_at: datetime | None = None

    def __post_init__(self) -> None:
        point_values = (
            self.home_points_final,
            self.away_points_final,
            self.home_points_regulation,
            self.away_points_regulation,
        )
        if any(value is not None and value < 0 for value in point_values):
            raise ValueError("football scores cannot be negative")
        if self.final_at is not None and self.final_at.tzinfo is None:
            raise ValueError("final_at must be timezone-aware when present")
        if self.home_points_regulation is not None:
            if self.home_points_regulation > self.home_points_final:
                raise ValueError("regulation home score cannot exceed final score")
        if self.away_points_regulation is not None:
            if self.away_points_regulation > self.away_points_final:
                raise ValueError("regulation away score cannot exceed final score")
        if (
            not self.overtime_played
            and self.home_points_regulation is not None
            and self.away_points_regulation is not None
            and (
                self.home_points_regulation != self.home_points_final
                or self.away_points_regulation != self.away_points_final
            )
        ):
            raise ValueError("non-overtime regulation scores must equal final scores")

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
