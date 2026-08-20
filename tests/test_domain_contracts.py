from dataclasses import fields
from datetime import UTC, datetime

import pytest

from daily_nfl.domain import (
    AvailabilityConfidence,
    AvailabilityMethod,
    DriveId,
    EventId,
    Game,
    GameId,
    GameResult,
    GameResultType,
    KnowledgeTimestamp,
    PlayDesignModifier,
    PlayExecution,
    PlayId,
    PlayType,
    Possession,
    PossessionId,
    PrePlayState,
    RulesetVersion,
    SeasonPhase,
    SeasonWeek,
    TeamSeasonId,
    VenueId,
)
from daily_nfl.domain.play import Period


def _possession() -> Possession:
    return Possession(
        possession_id=PossessionId("pos-1"),
        offense_team_season_id=TeamSeasonId("team-home-2026"),
        defense_team_season_id=TeamSeasonId("team-away-2026"),
    )


def test_game_contract_cannot_carry_final_result_fields() -> None:
    names = {field.name for field in fields(Game)}

    assert "home_points_final" not in names
    assert "away_points_final" not in names
    assert "winner" not in names


def test_game_and_result_are_separate_canonical_objects() -> None:
    game = Game(
        game_id=GameId("game-1"),
        event_id=EventId("event-1"),
        season_week=SeasonWeek(2026, SeasonPhase.REGULAR, 1),
        ruleset_version=RulesetVersion("NFL_2026"),
        home_team_season_id=TeamSeasonId("home-2026"),
        away_team_season_id=TeamSeasonId("away-2026"),
        venue_id=VenueId("venue-1"),
        scheduled_kickoff=datetime(2026, 9, 10, 17, 20, tzinfo=UTC),
    )
    result = GameResult(game.game_id, home_points_final=27, away_points_final=24)

    assert result.result_type is GameResultType.HOME_WIN
    assert result.margin == 3
    assert result.total == 51


def test_pre_play_state_has_no_outcome_or_analytics_fields() -> None:
    names = {field.name for field in fields(PrePlayState)}
    forbidden = {
        "yards_gained",
        "completion",
        "touchdown",
        "interception",
        "epa",
        "wpa",
        "success",
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
    )

    assert state.down == 2
    assert state.distance == 7
    assert state.yards_to_goal == 58


def test_play_action_is_a_design_modifier_not_container_name() -> None:
    execution = PlayExecution(
        primary_play_type=PlayType.PASS,
        modifiers=frozenset({PlayDesignModifier.PLAY_ACTION}),
    )

    assert execution.semantic_label == "PLAY_ACTION_PASS"
    assert type(execution).__name__ == "PlayExecution"


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
