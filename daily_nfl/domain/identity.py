"""Canonical football identity entities independent of provider IDs."""

from dataclasses import dataclass
from datetime import datetime

from daily_nfl.domain.ids import (
    CoachRoleId,
    CoachingStintId,
    FranchiseId,
    PersonId,
    PlayerId,
    RosterStintId,
    TeamSeasonId,
)


def _validate_optional_interval(
    started_at: datetime | None,
    ended_at: datetime | None,
) -> None:
    for value in (started_at, ended_at):
        if value is not None and value.tzinfo is None:
            raise ValueError("identity interval timestamps must be timezone-aware")
    if started_at is not None and ended_at is not None and ended_at < started_at:
        raise ValueError("identity interval cannot end before it starts")


@dataclass(frozen=True, slots=True)
class Franchise:
    """Persistent NFL franchise identity across seasons and provider changes."""

    franchise_id: FranchiseId


@dataclass(frozen=True, slots=True)
class TeamSeason:
    """Season-scoped team identity linked to a persistent franchise."""

    team_season_id: TeamSeasonId
    franchise_id: FranchiseId
    season: int

    def __post_init__(self) -> None:
        if self.season < 1920:
            raise ValueError("season is outside the supported NFL era")


@dataclass(frozen=True, slots=True)
class Person:
    """Persistent real-person identity independent of football role/context."""

    person_id: PersonId


@dataclass(frozen=True, slots=True)
class Player:
    """NFL player identity linked to a persistent person.

    Team membership is deliberately absent; it belongs to RosterStint.
    """

    player_id: PlayerId
    person_id: PersonId


@dataclass(frozen=True, slots=True)
class RosterStint:
    """A player's time-bounded relationship with one team-season.

    This preserves F-1's separation between persistent person/player identity
    and changing team membership. Unknown interval endpoints remain explicit.
    """

    roster_stint_id: RosterStintId
    player_id: PlayerId
    team_season_id: TeamSeasonId
    started_at: datetime | None = None
    ended_at: datetime | None = None

    def __post_init__(self) -> None:
        _validate_optional_interval(self.started_at, self.ended_at)


@dataclass(frozen=True, slots=True)
class CoachingStint:
    """A coach's time-bounded relationship with one team-season.

    Person identity persists across teams and years. A stint represents the
    team-scoped relationship; role titles and decision responsibilities may
    change within the stint and are therefore versioned separately by F-9.
    """

    coaching_stint_id: CoachingStintId
    person_id: PersonId
    team_season_id: TeamSeasonId
    started_at: datetime | None = None
    ended_at: datetime | None = None

    def __post_init__(self) -> None:
        _validate_optional_interval(self.started_at, self.ended_at)


@dataclass(frozen=True, slots=True)
class CoachingRole:
    """Time-bounded staff role without collapsing coaching identity into text.

    Coaches are represented by persistent Person identities. The role assignment
    changes independently across teams/seasons and over time.
    """

    coach_role_id: CoachRoleId
    person_id: PersonId
    team_season_id: TeamSeasonId
    role: str
    started_at: datetime | None = None
    ended_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.role.strip():
            raise ValueError("coaching role cannot be blank")
        _validate_optional_interval(self.started_at, self.ended_at)
