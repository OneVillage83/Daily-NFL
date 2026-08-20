"""Canonical football identity entities independent of provider IDs."""

from dataclasses import dataclass

from daily_nfl.domain.ids import FranchiseId, PersonId, PlayerId, TeamSeasonId


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
    """Persistent real-person identity independent of roster/team context."""

    person_id: PersonId


@dataclass(frozen=True, slots=True)
class Player:
    """NFL player identity linked to a persistent person.

    Team membership is deliberately absent; it belongs to roster-stint state.
    """

    player_id: PlayerId
    person_id: PersonId
