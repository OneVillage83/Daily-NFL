"""Extract the M6 semantic play contract from real nflverse PBP rows."""

from __future__ import annotations

import math
from collections.abc import Mapping

from daily_nfl.domain import PenaltyDisposition
from daily_nfl.normalization.contracts import NflversePlayRecord, ProviderPenaltyRecord


class NflverseRowExtractionError(ValueError):
    """Raised when a real nflverse row cannot be converted without guessing."""


def _value(row: Mapping[str, object], key: str) -> object | None:
    value = row.get(key)
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def _text(row: Mapping[str, object], key: str) -> str | None:
    value = _value(row, key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _id_text(row: Mapping[str, object], key: str) -> str | None:
    value = _value(row, key)
    if value is None:
        return None
    if isinstance(value, bool):
        raise NflverseRowExtractionError(f"{key} cannot be boolean")
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    text = str(value).strip()
    return text or None


def _integer(row: Mapping[str, object], key: str, *, required: bool = False) -> int | None:
    value = _value(row, key)
    if value is None:
        if required:
            raise NflverseRowExtractionError(f"required nflverse field {key!r} is missing")
        return None
    if isinstance(value, bool):
        raise NflverseRowExtractionError(f"{key} cannot be boolean")
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    raise NflverseRowExtractionError(f"{key} must be an integer-compatible value")


def _flag(row: Mapping[str, object], key: str) -> bool:
    value = _value(row, key)
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes"}:
        return True
    if text in {"0", "false", "no", ""}:
        return False
    raise NflverseRowExtractionError(f"{key} is not a recognizable binary flag")


def _optional_flag(row: Mapping[str, object], key: str) -> bool | None:
    if _value(row, key) is None:
        return None
    return _flag(row, key)


def _score_pair(
    row: Mapping[str, object],
    *,
    post: bool,
) -> tuple[int, int] | None:
    home = _text(row, "home_team")
    away = _text(row, "away_team")
    offense = _text(row, "posteam")
    defense = _text(row, "defteam")
    if home is None or away is None or offense is None or defense is None:
        return None

    offense_key = "posteam_score_post" if post else "posteam_score"
    defense_key = "defteam_score_post" if post else "defteam_score"
    offense_score = _integer(row, offense_key)
    defense_score = _integer(row, defense_key)
    if offense_score is None or defense_score is None:
        return None

    if offense == home and defense == away:
        return offense_score, defense_score
    if offense == away and defense == home:
        return defense_score, offense_score
    raise NflverseRowExtractionError("possession teams do not match home/away teams")


def _canonical_timeout(value: int | None) -> int | None:
    """Treat provider sentinel values outside NFL timeout state as unknown."""
    if value is None or value < 0:
        return None
    return value


def _timeouts(row: Mapping[str, object]) -> tuple[int | None, int | None]:
    home = _text(row, "home_team")
    away = _text(row, "away_team")
    offense = _text(row, "posteam")
    defense = _text(row, "defteam")
    offense_timeouts = _canonical_timeout(_integer(row, "posteam_timeouts_remaining"))
    defense_timeouts = _canonical_timeout(_integer(row, "defteam_timeouts_remaining"))
    if home is None or away is None or offense is None or defense is None:
        return None, None
    if offense == home and defense == away:
        return offense_timeouts, defense_timeouts
    if offense == away and defense == home:
        return defense_timeouts, offense_timeouts
    raise NflverseRowExtractionError("possession teams do not match home/away teams")


def _penalty_disposition(description: str | None) -> PenaltyDisposition:
    lowered = (description or "").lower()
    if "offsetting" in lowered:
        return PenaltyDisposition.OFFSETTING
    if "declined" in lowered:
        return PenaltyDisposition.DECLINED
    return PenaltyDisposition.ACCEPTED


def _penalties(row: Mapping[str, object], *, no_play: bool) -> tuple[ProviderPenaltyRecord, ...]:
    if not _flag(row, "penalty"):
        return ()
    team_code = _text(row, "penalty_team")
    penalty_type = _text(row, "penalty_type")
    if team_code is None or penalty_type is None:
        raise NflverseRowExtractionError(
            "penalty flag is set but structured penalty team/type is missing"
        )
    return (
        ProviderPenaltyRecord(
            team_code=team_code,
            penalty_type=penalty_type,
            disposition=_penalty_disposition(_text(row, "desc")),
            player_external_id=_text(row, "penalty_player_id"),
            yards=_integer(row, "penalty_yards"),
            automatic_first_down=_flag(row, "first_down_penalty"),
            nullifies_play=no_play,
        ),
    )


def extract_nflverse_play_record(row: Mapping[str, object]) -> NflversePlayRecord:
    """Convert one real nflverse PBP row into the small M6 semantic contract.

    Base PBP does not contain FTN charting concepts such as play action, motion,
    screen, or RPO. Those fields intentionally remain false until an explicit
    enrichment source is joined later.
    """

    game_id = _id_text(row, "game_id")
    play_id = _id_text(row, "play_id")
    if game_id is None or play_id is None:
        raise NflverseRowExtractionError("game_id and play_id are required")

    play_type = (_text(row, "play_type") or "").lower()
    no_play = play_type == "no_play"
    pre_score = _score_pair(row, post=False)
    if pre_score is None:
        raise NflverseRowExtractionError("pre-play home/away score cannot be reconstructed")
    post_score = _score_pair(row, post=True)
    home_timeouts, away_timeouts = _timeouts(row)

    period = _integer(row, "qtr", required=True)
    clock = _integer(row, "quarter_seconds_remaining", required=True)
    yards_to_goal = _integer(row, "yardline_100", required=True)
    assert period is not None
    assert clock is not None
    assert yards_to_goal is not None

    return NflversePlayRecord(
        provider_game_id=game_id,
        provider_play_id=play_id,
        provider_drive_id=_id_text(row, "drive"),
        offense_team_code=_text(row, "posteam"),
        defense_team_code=_text(row, "defteam"),
        period=period,
        quarter_seconds_remaining=clock,
        down=_integer(row, "down"),
        distance=_integer(row, "ydstogo"),
        yards_to_goal=yards_to_goal,
        home_score_before=pre_score[0],
        away_score_before=pre_score[1],
        home_score_after=(post_score[0] if post_score is not None else None),
        away_score_after=(post_score[1] if post_score is not None else None),
        home_timeouts_remaining=home_timeouts,
        away_timeouts_remaining=away_timeouts,
        play_type_hint=play_type or None,
        description=_text(row, "desc"),
        official_yards_gained=(None if no_play else _integer(row, "yards_gained")),
        physical_yards_gained=None,
        pass_attempt=_flag(row, "pass_attempt"),
        rush_attempt=_flag(row, "rush_attempt"),
        qb_scramble=_flag(row, "qb_scramble"),
        qb_kneel=_flag(row, "qb_kneel"),
        qb_spike=_flag(row, "qb_spike"),
        sack=_flag(row, "sack"),
        complete_pass=_optional_flag(row, "complete_pass"),
        interception=_flag(row, "interception"),
        touchdown=_flag(row, "touchdown"),
        safety=_flag(row, "safety"),
        first_down=_flag(row, "first_down"),
        fumble=_flag(row, "fumble"),
        fumble_lost=_flag(row, "fumble_lost"),
        no_play=no_play,
        punt_attempt=_flag(row, "punt_attempt"),
        field_goal_attempt=_flag(row, "field_goal_attempt"),
        kickoff_attempt=_flag(row, "kickoff_attempt"),
        extra_point_attempt=_flag(row, "extra_point_attempt"),
        two_point_attempt=_flag(row, "two_point_attempt"),
        timeout=_flag(row, "timeout") or play_type == "timeout",
        administrative=_flag(row, "quarter_end") or play_type == "note",
        shotgun=_flag(row, "shotgun"),
        no_huddle=_flag(row, "no_huddle"),
        penalties=_penalties(row, no_play=no_play),
    )
