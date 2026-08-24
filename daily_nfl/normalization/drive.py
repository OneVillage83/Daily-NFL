"""Deterministic canonical drive construction from normalized M6 plays."""

from __future__ import annotations

from daily_nfl.domain import Drive
from daily_nfl.normalization.contracts import NormalizedPlayBundle


class DriveNormalizationError(ValueError):
    """Raised when play bundles cannot define one canonical drive without guessing."""


def normalize_drive(plays: tuple[NormalizedPlayBundle, ...]) -> Drive:
    """Build the defensible F-5 drive summary carried by normalized play state."""

    if not plays:
        raise DriveNormalizationError("drive normalization requires at least one play")
    ordered = tuple(sorted(plays, key=lambda item: item.canonical_sequence))
    if len({item.canonical_sequence for item in ordered}) != len(ordered):
        raise DriveNormalizationError("drive cannot contain duplicate canonical play sequences")

    first = ordered[0]
    drive_id = first.pre_play_state.drive_id
    segment_id = first.pre_play_state.possession_segment_id
    if drive_id is None or segment_id is None:
        raise DriveNormalizationError(
            "drive normalization requires canonical drive and possession-segment identity"
        )
    offense_id = first.pre_play_state.possession.offense_team_season_id
    defense_id = first.pre_play_state.possession.defense_team_season_id

    for item in ordered:
        pre = item.pre_play_state
        if item.game_id != first.game_id:
            raise DriveNormalizationError("one canonical drive cannot span multiple games")
        if pre.drive_id != drive_id:
            raise DriveNormalizationError("play bundles disagree on canonical drive identity")
        if pre.possession_segment_id != segment_id:
            raise DriveNormalizationError("one drive cannot span possession segments")
        if (
            pre.possession.offense_team_season_id != offense_id
            or pre.possession.defense_team_season_id != defense_id
        ):
            raise DriveNormalizationError("drive play bundles disagree on possession teams")

    last = ordered[-1]
    after = last.state_after
    return Drive(
        drive_id=drive_id,
        game_id=first.game_id,
        possession_segment_id=segment_id,
        offense_team_season_id=offense_id,
        defense_team_season_id=defense_id,
        start_play_id=first.pre_play_state.play_id,
        end_play_id=last.pre_play_state.play_id,
        start_period=first.pre_play_state.period,
        end_period=after.period if after is not None else None,
        start_clock_seconds_remaining=first.pre_play_state.clock_seconds_remaining,
        end_clock_seconds_remaining=(
            after.clock_seconds_remaining if after is not None else None
        ),
        start_yards_to_goal=first.pre_play_state.yards_to_goal,
        end_yards_to_goal=after.yards_to_goal if after is not None else None,
        play_count=len(ordered),
        first_downs=sum(int(item.result.first_down) for item in ordered),
        points=sum(item.result.score_change for item in ordered),
        turnover=any(
            item.result.interception or item.result.fumble_lost for item in ordered
        ),
    )
