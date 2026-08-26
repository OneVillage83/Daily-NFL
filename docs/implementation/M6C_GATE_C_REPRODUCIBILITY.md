# M6C Gate C — Reproducibility / Resume / Idempotency Evidence

**Project:** The Daily Line — Daily NFL
**Checkpoint:** M6C — Controlled Historical Continuation / Full Historical Compatibility
**Status:** CLOSED / PASS
**Final runner/provenance authority:** `98aba116a80c51c6dc9f05d602f5bc41e68188e6`
**Validator:** `M6C_PBP_VALIDATOR_V3`
**Validator semantics authority:** `d4c3e14c2a3cd9c40dd33a9a2acc9c75d7b4dfd0`

## Locked Gate C requirements

M6C required proof that:

- stored raw bytes are reused rather than silently reacquired;
- stored raw SHA-256 is reverified;
- resumable PASS summaries are accepted only when integrity/version/raw identity match;
- corrupt or stale summaries are rejected;
- explicit revalidation reproduces the same validation fingerprint;
- evidence acquisition provenance is not conflated with current execution behavior;
- forced reacquisition may append a new acquisition observation without rewriting immutable raw evidence.

All requirements are now satisfied.

## Exact-head runner/provenance validation

Final runner/provenance authority:

```text
98aba116a80c51c6dc9f05d602f5bc41e68188e6
Track M6C raw resolution provenance
```

Environment:

```text
Python 3.12.10
E:\Daily-NFL\.venv\Scripts\python.exe
```

Quality gate:

```text
focused M6/M6C regressions: 50 passed
Ruff: PASS
mypy: PASS — 95 source files
full pytest: 189 passed
git diff --check: PASS
working tree: clean
```

The final runner keeps three provenance dimensions separate:

- `validation_acquisition_mode`: how the evidence used for the persisted validation summary was acquired;
- `raw_resolution_mode`: how the current invocation resolved raw evidence (`REUSED_RAW` or `ACQUIRED`);
- `execution_mode`: whether the current invocation `VALIDATED`, `REVALIDATED`, or `RESUMED_VALIDATION`.

This is runner/provenance metadata only; football validation semantics remain `M6C_PBP_VALIDATOR_V3` under validator authority `d4c3e14c...`.

## C-1 — valid summary resume

2025 normal resume:

```text
status: PASS
raw_resolution_mode: REUSED_RAW
execution_mode: RESUMED_VALIDATION
validation_fingerprint:
d66f08ec2dbd884ba611af590b51c83251fb3cbda1964cfee6f72b9f6b6b8f8e
```

Result: **PASS**. A valid integrity/version/raw-bound V3 summary resumed without revalidation.

## C-2 — deterministic stored-raw revalidation

Explicit `--revalidate` against the same 2025 raw object produced:

```text
status: PASS
raw_resolution_mode: REUSED_RAW
execution_mode: REVALIDATED
validation_fingerprint:
d66f08ec2dbd884ba611af590b51c83251fb3cbda1964cfee6f72b9f6b6b8f8e
previous_validation_fingerprint:
d66f08ec2dbd884ba611af590b51c83251fb3cbda1964cfee6f72b9f6b6b8f8e
reproducibility_match: True
```

Result: **PASS**. Exact football-validation identity reproduced from the same stored bytes.

## C-3 — fail-closed negative resume tests

All negative tests used isolated output directories and did not alter the authoritative validation summary.

### Corrupt summary integrity

A summary whose content was changed without recomputing `summary_sha256` was rejected as resumable evidence.

Observed replacement run:

```text
status: PASS
raw_resolution_mode: REUSED_RAW
execution_mode: VALIDATED
validation_fingerprint:
d66f08ec2dbd884ba611af590b51c83251fb3cbda1964cfee6f72b9f6b6b8f8e
reproducibility_match: None
```

### Stale validator version

A summary with internally valid integrity but `M6C_PBP_VALIDATOR_V2` was rejected under V3 and recomputed.

Observed replacement run reproduced the exact V3 fingerprint with `reproducibility_match: None`.

### Mismatched raw identity

A summary with internally valid integrity but a false raw SHA was rejected and recomputed from the certified stored raw object.

Observed replacement run restored:

```text
validator_version: M6C_PBP_VALIDATOR_V3
raw_sha256:
c6ecedd6d678cc37ed316b23ef84ee1ec6abb69c514bb11868a7ebd5a367df29
validation_status: PASS
validation_fingerprint:
d66f08ec2dbd884ba611af590b51c83251fb3cbda1964cfee6f72b9f6b6b8f8e
reproducibility_match: None
```

C-3 result: **CLOSED / PASS**.

Detailed record: `docs/implementation/M6C_GATE_C_C3_NEGATIVE_RESULT.md`.

## C-4 — forced reacquisition / immutable raw evidence

Before forced reacquisition, the 2025 raw evidence was:

```text
evidence_id:
b83076e5593cc4843132e29be86160e3fdcd668b0724d3ae20fc4c2bff8fbac3

raw_sha256:
c6ecedd6d678cc37ed316b23ef84ee1ec6abb69c514bb11868a7ebd5a367df29

object_path:
nflverse/play_by_play/c6ecedd6d678cc37ed316b23ef84ee1ec6abb69c514bb11868a7ebd5a367df29.raw

size_bytes: 20,337,029
mtime_ns: 1787698812340658200
observation_count: 1
latest_observation_id:
reo_024484a81bfb2a196302a8c34484674039db384dd1444355b89cc00f0100d45a
```

Forced `--force-reacquire --revalidate` produced:

```text
status: PASS
validation_acquisition_mode: ACQUIRED
raw_resolution_mode: ACQUIRED
execution_mode: REVALIDATED
validation_fingerprint:
d66f08ec2dbd884ba611af590b51c83251fb3cbda1964cfee6f72b9f6b6b8f8e
```

After reacquisition:

```text
evidence_id: unchanged
stored SHA: unchanged
actual SHA: unchanged
object path: unchanged
size: unchanged
mtime_ns: unchanged
observation_count: 2
latest_observation_id:
reo_6718bf91faa868ed0822e1a1c8a09205ea08d19be2497117fcb69df506051b12
```

Exact comparison:

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

This proves identical upstream bytes were deduplicated into the same immutable content-addressed raw object, the object was not rewritten, and a new append-only acquisition observation was retained.

A subsequent normal run produced:

```text
status: PASS
validation_acquisition_mode: ACQUIRED
raw_resolution_mode: REUSED_RAW
execution_mode: RESUMED_VALIDATION
validation_fingerprint:
d66f08ec2dbd884ba611af590b51c83251fb3cbda1964cfee6f72b9f6b6b8f8e
```

C-4 result: **CLOSED / PASS**.

Detailed record: `docs/implementation/M6C_GATE_C_C4_IDEMPOTENCY_RESULT.md`.

## Final Gate C disposition

```text
C-1 valid resume                    PASS
C-2 deterministic revalidation     PASS
C-3 corrupt-summary rejection      PASS
C-3 stale-validator rejection      PASS
C-3 raw-identity rejection         PASS
C-4 forced reacquisition           PASS
C-4 immutable raw proof            PASS
C-4 append-only observation        PASS
C-4 post-reacquisition resume      PASS
```

**Gate C: CLOSED / PASS.**

Gate A is already CLOSED / PASS. Gate B — the full 1999–2025 completed-history sweep — is now the only remaining historical validation gate before final M6C certification work.
