# M6C Gate C — C-3 Negative Resume Rejection

**Project:** The Daily Line — Daily NFL
**Checkpoint:** M6C — Controlled Historical Continuation / Full Historical Compatibility
**Status:** C-3 CLOSED / PASS
**Runner/provenance authority:** `19df3e5e8fc648a2071d94f1f2c310fb7033fac2`
**Validator:** `M6C_PBP_VALIDATOR_V3`

## Purpose

Prove that M6C does not resume stale, corrupted, or raw-mismatched season summaries merely because a `season-2025.json` file exists.

All destructive test summaries were created in isolated output directories under `local-data/m6c/gate-c-negative`; the authoritative `local-data/m6c/validation/season-2025.json` was not modified.

## Corrupt-integrity summary

The fixture changed `validation_status` without recomputing `summary_sha256`.

Observed runner result:

```text
acquisition_mode: REUSED_RAW
execution_mode: VALIDATED
season: 2025
status: PASS
validation_fingerprint: d66f08ec2dbd884ba611af590b51c83251fb3cbda1964cfee6f72b9f6b6b8f8e
```

Result: **PASS**. The corrupt summary was rejected and validation was recomputed from certified stored raw evidence.

## Stale-validator summary

The fixture was internally integrity-valid but declared `M6C_PBP_VALIDATOR_V2`.

Observed runner result:

```text
acquisition_mode: REUSED_RAW
execution_mode: VALIDATED
season: 2025
status: PASS
validation_fingerprint: d66f08ec2dbd884ba611af590b51c83251fb3cbda1964cfee6f72b9f6b6b8f8e
```

Result: **PASS**. An integrity-valid but stale validator summary cannot resume under V3.

## Raw-identity mismatch summary

The fixture was internally integrity-valid but replaced `raw_sha256` with sixty-four zeroes.

Observed runner result:

```text
acquisition_mode: REUSED_RAW
execution_mode: VALIDATED
season: 2025
status: PASS
validation_fingerprint: d66f08ec2dbd884ba611af590b51c83251fb3cbda1964cfee6f72b9f6b6b8f8e
```

Result: **PASS**. An integrity-valid summary bound to the wrong raw identity cannot resume.

## Rebuilt fixture inspection

All three isolated summaries were replaced by fresh V3 results with:

```text
validator_version: M6C_PBP_VALIDATOR_V3
raw_sha256: c6ecedd6d678cc37ed316b23ef84ee1ec6abb69c514bb11868a7ebd5a367df29
validation_status: PASS
validation_fingerprint: d66f08ec2dbd884ba611af590b51c83251fb3cbda1964cfee6f72b9f6b6b8f8e
fingerprint_match: True
reproducibility_match: None
```

`reproducibility_match=None` is correct: the bad prior summaries were rejected as ineligible rather than accepted as prior validation authorities.

## Gate-C state

```text
C-1 valid resume                  PASS
C-2 explicit raw revalidation     PASS
C-3 corrupt integrity rejection   PASS
C-3 stale validator rejection     PASS
C-3 raw identity rejection        PASS
C-4 forced reacquisition          PENDING
```

Gate C remains open only for the forced-reacquisition / immutable-raw / new-observation proof and a final normal-resume confirmation.
