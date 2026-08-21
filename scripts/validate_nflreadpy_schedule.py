"""Inspect a tiny nflreadpy schedule slice without bypassing raw-first production flow.

This is an M3 Lane-B validation utility only. Production acquisition continues
to use the provider adapter and immutable raw evidence path.
"""

from __future__ import annotations

import argparse
import json
from importlib.metadata import version

import nflreadpy as nfl  # type: ignore[import-untyped]

REQUIRED_COLUMNS = (
    "season",
    "game_id",
    "home_team",
    "away_team",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, default=2025)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    season: int = args.season
    frame = nfl.load_schedules(season)

    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise RuntimeError(f"nflreadpy schedule schema missing required columns: {missing}")
    if frame.height == 0:
        raise RuntimeError(f"nflreadpy returned no schedule rows for season {season}")

    seasons = frame.get_column("season").drop_nulls().unique().to_list()
    if seasons != [season]:
        raise RuntimeError(
            f"nflreadpy schedule season filter mismatch: expected {[season]}, found {seasons}"
        )

    first = frame.select(list(REQUIRED_COLUMNS)).head(1).to_dicts()[0]
    result = {
        "nflreadpy_version": version("nflreadpy"),
        "season": season,
        "row_count": frame.height,
        "column_count": frame.width,
        "required_columns": list(REQUIRED_COLUMNS),
        "required_schema": {
            column: str(frame.schema[column]) for column in REQUIRED_COLUMNS
        },
        "first_row": first,
    }
    print(json.dumps(result, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
