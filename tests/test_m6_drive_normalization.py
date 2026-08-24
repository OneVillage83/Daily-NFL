import pytest

from daily_nfl.domain import GameId, TeamSeasonId
from daily_nfl.normalization import (
    DriveNormalizationError,
    NflverseGameContext,
    NflversePlayRecord,
    normalize_drive,
    normalize_nflverse_play,
)

GAME_ID = GameId("nflg_m6_drive")
HOME_ID = TeamSeasonId("tms_home")
AWAY_ID = TeamSeasonId("tms_away")
CONTEXT = NflverseGameContext(
    game_id=GAME_ID,
    home_team_code="HOM",
    away_team_code="AWY",
    home_team_season_id=HOME_ID,
    away_team_season_id=AWAY_ID,
)


def _record(*, play_id: str, raw_index: int, yards_to_goal: int, first_down: bool = False) -> NflversePlayRecord:
    return NflversePlayRecord(
        provider_game_id="2026_01_AWY_HOM",
        provider_play_id=play_id,
        provider_drive_id="1",
        offense_team_code="HOM",
        defense_team_code="AWY",
        period=1,
        quarter_seconds_remaining=840 - (raw_index * 30),
        down=1,
        distance=10,
        yards_to_goal=yards_to_goal,
        home_score_before=0,
        away_score_before=0,
        source_row_index=raw_index,
        rush_attempt=True,
        official_yards_gained=10 if first_down else 4,
        first_down=first_down,
    )


def test_normalize_drive_summarizes_consistent_canonical_play_sequence() -> None:
    first_record = _record(play_id="100", raw_index=1, yards_to_goal=75, first_down=True)
    second_record = _record(play_id="110", raw_index=2, yards_to_goal=65)
    third_record = _record(play_id="120", raw_index=3, yards_to_goal=61)

    first = normalize_nflverse_play(
        first_record,
        context=CONTEXT,
        canonical_sequence=1,
        drive_sequence=1,
        possession_sequence=1,
        next_record=second_record,
        next_drive_sequence=1,
        next_possession_sequence=1,
    )
    second = normalize_nflverse_play(
        second_record,
        context=CONTEXT,
        canonical_sequence=2,
        drive_sequence=1,
        possession_sequence=1,
        next_record=third_record,
        next_drive_sequence=1,
        next_possession_sequence=1,
    )
    third = normalize_nflverse_play(
        third_record,
        context=CONTEXT,
        canonical_sequence=3,
        drive_sequence=1,
        possession_sequence=1,
    )

    drive = normalize_drive((third, first, second))

    assert drive.game_id == GAME_ID
    assert drive.start_play_id == first.pre_play_state.play_id
    assert drive.end_play_id == third.pre_play_state.play_id
    assert drive.play_count == 3
    assert drive.first_downs == 1
    assert drive.points == 0
    assert drive.turnover is False
    assert drive.start_yards_to_goal == 75
    assert drive.end_yards_to_goal is None


def test_normalize_drive_rejects_mixed_drive_identity() -> None:
    first = normalize_nflverse_play(
        _record(play_id="100", raw_index=1, yards_to_goal=75),
        context=CONTEXT,
        canonical_sequence=1,
        drive_sequence=1,
        possession_sequence=1,
    )
    second = normalize_nflverse_play(
        _record(play_id="110", raw_index=2, yards_to_goal=71),
        context=CONTEXT,
        canonical_sequence=2,
        drive_sequence=2,
        possession_sequence=1,
    )

    with pytest.raises(DriveNormalizationError, match="drive identity"):
        normalize_drive((first, second))
