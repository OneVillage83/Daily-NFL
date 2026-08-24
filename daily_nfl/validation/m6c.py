"""M6C historical-continuation classification and manifest helpers."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from enum import StrEnum
from typing import cast

M6C_CONTRACT_VERSION = "M6C_HISTORICAL_CHECKPOINT_V1"
M6C_VALIDATOR_VERSION = "M6C_PBP_VALIDATOR_V1"

KNOWN_EXTRACTION_REASONS = frozenset(
    {
        "pre-play home/away score cannot be reconstructed",
        "required nflverse field 'quarter_seconds_remaining' is missing",
        "required nflverse field 'yardline_100' is missing",
    }
)
ALLOWED_EXCLUDED_PLAY_TYPES = frozenset({"<NULL>", "no_play"})


class M6CStatus(StrEnum):
    PASS = "PASS"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    FAIL = "FAIL"


def document_sha256(document: Mapping[str, object]) -> str:
    """Return a deterministic SHA-256 for one JSON-compatible document."""

    encoded = json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _int_value(result: Mapping[str, object], key: str) -> int:
    value = result.get(key)
    if not isinstance(value, int):
        raise ValueError(f"validation result field {key!r} must be an integer")
    return value


def classify_m6c_validation(
    result: Mapping[str, object],
) -> tuple[M6CStatus, tuple[str, ...]]:
    """Classify one season under the locked M6C fail-closed policy."""

    reasons: list[str] = []
    review_reasons: list[str] = []

    row_count = _int_value(result, "row_count")
    extracted = _int_value(result, "extracted_and_normalized_count")
    extraction_errors = _int_value(result, "extraction_error_count")
    normalization_errors = _int_value(result, "normalization_error_count")
    next_state_errors = _int_value(result, "next_state_error_count")

    if row_count <= 0:
        reasons.append("provider season contains no rows")
    if normalization_errors != 0:
        reasons.append(f"normalization_error_count={normalization_errors}")
    if next_state_errors != 0:
        reasons.append(f"next_state_error_count={next_state_errors}")
    if extracted + extraction_errors + normalization_errors != row_count:
        reasons.append(
            "row accounting mismatch: normalized + extraction errors + normalization errors "
            "does not equal row_count"
        )

    raw_error_reasons = result.get("extraction_errors")
    if not isinstance(raw_error_reasons, dict):
        raise ValueError("validation result extraction_errors must be a mapping")
    error_reasons = cast(dict[str, int], raw_error_reasons)
    for reason, count in error_reasons.items():
        if count > 0 and reason not in KNOWN_EXTRACTION_REASONS:
            review_reasons.append(f"new extraction reason: {reason}")

    raw_play_types = result.get("extraction_error_play_types")
    if not isinstance(raw_play_types, dict):
        raise ValueError("validation result extraction_error_play_types must be a mapping")
    play_types_by_reason = cast(dict[str, dict[str, int]], raw_play_types)
    for reason, play_types in play_types_by_reason.items():
        for play_type, count in play_types.items():
            if count > 0 and play_type not in ALLOWED_EXCLUDED_PLAY_TYPES:
                reasons.append(
                    f"excluded core/unreviewed play_type {play_type!r} under reason {reason!r}"
                )

    if reasons:
        return M6CStatus.FAIL, tuple(sorted(set(reasons + review_reasons)))
    if review_reasons:
        return M6CStatus.REVIEW_REQUIRED, tuple(sorted(set(review_reasons)))
    return M6CStatus.PASS, ()
