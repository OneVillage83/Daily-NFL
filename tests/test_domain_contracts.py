from dataclasses import fields
from datetime import UTC, datetime, timedelta

import pytest

from daily_nfl.domain import (
    AvailabilityConfidence,
    AvailabilityMethod,
    CoachRoleId,
    CoachingRole,
    CompetitionId,
    Drive,
    DriveId,
    EventId,
    Franchise,
    FranchiseId,
    Game,
    GameId,
    GameResult,
    GameResultType,
    KnowledgeTimestamp,
    ObservedPhysicalOutcome,
    Participation,
    ParticipationId,
    ParticipationSide,
    Penalty,
    PenaltyDisposition,
    PenaltyId,
    Person,
    PersonId,
    Play,
    PlayDesignModifier,
    Player,
    PlayerId,
    PlayExecution,
    PlayId,
    PlayResult,
    PlayType,
    Possession,
    PossessionId,
    PossessionSegment,
    PossessionSegmentId,
    PrePlayState,
    RosterStint,
    RosterStintId,
    RulesetVersion,
    Season,
    SeasonPhase,
    SeasonWeek,
    TeamSeason,
    TeamSeasonId,
    VenueId,
    Week,
)
from daily_nfl.domain.play import Period

COMPETITION_ID = CompetitionId("core-competition-nfl")
GAME_ID = GameId("game-1")
HOME_ID = TeamSeasonId("team-home-2026")
AWAY_ID = TeamSeasonId("team-away-2026")


def _possession() -> Possession:
    return Possession(
        possession_id=PossessionId("pos-1"),
        offense_team_season_id=HOME_ID,
        defense_team_season_id=AWAY_ID,
    )


def test_season_phase_week_are_distinct_canonical_concepts() -> None:
    season = Season(competition_id=COMPETITION_ID, year=2026)
    week = Week(season=season, phase=SeasonPhase.REGULAR, number=1)
    compact = SeasonWeek(2026, SeasonPhase.REGULAR, 1)

    assert week.season.competition_id == COMPETITION_ID
    assert week.season.year == compact.season
    assert week.phase is compact.phase
    assert week.number == compact.week


def test_franchise_and_team_season_are_distinct_identities() -> None:
    franchise = Franchise(franchise_id=FranchiseId("franchise-1"))
    team_season = TeamSeason(
        team_season_id=TeamSeasonId("franchise-1-2026"),
        franchise_id=franchise.franchise_id,
        season=2026,
    )

    assert team_season.franchise_id == franchise.franchise_id
    assert str(team_season.team_season_id) != str(franchise.franchise_id)


def test_person_player_and_roster_stint_are_separate_identities() -> None:
    person = Person(person_id=PersonId("person-1"))
    player = Player(player_id=PlayerId("player-1"), person_id=person.person_id)
    stint = RosterStint(
        roster_stint_id=RosterStintId("stint-1"),
        player_id=player.player_id,
        team_season_id=HOME_ID,
        started_at=datetime(2026, 3, 1, tzinfo=UTC),
    )
    player_fields = {field.name for field in fields(Player)}

    assert stint.player_id == player.player_id
    assert "team_season_id" not in player_fields
    assert "provider_id" not in player_fields


def test_roster_stint_rejects_invalid_time_interval() -> None:
    start = datetime(2026, 9, 1, tzinfo=UTC)
    with pytest.raises(ValueError, match="cannot end before"):
        RosterStint(
            roster_stint_id=RosterStintId("stint-1"),
            player_id=PlayerId("player-1"),
            team_season_id=HOME_ID,
            started_at=start,
            ended_at=start - timedelta(days=1),
        )


def test_coaching_role_is_structured_and_time_bounded() -> None:
    role = CoachingRole(
        coach_role_id=CoachRoleId("coach-role-1"),
        person_id=PersonId("coach-person-1"),
        team_season_id=HOME_ID,
        role="HEAD_COACH",
        started_at=datetime(2026, 1, 1, tzinfo=UTC),
    )

    assert role.role == "HEAD_COACH"
    assert role.team_season_id == HOME_ID


def test_game_contract_cannot_carry_final_result_fields() -> None:
    names = {field.name for field in fields(Game)}

    assert "home_points_final" not in names
    assert "away_points_final" not in names
    assert "winner" not in names
    assert "overtime_played" not in names


def test_game_and_result_are_separate_canonical_objects() -> None:
    game = Game(
        game_id=GAME_ID,
        event_id=EventId("event-1"),
        competition_id=COMPETITION_ID,
        season_week=SeasonWeek(2026, SeasonPhase.REGULAR, 1),
        ruleset_version=RulesetVersion("NFL_2026"),
        home_team_season_id=HOME_ID,
        away_team_season_id=AWAY_ID,
        venue_id=VenueId("venue-1"),
        scheduled_kickoff=datetime(2026, 9, 10, 17, 20, tzinfo=UTC),
        schedule_version="schedule-v1",
    )
    result = GameResult(
        game.game_id,
        home_points_final=27,
        away_points_final=24,
        final_at=datetime(2026, 9, 10, 20, 30, tzinfo=UTC),
    )

    assert game.core_event_id == game.event_id
    assert game.competition_id == COMPETITION_ID
    assert result.result_type is GameResultType.HOME_WIN
    assert result.margin == 3
    assert result.total == 51


def test_possession_segment_drive_and_play_are_distinct_ledger_objects() -> None:
    segment_id = PossessionSegmentId("segment-1")
    drive_id = DriveId("drive-1")
    segment = PossessionSegment(
        possession_segment_id=segment_id,
        game_id=GAME_ID,
        canonical_sequence=1,
        offense_team_season_id=HOME_ID,
        defense_team_season_id=AWAY_ID,
    )
    drive = Drive(
        drive_id=drive_id,
        game_id=GAME_ID,
        possession_segment_id=segment.possession_segment_id,
        offense_team_season_id=HOME_ID,
        defense_team_season_id=AWAY_ID,
        play_count=1,
    )
    play = Play(
        play_id=PlayId("play-1"),
        game_id=GAME_ID,
        canonical_sequence=1,
        possession_segment_id=segment.possession_segment_id,
        drive_id=drive.drive_id,
    )

    assert play.possession_segment_id == segment.possession_segment_id
    assert play.drive_id == drive.drive_id
    assert str(segment.possession_segment_id) != str(drive.drive_id)


def test_pre_play_state_has_no_outcome_or_analytics_fields() -> None:
    names = {field.name for field in fields(PrePlayState)}
    forbidden = {
        "yards_gained",
        "official_yards_gained",
        "physical_yards_gained",
        "completion",
        "touchdown",
        "interception",
        "sack",
        "epa",
        "wpa",
        "success",
        "first_down",
    }

    assert names.isdisjoint(forbidden)


def test_pre_play_state_accepts_only_pre_execution_information() -> None:
    state = PrePlayState(
        play_id=PlayId("play-1"),
        drive_id=DriveId("drive-1"),
        possession=_possession(),
        period=Period(2),
        clock_seconds_remaining=703,
        down=2,
        distance=7,
        yards_to_goal=58,
        home_score=10,
        away_score=7,
        home_timeouts_remaining=3,
        away_timeouts_remaining=2,
        possession_segment_id=PossessionSegmentId("segment-1"),
        play_clock_seconds_remaining=20,
        previous_play_id=PlayId("play-0"),
        offensive_personnel="11",
        offensive_formation="SHOTGUN",
        motion=True,
    )

    assert state.down == 2
    assert state.distance == 7
    assert state.yards_to_goal == 58
    assert state.previous_play_id == PlayId("play-0")


def test_primary_play_type_enum_matches_locked_f5_taxonomy() -> None:
    assert {item.value for item in PlayType} == {
        "PASS",
        "RUSH",
        "SCRAMBLE",
        "SACK",
        "KNEEL",
        "SPIKE",
        "PUNT",
        "FIELD_GOAL",
        "KICKOFF",
        "EXTRA_POINT",
        "TWO_POINT",
        "PENALTY_ONLY",
        "TIMEOUT",
        "ADMINISTRATIVE",
        "OTHER",
    }


def test_play_design_modifier_contains_locked_f5_vocabulary() -> None:
    required = {
        "PLAY_ACTION",
        "RPO",
        "SCREEN",
        "BOOT",
        "NAKED_BOOT",
        "DRAW",
        "READ_OPTION",
        "SPEED_OPTION",
        "DESIGNED_QB_RUN",
        "DROPBACK",
        "QUICK_GAME",
        "EMPTY",
        "MOTION",
        "SHIFT",
        "UNDER_CENTER",
        "SHOTGUN",
    }

    assert required.issubset({item.value for item in PlayDesignModifier})


def test_play_action_is_a_design_modifier_not_container_name() -> None:
    execution = PlayExecution(
        primary_play_type=PlayType.PASS,
        modifiers=frozenset({PlayDesignModifier.PLAY_ACTION}),
    )

    assert execution.semantic_label == "PLAY_ACTION_PASS"
    assert type(execution).__name__ == "PlayExecution"
    assert PlayDesignModifier.PLAY_ACTION.value == "PLAY_ACTION"


def test_rpo_label_distinguishes_pass_from_run() -> None:
    pass_execution = PlayExecution(
        PlayType.PASS,
        frozenset({PlayDesignModifier.RPO}),
    )
    run_execution = PlayExecution(
        PlayType.RUSH,
        frozenset({PlayDesignModifier.RPO}),
    )

    assert pass_execution.semantic_label == "RPO_PASS"
    assert run_execution.semantic_label == "RPO_RUSH"


def test_special_teams_play_rejects_offensive_design_modifier() -> None:
    with pytest.raises(ValueError, match="offensive scrimmage play"):
        PlayExecution(
            PlayType.PUNT,
            frozenset({PlayDesignModifier.PLAY_ACTION}),
        )


def test_designed_qb_run_requires_rush_family() -> None:
    with pytest.raises(ValueError, match="requires primary RUSH"):
        PlayExecution(
            PlayType.SCRAMBLE,
            frozenset({PlayDesignModifier.DESIGNED_QB_RUN}),
        )


def test_mutually_exclusive_snap_structures_are_rejected() -> None:
    with pytest.raises(ValueError, match="cannot both"):
        PlayExecution(
            PlayType.PASS,
            frozenset(
                {
                    PlayDesignModifier.SHOTGUN,
                    PlayDesignModifier.UNDER_CENTER,
                }
            ),
        )


def test_participation_has_first_class_identity() -> None:
    participation = Participation(
        participation_id=ParticipationId("participation-1"),
        play_id=PlayId("play-1"),
        player_id=PlayerId("player-1"),
        team_season_id=HOME_ID,
        side=ParticipationSide.OFFENSE,
        role="PASSER",
    )

    assert participation.participation_id == ParticipationId("participation-1")


def test_penalty_has_first_class_identity_and_official_disposition() -> None:
    penalty = Penalty(
        penalty_id=PenaltyId("penalty-1"),
        play_id=PlayId("play-1"),
        team_season_id=AWAY_ID,
        penalty_type="Defensive Offside",
        disposition=PenaltyDisposition.ACCEPTED,
        yards=5,
    )

    assert penalty.penalty_id == PenaltyId("penalty-1")
    assert penalty.disposition is PenaltyDisposition.ACCEPTED


def test_physical_outcome_is_separate_from_official_result() -> None:
    result = PlayResult(
        play_id=PlayId("play-1"),
        official_yards_gained=None,
        no_play=True,
        physical_outcome=ObservedPhysicalOutcome(yards_gained=12, first_down=True),
    )

    assert result.official_yards_gained is None
    assert result.physical_yards_gained == 12
    assert result.physical_outcome is not None
    assert result.physical_outcome.first_down


def test_knowledge_timestamp_requires_timezone_aware_clocks() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        KnowledgeTimestamp(available_at=datetime(2026, 8, 20, 12, 0))


def test_knowledge_timestamp_applies_pit_cutoff() -> None:
    knowledge = KnowledgeTimestamp(
        available_at=datetime(2026, 8, 20, 19, 0, tzinfo=UTC),
        published_at=datetime(2026, 8, 20, 18, 55, tzinfo=UTC),
        observed_at=datetime(2026, 8, 20, 19, 0, tzinfo=UTC),
        availability_method=AvailabilityMethod.OUR_OBSERVATION_TIME,
        availability_confidence=AvailabilityConfidence.HIGH,
    )

    assert not knowledge.is_available_by(datetime(2026, 8, 20, 18, 59, tzinfo=UTC))
    assert knowledge.is_available_by(datetime(2026, 8, 20, 19, 0, tzinfo=UTC))
