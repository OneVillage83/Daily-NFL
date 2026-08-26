# M6C Gate A Closure — Era Sentinels

**Project:** The Daily Line — Daily NFL  
**Checkpoint:** M6C — Controlled Historical Continuation / Full Historical Compatibility  
**Status:** GATE A CLOSED / PASS  
**Exact executable authority:** `d4c3e14c2a3cd9c40dd33a9a2acc9c75d7b4dfd0`  
**Validator:** `M6C_PBP_VALIDATOR_V3`  
**Certified M6 base:** `7815873d97b3233e0d67f7e16b8315b8c02d44ef`

## 1. Exact-head quality gate

User-local certified environment:

```text
Python 3.12.10
E:\Daily-NFL\.venv\Scripts\python.exe
```

Exact committed SHA validation:

```text
focused M6/M6C regressions: 47 passed
Ruff: PASS
strict mypy: PASS — 95 source files
full pytest: 186 passed
git diff --check: PASS
working tree: clean
```

GitHub commit inspection confirms the executable commit changes only:

```text
daily_nfl/validation/m6c.py
daily_nfl/validation/nflverse_pbp.py
tests/test_m6c_historical_checkpoint.py
```

The commit bumps the validator from V2 to V3 and classifies only the exact audited initial review-placeholder shape as `ADMINISTRATIVE` before inherited action flags are considered. Real opening kickoffs and near-miss review rows remain `KICKOFF` and therefore remain protected by the core hard-reject gate.

## 2. V3 sentinel command

```text
python scripts/run_m6c_historical_checkpoint.py \
    --gate sentinel \
    --revalidate \
    --database local-data/m6c/m6c-history.db \
    --raw-root local-data/m6c/raw \
    --output-root local-data/m6c/validation
```

Every sentinel reused stored raw evidence.

## 3. Exact sentinel results

```text
1999  PASS  449ea036dec6b782335c518125e8aa8f88dc5ab7800958789c967c07222bcd9b
2005  PASS  d5a2f357b97bdec17d9dbd1df52d2e47fef1f7e38cdf5ad124f7378a24cfb796
2010  PASS  ea4e95b083c48b22f42b35180f2b7a9cab4c9b7b0c41be88e25fc294e316e898
2015  PASS  e38576c5954367147796b68263e4530ba7c31e6a74f0250bcf8b7af942cb5917
2020  PASS  55fc4ef101df4f2167e92b0ae548aafe513bc92255d2a4e87323d068299d71ac
2025  PASS  d66f08ec2dbd884ba611af590b51c83251fb3cbda1964cfee6f72b9f6b6b8f8e
```

Aggregate exact-head evidence:

```text
overall_status: PASS
season_count: 6
row_count: 284,449
extracted_and_normalized_count: 267,143
extraction_error_count: 17,306
normalization_error_count: 0
next_state_adjacent_validated: 251,607
next_state_nonadjacent_skipped: 13,923
next_state_error_count: 0
raw_size_bytes: 106,230,513
schema_version: 7
manifest_sha256: 9cb9823267893a89b9dac85384a1db45a75353c70b95b9ec9bf59eff2a2c7008
```

Row accounting balances exactly:

```text
267,143 + 17,306 + 0 = 284,449
```

## 4. Historical-remediation findings preserved

Gate A did not become green through blanket allowlisting.

### 1999

Raw evidence proved that all 253 affected missing-pre-score kickoff rows were exact game-opening states. The extractor may reconstruct 0-0 only under the strict proven first-row/Q1/15:00/kickoff invariant. Incomplete historical penalties with known team but unavailable foul type are retained with explicit `UNKNOWN` type rather than dropping the play or inferring prose.

### 2010

Exactly five remaining V2 hard rejects were provider review-placeholder rows with:

```text
play_id = 1
play_type = NULL
desc = "*** play under review ***"
qtr = 1
clock = NULL
yardline = NULL
pre-scores = NULL
kickoff_attempt = 1
```

For all five affected games, raw adjacency proved that this row was immediately followed by the real opening kickoff with a normal kickoff description, Q1 15:00 clock, valid yardline, and 0-0 state. V3 therefore classifies only this exact rejected-row placeholder shape as administrative. The actual opening kickoff remains the state-bearing canonical row.

## 5. Manifest-hash note

The uncommitted V3 candidate run produced aggregate manifest SHA:

```text
ece12e73858e0a5c895678a544a26efa79b37815190bdf3f4422e72f4e79ba85
```

The exact committed V3 rerun produced:

```text
9cb9823267893a89b9dac85384a1db45a75353c70b95b9ec9bf59eff2a2c7008
```

This does not indicate validation drift. All six per-season `validation_fingerprint` values reproduced exactly. The runner includes revalidation metadata in season summaries/manifests: the first V3 run had no prior valid V3 summary, while the exact-head rerun found the prior V3 summary and recorded `previous_validation_fingerprint` plus `reproducibility_match=true`. Those metadata fields legitimately change the aggregate manifest document while the validation payload fingerprint remains stable.

Gate C will explicitly test stored-summary resume/revalidation/idempotency semantics before final M6C certification.

## 6. Gate state

```text
Gate 0                 CLOSED / PASS
Gate A                 CLOSED / PASS
Gate B full history    UNLOCKED / NOT YET RUN
Gate C reproducibility NEXT CHECKPOINT
M6C certification      WITHHELD
M7                      NOT STARTED
```

The next operation is a focused Gate-C reproducibility/resume proof on 2025 before launching the full 1999-2025 Gate-B sweep. This minimizes the risk of discovering resume/evidence-integrity issues only after a 27-season run.
