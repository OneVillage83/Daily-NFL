# M6C — Controlled Historical Continuation Progress Log

**Project:** The Daily Line — Daily NFL  
**Checkpoint:** M6C — Controlled Historical Continuation / Full Historical Compatibility  
**Status:** IN PROGRESS  
**Branch:** `checkpoint/m6c-historical-continuation`  
**Draft PR:** #9  
**Certified M6 base:** `7815873d97b3233e0d67f7e16b8315b8c02d44ef`

This is the running resume/handoff log for M6C. Update it as evidence, decisions, defects, fixes, and validation gates occur. It is intentionally separate from the final certification evidence so an interrupted checkpoint can be resumed without reconstructing chat history.

---

## 1. Locked M6C purpose

M6C proves that the certified M3–M6 raw-evidence, PIT, reconciliation-boundary, and canonical play-normalization contracts remain compatible across the completed nflverse historical PBP range before M7 State Engine V1 begins.

M6C is **not** permission to fabricate a production canonical historical-player backfill.

The provider descriptor exposes nflverse PBP from 1999 onward, but the repository does not yet contain the certified historical roster/player acquisition required to reconcile every historical actor to production canonical PlayerIds. Therefore:

- exact raw nflverse PBP assets are persisted through the certified M3 evidence ledger;
- every selected historical season is scanned through the certified M6 extraction/normalization semantics;
- validation-only opaque player IDs may be allocated in memory only to exercise participation normalization;
- those validation-only IDs must never be written to production canonical identity/play tables;
- production canonical historical play persistence remains blocked until real identity reconciliation exists.

This avoids creating technically complete-looking historical tables whose player identity is false.

---

## 2. Historical range and gates

Completed-season target:

```text
1999 through 2025 inclusive
```

### Gate 0 — local/static regression gate

Required before any historical network/data sweep:

- focused M6C/M6 regression tests;
- Ruff;
- strict mypy;
- full pytest;
- clean working tree / exact branch SHA.

### Gate A — era sentinels

```text
1999
2005
2010
2015
2020
2025
```

Purpose: expose historical schema/semantic drift cheaply before the full sweep.

### Gate B — full completed-history sweep

```text
1999-2025 inclusive
27 seasons
```

Each season must have an auditable raw-evidence identity and a deterministic validation summary.

### Gate C — reproducibility / resume / idempotency

At minimum:

- stored raw bytes reused rather than silently reacquired;
- stored raw SHA-256 reverified;
- resumable PASS summary accepted only when contract/validator/parser/raw identity and summary-integrity hash match;
- corrupted or stale summary rejected;
- explicit revalidation from stored raw reproduces the same validation fingerprint;
- forced reacquisition may append a new acquisition observation without rewriting immutable raw content/history.

---

## 3. Fail-closed M6C classification

### PASS

Known strict row-local exclusions remain explainable and confined to reviewed provider rows such as `<NULL>` / `no_play` where required causal prestate cannot be reconstructed without guessing.

### REVIEW_REQUIRED

A historical season introduces a new extraction-rejection reason that is not yet known to be unsafe but requires explicit investigation before the checkpoint can close.

### FAIL

Any of the following blocks M6C:

- normalization error on a successfully extracted row;
- adjacent `PLAY_STATE_AFTER` error;
- excluded core play family (pass/rush/sack/scramble/punt/FG/kickoff/XP/2PT/kneel/spike, etc.);
- raw checksum mismatch or missing stored raw object;
- corrupted/mismatched resume summary;
- revalidation fingerprint mismatch against the same raw artifact and validator contract;
- fabricated production canonical identity;
- unreviewed data loss hidden by aggregate counts.

---

## 4. Implementation surface added for M6C

Expected M6C-only surface at checkpoint start:

```text
daily_nfl/validation/__init__.py
daily_nfl/validation/m6c.py
daily_nfl/validation/nflverse_pbp.py
docs/implementation/M6C_HISTORICAL_CONTINUATION_CONTRACT.md
docs/implementation/M6C_PROGRESS_LOG.md
scripts/run_m6c_historical_checkpoint.py
scripts/validate_nflverse_pbp_normalization.py
tests/test_m6c_historical_checkpoint.py
scripts/__init__.py
```

The existing single-season M6 nflverse validator was refactored to use the same reusable validation core as M6C so the historical sweep cannot silently use different football semantics from the M6 certification run.

---

## 5. Gate 0 evidence

### Initial run — branch SHA `4120f449700231b7ad7c9d41eaccaa5f2ee68c72`

User-local environment:

```text
Python 3.12.10
E:\Daily-NFL\.venv\Scripts\python.exe
```

Focused gate:

```text
39 passed in 3.60s
```

Full repository gate:

```text
178 passed in 4.54s
```

Initial Ruff blocker:

```text
I001 import block un-sorted/un-formatted
scripts/run_m6c_historical_checkpoint.py
```

Initial mypy blocker:

```text
scripts/run_m6c_historical_checkpoint.py found twice as:
  run_m6c_historical_checkpoint
  scripts.run_m6c_historical_checkpoint
```

Remediation:

- added `scripts/__init__.py` to establish one explicit package identity;
- Ruff deterministic import ordering applied locally.

### Static rerun — local HEAD `047b668b4334cb42cc3a4cc0fc72a567cddecb60`

Ruff:

```text
All checks passed!
```

Full pytest:

```text
178 passed in 4.36s
```

mypy progressed past the package/module-identity collision and exposed eight strict typing errors in `scripts/run_m6c_historical_checkpoint.py` manifest aggregation. Every error was the same class: calling `int(...)` on a value typed as generic `object` from `dict[str, object]` validation/summary documents.

Interpretation:

- this was a static typing contract issue, not a behavioral normalization failure;
- the remediation must validate the runtime type rather than weaken mypy.

### Exact executable Gate-0 pass — `4a17bb0722efe37603c2856447ba02fd1005f690`

Remediation committed:

- added fail-closed `_required_int(document, key)` validation;
- booleans and non-integers are rejected explicitly;
- manifest totals now consume only validated integer fields;
- Ruff import ordering included in the same executable commit.

Exact-head quality gate:

```text
python -m ruff check .
All checks passed!

python -m mypy .
Success: no issues found in 95 source files

python -m pytest -q
178 passed in 6.95s
```

GitHub commit inspection confirms `4a17bb0722efe37603c2856447ba02fd1005f690` changes only `scripts/run_m6c_historical_checkpoint.py` and contains the tested `_required_int` remediation plus Ruff import ordering.

The later local run began Gate A from branch head `7a6f409bde9b26a83de4d697bd276a6201b6ef8e` with a clean `git status --short`. That head only advanced documentation after the executable Gate-0 authority, so the M6C runner under test remained the code validated at `4a17bb0722efe37603c2856447ba02fd1005f690`.

Gate 0 is **CLOSED / PASS**.

---

## 6. Gate A era-sentinel evidence

Gate A command:

```text
python scripts/run_m6c_historical_checkpoint.py \
    --gate sentinel \
    --database local-data/m6c/m6c-history.db \
    --raw-root local-data/m6c/raw \
    --output-root local-data/m6c/validation
```

Sentinel status/fingerprint results:

```text
1999  FAIL  69d402fdf4632aa9ad7e1cb5e25f4e620e362e5fe69efec6a1c8583359c9580d
2005  PASS  3b47ae76bb66a0b5ebfde29bc731d6514d164e183a04561ccd20f06b2641a9c8
2010  FAIL  1efce259db3a3a4c4c1bee376d4f28de01e8de36a1f4faa08fcaec1040e6260e
2015  PASS  ba39026ef7c00a73fab1b44dce6ff041e51eab49350af86a66ffeae4e569b073
2020  PASS  d4c2920f5a06c135c57e7d1dd0e9b569c9ad577276c3253467ba5ce381375bf5
2025  PASS  46403a8bfb377acb258789f63cf04dbcebb1df676bd53644a34645e96f95cde4
```

Aggregate manifest:

```text
overall_status: FAIL
season_count: 6
schema_version: 7
row_count: 284,449
extracted_and_normalized_count: 266,862
extraction_error_count: 17,587
normalization_error_count: 0
next_state_adjacent_validated: 251,299
next_state_nonadjacent_skipped: 13,950
next_state_error_count: 0
raw_size_bytes: 106,230,513
manifest_sha256: 9ede333e978ef19dc5e59a6abd72fe4b2e802f23495bfd1b4964433601b620a5
```

Interpretation at first failure triage:

- four of six era sentinels are clean PASS;
- no successfully extracted row failed canonical normalization in any sentinel season;
- no literally adjacent raw-row state transition failed in any sentinel season;
- aggregate row accounting balances exactly: `266,862 + 17,587 + 0 = 284,449`;
- therefore the M6 normalization/state machinery is holding across the sentinel corpus;
- 1999 and 2010 are blocked by fail-closed historical extraction classification and require row/play-type inspection before any remediation or allowance is approved;
- Gate B full 1999-2025 sweep is prohibited until both failing sentinels are understood and Gate A is green.

Exact per-season `validation_reasons`, extraction-rejection play-type buckets, and representative rejected rows for 1999/2010 are the next required evidence. No architecture or allowlist change may be made based only on the aggregate counts.

Gate A is **OPEN / BLOCKED — 1999 AND 2010 REQUIRE TRIAGE**.

---

## 7. Decisions made during M6C setup

1. **Raw-first history is authoritative.** M6C validation reads the exact stored parquet asset retained through the certified raw-evidence path.
2. **Season-addressed acquisition.** PBP acquisition is one explicit season asset at a time so failure/resume/accounting is auditable.
3. **No hidden full-history launch.** Gate A sentinels must pass before Gate B 1999-2025.
4. **Validation aliases are not canonical identity.** In-memory opaque IDs exist only to exercise normalization when provider participant IDs are present.
5. **Known exclusions are measured, not silently filled.** The normalizer continues to fail closed rather than inferring missing pre-play state from incompatible post-play/cumulative evidence.
6. **Raw-row adjacency remains mandatory.** State-after validation only uses literally adjacent raw rows; surviving extracted rows separated by excluded provider rows are counted as skipped rather than bridged.
7. **Resume is content/version bound.** A previous PASS is reusable only when summary integrity, raw SHA/evidence, contract version, validator version, and parser version all match.
8. **M6C does not certify F-6 through F-9.** TeamState, PlayerState, UnitState, CoachingState, and injury/availability state remain M7 work.
9. **Strict typing remains fail-closed.** Manifest aggregation validates integer-valued fields explicitly; M6C will not suppress mypy errors with broad casts/ignores simply to advance the checkpoint.
10. **Historical FAIL is investigated before allowlisting.** A provider-era play type/rejection combination is not added to the allowed set merely because it is old or rare; representative rows must show that excluding it preserves the F-5 causal/state contract.

---

## 8. Current resume point

```text
M6                     ARCHITECTURE-CERTIFIED
M6C contract           LOCKED
M6C implementation     PRESENT ON FEATURE BRANCH
M6C draft PR           #9 OPEN / DRAFT
Gate 0                 CLOSED / PASS
Gate A                  OPEN / BLOCKED
Gate A 1999             FAIL — TRIAGE REQUIRED
Gate A 2005             PASS
Gate A 2010             FAIL — TRIAGE REQUIRED
Gate A 2015             PASS
Gate A 2020             PASS
Gate A 2025             PASS
Gate B full history     NOT STARTED
Gate C reproducibility  NOT STARTED
M6C certification       WITHHELD
M7                      NOT STARTED
```

Next actions:

1. inspect `season-1999.json` and `season-2010.json` validation reasons;
2. print extraction-error play-type buckets for both failing seasons;
3. inspect representative rejected rows for every disallowed play-type/reason pair;
4. determine whether each case is provider schema drift, a legitimate canonical extraction gap, or a safely non-state-bearing row;
5. remediate or explicitly approve only evidence-backed exclusions;
6. rerun 1999 and 2010 from stored raw bytes;
7. rerun all six Gate-A sentinels after any executable change;
8. only after Gate A is fully PASS, execute Gate B full 1999-2025 sweep;
9. run Gate C resume/revalidation proof;
10. produce final M6C evidence/certification docs and update authoritative certification state;
11. review/squash-merge PR #9 pinned to exact final head;
12. begin M7 only after M6C closes.

---

## 9. Update rule

Append or revise this file whenever any of the following occurs:

- checkpoint scope changes;
- a defect or provider-era incompatibility is found;
- a remediation is implemented;
- an exact-head validation gate is run;
- raw-history coverage changes;
- a new allowed exclusion is approved;
- a deferred item is created or resolved;
- a PR head or certification authority changes;
- the exact resume point moves.

Final certification evidence must remain separate and concise; this file preserves the working history that explains how the final result was reached.
