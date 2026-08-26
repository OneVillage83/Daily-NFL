# M6C Gate C — Reproducibility / Resume / Idempotency Evidence

**Project:** The Daily Line — Daily NFL  
**Checkpoint:** M6C — Controlled Historical Continuation / Full Historical Compatibility  
**Status:** IN PROGRESS — C-1/C-2 PASS; negative/idempotency proofs remain  
**Runner/provenance authority:** `19df3e5e8fc648a2071d94f1f2c310fb7033fac2`  
**Validator:** `M6C_PBP_VALIDATOR_V3`  
**Validator semantics authority:** `d4c3e14c2a3cd9c40dd33a9a2acc9c75d7b4dfd0`

## Gate C requirements

M6C requires proof that:

- stored raw bytes are reused rather than silently reacquired;
- stored raw SHA-256 is reverified;
- resumable PASS summaries are accepted only when integrity/version/raw identity match;
- corrupt or stale summaries are rejected;
- explicit revalidation reproduces the same validation fingerprint;
- evidence acquisition provenance is not conflated with current execution behavior;
- forced reacquisition may append a new acquisition observation without rewriting immutable raw evidence.

## Exact-head runner validation

Commit `19df3e5e8fc648a2071d94f1f2c310fb7033fac2` separates immutable raw acquisition provenance from per-run execution mode.

Environment:

```text
Python 3.12.10
E:\Daily-NFL\.venv\Scripts\python.exe
```

Quality gate:

```text
focused M6/M6C tests: 49 passed
Ruff: PASS
mypy: PASS — 95 source files
full pytest: 188 passed
git diff --check: PASS
working tree: clean
```

The runner now leaves the integrity-bound season summary unchanged and emits current behavior separately as `execution_mode`.

## C-1 — resumable PASS on 2025

Observed after the runner/provenance remediation:

```text
season: 2025
status: PASS
acquisition_mode: REUSED_RAW
execution_mode: RESUMED_VALIDATION
validation_fingerprint: d66f08ec2dbd884ba611af590b51c83251fb3cbda1964cfee6f72b9f6b6b8f8e
```

Aggregate one-season totals remained:

```text
row_count: 48,771
extracted_and_normalized_count: 45,196
extraction_error_count: 3,575
normalization_error_count: 0
next_state_adjacent_validated: 41,975
next_state_nonadjacent_skipped: 2,936
next_state_error_count: 0
raw_size_bytes: 20,337,029
```

C-1 result: **PASS**. A valid integrity/version/raw-bound V3 summary is resumed without mutating acquisition provenance.

## C-2 — explicit stored-raw revalidation on 2025

Observed:

```text
season: 2025
status: PASS
acquisition_mode: REUSED_RAW
execution_mode: REVALIDATED
validation_fingerprint: d66f08ec2dbd884ba611af590b51c83251fb3cbda1964cfee6f72b9f6b6b8f8e
```

Persisted summary after revalidation:

```text
validator_version: M6C_PBP_VALIDATOR_V3
season: 2025
evidence_id: b83076e5593cc4843132e29be86160e3fdcd668b0724d3ae20fc4c2bff8fbac3
evidence_observation_id: reo_024484a81bfb2a196302a8c34484674039db384dd1444355b89cc00f0100d45a
raw_sha256: c6ecedd6d678cc37ed316b23ef84ee1ec6abb69c514bb11868a7ebd5a367df29
acquisition_mode: REUSED_RAW
validation_status: PASS
validation_fingerprint: d66f08ec2dbd884ba611af590b51c83251fb3cbda1964cfee6f72b9f6b6b8f8e
previous_validation_fingerprint: d66f08ec2dbd884ba611af590b51c83251fb3cbda1964cfee6f72b9f6b6b8f8e
reproducibility_match: True
summary_sha256: 571e801f67d547fb503ef3dc4193eecf43b7eb8728dc4d16a1e6d02737427b65
```

Current manifest season entry correctly separates:

```text
acquisition_mode: REUSED_RAW
execution_mode: REVALIDATED
reproducibility_match: True
```

C-2 result: **PASS**. Exact validation output reproduced from the same stored raw artifact, and acquisition provenance remained distinct from execution behavior.

## Manifest SHA interpretation

Different execution paths legitimately produce different aggregate manifest SHA-256 values because `execution_mode` and reproducibility metadata are part of the manifest. The validation fingerprint is the stable football-validation identity and remained unchanged.

## Raw-store idempotency contract

`FileSystemRawEvidenceStore` is content-addressed by SHA-256. It attempts exclusive creation and, when an object already exists, verifies that the existing bytes and digest match rather than rewriting the object. Therefore a forced reacquisition of identical upstream bytes should retain the same evidence ID/path/SHA while allowing a new acquisition observation.

## Remaining C-3/C-4 work

Before Gate C can close:

1. prove corrupt summary integrity is rejected;
2. prove stale validator/version metadata is rejected even with internally valid summary integrity;
3. prove mismatched raw identity is rejected even with internally valid summary integrity;
4. force reacquisition of 2025 and prove immutable raw evidence identity/content is unchanged while a new acquisition observation is recorded;
5. restore/confirm a normal resume remains PASS after those checks.

All destructive-negative summary tests must use isolated output directories and must not alter the authoritative `local-data/m6c/validation/season-2025.json`.

Gate C remains **OPEN / IN PROGRESS**. Gate B is unlocked but intentionally deferred until Gate C closes.
