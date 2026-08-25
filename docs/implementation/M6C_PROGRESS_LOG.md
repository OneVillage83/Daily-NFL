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

Local post-push status exposed one unrelated untracked artifact:

```text
?? "t -q"
```

This does not invalidate the tested executable commit because it is untracked and not part of the code under test, but Gate 0's clean-worktree requirement is not administratively closed until that file is inspected/removed and `git status --short` is empty.

Gate-0 executable behavior/static analysis is therefore **PASS**, with only clean-tree housekeeping pending.

---

## 6. Decisions made during M6C setup

1. **Raw-first history is authoritative.** M6C validation reads the exact stored parquet asset retained through the certified raw-evidence path.
2. **Season-addressed acquisition.** PBP acquisition is one explicit season asset at a time so failure/resume/accounting is auditable.
3. **No hidden full-history launch.** Gate A sentinels must pass before Gate B 1999-2025.
4. **Validation aliases are not canonical identity.** In-memory opaque IDs exist only to exercise normalization when provider participant IDs are present.
5. **Known exclusions are measured, not silently filled.** The normalizer continues to fail closed rather than inferring missing pre-play state from incompatible post-play/cumulative evidence.
6. **Raw-row adjacency remains mandatory.** State-after validation only uses literally adjacent raw rows; surviving extracted rows separated by excluded provider rows are counted as skipped rather than bridged.
7. **Resume is content/version bound.** A previous PASS is reusable only when summary integrity, raw SHA/evidence, contract version, validator version, and parser version all match.
8. **M6C does not certify F-6 through F-9.** TeamState, PlayerState, UnitState, CoachingState, and injury/availability state remain M7 work.
9. **Strict typing remains fail-closed.** Manifest aggregation validates integer-valued fields explicitly; M6C will not suppress mypy errors with broad casts/ignores simply to advance the checkpoint.

---

## 7. Current resume point

```text
M6                     ARCHITECTURE-CERTIFIED
M6C contract           LOCKED
M6C implementation     PRESENT ON FEATURE BRANCH
M6C draft PR           #9 OPEN / DRAFT
Gate 0 executable      PASS — 4a17bb0722efe37603c2856447ba02fd1005f690
Gate 0 Ruff            PASS
Gate 0 mypy            PASS — 95 source files
Gate 0 pytest          PASS — 178 tests
Gate 0 clean tree      PENDING — untracked "t -q" artifact
Gate A real history    NOT STARTED
Gate B full history    NOT STARTED
Gate C reproducibility NOT STARTED
M6C certification      WITHHELD
M7                     NOT STARTED
```

Next actions:

1. inspect/remove the untracked `t -q` artifact and verify a clean worktree;
2. pull any documentation-only branch update while preserving executable authority at `4a17bb0722efe37603c2856447ba02fd1005f690`;
3. record clean-tree closure for Gate 0;
4. execute Gate A sentinel seasons only: 1999, 2005, 2010, 2015, 2020, 2025;
5. investigate any REVIEW_REQUIRED/FAIL season before proceeding;
6. only after Gate A is green, execute Gate B full 1999-2025 sweep;
7. run Gate C resume/revalidation proof;
8. produce final M6C evidence/certification docs and update authoritative certification state;
9. review/squash-merge PR #9 pinned to exact final head;
10. begin M7 only after M6C closes.

---

## 8. Update rule

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
