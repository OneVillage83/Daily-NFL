# M6C Gate A V2 — Revalidation Result

**Project:** The Daily Line — Daily NFL
**Checkpoint:** M6C — Controlled Historical Continuation / Full Historical Compatibility
**Status:** GATE A OPEN — 2010 ONLY BLOCKED
**Executable authority:** `695f30f175cf70468c38b79e4150592b6ed692a9`
**Validator:** `M6C_PBP_VALIDATOR_V2`

This document records the exact-head remediation validation and the first Gate-A rerun after the 1999/2010 historical extraction hardening.

---

## 1. Remediation executable

Commit:

```text
695f30f175cf70468c38b79e4150592b6ed692a9
Harden M6C historical extraction semantics
```

The commit:

- permits 0-0 pre-score reconstruction only for an explicitly proven first raw-row game-opening kickoff at Q1 15:00 with both pre-score fields unavailable;
- preserves a structured penalty with known team but unavailable type using reserved type `UNKNOWN` rather than dropping the play or inferring a foul from prose;
- still fails closed when penalty team is unavailable;
- adds rejected-row action-family accounting from structured provider action flags so nullable provider `play_type` cannot hide rejected core PASS/RUSH/etc. rows;
- bumps the historical validator from V1 to V2 so prior summaries cannot be resumed as equivalent evidence.

---

## 2. Exact-head local quality gate

Certified interpreter:

```text
Python 3.12.10
E:\Daily-NFL\.venv\Scripts\python.exe
```

Exact committed SHA validation:

```text
focused M6/M6C regression tests: 44 passed
Ruff: All checks passed
mypy: Success — 95 source files
full pytest: 183 passed
git diff --check: PASS
git status --short: clean
```

A prior validation attempt accidentally ran after the project venv had been deactivated and used `C:\Python314\python.exe`. That attempt failed because Polars/Ruff/mypy were not installed in the system interpreter. It is explicitly **non-authoritative environment evidence** and is not treated as a Daily-NFL code failure.

---

## 3. Gate A V2 command

```text
python scripts/run_m6c_historical_checkpoint.py \
    --gate sentinel \
    --revalidate \
    --database local-data/m6c/m6c-history.db \
    --raw-root local-data/m6c/raw \
    --output-root local-data/m6c/validation
```

All six seasons reused previously stored raw evidence; no sentinel asset was reacquired.

---

## 4. Gate A V2 season results

```text
1999  PASS  449ea036dec6b782335c518125e8aa8f88dc5ab7800958789c967c07222bcd9b
2005  PASS  d5a2f357b97bdec17d9dbd1df52d2e47fef1f7e38cdf5ad124f7378a24cfb796
2010  FAIL  539809d9618786a111e5a8a9915a63d3ae5685e2031b61785268e583b7c20702
2015  PASS  e38576c5954367147796b68263e4530ba7c31e6a74f0250bcf8b7af942cb5917
2020  PASS  55fc4ef101df4f2167e92b0ae548aafe513bc92255d2a4e87323d068299d71ac
2025  PASS  d66f08ec2dbd884ba611af590b51c83251fb3cbda1964cfee6f72b9f6b6b8f8e
```

The remediation successfully moves 1999 from FAIL to PASS.

2010 remains the only blocked sentinel and must be inspected under the stricter V2 rejected-action accounting before any further architecture or allowlist change.

---

## 5. Aggregate V2 manifest

```text
overall_status: FAIL
season_count: 6
schema_version: 7
row_count: 284,449
extracted_and_normalized_count: 267,143
extraction_error_count: 17,306
normalization_error_count: 0
next_state_adjacent_validated: 251,607
next_state_nonadjacent_skipped: 13,923
next_state_error_count: 0
raw_size_bytes: 106,230,513
manifest_sha256: b8b1fbf75d0e26cdb9f7d57376af1641d33a405a68a0f9dab10ad23c8285e5a0
```

Compared with Gate A V1, V2 retains 281 additional rows (`267,143` vs `266,862`) and reduces extraction errors by 281 (`17,306` vs `17,587`) while keeping normalization and adjacent-state errors at zero.

The aggregate row accounting remains exact:

```text
267,143 normalized + 17,306 extraction errors + 0 normalization errors = 284,449 rows
```

---

## 6. Current interpretation

- The 1999 opening-kickoff and incomplete-penalty remediation is evidence-backed and passes the sentinel season.
- The canonical normalization engine still has zero normalization errors across the six-era corpus.
- Literal raw-row adjacency state validation still has zero state-transition errors.
- All sentinel validation uses retained raw evidence and exact checksum-bound historical artifacts.
- Gate B remains prohibited because Gate A is not yet fully green.
- The remaining 2010 failure must be classified from `validation_reasons`, `extraction_error_play_types`, `extraction_error_action_types`, and representative samples from the V2 season summary before another code change is approved.

---

## 7. Resume point

```text
M6                      ARCHITECTURE-CERTIFIED
M6C Gate 0              PASS
M6C Gate A V2 1999      PASS
M6C Gate A V2 2005      PASS
M6C Gate A V2 2010      FAIL — V2 TRIAGE REQUIRED
M6C Gate A V2 2015      PASS
M6C Gate A V2 2020      PASS
M6C Gate A V2 2025      PASS
M6C Gate B              NOT STARTED
M6C Gate C              NOT STARTED
M6C certification       WITHHELD
M7                      NOT STARTED
```

Next action: inspect the V2 `season-2010.json` classification evidence. Do not broaden exclusions or change semantics until the exact rejected action/reason pair is proven.
