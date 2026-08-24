"""Validate M6 nflverse extraction/normalization against a real PBP season."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import cast

import nflreadpy as nfl  # type: ignore[import-untyped]

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from daily_nfl.validation import validate_nflverse_pbp_rows  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, default=2025)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("local-data/m6b/pbp-normalization-validation-2025.json"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    season = int(args.season)
    frame = nfl.load_pbp([season])
    rows = cast(list[dict[str, object]], frame.to_dicts())
    result = validate_nflverse_pbp_rows(
        rows,
        row_count=frame.height,
        column_count=frame.width,
        id_prefix=f"m6b_{season}",
    )
    result["season"] = season

    output: Path = args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")

    summary = {
        "season": season,
        "row_count": result["row_count"],
        "extracted_and_normalized_count": result["extracted_and_normalized_count"],
        "extraction_error_count": result["extraction_error_count"],
        "normalization_error_count": result["normalization_error_count"],
        "canonical_play_type_counts": result["canonical_play_type_counts"],
        "extraction_error_play_types": result["extraction_error_play_types"],
        "next_state_adjacent_validated": result["next_state_adjacent_validated"],
        "next_state_nonadjacent_skipped": result["next_state_nonadjacent_skipped"],
        "next_state_error_count": result["next_state_error_count"],
        "output": str(output),
    }
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
