import pytest

from daily_nfl.domain import PenaltyDisposition
from daily_nfl.normalization import NflverseRowExtractionError, extract_nflverse_play_record


def _row(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "game_id": "2025_01_ARI_NO",
        "play_id": 55,
        "drive": 1,
        "home_team": "NO",
        "away_team": "ARI",
        "posteam": "ARI",
        "defteam": "NO",
        "qtr": 1,
        "quarter_seconds_remaining": 840.0,
        "down": 1.0,
        "ydstogo": 10.0,
        "yardline_100": 75.0,
        "posteam_score": 0.0,
        "defteam_score": 0.0,
        "posteam_score_post": 0.0,
        "defteam_score_post": 0.0,
        "posteam_timeouts_remaining": 3.0,
        "defteam_timeouts_remaining": 3.0,
        "desc": "fixture",
        "play_type": "pass",
        "yards_gained": 12.0,
        "pass_attempt": 1.0,
        "complete_pass": 1.0,
        "first_down": 1.0,
        "shotgun": 1.0,
    }
    values.update(overrides)
    return values


def test_extracts_scores_in_home_away_orientation() -> None:
    record = extract_nflverse_play_record(
        _row(
            posteam_score=7.0,
            defteam_score=10.0,
            posteam_score_post=14.0,
            defteam_score_post=10.0,
        )
    )
    assert (record.home_score_before, record.away_score_before) == (10, 7)
    assert (record.home_score_after, record.away_score_after) == (10, 14)
    assert record.official_yards_gained == 12
    assert record.shotgun


def test_no_play_comes_from_play_type() -> None:
    record = extract_nflverse_play_record(
        _row(
            play_type="no_play",
            yards_gained=None,
            pass_attempt=0.0,
            complete_pass=None,
            penalty=1.0,
            penalty_team="NO",
            penalty_type="Offside",
            penalty_yards=5.0,
        )
    )
    assert record.no_play
    assert record.official_yards_gained is None
    assert record.physical_yards_gained is None
    assert record.penalties[0].disposition is PenaltyDisposition.ACCEPTED
    assert record.penalties[0].nullifies_play


def test_base_pbp_does_not_infer_ftn_modifiers() -> None:
    record = extract_nflverse_play_record(_row())
    assert not record.play_action
    assert not record.rpo
    assert not record.screen
    assert not record.motion
    assert not record.shift
    assert not record.designed_qb_run


def test_missing_preplay_score_fails_closed() -> None:
    with pytest.raises(NflverseRowExtractionError, match="pre-play home/away score"):
        extract_nflverse_play_record(_row(posteam_score=None))
