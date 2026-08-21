"""Canonical Daily NFL identity generation independent of provider identifiers."""

from __future__ import annotations

from uuid import UUID, uuid4, uuid5

from daily_nfl.domain import (
    EventId,
    FranchiseId,
    GameId,
    PersonId,
    PlayerId,
    TeamSeasonId,
)

_DERIVED_NAMESPACE = UUID("ec26ed77-a1f1-4aac-86f0-bbfa475ddd32")


def _root_id(prefix: str, value: UUID | None = None) -> str:
    token = value or uuid4()
    return f"{prefix}_{token.hex}"


def _derived_id(prefix: str, identity: str) -> str:
    return f"{prefix}_{uuid5(_DERIVED_NAMESPACE, identity).hex}"


def new_franchise_id(value: UUID | None = None) -> FranchiseId:
    return FranchiseId(_root_id("frn", value))


def team_season_id_for(franchise_id: FranchiseId, season: int) -> TeamSeasonId:
    if season < 1920:
        raise ValueError("season is outside the supported NFL era")
    return TeamSeasonId(_derived_id("tms", f"team-season:{franchise_id}:{season}"))


def new_person_id(value: UUID | None = None) -> PersonId:
    return PersonId(_root_id("per", value))


def player_id_for_person(person_id: PersonId) -> PlayerId:
    return PlayerId(_derived_id("ply", f"player:{person_id}"))


def new_event_id(value: UUID | None = None) -> EventId:
    return EventId(_root_id("evt", value))


def game_id_for_event(event_id: EventId) -> GameId:
    return GameId(_derived_id("nflg", f"nfl-game:{event_id}"))


def new_reconciliation_decision_id(value: UUID | None = None) -> str:
    return _root_id("idr", value)
