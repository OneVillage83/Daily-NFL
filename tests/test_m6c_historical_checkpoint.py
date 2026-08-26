import argparse
import json
from pathlib import Path

from daily_nfl.providers import NFLVERSE_DESCRIPTOR
from daily_nfl.validation import (
    M6C_CONTRACT_VERSION,
    M6C_VALIDATOR_VERSION,
    M6CStatus,
    classify_m6c_validation,
    document_sha256,
)
from daily_nfl.validation.nflverse_pbp import _rejected_action_family
from scripts.run_m6c_historical_checkpoint import (
    RawSeasonEvidence,
    _resolve_seasons,
    _season_manifest_entry,
    _valid_resumable_summary,
)


def _result(
    *,
    extraction_errors: dict[str, int] | None = None,
    play_types: dict[str, dict[str, int]] | None = None,
    action_types: dict[str, dict[str, int]] | None = None,
    normalization_errors: int = 0,
    next_state_errors: int = 0,
) -> dict[str, object]:
    reasons = extraction_errors or {}
    error_count = sum(reasons.values())
    row_count = 100
    return {
        "row_count": row_count,
        "column_count": 300,
        "extracted_and_normalized_count": row_count - error_count - normalization_errors,
        "extraction_error_count": error_count,
        "normalization_error_count": normalization_errors,
        "extraction_errors": reasons,
        "extraction_error_play_types": play_types or {},
        "extraction_error_action_types": action_types or {},
        "extraction_error_samples": {},
        "normalization_errors": {},
        "canonical_play_type_counts": {"PASS": row_count - error_count - normalization_errors},
        "representative_normalized_rows": {},
        "next_state_adjacent_validated": 80,
        "next_state_nonadjacent_skipped": 10,
        "next_state_error_count": next_state_errors,
        "next_state_errors": {},
    }


def test_m6c_known_null_no_play_exclusions_pass() -> None:
    result = _result(
        extraction_errors={"pre-play home/away score cannot be reconstructed": 5},
        play_types={
            "pre-play home/away score cannot be reconstructed": {
                "<NULL>": 2,
                "no_play": 3,
            }
        },
    )

    status, reasons = classify_m6c_validation(result)

    assert status is M6CStatus.PASS
    assert reasons == ()


def test_m6c_new_extraction_reason_requires_review() -> None:
    result = _result(
        extraction_errors={"new historical schema gap": 2},
        play_types={"new historical schema gap": {"<NULL>": 2}},
    )

    status, reasons = classify_m6c_validation(result)

    assert status is M6CStatus.REVIEW_REQUIRED
    assert reasons == ("new extraction reason: new historical schema gap",)


def test_m6c_excluded_core_play_family_fails() -> None:
    reason = "required nflverse field 'yardline_100' is missing"
    result = _result(
        extraction_errors={reason: 1},
        play_types={reason: {"pass": 1}},
    )

    status, reasons = classify_m6c_validation(result)

    assert status is M6CStatus.FAIL
    assert "excluded core/unreviewed play_type 'pass'" in reasons[0]


def test_m6c_null_play_type_cannot_hide_rejected_core_action() -> None:
    reason = "legacy structured penalty gap"
    result = _result(
        extraction_errors={reason: 1},
        play_types={reason: {"<NULL>": 1}},
        action_types={reason: {"RUSH": 1}},
    )

    status, reasons = classify_m6c_validation(result)

    assert status is M6CStatus.FAIL
    assert any(
        "excluded core action_family 'RUSH'" in reason_text
        for reason_text in reasons
    )


def _initial_review_placeholder(
    **overrides: object,
) -> dict[str, object]:
    row: dict[str, object] = {
        "game_id": "2010_01_DEN_JAX",
        "play_id": 1.0,
        "play_type": None,
        "desc": "*** play under review ***",
        "qtr": 1.0,
        "quarter_seconds_remaining": None,
        "yardline_100": None,
        "posteam_score": None,
        "defteam_score": None,
        "kickoff_attempt": 1.0,
    }
    row.update(overrides)
    return row


def test_m6c_initial_review_placeholder_is_administrative() -> None:
    row = _initial_review_placeholder()

    assert _rejected_action_family(row) == "ADMINISTRATIVE"


def test_m6c_review_placeholder_with_real_clock_stays_kickoff() -> None:
    row = _initial_review_placeholder(
        quarter_seconds_remaining=900.0,
    )

    assert _rejected_action_family(row) == "KICKOFF"


def test_m6c_real_opening_kickoff_stays_kickoff() -> None:
    row = _initial_review_placeholder(
        play_id=39.0,
        play_type="kickoff",
        desc="10-J.Scobee kicks 67 yards from JAX 30 to DEN 3.",
        quarter_seconds_remaining=900.0,
        yardline_100=30.0,
        posteam_score=0.0,
        defteam_score=0.0,
    )

    assert _rejected_action_family(row) == "KICKOFF"


def test_m6c_normalization_or_state_error_fails() -> None:
    result = _result(normalization_errors=1, next_state_errors=1)

    status, reasons = classify_m6c_validation(result)

    assert status is M6CStatus.FAIL
    assert "normalization_error_count=1" in reasons
    assert "next_state_error_count=1" in reasons


def test_m6c_document_fingerprint_is_deterministic_and_sensitive() -> None:
    first = {"season": 1999, "counts": {"PASS": 10, "RUSH": 5}}
    same_different_order = {"counts": {"RUSH": 5, "PASS": 10}, "season": 1999}
    changed = {"season": 1999, "counts": {"PASS": 11, "RUSH": 5}}

    assert document_sha256(first) == document_sha256(same_different_order)
    assert document_sha256(first) != document_sha256(changed)


def test_m6c_resume_requires_integrity_raw_identity_and_pass(tmp_path: Path) -> None:
    raw_path = tmp_path / "season.raw"
    raw_path.write_bytes(b"fixture")
    raw = RawSeasonEvidence(
        season=1999,
        evidence_id="evidence-1999",
        evidence_observation_id="reo-1999",
        sha256="a" * 64,
        raw_path=raw_path,
        source_uri="fixture://1999",
        size_bytes=7,
        acquisition_mode="REUSED_RAW",
    )
    summary: dict[str, object] = {
        "contract_version": M6C_CONTRACT_VERSION,
        "validator_version": M6C_VALIDATOR_VERSION,
        "season": 1999,
        "evidence_id": raw.evidence_id,
        "raw_sha256": raw.sha256,
        "parser_version": NFLVERSE_DESCRIPTOR.parser_version,
        "validation_status": M6CStatus.PASS.value,
        "validation_fingerprint": "fingerprint",
        "validation": _result(),
    }
    summary["summary_sha256"] = document_sha256(summary)
    path = tmp_path / "season-1999.json"
    path.write_text(json.dumps(summary), encoding="utf-8")

    assert _valid_resumable_summary(path, season=1999, raw=raw) is not None

    corrupted = json.loads(path.read_text(encoding="utf-8"))
    corrupted["validation_status"] = M6CStatus.FAIL.value
    path.write_text(json.dumps(corrupted), encoding="utf-8")
    assert _valid_resumable_summary(path, season=1999, raw=raw) is None


def test_m6c_manifest_separates_acquisition_and_execution_modes() -> None:
    summary: dict[str, object] = {
        "season": 2025,
        "validation_status": M6CStatus.PASS.value,
        "validation_reasons": [],
        "evidence_id": "evidence-2025",
        "evidence_observation_id": "reo-2025",
        "raw_sha256": "a" * 64,
        "raw_size_bytes": 123,
        "acquisition_mode": "ACQUIRED",
        "validation_fingerprint": "fingerprint-2025",
        "reproducibility_match": True,
    }
    original = dict(summary)

    entry = _season_manifest_entry(
        summary,
        execution_mode="RESUMED_VALIDATION",
        raw_resolution_mode="REUSED_RAW",
    )

    assert summary == original
    assert summary["acquisition_mode"] == "ACQUIRED"
    assert entry["validation_acquisition_mode"] == "ACQUIRED"
    assert entry["raw_resolution_mode"] == "REUSED_RAW"
    assert entry["execution_mode"] == "RESUMED_VALIDATION"


def test_m6c_manifest_rejects_unknown_execution_mode() -> None:
    summary: dict[str, object] = {
        "season": 2025,
        "validation_status": M6CStatus.PASS.value,
        "validation_reasons": [],
        "evidence_id": "evidence-2025",
        "evidence_observation_id": "reo-2025",
        "raw_sha256": "a" * 64,
        "raw_size_bytes": 123,
        "acquisition_mode": "ACQUIRED",
        "validation_fingerprint": "fingerprint-2025",
        "reproducibility_match": True,
    }

    try:
        _season_manifest_entry(
            summary,
            execution_mode="UNKNOWN_MODE",
            raw_resolution_mode="REUSED_RAW",
        )
    except ValueError as exc:
        assert "unsupported M6C execution mode" in str(exc)
    else:
        raise AssertionError("unknown execution mode must fail closed")


def test_m6c_manifest_rejects_unknown_raw_resolution_mode() -> None:
    summary: dict[str, object] = {
        "season": 2025,
        "validation_status": M6CStatus.PASS.value,
        "validation_reasons": [],
        "evidence_id": "evidence-2025",
        "evidence_observation_id": "reo-2025",
        "raw_sha256": "a" * 64,
        "raw_size_bytes": 123,
        "acquisition_mode": "ACQUIRED",
        "validation_fingerprint": "fingerprint-2025",
        "reproducibility_match": True,
    }

    try:
        _season_manifest_entry(
            summary,
            execution_mode="RESUMED_VALIDATION",
            raw_resolution_mode="UNKNOWN_MODE",
        )
    except ValueError as exc:
        assert "unsupported M6C raw resolution mode" in str(exc)
    else:
        raise AssertionError("unknown raw resolution mode must fail closed")


def test_m6c_season_selection_supports_sentinel_full_and_ranges() -> None:
    sentinel = argparse.Namespace(
        seasons=None,
        start_season=None,
        end_season=None,
        gate="sentinel",
    )
    full = argparse.Namespace(
        seasons=None,
        start_season=None,
        end_season=None,
        gate="full",
    )
    narrowed = argparse.Namespace(
        seasons=None,
        start_season=2010,
        end_season=2012,
        gate="sentinel",
    )

    assert _resolve_seasons(sentinel) == (1999, 2005, 2010, 2015, 2020, 2025)
    assert _resolve_seasons(full) == tuple(range(1999, 2026))
    assert _resolve_seasons(narrowed) == (2010, 2011, 2012)
