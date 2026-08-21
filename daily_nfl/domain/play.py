"""Canonical play, possession, drive, participation, and penalty contracts."""

from __future__ import annotations

from dataclasses import dataclass, field

from daily_nfl.domain.enums import (
    ParticipationSide,
    PenaltyDisposition,
    PlayDesignModifier,
    PlayEventType,
    PlayType,
)
from daily_nfl.domain.ids import (
    DriveId,
    GameId,
    ParticipationId,
    PenaltyId,
    PlayerId,
    PlayEventId,
    PlayId,
    PossessionId,
    PossessionSegmentId,
    TeamSeasonId,
)


@dataclass(frozen=True, slots=True)
class Period:
    number: int
    is_overtime: bool = False

    def __post_init__(self) -> None:
        if self.number < 1:
            raise ValueError("period number must be positive")
        if self.number <= 4 and self.is_overtime:
            raise ValueError("regulation periods cannot be marked overtime")
        if self.number > 4 and not self.is_overtime:
            raise ValueError("periods after the fourth must be marked overtime")


@dataclass(frozen=True, slots=True)
class Possession:
    """Current possession context used by play-state objects.

    F-5's persistent possession-ledger concept is exposed separately as
    PossessionSegment; this lightweight state object remains compatible with
    the existing M6 normalization boundary.
    """

    possession_id: PossessionId
    offense_team_season_id: TeamSeasonId
    defense_team_season_id: TeamSeasonId

    def __post_init__(self) -> None:
        if self.offense_team_season_id == self.defense_team_season_id:
            raise ValueError("offense and defense teams must differ")


@dataclass(frozen=True, slots=True)
class PossessionSegment:
    """A canonical time-ordered segment of game possession."""

    possession_segment_id: PossessionSegmentId
    game_id: GameId
    canonical_sequence: int
    offense_team_season_id: TeamSeasonId
    defense_team_season_id: TeamSeasonId
    start_play_id: PlayId | None = None
    end_play_id: PlayId | None = None

    def __post_init__(self) -> None:
        if self.canonical_sequence < 1:
            raise ValueError("possession-segment sequence must be positive")
        if self.offense_team_season_id == self.defense_team_season_id:
            raise ValueError("offense and defense teams must differ")


@dataclass(frozen=True, slots=True)
class Drive:
    """Canonical drive ledger distinct from the possession segment."""

    drive_id: DriveId
    game_id: GameId
    possession_segment_id: PossessionSegmentId
    offense_team_season_id: TeamSeasonId
    defense_team_season_id: TeamSeasonId
    start_play_id: PlayId | None = None
    end_play_id: PlayId | None = None
    start_period: Period | None = None
    end_period: Period | None = None
    start_clock_seconds_remaining: int | None = None
    end_clock_seconds_remaining: int | None = None
    start_yards_to_goal: int | None = None
    end_yards_to_goal: int | None = None
    play_count: int | None = None
    first_downs: int | None = None
    result: str | None = None
    points: int | None = None
    turnover: bool | None = None

    def __post_init__(self) -> None:
        if self.offense_team_season_id == self.defense_team_season_id:
            raise ValueError("offense and defense teams must differ")
        for value, label in (
            (self.start_clock_seconds_remaining, "start clock"),
            (self.end_clock_seconds_remaining, "end clock"),
            (self.play_count, "play_count"),
            (self.first_downs, "first_downs"),
            (self.points, "points"),
        ):
            if value is not None and value < 0:
                raise ValueError(f"{label} cannot be negative")
        for value in (self.start_yards_to_goal, self.end_yards_to_goal):
            if value is not None and not 0 <= value <= 100:
                raise ValueError("drive yards_to_goal must be between 0 and 100")
        if self.result is not None and not self.result.strip():
            raise ValueError("drive result cannot be blank when present")


@dataclass(frozen=True, slots=True)
class Play:
    """Canonical play ledger identity independent of provider row identity."""

    play_id: PlayId
    game_id: GameId
    canonical_sequence: int
    possession_segment_id: PossessionSegmentId
    drive_id: DriveId | None = None
    previous_play_id: PlayId | None = None

    def __post_init__(self) -> None:
        if self.canonical_sequence < 1:
            raise ValueError("play sequence must be positive")
        if self.previous_play_id == self.play_id:
            raise ValueError("play cannot reference itself as previous_play_id")


@dataclass(frozen=True, slots=True)
class PrePlayState:
    """Football state immediately before execution begins.

    Outcome fields are intentionally impossible to provide here. Yards gained,
    completion, touchdown, turnover, EPA/WPA, and success metrics belong to
    result/analytics layers instead.
    """

    play_id: PlayId
    drive_id: DriveId | None
    possession: Possession
    period: Period
    clock_seconds_remaining: int
    down: int | None
    distance: int | None
    yards_to_goal: int
    home_score: int
    away_score: int
    home_timeouts_remaining: int | None = None
    away_timeouts_remaining: int | None = None
    possession_segment_id: PossessionSegmentId | None = None
    play_clock_seconds_remaining: int | None = None
    previous_play_id: PlayId | None = None
    kickoff_state: str | None = None
    try_state: str | None = None
    two_minute_state: bool | None = None
    overtime_state: str | None = None
    offensive_personnel: str | None = None
    defensive_personnel: str | None = None
    offensive_formation: str | None = None
    defensive_front: str | None = None
    coverage_shell: str | None = None
    motion: bool | None = None
    shift: bool | None = None
    shotgun: bool | None = None
    no_huddle: bool | None = None
    weather_snapshot_id: str | None = None
    surface_state_id: str | None = None

    def __post_init__(self) -> None:
        if self.clock_seconds_remaining < 0:
            raise ValueError("clock seconds cannot be negative")
        if self.play_clock_seconds_remaining is not None and self.play_clock_seconds_remaining < 0:
            raise ValueError("play clock seconds cannot be negative")
        if self.down is not None and self.down not in {1, 2, 3, 4}:
            raise ValueError("down must be 1-4 when present")
        if self.distance is not None and self.distance < 0:
            raise ValueError("distance cannot be negative")
        if not 0 <= self.yards_to_goal <= 100:
            raise ValueError("yards_to_goal must be between 0 and 100")
        if self.home_score < 0 or self.away_score < 0:
            raise ValueError("scores cannot be negative")
        for timeouts in (self.home_timeouts_remaining, self.away_timeouts_remaining):
            if timeouts is not None and timeouts < 0:
                raise ValueError("timeouts remaining cannot be negative")
        if self.previous_play_id == self.play_id:
            raise ValueError("play cannot reference itself as previous_play_id")
        for value, label in (
            (self.kickoff_state, "kickoff_state"),
            (self.try_state, "try_state"),
            (self.overtime_state, "overtime_state"),
            (self.offensive_personnel, "offensive_personnel"),
            (self.defensive_personnel, "defensive_personnel"),
            (self.offensive_formation, "offensive_formation"),
            (self.defensive_front, "defensive_front"),
            (self.coverage_shell, "coverage_shell"),
            (self.weather_snapshot_id, "weather_snapshot_id"),
            (self.surface_state_id, "surface_state_id"),
        ):
            if value is not None and not value.strip():
                raise ValueError(f"{label} cannot be blank when present")


@dataclass(frozen=True, slots=True)
class PlayExecution:
    """What the offense/special-teams unit attempted on the play.

    The object is deliberately named PlayExecution. `PLAY_ACTION` is reserved
    for the real football play-design modifier and never names this container.
    """

    primary_play_type: PlayType
    modifiers: frozenset[PlayDesignModifier] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        offensive_design_types = {
            PlayType.PASS,
            PlayType.RUSH,
            PlayType.SCRAMBLE,
            PlayType.SACK,
        }
        if self.modifiers and self.primary_play_type not in offensive_design_types:
            raise ValueError("play-design modifiers require an offensive scrimmage play")
        if PlayDesignModifier.RPO in self.modifiers and self.primary_play_type not in {
            PlayType.PASS,
            PlayType.RUSH,
        }:
            raise ValueError("RPO modifier is only valid on PASS or RUSH")
        if (
            PlayDesignModifier.DESIGNED_QB_RUN in self.modifiers
            and self.primary_play_type is not PlayType.RUSH
        ):
            raise ValueError("DESIGNED_QB_RUN modifier requires primary RUSH")
        if {
            PlayDesignModifier.SHOTGUN,
            PlayDesignModifier.UNDER_CENTER,
        }.issubset(self.modifiers):
            raise ValueError("SHOTGUN and UNDER_CENTER cannot both describe one snap")

    @property
    def semantic_label(self) -> str:
        """Return a stable descriptive label without redefining canonical fields."""
        if PlayDesignModifier.PLAY_ACTION in self.modifiers:
            return f"PLAY_ACTION_{self.primary_play_type.value}"
        if PlayDesignModifier.RPO in self.modifiers:
            return f"RPO_{self.primary_play_type.value}"
        if PlayDesignModifier.SCREEN in self.modifiers:
            return f"SCREEN_{self.primary_play_type.value}"
        return self.primary_play_type.value


@dataclass(frozen=True, slots=True)
class PlayEvent:
    play_event_id: PlayEventId
    play_id: PlayId
    sequence: int
    event_type: PlayEventType
    player_id: PlayerId | None = None
    team_season_id: TeamSeasonId | None = None
    detail: str | None = None

    def __post_init__(self) -> None:
        if self.sequence < 1:
            raise ValueError("play-event sequence must be positive")


@dataclass(frozen=True, slots=True)
class Participation:
    participation_id: ParticipationId
    play_id: PlayId
    player_id: PlayerId
    team_season_id: TeamSeasonId
    side: ParticipationSide
    role: str
    on_field: bool = True

    def __post_init__(self) -> None:
        if not self.role.strip():
            raise ValueError("participation role cannot be blank")


@dataclass(frozen=True, slots=True)
class Penalty:
    penalty_id: PenaltyId
    play_id: PlayId
    team_season_id: TeamSeasonId
    penalty_type: str
    disposition: PenaltyDisposition
    player_id: PlayerId | None = None
    yards: int | None = None
    automatic_first_down: bool = False
    loss_of_down: bool = False
    nullifies_play: bool = False
    enforcement_spot: str | None = None

    def __post_init__(self) -> None:
        if not self.penalty_type.strip():
            raise ValueError("penalty_type cannot be blank")
        if self.yards is not None and self.yards < 0:
            raise ValueError("penalty yards cannot be negative")
        if self.enforcement_spot is not None and not self.enforcement_spot.strip():
            raise ValueError("enforcement_spot cannot be blank when present")


@dataclass(frozen=True, slots=True)
class ObservedPhysicalOutcome:
    """What physically occurred before official enforcement, when observable."""

    yards_gained: int | None = None
    first_down: bool = False
    touchdown: bool = False
    safety: bool = False
    completion: bool | None = None
    interception: bool = False
    sack: bool = False
    fumble: bool = False
    fumble_lost: bool = False
    possession_changed: bool = False
    score_change: int = 0

    def __post_init__(self) -> None:
        if self.score_change < 0:
            raise ValueError("physical score_change cannot be negative")
        if self.fumble_lost and not self.fumble:
            raise ValueError("physical fumble_lost requires fumble=True")


@dataclass(frozen=True, slots=True)
class PlayResult:
    """Official play result plus optional separately observed physical truth."""

    play_id: PlayId
    official_yards_gained: int | None = None
    first_down: bool = False
    touchdown: bool = False
    safety: bool = False
    completion: bool | None = None
    interception: bool = False
    sack: bool = False
    fumble: bool = False
    fumble_lost: bool = False
    possession_changed: bool = False
    score_change: int = 0
    no_play: bool = False
    kick_result: str | None = None
    physical_outcome: ObservedPhysicalOutcome | None = None

    def __post_init__(self) -> None:
        if self.score_change < 0:
            raise ValueError("score_change cannot be negative")
        if self.fumble_lost and not self.fumble:
            raise ValueError("fumble_lost requires fumble=True")
        if self.no_play and self.official_yards_gained not in {None, 0}:
            raise ValueError("no-play result cannot carry official yards")
        if self.kick_result is not None and not self.kick_result.strip():
            raise ValueError("kick_result cannot be blank when present")

    @property
    def physical_yards_gained(self) -> int | None:
        """Compatibility accessor for the richer physical-outcome object."""

        if self.physical_outcome is None:
            return None
        return self.physical_outcome.yards_gained


@dataclass(frozen=True, slots=True)
class PlayStateAfter:
    """Canonical football state after official enforcement/scoring."""

    play_id: PlayId
    next_possession: Possession | None
    period: Period
    clock_seconds_remaining: int
    down: int | None
    distance: int | None
    yards_to_goal: int | None
    home_score: int
    away_score: int
    drive_continues: bool

    def __post_init__(self) -> None:
        if self.clock_seconds_remaining < 0:
            raise ValueError("clock seconds cannot be negative")
        if self.down is not None and self.down not in {1, 2, 3, 4}:
            raise ValueError("down must be 1-4 when present")
        if self.distance is not None and self.distance < 0:
            raise ValueError("distance cannot be negative")
        if self.yards_to_goal is not None and not 0 <= self.yards_to_goal <= 100:
            raise ValueError("yards_to_goal must be between 0 and 100")
        if self.home_score < 0 or self.away_score < 0:
            raise ValueError("scores cannot be negative")
