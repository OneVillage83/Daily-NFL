"""Typed provider-row and canonical normalization contracts for M6."""

from __future__ import annotations

from dataclasses import dataclass, field

from daily_nfl.domain import (
    GameId,
    Participation,
    Penalty,
    PenaltyDisposition,
    PlayEvent,
    PlayExecution,
    PlayResult,
    PlayStateAfter,
    PrePlayState,
    TeamSeasonId,
)


@dataclass(frozen=True, slots=True)
class ProviderPenaltyRecord:
    """Provider penalty fact after provider-specific extraction."""

    team_code: str
    penalty_type: str
    disposition: PenaltyDisposition = PenaltyDisposition.ACCEPTED
    player_external_id: str | None = None
    yards: int | None = None
    automatic_first_down: bool = False
    loss_of_down: bool = False
    nullifies_play: bool = False
    enforcement_spot: str | None = None

    def __post_init__(self) -> None:
        if not self.team_code.strip():
            raise ValueError("penalty team_code cannot be blank")
        if not self.penalty_type.strip():
            raise ValueError("penalty_type cannot be blank")
        if self.yards is not None and self.yards < 0:
            raise ValueError("penalty yards cannot be negative")
        if self.player_external_id is not None and not self.player_external_id.strip():
            raise ValueError("player_external_id cannot be blank when present")


@dataclass(frozen=True, slots=True)
class NflversePlayRecord:
    """Small semantic subset extracted from one nflverse PBP row.

    The full upstream row remains in immutable raw evidence. This contract only
    carries fields needed to construct canonical football state in M6.
    """

    provider_game_id: str
    provider_play_id: str
    provider_drive_id: str | None
    offense_team_code: str | None
    defense_team_code: str | None
    period: int
    quarter_seconds_remaining: int
    down: int | None
    distance: int | None
    yards_to_goal: int
    home_score_before: int
    away_score_before: int
    home_score_after: int | None = None
    away_score_after: int | None = None
    home_timeouts_remaining: int | None = None
    away_timeouts_remaining: int | None = None
    play_type_hint: str | None = None
    description: str | None = None
    official_yards_gained: int | None = None
    physical_yards_gained: int | None = None
    pass_attempt: bool = False
    rush_attempt: bool = False
    qb_scramble: bool = False
    qb_kneel: bool = False
    qb_spike: bool = False
    sack: bool = False
    complete_pass: bool | None = None
    interception: bool = False
    touchdown: bool = False
    safety: bool = False
    first_down: bool = False
    fumble: bool = False
    fumble_lost: bool = False
    no_play: bool = False
    punt_attempt: bool = False
    field_goal_attempt: bool = False
    kickoff_attempt: bool = False
    extra_point_attempt: bool = False
    two_point_attempt: bool = False
    timeout: bool = False
    administrative: bool = False
    play_action: bool = False
    rpo: bool = False
    screen: bool = False
    shotgun: bool = False
    under_center: bool = False
    motion: bool = False
    shift: bool = False
    no_huddle: bool = False
    designed_qb_run: bool = False
    penalties: tuple[ProviderPenaltyRecord, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        for value, label in (
            (self.provider_game_id, "provider_game_id"),
            (self.provider_play_id, "provider_play_id"),
        ):
            if not value.strip():
                raise ValueError(f"{label} cannot be blank")
        if self.provider_drive_id is not None and not self.provider_drive_id.strip():
            raise ValueError("provider_drive_id cannot be blank when present")
        if self.period < 1:
            raise ValueError("period must be positive")
        if self.quarter_seconds_remaining < 0:
            raise ValueError("quarter_seconds_remaining cannot be negative")
        if self.down is not None and self.down not in {1, 2, 3, 4}:
            raise ValueError("down must be 1-4 when present")
        if self.distance is not None and self.distance < 0:
            raise ValueError("distance cannot be negative")
        if not 0 <= self.yards_to_goal <= 100:
            raise ValueError("yards_to_goal must be between 0 and 100")
        if self.home_score_before < 0 or self.away_score_before < 0:
            raise ValueError("pre-play scores cannot be negative")
        for score in (self.home_score_after, self.away_score_after):
            if score is not None and score < 0:
                raise ValueError("post-play scores cannot be negative")


@dataclass(frozen=True, slots=True)
class NflverseGameContext:
    game_id: GameId
    home_team_code: str
    away_team_code: str
    home_team_season_id: TeamSeasonId
    away_team_season_id: TeamSeasonId

    def __post_init__(self) -> None:
        if not self.home_team_code.strip() or not self.away_team_code.strip():
            raise ValueError("team codes cannot be blank")
        if self.home_team_code == self.away_team_code:
            raise ValueError("home and away team codes must differ")
        if self.home_team_season_id == self.away_team_season_id:
            raise ValueError("home and away canonical teams must differ")

    def team_id_for_code(self, team_code: str) -> TeamSeasonId:
        if team_code == self.home_team_code:
            return self.home_team_season_id
        if team_code == self.away_team_code:
            return self.away_team_season_id
        raise ValueError(f"team code {team_code!r} is not part of canonical game")


@dataclass(frozen=True, slots=True)
class NormalizedPlayBundle:
    """Provider-neutral canonical representation of one normalized play."""

    game_id: GameId
    canonical_sequence: int
    drive_sequence: int | None
    possession_sequence: int | None
    provider_id: str
    provider_play_id: str
    provider_drive_id: str | None
    pre_play_state: PrePlayState
    execution: PlayExecution
    events: tuple[PlayEvent, ...]
    participation: tuple[Participation, ...]
    penalties: tuple[Penalty, ...]
    result: PlayResult
    state_after: PlayStateAfter | None
    description: str | None = None

    def __post_init__(self) -> None:
        if self.canonical_sequence < 1:
            raise ValueError("canonical_sequence must be positive")
        if self.drive_sequence is not None and self.drive_sequence < 1:
            raise ValueError("drive_sequence must be positive when present")
        if self.possession_sequence is not None and self.possession_sequence < 1:
            raise ValueError("possession_sequence must be positive when present")
        if not self.provider_id.strip() or not self.provider_play_id.strip():
            raise ValueError("provider identifiers cannot be blank")
        play_id = self.pre_play_state.play_id
        if self.result.play_id != play_id:
            raise ValueError("play result must refer to normalized play_id")
        if self.state_after is not None and self.state_after.play_id != play_id:
            raise ValueError("state_after must refer to normalized play_id")
        if any(event.play_id != play_id for event in self.events):
            raise ValueError("all play events must refer to normalized play_id")
        if any(penalty.play_id != play_id for penalty in self.penalties):
            raise ValueError("all penalties must refer to normalized play_id")
        if any(item.play_id != play_id for item in self.participation):
            raise ValueError("all participation must refer to normalized play_id")
