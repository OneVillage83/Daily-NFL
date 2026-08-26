# M6C Local Validation — 2026-08-26

**Project:** The Daily Line — Daily NFL
**Milestone:** M6C — Controlled Historical Continuation / Full Historical Compatibility
**Validator:** `M6C_PBP_VALIDATOR_V3`
**Contract:** `M6C_HISTORICAL_CHECKPOINT_V1`
**Validator semantics authority:** `d4c3e14c2a3cd9c40dd33a9a2acc9c75d7b4dfd0`
**Runner/provenance authority:** `98aba116a80c51c6dc9f05d602f5bc41e68188e6`
**Final executable-quality test head:** `d23eed3fb9c2283eeee5d5fac454bef2da364e99`
**Final pre-certification hygiene head:** `d3a505309f5145f78645f3cae47d139c7b8f7c89`
**Result:** PASS

## 1. Certified local environment

```text
Python 3.12.10
E:\Daily-NFL\.venv\Scripts\python.exe
```

The system Python 3.14 installation is not part of M6C certification. All final certification commands were run from the project Python 3.12.10 virtual environment.

## 2. Gate A — era sentinels

Final exact V3 sentinel fingerprints:

```text
1999 PASS 449ea036dec6b782335c518125e8aa8f88dc5ab7800958789c967c07222bcd9b
2005 PASS d5a2f357b97bdec17d9dbd1df52d2e47fef1f7e38cdf5ad124f7378a24cfb796
2010 PASS ea4e95b083c48b22f42b35180f2b7a9cab4c9b7b0c41be88e25fc294e316e898
2015 PASS e38576c5954367147796b68263e4530ba7c31e6a74f0250bcf8b7af942cb5917
2020 PASS 55fc4ef101df4f2167e92b0ae548aafe513bc92255d2a4e87323d068299d71ac
2025 PASS d66f08ec2dbd884ba611af590b51c83251fb3cbda1964cfee6f72b9f6b6b8f8e
```

Aggregate sentinel evidence:

```text
season_count: 6
row_count: 284,449
extracted_and_normalized_count: 267,143
extraction_error_count: 17,306
normalization_error_count: 0
next_state_adjacent_validated: 251,607
next_state_nonadjacent_skipped: 13,923
next_state_error_count: 0
raw_size_bytes: 106,230,513
```

Gate A result: **PASS**.

## 3. Gate C — resume / reproducibility / idempotency

### C-1 valid resume

2025 valid V3 summary resumed without revalidation:

```text
validation_acquisition_mode: REUSED_RAW
raw_resolution_mode: REUSED_RAW
execution_mode: RESUMED_VALIDATION
status: PASS
validation_fingerprint: d66f08ec2dbd884ba611af590b51c83251fb3cbda1964cfee6f72b9f6b6b8f8e
```

### C-2 explicit stored-raw revalidation

```text
validation_acquisition_mode: REUSED_RAW
raw_resolution_mode: REUSED_RAW
execution_mode: REVALIDATED
status: PASS
previous_validation_fingerprint: d66f08ec2dbd884ba611af590b51c83251fb3cbda1964cfee6f72b9f6b6b8f8e
validation_fingerprint: d66f08ec2dbd884ba611af590b51c83251fb3cbda1964cfee6f72b9f6b6b8f8e
reproducibility_match: true
```

### C-3 fail-closed negative resume checks

Isolated summary fixtures proved that all of the following are rejected as resumable evidence:

```text
corrupt summary integrity
stale validator version
mismatched raw SHA identity
```

All three were recomputed from the real stored raw artifact and returned:

```text
validator_version: M6C_PBP_VALIDATOR_V3
raw_sha256: c6ecedd6d678cc37ed316b23ef84ee1ec6abb69c514bb11868a7ebd5a367df29
validation_status: PASS
validation_fingerprint: d66f08ec2dbd884ba611af590b51c83251fb3cbda1964cfee6f72b9f6b6b8f8e
reproducibility_match: None
```

### C-4 forced reacquisition / immutable raw proof

Before forced reacquisition:

```text
evidence_id: b83076e5593cc4843132e29be86160e3fdcd668b0724d3ae20fc4c2bff8fbac3
raw_sha256: c6ecedd6d678cc37ed316b23ef84ee1ec6abb69c514bb11868a7ebd5a367df29
size_bytes: 20,337,029
observation_count: 1
```

Forced 2025 reacquisition plus revalidation:

```text
validation_acquisition_mode: ACQUIRED
raw_resolution_mode: ACQUIRED
execution_mode: REVALIDATED
status: PASS
validation_fingerprint: d66f08ec2dbd884ba611af590b51c83251fb3cbda1964cfee6f72b9f6b6b8f8e
```

Post-acquisition comparison:

```text
evidence_id_same: true
stored_sha_same: true
actual_sha_same: true
object_path_same: true
size_same: true
mtime_same: true
new_observation: true
observation_count_plus_one: true
ALL_PASS: true
```

Observation count advanced exactly:

```text
1 -> 2
```

A subsequent normal invocation proved:

```text
validation_acquisition_mode: ACQUIRED
raw_resolution_mode: REUSED_RAW
execution_mode: RESUMED_VALIDATION
status: PASS
validation_fingerprint: d66f08ec2dbd884ba611af590b51c83251fb3cbda1964cfee6f72b9f6b6b8f8e
```

Gate C result: **PASS**.

## 4. Gate B — full 1999-2025 historical compatibility

Final full-history manifest:

```text
contract_version: M6C_HISTORICAL_CHECKPOINT_V1
validator_version: M6C_PBP_VALIDATOR_V3
overall_status: PASS
schema_version: 7
season_count: 27
requested_seasons: 1999 through 2025 inclusive
manifest_sha256: e28c45a371c2c85926444c92808385f993595c9cdb8fecc5973338393c450634
```

Aggregate totals:

```text
row_count: 1,279,628
extracted_and_normalized_count: 1,195,503
extraction_error_count: 84,125
normalization_error_count: 0
next_state_adjacent_validated: 1,120,141
next_state_nonadjacent_skipped: 68,089
next_state_error_count: 0
raw_size_bytes: 488,034,547
non_pass_count: 0
```

Exact row accounting:

```text
1,195,503 + 84,125 + 0 = 1,279,628
```

All 27 seasons independently reported `PASS`.

Gate B result: **PASS**.

## 5. Legacy M6 2025 regression

The original real-season M6 validation command was rerun after all M6C executable work:

```text
season: 2025
row_count: 48,771
extracted_and_normalized_count: 45,196
extraction_error_count: 3,575
normalization_error_count: 0
next_state_adjacent_validated: 41,975
next_state_nonadjacent_skipped: 2,936
next_state_error_count: 0
```

This exactly preserves the certified M6 2025 totals and proves the reusable M6C validation core did not regress the prior certification behavior.

Legacy M6 regression result: **PASS**.

## 6. SQLite migration / integrity gate

A fresh final-certification database was removed and recreated from schema 0.

Migration result:

```text
schema_version_before: 0
schema_version_after: 7
supported_schema_version: 7
foreign_keys_enabled: true
integrity_ok: true
mode: migrate
```

Existing-database check result:

```text
schema_version_before: 7
schema_version_after: 7
supported_schema_version: 7
foreign_keys_enabled: true
integrity_ok: true
mode: check
```

SQLite gate result: **PASS**.

## 7. Final quality gate

Final executable-quality run:

```text
focused M6/M6C tests: 50 passed in 0.63s
Ruff: All checks passed!
mypy: Success: no issues found in 95 source files
full pytest: 189 passed in 3.87s
git diff --check: PASS
working tree: clean
```

The focused set was:

```text
tests/test_m6c_historical_checkpoint.py
tests/test_nflverse_extraction.py
tests/test_play_normalization.py
tests/test_play_normalization_persistence.py
```

Final executable-quality result: **PASS**.

## 8. Post-test documentation-only hygiene

After the final executable-quality gate, only Markdown trailing whitespace was removed from M6C evidence files.

Direct commit comparison from `d23eed3fb9c2283eeee5d5fac454bef2da364e99` through `d3a505309f5145f78645f3cae47d139c7b8f7c89` shows only documentation files changed; no Python/source/test file changed.

Final hygiene results at `d3a505309f5145f78645f3cae47d139c7b8f7c89`:

```text
git diff --check: PASS
git diff --check origin/main...HEAD: PASS
git status --short: clean
local HEAD == origin/checkpoint/m6c-historical-continuation: PASS
```

No additional executable test run was required after whitespace-only documentation edits.

## 9. Final local-validation decision

```text
Gate 0: PASS
Gate A: PASS
Gate B: PASS
Gate C: PASS
Legacy M6 2025 regression: PASS
SQLite schema/integrity: PASS
Focused regressions: PASS
Ruff: PASS
strict mypy: PASS
full pytest: PASS
PR-range hygiene: PASS
```

Local-validation decision:

```text
M6C — PASS
No executable blocker remains.
Eligible for ARCHITECTURE-CERTIFIED status after final status-document stamping and PR closure.
```
