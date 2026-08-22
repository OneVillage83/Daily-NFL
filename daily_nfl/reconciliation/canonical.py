"""Canonical Daily NFL identity generation independent of provider identifiers."""

from __future__ import annotations

from uuid import UUID, uuid4, uuid5

from daily_nfl.domain import (
    CoachRoleId,
    DepthChartSnapshotId,
    DriveId,
    EventId,
    FranchiseId,
    GameId,
    InjuryObservationId,
    ParticipationId,
    PenaltyId,
    PersonId,
    PlayerId,
    PlayEventId,
    PlayId,
    PossessionId,
    PossessionSegmentId,
    RosterStintId,
    TeamSeasonId,
)

_DERIVED_NAMESPACE = UUID("ec26ed77-a1f1-4aac-86f0-bbfa475ddd32")


def _root_id(prefix: str, value: UUID | None = None) -> str:
    token = value or uuid4()
    return f"{prefix}_{token.hex}"


def _derived_id(prefix: str, identity: str) -> str:
    return f"{prefix}_{uuid5(_DERIVED_NAMESPACE, identity).hex}"


def _positive_sequence(sequence: int, label: str) -> None:
    if sequence < 1:
        raise ValueError(f"{label} must be positive")


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


def new_roster_stint_id(value: UUID | None = None) -> RosterStintId:
    """Allocate an opaque roster-stint identity without provider-derived inputs."""

    return RosterStintId(_root_id("rst", value))


def new_coach_role_id(value: UUID | None = None) -> CoachRoleId:
    """Allocate an opaque coaching-role identity without provider-derived inputs."""

    return CoachRoleId(_root_id("cor", value))


def new_event_id(value: UUID | None = None) -> EventId:
    return EventId(_root_id("evt", value))


def game_id_for_event(event_id: EventId) -> GameId:
    return GameId(_derived_id("nflg", f"nfl-game:{event_id}"))


def possession_id_for(game_id: GameId, canonical_sequence: int) -> PossessionId:
    _positive_sequence(canonical_sequence, "possession sequence")
    return PossessionId(_derived_id("pos", f"nfl-possession:{game_id}:{canonical_sequence}"))


def possession_segment_id_for(
    game_id: GameId,
    canonical_sequence: int,
) -> PossessionSegmentId:
    _positive_sequence(canonical_sequence, "possession-segment sequence")
    return PossessionSegmentId(
        _derived_id("psg", f"nfl-possession-segment:{game_id}:{canonical_sequence}")
    )


def drive_id_for(game_id: GameId, canonical_sequence: int) -> DriveId:
    _positive_sequence(canonical_sequence, "drive sequence")
    return DriveId(_derived_id("drv", f"nfl-drive:{game_id}:{canonical_sequence}"))


def play_id_for(game_id: GameId, canonical_sequence: int) -> PlayId:
    _positive_sequence(canonical_sequence, "play sequence")
    return PlayId(_derived_id("plx", f"nfl-play:{game_id}:{canonical_sequence}"))


def play_event_id_for(play_id: PlayId, sequence: int) -> PlayEventId:
    _positive_sequence(sequence, "play-event sequence")
    return PlayEventId(_derived_id("pev", f"nfl-play-event:{play_id}:{sequence}"))


def participation_id_for(play_id: PlayId, sequence: int) -> ParticipationId:
    _positive_sequence(sequence, "participation sequence")
    return ParticipationId(
        _derived_id("par", f"nfl-participation:{play_id}:{sequence}")
    )


def penalty_id_for(play_id: PlayId, sequence: int) -> PenaltyId:
    _positive_sequence(sequence, "penalty sequence")
    return PenaltyId(_derived_id("pnl", f"nfl-penalty:{play_id}:{sequence}"))


def new_injury_observation_id(value: UUID | None = None) -> InjuryObservationId:
    """Allocate an opaque canonical injury-observation identity."""

    return InjuryObservationId(_root_id("inj", value))


def new_depth_chart_snapshot_id(value: UUID | None = None) -> DepthChartSnapshotId:
    """Allocate an opaque canonical depth-chart snapshot identity."""

    return DepthChartSnapshotId(_root_id("dcs", value))


def new_reconciliation_decision_id(value: UUID | None = None) -> str:
    return _root_id("idr", value)
