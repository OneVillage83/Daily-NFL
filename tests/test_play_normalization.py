from uuid import UUID

import pytest

from daily_nfl.domain import (
    GameId,
    PenaltyDisposition,
    PlayDesignModifier,
    PlayEventType,
    PlayType,
    TeamSeasonId,
)
from daily_nfl.normalization import (
    NflverseGameContext,
    NflversePlayRecord,
    PlayNormalizationError,
    ProviderPenaltyRecord,
    classify_play_type,
    normalize_nflverse_play,
)
from daily_nfl.reconciliation import play_id_for


GAME_ID = GameId("nflg_fixture")
HOME_ID = TeamSeasonId("tms_home")
AWAY_ID = TeamSeasonId("tms_away")
CONTEXT = NflverseGameContext(
    game_id=GAME_ID,
    home_team_code="HOM",
    away_team_code="AWY",
    home_team_season_id=HOME_ID,
    away_team_season_id=AWAY_ID,
)


def _row(**overrides: object) -> NflversePlayRecord:
    values: dict[str, object] = {
        "provider_game_id": "2026_01_AWY_HOM",
        "provider_play_id": "100",
        "provider_drive_id": "1",
        "offense_team_code": "HOM",
        "defense_team_code": "AWY",
        "period": 1,
        "quarter_seconds_remaining": 840,
        "down": 1,
        "distance": 10,
        "yards_to_goal": 75,
        "home_score_before": 0,
        "away_score_before": 0,
    }
    values.update(overrides)
    return NflversePlayRecord(**values)  # type: ignore[arg-type]


def test_complete_play_action_pass_normalizes_to_canonical_state() -> None:
    current = _row(
        pass_attempt=True,
        complete_pass=True,
        play_action=True,
        official_yards_gained=12,
        first_down=True,
        description="fixture completed pass",
    )
    following = _row(
        provider_play_id="120",
        quarter_seconds_remaining=800,
        down=1,
        distance=10,
        yards_to_goal=63,
    )

    bundle = normalize_nflverse_play(
        current,
        context=CONTEXT,
        canonical_sequence=7,
        drive_sequence=2,
        possession_sequence=3,
        next_record=following,
        next_drive_sequence=2,
        next_possession_sequence=3,
    )

    assert bundle.pre_play_state.play_id == play_id_for(GAME_ID, 7)
    assert bundle.execution.primary_play_type is PlayType.PASS
    assert PlayDesignModifier.PLAY_ACTION in bundle.execution.modifiers
    assert bundle.execution.semantic_label == "PLAY_ACTION_PASS"
    assert bundle.result.official_yards_gained == 12
    assert bundle.result.first_down
    assert [event.event_type for event in bundle.events] == [
        PlayEventType.SNAP,
        PlayEventType.THROW,
        PlayEventType.CATCH,
    ]
    assert bundle.state_after is not None
    assert bundle.state_after.down == 1
    assert bundle.state_after.yards_to_goal == 63
    assert bundle.state_after.drive_continues


def test_interception_uses_next_row_to_close_drive_and_change_possession() -> None:
    current = _row(
        pass_attempt=True,
        interception=True,
        official_yards_gained=0,
    )
    following = _row(
        provider_play_id="200",
        provider_drive_id="2",
        offense_team_code="AWY",
        defense_team_code="HOM",
        quarter_seconds_remaining=700,
        down=1,
        distance=10,
        yards_to_goal=80,
    )

    bundle = normalize_nflverse_play(
        current,
        context=CONTEXT,
        canonical_sequence=8,
        drive_sequence=2,
        possession_sequence=3,
        next_record=following,
        next_drive_sequence=3,
        next_possession_sequence=4,
    )

    assert bundle.result.interception
    assert bundle.result.possession_changed
    assert bundle.state_after is not None
    assert bundle.state_after.next_possession is not None
    assert bundle.state_after.next_possession.offense_team_season_id == AWAY_ID
    assert not bundle.state_after.drive_continues
    assert PlayEventType.INTERCEPTION in {event.event_type for event in bundle.events}


def test_penalty_only_no_play_preserves_physical_from_official_result() -> None:
    penalty = ProviderPenaltyRecord(
        team_code="HOM",
        penalty_type="False Start",
        disposition=PenaltyDisposition.ACCEPTED,
        yards=5,
        nullifies_play=True,
    )
    record = _row(
        no_play=True,
        official_yards_gained=5,
        physical_yards_gained=0,
        penalties=(penalty,),
    )

    bundle = normalize_nflverse_play(
        record,
        context=CONTEXT,
        canonical_sequence=9,
        drive_sequence=2,
        possession_sequence=3,
    )

    assert bundle.execution.primary_play_type is PlayType.PENALTY_ONLY
    assert bundle.result.no_play
    assert bundle.result.official_yards_gained is None
    assert bundle.result.physical_yards_gained == 0
    assert len(bundle.penalties) == 1
    assert bundle.penalties[0].penalty_type == "False Start"
    assert [event.event_type for event in bundle.events] == [PlayEventType.PENALTY]


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"qb_kneel": True}, PlayType.KNEEL),
        ({"qb_spike": True}, PlayType.SPIKE),
        ({"punt_attempt": True}, PlayType.PUNT),
        ({"field_goal_attempt": True}, PlayType.FIELD_GOAL),
        ({"kickoff_attempt": True}, PlayType.KICKOFF),
        ({"extra_point_attempt": True}, PlayType.EXTRA_POINT),
        ({"two_point_attempt": True}, PlayType.TWO_POINT),
        ({"sack": True}, PlayType.SACK),
        ({"qb_scramble": True}, PlayType.SCRAMBLE),
        ({"pass_attempt": True}, PlayType.PASS),
        ({"rush_attempt": True}, PlayType.RUSH),
        ({"timeout": True}, PlayType.TIMEOUT),
        ({"administrative": True}, PlayType.ADMINISTRATIVE),
    ],
)
def test_primary_play_taxonomy(overrides: dict[str, object], expected: PlayType) -> None:
    assert classify_play_type(_row(**overrides)) is expected


def test_rpo_marker_does_not_create_invalid_scramble_execution() -> None:
    bundle = normalize_nflverse_play(
        _row(qb_scramble=True, rpo=True),
        context=CONTEXT,
        canonical_sequence=10,
        drive_sequence=2,
        possession_sequence=3,
    )

    assert bundle.execution.primary_play_type is PlayType.SCRAMBLE
    assert PlayDesignModifier.RPO not in bundle.execution.modifiers


def test_missing_possession_teams_fails_closed() -> None:
    with pytest.raises(PlayNormalizationError, match="explicit offense and defense"):
        normalize_nflverse_play(
            _row(offense_team_code=None),
            context=CONTEXT,
            canonical_sequence=11,
            drive_sequence=2,
            possession_sequence=3,
        )
