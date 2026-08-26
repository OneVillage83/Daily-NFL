# M6C Architecture Conformance Audit

**Project:** The Daily Line — Daily NFL
**Milestone:** M6C — Controlled Historical Continuation / Full Historical Compatibility
**Certified dependency base:** M0-M6
**Base main SHA:** `7815873d97b3233e0d67f7e16b8315b8c02d44ef`
**Validator semantics authority:** `d4c3e14c2a3cd9c40dd33a9a2acc9c75d7b4dfd0`
**Final runner/provenance authority:** `98aba116a80c51c6dc9f05d602f5bc41e68188e6`
**Final pre-certification hygiene head:** `d3a505309f5145f78645f3cae47d139c7b8f7c89`
**Validator:** `M6C_PBP_VALIDATOR_V3`
**Contract:** `M6C_HISTORICAL_CHECKPOINT_V1`
**Decision:** PASS — M6C satisfies its locked checkpoint contract and is eligible for `ARCHITECTURE-CERTIFIED` status after final status-document stamping.

## 1. Scope audited

M6C is the historical-compatibility checkpoint between certified M6 canonical play/drive normalization and M7 State Engine V1.

The audit is limited to the historical compatibility of the already-certified M3-M6 stack:

- F-2 raw evidence / provider abstraction compatibility;
- F-3 identity-boundary compatibility;
- F-4 historical PIT separation and provenance compatibility;
- F-5 canonical play / event / drive normalization compatibility.

M6C does **not** certify F-6 through F-9 state engines. TeamState, PlayerState, UnitState, CoachingState, injury/availability state, and related state engines remain M7 work.

M6C also does not claim a production canonical historical-player backfill. Validation-only opaque PlayerIds are in-memory test identities only and are never written as production M4 identity decisions or canonical historical play identity.

## 2. PR scope audit

PR #9 is based directly on certified M6 main `7815873d97b3233e0d67f7e16b8315b8c02d44ef`.

The final pre-certification compare is ahead-only with no divergence from main. The changed executable surface is limited to:

```text
daily_nfl/normalization/nflverse_extract.py
daily_nfl/validation/__init__.py
daily_nfl/validation/m6c.py
daily_nfl/validation/nflverse_pbp.py
scripts/__init__.py
scripts/run_m6c_historical_checkpoint.py
scripts/validate_nflverse_pbp_normalization.py
tests/test_m6c_historical_checkpoint.py
tests/test_nflverse_extraction.py
```

The remaining PR files are README / M6C contract, progress, triage, gate, and certification evidence documents.

No F-6/F-7/F-8/F-9 state-engine implementation files are present in the PR range.

The legacy single-season M6 nflverse validator was refactored to call the same reusable validation core used by M6C rather than maintaining a competing normalization implementation.

## 3. Conformance matrix

| Locked M6C requirement | Evidence | Result |
| --- | --- | --- |
| Historical range is exactly completed seasons 1999-2025 | Gate B manifest contains 27 seasons, 1999 through 2025 inclusive | PASS |
| Partial 2026 season excluded | Gate B requested season list ends at 2025 | PASS |
| Exact raw nflverse season assets persist before parsing | M6C runner acquires through certified `AcquisitionService` / `FileSystemRawEvidenceStore` | PASS |
| Raw content identity retained by SHA-256 | Per-season summaries bind raw SHA; C-4 verified stored and actual SHA equality | PASS |
| Acquisition observation identity separate from content identity | Gate C distinguishes immutable evidence ID from append-only observation IDs | PASS |
| Stored raw checksum reverified before resume | C-1/C-3 resume checks reject invalid raw identity and reuse only verified raw | PASS |
| Resume is not based on output-file existence alone | Corrupt, stale-validator, and raw-mismatch summaries were all rejected and recomputed | PASS |
| Revalidation from identical raw reproduces football fingerprint | 2025 fingerprint remained `d66f08ec2dbd884ba611af590b51c83251fb3cbda1964cfee6f72b9f6b6b8f8e` | PASS |
| Forced identical reacquisition does not rewrite immutable raw | C-4 retained identical evidence ID, SHA, path, size, and filesystem mtime | PASS |
| Repeated acquisition may append observation history | 2025 observation count advanced exactly 1 -> 2 with a distinct observation ID | PASS |
| Validation acquisition provenance is separate from current execution behavior | Manifest separates `validation_acquisition_mode`, `raw_resolution_mode`, and `execution_mode` | PASS |
| Coverage accounting is exact | Gate B: 1,195,503 normalized + 84,125 extraction exclusions + 0 normalization errors = 1,279,628 rows | PASS |
| Normalization errors are zero for every season | Gate B aggregate and every season PASS; aggregate normalization errors = 0 | PASS |
| Adjacent next-state errors are zero | 1,120,141 adjacent transitions validated; aggregate next-state errors = 0 | PASS |
| Nonadjacent raw rows are never bridged | 68,089 nonadjacent transitions explicitly skipped | PASS |
| New extraction reasons are fail-closed/reviewed | V1/V2 historical failures were triaged before remediation; no automatic allowlist broadening | PASS |
| Excluded core state-bearing families are not silently lost | V2 added structured rejected action-family classification; V3 Gate A/B contain no unexplained core-family exclusion | PASS |
| No fabricated pre-play state to increase coverage | Only the evidence-proven first raw-row Q1 15:00 opening-kickoff invariant may reconstruct 0-0 | PASS |
| Incomplete provider penalty type is not guessed | Known team + missing type is represented explicitly as `UNKNOWN`; missing team remains fail-closed | PASS |
| Provider metadata placeholder is not treated as football execution | Only the exact audited 2010 initial review-placeholder signature is classified administrative | PASS |
| Production canonical PlayerIds are not fabricated | Historical validation IDs are in-memory only; full historical canonical persistence remains blocked | PASS |
| Archival availability is not treated as pregame knowability | M5 PIT remains authoritative; M6C archival assets are retrospective normalization evidence only | PASS |
| Gate A era sentinels pass | 1999, 2005, 2010, 2015, 2020, 2025 all PASS under V3 | PASS |
| Gate B full-history sweep passes | 27 / 27 seasons PASS; non-pass count = 0 | PASS |
| Gate C resume/reproducibility/idempotency passes | C-1 through C-4 all closed / PASS | PASS |
| Legacy M6 real-2025 behavior is preserved | 48,771 rows; 45,196 normalized; 3,575 extraction exclusions; 0 normalization errors; 41,975 adjacent; 0 state errors | PASS |
| Database schema/history remains valid | Fresh SQLite 0 -> 7 and check 7 -> 7; foreign keys/integrity true | PASS |
| Static and test quality gates pass | Focused 50; Ruff PASS; strict mypy 95 files; full pytest 189 | PASS |
| Exact PR-range hygiene passes | `git diff --check` and `git diff --check origin/main...HEAD` both empty at final cleanup head | PASS |

## 4. Historical remediation audit

### 4.1 1999 opening-kickoff score reconstruction

Initial Gate A proved exactly 253 affected rows, one per affected game, and all satisfied the strict game-opening structural invariant. M6C therefore permits pre-play 0-0 reconstruction only when the caller proves the row is the first raw row for the game and the row is Q1 15:00 with kickoff semantics and both pre-score fields absent.

This is not a generic missing-score fill. Near-miss rows remain fail-closed.

### 4.2 Incomplete historical penalty type

Historical nflverse rows can structurally assert that a penalty occurred and identify the penalty team while omitting the foul type. M6C preserves that provider assertion with explicit `UNKNOWN` rather than dropping the play or inferring a foul from prose. Missing penalty team remains an extraction failure.

### 4.3 2010 initial review placeholders

Five V2 hard rejects were audited against raw adjacency. In every affected game, an initial `*** play under review ***` row with null clock/yardline/pre-score fields and an inherited kickoff flag was immediately followed by the real opening kickoff.

V3 recognizes only that exact placeholder shape as administrative for rejected-row coverage accounting. A real kickoff or a near-miss review row remains protected by the core-family hard-failure rule.

### 4.4 Resume/provenance vocabulary

Gate C exposed a metadata ambiguity where an integrity-verified persisted summary was temporarily represented with a current-run resume value in the acquisition field. M6C corrected this without changing football validation semantics by separating:

```text
validation_acquisition_mode
raw_resolution_mode
execution_mode
```

The validator remained V3 because the change was runner/provenance metadata only.

## 5. Full historical compatibility result

Gate B final manifest:

```text
contract_version: M6C_HISTORICAL_CHECKPOINT_V1
validator_version: M6C_PBP_VALIDATOR_V3
overall_status: PASS
schema_version: 7
season_count: 27
range: 1999-2025
row_count: 1,279,628
extracted_and_normalized_count: 1,195,503
extraction_error_count: 84,125
normalization_error_count: 0
next_state_adjacent_validated: 1,120,141
next_state_nonadjacent_skipped: 68,089
next_state_error_count: 0
raw_size_bytes: 488,034,547
non_pass_count: 0
manifest_sha256: e28c45a371c2c85926444c92808385f993595c9cdb8fecc5973338393c450634
```

The 84,125 extraction exclusions are not treated as hidden failures. They remain explicit, reason-bucketed, provider-play-type/action-family audited, and fail-closed where causal prestate cannot be reconstructed defensibly.

## 6. Final certification-time validation

User-local certified environment:

```text
Python 3.12.10
E:\Daily-NFL\.venv\Scripts\python.exe
```

Final executable-quality gate was run on docs head `d23eed3fb9c2283eeee5d5fac454bef2da364e99`, whose executable tree is unchanged from runner/provenance authority `98aba116a80c51c6dc9f05d602f5bc41e68188e6`:

```text
focused M6/M6C regressions: 50 passed
Ruff: PASS
strict mypy: PASS — 95 source files
full pytest: 189 passed
git diff --check: PASS
working tree: clean
```

Subsequent commits through `d3a505309f5145f78645f3cae47d139c7b8f7c89` changed only M6C Markdown trailing whitespace. A direct commit comparison confirms no executable file changed after the final test head.

Final PR-range hygiene at `d3a505309f5145f78645f3cae47d139c7b8f7c89`:

```text
git diff --check: PASS
git diff --check origin/main...HEAD: PASS
working tree: clean
local HEAD == origin feature branch: PASS
```

## 7. Deferred / explicitly not certified

The following remain outside M6C and must not be inferred from this certification:

- production full-history canonical player reconciliation/backfill;
- TeamState V1;
- PlayerState V1;
- UnitState V1;
- CoachingState V1;
- injury / availability state engine;
- F-6 through F-9 state architecture implementation;
- feature/model use of retrospective PBP as if it were historically pregame-available.

These boundaries are intentional and preserve the dependency order into M7.

## 8. Certification decision

No unresolved M6C architecture non-conformance remains.

All locked checkpoint success thresholds are satisfied. The historical corpus is fully accounted for, normalization and truly-adjacent state transition errors are zero, historical remediation was evidence-backed and fail-closed, raw evidence remains immutable and reproducible, legacy M6 behavior is preserved, and the PR contains no state-engine scope expansion.

Final decision:

```text
M6C — PASS
ARCHITECTURE-CERTIFIED eligible
M7 — may begin only after final status documents are stamped and PR #9 is merged
```
