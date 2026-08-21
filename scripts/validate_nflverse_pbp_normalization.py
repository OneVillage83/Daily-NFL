"""Validate M6 nflverse extraction/normalization against a real PBP season."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import nflreadpy as nfl  # type: ignore[import-untyped]

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from daily_nfl.domain import GameId, TeamSeasonId  # noqa: E402
from daily_nfl.normalization import (  # noqa: E402
    NflverseGameContext,
    NflversePlayRecord,
    extract_nflverse_play_record,
    normalize_nflverse_play,
)


@dataclass(frozen=True, slots=True)
class ExtractedRow:
    record: NflversePlayRecord
    canonical_sequence: int
    drive_sequence: int | None
    possession_sequence: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, default=2025)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("local-data/m6b/pbp-normalization-validation-2025.json"),
    )
    return parser.parse_args()


def _context(game_id: str, home: str, away: str) -> NflverseGameContext:
    return NflverseGameContext(
        game_id=GameId(f"m6b_{game_id}"),
        home_team_code=home,
        away_team_code=away,
        home_team_season_id=TeamSeasonId(f"m6b_{game_id}_{home}"),
        away_team_season_id=TeamSeasonId(f"m6b_{game_id}_{away}"),
    )


def _record_context(row: dict[str, object], record: NflversePlayRecord) -> NflverseGameContext:
    home = str(row.get("home_team") or "").strip()
    away = str(row.get("away_team") or "").strip()
    if not home or not away:
        raise ValueError("home_team/away_team missing")
    return _context(record.provider_game_id, home, away)


def _reject_sample(row: dict[str, object]) -> dict[str, object]:
    keys = (
        "game_id",
        "play_id",
        "play_type",
        "desc",
        "qtr",
        "quarter_seconds_remaining",
        "yardline_100",
        "posteam",
        "defteam",
        "posteam_score",
        "defteam_score",
        "timeout",
        "quarter_end",
    )
    return {key: row.get(key) for key in keys}


def main() -> int:
    args = parse_args()
    season = int(args.season)
    frame = nfl.load_pbp([season])

    extraction_errors: Counter[str] = Counter()
    extraction_error_play_types: dict[str, Counter[str]] = defaultdict(Counter)
    extraction_error_samples: dict[str, list[dict[str, object]]] = defaultdict(list)
    normalization_errors: Counter[str] = Counter()
    taxonomy: Counter[str] = Counter()
    extracted_by_game: dict[str, list[ExtractedRow]] = defaultdict(list)
    context_by_game: dict[str, NflverseGameContext] = {}
    sequence_by_game: Counter[str] = Counter()
    possession_by_game: Counter[str] = Counter()
    last_offense_by_game: dict[str, str | None] = {}
    drive_maps: dict[str, dict[str, int]] = defaultdict(dict)
    representative: dict[str, dict[str, object]] = {}

    for raw_row in frame.to_dicts():
        row = dict(raw_row)
        try:
            record = extract_nflverse_play_record(row)
            context = _record_context(row, record)
        except (TypeError, ValueError) as exc:
            reason = str(exc)
            extraction_errors[reason] += 1
            play_type = str(row.get("play_type") or "<NULL>")
            extraction_error_play_types[reason][play_type] += 1
            if len(extraction_error_samples[reason]) < 5:
                extraction_error_samples[reason].append(_reject_sample(row))
            continue

        game_id = record.provider_game_id
        context_by_game.setdefault(game_id, context)
        sequence_by_game[game_id] += 1
        canonical_sequence = sequence_by_game[game_id]

        offense = record.offense_team_code
        if offense != last_offense_by_game.get(game_id):
            possession_by_game[game_id] += 1
            last_offense_by_game[game_id] = offense
        possession_sequence = possession_by_game[game_id]

        drive_sequence: int | None = None
        if record.provider_drive_id is not None:
            drive_map = drive_maps[game_id]
            if record.provider_drive_id not in drive_map:
                drive_map[record.provider_drive_id] = len(drive_map) + 1
            drive_sequence = drive_map[record.provider_drive_id]

        try:
            bundle = normalize_nflverse_play(
                record,
                context=context,
                canonical_sequence=canonical_sequence,
                drive_sequence=drive_sequence,
                possession_sequence=possession_sequence,
            )
        except (TypeError, ValueError) as exc:
            normalization_errors[str(exc)] += 1
            continue

        label = bundle.execution.primary_play_type.value
        taxonomy[label] += 1
        representative.setdefault(
            label,
            {
                "game_id": game_id,
                "provider_play_id": record.provider_play_id,
                "provider_drive_id": record.provider_drive_id,
                "description": record.description,
                "semantic_label": bundle.execution.semantic_label,
                "no_play": bundle.result.no_play,
            },
        )
        extracted_by_game[game_id].append(
            ExtractedRow(
                record=record,
                canonical_sequence=canonical_sequence,
                drive_sequence=drive_sequence,
                possession_sequence=possession_sequence,
            )
        )

    next_state_errors: Counter[str] = Counter()
    next_state_validated = 0
    sample_game_id = next(iter(extracted_by_game), None)
    if sample_game_id is not None:
        items = extracted_by_game[sample_game_id]
        context = context_by_game[sample_game_id]
        for current, following in zip(items, items[1:], strict=False):
            try:
                normalize_nflverse_play(
                    current.record,
                    context=context,
                    canonical_sequence=current.canonical_sequence,
                    drive_sequence=current.drive_sequence,
                    possession_sequence=current.possession_sequence,
                    next_record=following.record,
                    next_drive_sequence=following.drive_sequence,
                    next_possession_sequence=following.possession_sequence,
                )
            except (TypeError, ValueError) as exc:
                next_state_errors[str(exc)] += 1
            else:
                next_state_validated += 1

    extracted_count = sum(len(rows) for rows in extracted_by_game.values())
    result = {
        "season": season,
        "row_count": frame.height,
        "column_count": frame.width,
        "extracted_and_normalized_count": extracted_count,
        "extraction_error_count": sum(extraction_errors.values()),
        "normalization_error_count": sum(normalization_errors.values()),
        "extraction_errors": dict(extraction_errors.most_common()),
        "extraction_error_play_types": {
            reason: dict(counts.most_common())
            for reason, counts in extraction_error_play_types.items()
        },
        "extraction_error_samples": dict(extraction_error_samples),
        "normalization_errors": dict(normalization_errors.most_common()),
        "canonical_play_type_counts": dict(sorted(taxonomy.items())),
        "representative_normalized_rows": representative,
        "sample_game_id": sample_game_id,
        "next_state_validated": next_state_validated,
        "next_state_error_count": sum(next_state_errors.values()),
        "next_state_errors": dict(next_state_errors.most_common()),
    }

    output: Path = args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")

    summary = {
        "season": season,
        "row_count": frame.height,
        "extracted_and_normalized_count": extracted_count,
        "extraction_error_count": result["extraction_error_count"],
        "normalization_error_count": result["normalization_error_count"],
        "canonical_play_type_counts": result["canonical_play_type_counts"],
        "extraction_error_play_types": result["extraction_error_play_types"],
        "sample_game_id": sample_game_id,
        "next_state_validated": next_state_validated,
        "next_state_error_count": result["next_state_error_count"],
        "output": str(output),
    }
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
