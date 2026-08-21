"""Inspect one completed nflverse PBP season for M6B contract validation."""

from __future__ import annotations

import argparse
import json
from importlib.metadata import version
from pathlib import Path

import nflreadpy as nfl  # type: ignore[import-untyped]
import polars as pl

CANDIDATE_COLUMNS = (
    "play_id",
    "game_id",
    "home_team",
    "away_team",
    "posteam",
    "defteam",
    "qtr",
    "quarter_seconds_remaining",
    "down",
    "ydstogo",
    "yardline_100",
    "drive",
    "desc",
    "play_type",
    "yards_gained",
    "total_home_score",
    "total_away_score",
    "posteam_score",
    "defteam_score",
    "posteam_score_post",
    "defteam_score_post",
    "posteam_timeouts_remaining",
    "defteam_timeouts_remaining",
    "pass_attempt",
    "rush_attempt",
    "qb_scramble",
    "qb_kneel",
    "qb_spike",
    "sack",
    "complete_pass",
    "interception",
    "touchdown",
    "safety",
    "first_down",
    "fumble",
    "fumble_lost",
    "no_play",
    "punt_attempt",
    "field_goal_attempt",
    "kickoff_attempt",
    "extra_point_attempt",
    "two_point_attempt",
    "timeout",
    "quarter_end",
    "penalty",
    "penalty_team",
    "penalty_type",
    "penalty_yards",
    "penalty_player_id",
    "first_down_penalty",
    "shotgun",
    "no_huddle",
    "play_action",
    "rpo",
    "screen",
    "motion",
    "shift",
    "designed_qb_run",
)

SAMPLE_FLAGS = (
    "pass_attempt",
    "rush_attempt",
    "qb_scramble",
    "sack",
    "qb_kneel",
    "qb_spike",
    "punt_attempt",
    "field_goal_attempt",
    "kickoff_attempt",
    "extra_point_attempt",
    "two_point_attempt",
    "interception",
    "fumble_lost",
    "no_play",
    "penalty",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, default=2025)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("local-data/m6b/pbp-inspection-2025.json"),
    )
    return parser.parse_args()


def _first_flagged_row(
    frame: pl.DataFrame,
    flag: str,
    selected_columns: list[str],
) -> dict[str, object] | None:
    if flag not in frame.columns:
        return None
    rows = (
        frame.filter(pl.col(flag).fill_null(0) == 1)
        .select(selected_columns)
        .head(1)
        .to_dicts()
    )
    return rows[0] if rows else None


def main() -> int:
    args = parse_args()
    season = int(args.season)
    if season < 1999:
        raise ValueError("nflverse PBP is available from the 1999 season")

    frame = nfl.load_pbp([season])
    available_columns = [column for column in CANDIDATE_COLUMNS if column in frame.columns]
    missing_columns = [column for column in CANDIDATE_COLUMNS if column not in frame.columns]

    candidate_schema = {
        column: str(frame.schema[column])
        for column in available_columns
    }
    non_null_counts_row = frame.select(
        [pl.col(column).is_not_null().sum().alias(column) for column in available_columns]
    ).to_dicts()[0]

    play_type_counts: list[dict[str, object]] = []
    if "play_type" in frame.columns:
        play_type_counts = (
            frame.group_by("play_type")
            .len()
            .sort("len", descending=True)
            .to_dicts()
        )

    samples = {
        flag: _first_flagged_row(frame, flag, available_columns)
        for flag in SAMPLE_FLAGS
    }

    sample_game_rows: list[dict[str, object]] = []
    sample_game_id: str | None = None
    if "game_id" in frame.columns:
        game_ids = frame.select("game_id").drop_nulls().unique(maintain_order=True).to_series()
        if len(game_ids) > 0:
            sample_game_id = str(game_ids[0])
            sample_game_rows = (
                frame.filter(pl.col("game_id") == sample_game_id)
                .select(available_columns)
                .head(12)
                .to_dicts()
            )

    result = {
        "season": season,
        "nflreadpy_version": version("nflreadpy"),
        "row_count": frame.height,
        "column_count": frame.width,
        "candidate_schema": candidate_schema,
        "candidate_non_null_counts": non_null_counts_row,
        "missing_candidate_columns": missing_columns,
        "play_type_counts": play_type_counts,
        "representative_rows": samples,
        "sample_game_id": sample_game_id,
        "sample_game_rows": sample_game_rows,
    }

    output: Path = args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )

    summary = {
        "season": season,
        "nflreadpy_version": result["nflreadpy_version"],
        "row_count": frame.height,
        "column_count": frame.width,
        "available_candidate_columns": len(available_columns),
        "missing_candidate_columns": missing_columns,
        "sample_game_id": sample_game_id,
        "output": str(output),
    }
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
