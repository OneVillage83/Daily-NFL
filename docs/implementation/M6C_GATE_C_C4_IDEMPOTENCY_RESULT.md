# M6C Gate C — C-4 Forced Reacquisition / Idempotency Result

**Project:** The Daily Line — Daily NFL  
**Checkpoint:** M6C — Controlled Historical Continuation / Full Historical Compatibility  
**Status:** PASS  
**Runner/provenance authority:** `98aba116a80c51c6dc9f05d602f5bc41e68188e6`  
**Validator:** `M6C_PBP_VALIDATOR_V3`  
**Validator semantics authority:** `d4c3e14c2a3cd9c40dd33a9a2acc9c75d7b4dfd0`

## Exact-head quality gate

Environment:

```text
Python 3.12.10
E:\Daily-NFL\.venv\Scripts\python.exe
```

Validation at exact committed SHA `98aba116a80c51c6dc9f05d602f5bc41e68188e6`:

```text
focused M6/M6C regressions: 50 passed
Ruff: PASS
mypy: PASS — 95 source files
full pytest: 189 passed
git diff --check: PASS
working tree: clean
```

The commit separates three provenance dimensions without changing football validation semantics:

- `validation_acquisition_mode`: how the raw evidence used to create the persisted validation summary was acquired;
- `raw_resolution_mode`: how the current runner invocation resolved raw evidence;
- `execution_mode`: whether the current invocation validated, revalidated, or resumed validation.

## Before forced reacquisition

2025 raw evidence snapshot:

```text
evidence_id:
b83076e5593cc4843132e29be86160e3fdcd668b0724d3ae20fc4c2bff8fbac3

stored_sha256:
c6ecedd6d678cc37ed316b23ef84ee1ec6abb69c514bb11868a7ebd5a367df29

actual_sha256:
c6ecedd6d678cc37ed316b23ef84ee1ec6abb69c514bb11868a7ebd5a367df29

object_path:
nflverse/play_by_play/c6ecedd6d678cc37ed316b23ef84ee1ec6abb69c514bb11868a7ebd5a367df29.raw

size_bytes: 20,337,029
mtime_ns: 1787698812340658200
observation_count: 1
latest_observation_id:
reo_024484a81bfb2a196302a8c34484674039db384dd1444355b89cc00f0100d45a
```

## Forced reacquisition and revalidation

The runner was invoked with both `--force-reacquire` and `--revalidate` for 2025.

Observed:

```text
status: PASS
validation_acquisition_mode: ACQUIRED
raw_resolution_mode: ACQUIRED
execution_mode: REVALIDATED
validation_fingerprint:
d66f08ec2dbd884ba611af590b51c83251fb3cbda1964cfee6f72b9f6b6b8f8e
```

The validation result remained exactly stable:

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

## After forced reacquisition

Post-run raw evidence snapshot:

```text
evidence_id:
b83076e5593cc4843132e29be86160e3fdcd668b0724d3ae20fc4c2bff8fbac3

stored_sha256:
c6ecedd6d678cc37ed316b23ef84ee1ec6abb69c514bb11868a7ebd5a367df29

actual_sha256:
c6ecedd6d678cc37ed316b23ef84ee1ec6abb69c514bb11868a7ebd5a367df29

object_path:
nflverse/play_by_play/c6ecedd6d678cc37ed316b23ef84ee1ec6abb69c514bb11868a7ebd5a367df29.raw

size_bytes: 20,337,029
mtime_ns: 1787698812340658200
observation_count: 2
latest_observation_id:
reo_6718bf91faa868ed0822e1a1c8a09205ea08d19be2497117fcb69df506051b12
```

Exact idempotency checks:

```text
evidence_id_same: True
stored_sha_same: True
actual_sha_same: True
object_path_same: True
size_same: True
mtime_same: True
new_observation: True
observation_count_plus_one: True
ALL_PASS: True
```

Interpretation:

1. Upstream 2025 bytes were identical on forced reacquisition.
2. The content-addressed raw evidence object was not rewritten: its path, bytes, size, digest, evidence ID, and filesystem mtime are unchanged.
3. A distinct acquisition observation was appended, increasing the observation count from 1 to 2.
4. Revalidation against the reacquired evidence reproduced the exact V3 validation fingerprint.

## Post-reacquisition resume

A subsequent normal run produced:

```text
status: PASS
validation_acquisition_mode: ACQUIRED
raw_resolution_mode: REUSED_RAW
execution_mode: RESUMED_VALIDATION
validation_fingerprint:
d66f08ec2dbd884ba611af590b51c83251fb3cbda1964cfee6f72b9f6b6b8f8e
```

This independently demonstrates that:

- the persisted validation summary records that it was generated from a forced acquisition;
- the subsequent invocation reused the immutable stored raw object;
- the subsequent invocation safely resumed the valid summary;
- football validation identity remained unchanged.

## C-4 disposition

**C-4 CLOSED / PASS.**

Together with C-1/C-2 and the C-3 negative tests, this satisfies the locked Gate C requirements for stored-raw reuse, checksum/integrity-bound resume, deterministic revalidation, fail-closed stale/corrupt summary rejection, immutable content-addressed raw evidence, and append-only acquisition observations.
