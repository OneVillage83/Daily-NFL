"""Reusable real-data validation for the certified M6 nflverse PBP boundary."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass, replace

from daily_nfl.domain import GameId, PlayerId, TeamSeasonId
from daily_nfl.normalization import (
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


def _context(
    *,
    id_prefix: str,
    game_id: str,
    home: str,
    away: str,
    player_ids: dict[str, PlayerId],
) -> NflverseGameContext:
    return NflverseGameContext(
        game_id=GameId(f"{id_prefix}_{game_id}"),
        home_team_code=home,
        away_team_code=away,
        home_team_season_id=TeamSeasonId(f"{id_prefix}_{game_id}_{home}"),
        away_team_season_id=TeamSeasonId(f"{id_prefix}_{game_id}_{away}"),
        player_ids_by_external_id=player_ids,
    )


def _record_context(
    row: dict[str, object],
    record: NflversePlayRecord,
    player_ids: dict[str, PlayerId],
    *,
    id_prefix: str,
) -> NflverseGameContext:
    home = str(row.get("home_team") or "").strip()
    away = str(row.get("away_team") or "").strip()
    if not home or not away:
        raise ValueError("home_team/away_team missing")
    return _context(
        id_prefix=id_prefix,
        game_id=record.provider_game_id,
        home=home,
        away=away,
        player_ids=player_ids,
    )


def _provider_player_ids(record: NflversePlayRecord) -> tuple[str, ...]:
    values = [item.player_external_id for item in record.participants]
    values.extend(
        penalty.player_external_id
        for penalty in record.penalties
        if penalty.player_external_id is not None
    )
    return tuple(values)


def _ensure_validation_player_ids(
    *,
    id_prefix: str,
    game_id: str,
    record: NflversePlayRecord,
    player_ids: dict[str, PlayerId],
) -> None:
    """Allocate opaque in-memory IDs only to exercise normalization contracts."""

    for external_id in _provider_player_ids(record):
        if external_id not in player_ids:
            ordinal = len(player_ids) + 1
            player_ids[external_id] = PlayerId(
                f"{id_prefix}_ply_{game_id}_{ordinal:03d}"
            )


def _reject_sample(row: dict[str, object], raw_index: int) -> dict[str, object]:
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
    sample = {key: row.get(key) for key in keys}
    sample["raw_row_index"] = raw_index
    return sample


def _raw_flag(row: dict[str, object], key: str) -> bool:
    value = row.get(key)
    if value is None:
        return False
    if isinstance(value, float) and math.isnan(value):
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0

    text = str(value).strip().lower()
    return text in {"1", "true", "yes"}


def _raw_missing(row: dict[str, object], key: str) -> bool:
    value = row.get(key)
    return value is None or (
        isinstance(value, float) and math.isnan(value)
    )


def _is_initial_review_placeholder(row: dict[str, object]) -> bool:
    """Identify the exact audited 2010 provider review-placeholder shape."""

    return (
        str(row.get("desc") or "").strip() == "*** play under review ***"
        and row.get("play_id") == 1
        and not str(row.get("play_type") or "").strip()
        and row.get("qtr") == 1
        and _raw_missing(row, "quarter_seconds_remaining")
        and _raw_missing(row, "yardline_100")
        and _raw_missing(row, "posteam_score")
        and _raw_missing(row, "defteam_score")
        and _raw_flag(row, "kickoff_attempt")
    )


def _rejected_action_family(row: dict[str, object]) -> str:
    """Classify rejected rows from structured provider facts when possible."""

    if _is_initial_review_placeholder(row):
        return "ADMINISTRATIVE"

    hint = str(row.get("play_type") or "").strip().lower().replace("-", "_")

    if hint == "no_play" and _raw_flag(row, "penalty"):
        return "PENALTY_ONLY"
    if _raw_flag(row, "qb_kneel") or hint in {"qb_kneel", "kneel"}:
        return "KNEEL"
    if _raw_flag(row, "qb_spike") or hint in {"qb_spike", "spike"}:
        return "SPIKE"
    if _raw_flag(row, "punt_attempt") or hint == "punt":
        return "PUNT"
    if _raw_flag(row, "field_goal_attempt") or hint in {
        "field_goal",
        "field_goal_attempt",
    }:
        return "FIELD_GOAL"
    if _raw_flag(row, "kickoff_attempt") or hint == "kickoff":
        return "KICKOFF"
    if _raw_flag(row, "extra_point_attempt") or hint in {
        "extra_point",
        "extra_point_attempt",
    }:
        return "EXTRA_POINT"
    if _raw_flag(row, "two_point_attempt") or hint in {
        "two_point",
        "two_point_attempt",
    }:
        return "TWO_POINT"
    if _raw_flag(row, "sack") or hint == "sack":
        return "SACK"
    if _raw_flag(row, "qb_scramble") or hint in {"qb_scramble", "scramble"}:
        return "SCRAMBLE"
    if _raw_flag(row, "pass_attempt") or hint == "pass":
        return "PASS"
    if _raw_flag(row, "rush_attempt") or hint in {"run", "rush"}:
        return "RUSH"
    if _raw_flag(row, "timeout") or hint == "timeout":
        return "TIMEOUT"
    if _raw_flag(row, "quarter_end") or hint in {
        "note",
        "administrative",
        "end_game",
        "end_period",
        "game_start",
        "quarter_end",
    }:
        return "ADMINISTRATIVE"

    return "<UNKNOWN>"


def validate_nflverse_pbp_rows(
    rows: list[dict[str, object]],
    *,
    row_count: int,
    column_count: int,
    id_prefix: str,
) -> dict[str, object]:
    """Validate one ordered nflverse PBP season without persisting validation IDs."""

    if row_count != len(rows):
        raise ValueError("row_count must equal the supplied row collection length")
    if row_count < 1:
        raise ValueError("PBP validation requires at least one row")
    if column_count < 1:
        raise ValueError("column_count must be positive")
    if not id_prefix.strip():
        raise ValueError("id_prefix cannot be blank")

    extraction_errors: Counter[str] = Counter()
    extraction_error_play_types: dict[str, Counter[str]] = defaultdict(Counter)
    extraction_error_action_types: dict[str, Counter[str]] = defaultdict(Counter)
    extraction_error_samples: dict[str, list[dict[str, object]]] = defaultdict(list)
    normalization_errors: Counter[str] = Counter()
    taxonomy: Counter[str] = Counter()
    extracted_by_game: dict[str, list[ExtractedRow]] = defaultdict(list)
    context_by_game: dict[str, NflverseGameContext] = {}
    player_ids_by_game: dict[str, dict[str, PlayerId]] = defaultdict(dict)
    sequence_by_game: Counter[str] = Counter()
    possession_by_game: Counter[str] = Counter()
    last_offense_by_game: dict[str, str | None] = {}
    drive_maps: dict[str, dict[str, int]] = defaultdict(dict)
    representative: dict[str, dict[str, object]] = {}

    first_raw_index_by_game: dict[str, int] = {}
    for raw_index, raw_row in enumerate(rows):
        game_id = str(raw_row.get("game_id") or "").strip()
        if game_id:
            first_raw_index_by_game.setdefault(game_id, raw_index)

    for raw_index, raw_row in enumerate(rows):
        row = dict(raw_row)
        try:
            raw_game_id = str(row.get("game_id") or "").strip()
            extracted = extract_nflverse_play_record(
                row,
                game_opening_row=(
                    bool(raw_game_id)
                    and first_raw_index_by_game.get(raw_game_id) == raw_index
                ),
            )
            record = replace(extracted, source_row_index=raw_index)
            player_ids = player_ids_by_game[record.provider_game_id]
            _ensure_validation_player_ids(
                id_prefix=id_prefix,
                game_id=record.provider_game_id,
                record=record,
                player_ids=player_ids,
            )
            context = _record_context(
                row,
                record,
                player_ids,
                id_prefix=id_prefix,
            )
        except (TypeError, ValueError) as exc:
            reason = str(exc)
            extraction_errors[reason] += 1
            play_type = str(row.get("play_type") or "<NULL>")
            extraction_error_play_types[reason][play_type] += 1
            extraction_error_action_types[reason][_rejected_action_family(row)] += 1
            if len(extraction_error_samples[reason]) < 5:
                extraction_error_samples[reason].append(_reject_sample(row, raw_index))
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
                "raw_row_index": raw_index,
                "description": record.description,
                "semantic_label": bundle.execution.semantic_label,
                "no_play": bundle.result.no_play,
                "participation_count": len(bundle.participation),
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
    next_state_nonadjacent_skipped = 0
    for game_id, items in extracted_by_game.items():
        context = context_by_game[game_id]
        for current, following in zip(items, items[1:], strict=False):
            current_index = current.record.source_row_index
            following_index = following.record.source_row_index
            if (
                current_index is None
                or following_index is None
                or following_index != current_index + 1
            ):
                next_state_nonadjacent_skipped += 1
                continue
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

    extracted_count = sum(len(game_rows) for game_rows in extracted_by_game.values())
    return {
        "row_count": row_count,
        "column_count": column_count,
        "extracted_and_normalized_count": extracted_count,
        "extraction_error_count": sum(extraction_errors.values()),
        "normalization_error_count": sum(normalization_errors.values()),
        "extraction_errors": dict(extraction_errors.most_common()),
        "extraction_error_play_types": {
            reason: dict(counts.most_common())
            for reason, counts in extraction_error_play_types.items()
        },
        "extraction_error_action_types": {
            reason: dict(counts.most_common())
            for reason, counts in extraction_error_action_types.items()
        },
        "extraction_error_samples": dict(extraction_error_samples),
        "normalization_errors": dict(normalization_errors.most_common()),
        "canonical_play_type_counts": dict(sorted(taxonomy.items())),
        "representative_normalized_rows": representative,
        "next_state_adjacent_validated": next_state_validated,
        "next_state_nonadjacent_skipped": next_state_nonadjacent_skipped,
        "next_state_error_count": sum(next_state_errors.values()),
        "next_state_errors": dict(next_state_errors.most_common()),
    }
