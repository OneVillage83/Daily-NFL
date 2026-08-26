# M6C Gate C — Reproducibility / Resume / Idempotency Evidence

**Project:** The Daily Line — Daily NFL  
**Checkpoint:** M6C — Controlled Historical Continuation / Full Historical Compatibility  
**Status:** IN PROGRESS — C-1/C-2 PASS; execution/acquisition metadata separation requires remediation  
**Executable authority:** `d4c3e14c2a3cd9c40dd33a9a2acc9c75d7b4dfd0`  
**Validator:** `M6C_PBP_VALIDATOR_V3`

## Gate C requirements

M6C requires proof that:

- stored raw bytes are reused rather than silently reacquired;
- stored raw SHA-256 is reverified;
- resumable PASS summaries are accepted only when integrity/version/raw identity match;
- corrupt or stale summaries are rejected;
- explicit revalidation reproduces the same validation fingerprint;
- forced reacquisition may append an acquisition observation without rewriting immutable raw evidence.

## C-1 — resumable PASS on 2025

Command omitted `--revalidate` and reused the existing valid V3 season summary.

Observed:

```text
season: 2025
status: PASS
acquisition_mode: RESUMED_VALIDATION
validation_fingerprint: d66f08ec2dbd884ba611af590b51c83251fb3cbda1964cfee6f72b9f6b6b8f8e
row_count: 48,771
extracted_and_normalized_count: 45,196
extraction_error_count: 3,575
normalization_error_count: 0
next_state_adjacent_validated: 41,975
next_state_nonadjacent_skipped: 2,936
next_state_error_count: 0
```

C-1 result: **PASS**. The summary satisfied the integrity/version/raw-identity resume gate.

## C-2 — explicit stored-raw revalidation on 2025

Command used `--revalidate` against the same stored raw evidence.

Observed:

```text
season: 2025
status: PASS
acquisition_mode: REUSED_RAW
validation_fingerprint: d66f08ec2dbd884ba611af590b51c83251fb3cbda1964cfee6f72b9f6b6b8f8e
previous_validation_fingerprint: d66f08ec2dbd884ba611af590b51c83251fb3cbda1964cfee6f72b9f6b6b8f8e
reproducibility_match: True
```

Persisted summary identity:

```text
contract_version: M6C_HISTORICAL_CHECKPOINT_V1
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

C-2 result: **PASS**. The exact validation fingerprint reproduced from the same stored raw artifact.

## Manifest SHA note

The one-season resume manifest and revalidation manifest have different SHA-256 values because current runner metadata differs between execution paths:

- resume path mutates the loaded summary in memory to `acquisition_mode = RESUMED_VALIDATION`;
- explicit revalidation persists `acquisition_mode = REUSED_RAW` and sets prior-fingerprint/reproducibility metadata.

This does not indicate football-data drift: the validation fingerprint is identical. However, the current runner overloads the field `acquisition_mode` to represent both evidence acquisition provenance and current execution behavior.

## Open remediation before Gate C closure

The persisted season summary is integrity-bound and correctly retains the evidence acquisition provenance (`REUSED_RAW`). On the resume path the runner mutates only the in-memory loaded summary to `RESUMED_VALIDATION` without recomputing or persisting `summary_sha256`.

Although this does not corrupt the stored summary, it creates semantic ambiguity between:

1. immutable evidence acquisition provenance; and
2. current checkpoint execution mode.

Gate C will not close with that ambiguity. The runner should preserve `acquisition_mode` as immutable evidence provenance and represent the current run separately, e.g. `execution_mode = RESUMED_VALIDATION` versus `execution_mode = REVALIDATED`/`VALIDATED`.

After this narrow remediation, rerun focused/full quality gates and repeat C-1/C-2 before corruption-rejection and forced-reacquisition proofs.

Gate C remains **OPEN / IN PROGRESS**. Gate B remains unlocked but should not start until this runner semantics issue is resolved.
