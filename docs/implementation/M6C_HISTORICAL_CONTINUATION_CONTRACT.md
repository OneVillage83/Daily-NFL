# M6C Controlled Historical Continuation Contract

**Project:** The Daily Line — Daily NFL
**Checkpoint:** M6C — Controlled Historical Continuation / Full Historical Compatibility
**Certified dependency base:** M0-M6
**Base main SHA:** `7815873d97b3233e0d67f7e16b8315b8c02d44ef`
**Status:** CONTRACT LOCKED — EXECUTION PENDING

## 1. Purpose

M6C is the historical continuation checkpoint between certified M6 canonical play/drive normalization and M7 State Engine V1.

It answers the question:

> Does the certified M3-M6 raw-evidence/extraction/normalization stack remain defensible across the full nflverse historical PBP era before state-engine work begins?

M6C is deliberately not allowed to weaken M3-M6 invariants merely to increase coverage.

## 2. Historical range

Primary full-history target:

```text
1999 through 2025 inclusive
```

This is the completed nflverse PBP era available before the current 2026 season is complete. The range is explicit and season-addressed; M6C must not silently include a partial current season in the historical certification corpus.

The runner must support narrower start/end seasons so the full pass can be executed in controlled chunks and resumed without changing semantics.

## 3. Persistence mode

M6C persists:

- exact raw nflverse season parquet bytes through `AcquisitionService` + `FileSystemRawEvidenceStore`;
- `raw_evidence` content identity;
- `raw_evidence_observations` acquisition history;
- provider capability/licensing snapshots;
- deterministic checkpoint manifests and per-season validation summaries.

M6C does **not** persist production canonical play/participation/penalty observations for the full history.

Reason: certified M6 persistence requires production canonical PlayerIds for explicit participants and penalty players. The repository does not yet own a certified full-history roster/player acquisition and reconciliation feed capable of resolving every historical PBP actor. Validation-only opaque PlayerIds may exercise the M6 contract in memory, but they must never enter the production canonical database.

This is a fail-closed identity boundary, not missingness to paper over.

## 4. Raw evidence requirements

Every acquired season must:

1. resolve through the certified nflverse exact-raw PBP asset mapping;
2. be stored before parsing/normalization;
3. retain SHA-256 content identity;
4. retain the exact acquisition-observation identity separately from content identity;
5. retain source URI, publication/observation/ingestion/availability clocks, provider/parser metadata, capability snapshot, and licensing metadata;
6. pass a stored-byte checksum comparison before that season is considered acquired.

## 5. Resume and idempotency

M6C must be restartable by season.

- Existing identical raw content is content-deduplicated by the certified raw store.
- A repeated acquisition is still allowed to create a distinct acquisition observation because acquisition time is historical evidence.
- Validation output is one deterministic per-season summary plus one aggregate manifest.
- Re-running validation from the same stored bytes and parser version must reproduce the same football counts/error buckets/checksums.
- A partially completed range must be resumable without deleting successful prior seasons.

The runner must never use "output file exists" alone as proof that a season is valid; it must verify the manifest/checksum/status.

## 6. Coverage accounting

For every season, record at minimum:

- raw evidence ID and SHA-256;
- evidence observation ID;
- raw byte size;
- row and column counts;
- extracted-and-normalized count;
- extraction-error count and reason/play-type buckets;
- normalization-error count and reason buckets;
- canonical play taxonomy counts;
- adjacent state transitions validated;
- nonadjacent state transitions skipped;
- adjacent state-transition error count;
- representative rejection samples;
- parser version and nflreadpy/polars validation version where applicable.

Aggregate output must include exact totals and per-season PASS/FAIL status.

## 7. Allowed exclusions

M6C preserves M6's fail-closed contract.

An exclusion is allowed only when the provider row cannot defensibly reconstruct the required causal pre-play state or another certified M6 prerequisite.

Known 2025 examples include `<NULL>` / `no_play` rows lacking defensible pre-play score, quarter clock, or yardline.

Allowed exclusion policy:

- exclusion reason must be explicit and counted;
- provider `play_type` distribution for every reason must be reported;
- no exclusion may be silently converted into a fabricated value;
- new exclusion reasons outside the locked/understood families make that season `REVIEW_REQUIRED` until audited;
- any excluded core state-bearing family (PASS/RUSH/SACK/SCRAMBLE/PUNT/FIELD_GOAL/KICKOFF/EXTRA_POINT/TWO_POINT/KNEEL/SPIKE) is a checkpoint blocker unless independently explained and architecture-reviewed.

## 8. Reconciliation requirements

For compatibility validation, provider player IDs may be mapped to deterministic opaque **in-memory validation IDs** scoped to the validation run so participation/event contracts are exercised.

Those validation IDs:

- are not M4 reconciliation decisions;
- must not be written into canonical identity/crosswalk/play tables;
- must not be represented as production player identity.

Team/game/provider identity in the validation layer remains provider-shaped only at the extraction boundary and is converted to validation-scoped canonical objects before normalization.

Production historical canonical persistence remains blocked until real identity reconciliation inputs exist.

## 9. PIT implications

Historical nflverse release assets are archival provider evidence with partial PIT fidelity. M6C validates football normalization compatibility, not historical pregame knowability of every play row.

Therefore:

- M6C raw acquisition `available_at` describes when Daily NFL observed the archival asset, not when each historical play was knowable live;
- no M6C output may be consumed as a pregame feature merely because the archival file is now stored;
- M5 PIT rules remain fully authoritative for future state/feature reconstruction;
- retrospective game/play truth and historical pregame knowledge remain separate.

## 10. Validation strategy

M6C executes in three gates.

### Gate A — era sentinels

Run representative completed seasons spanning the provider era before the full sweep:

```text
1999, 2005, 2010, 2015, 2020, 2025
```

Gate A must expose schema-era drift cheaply.

### Gate B — full historical sweep

After Gate A passes, run every completed season 1999-2025.

Each season is independently PASS/REVIEW_REQUIRED/FAIL and recorded in the aggregate manifest.

### Gate C — reproducibility/resume

Re-run at least one already completed season from the stored raw artifact without reacquiring it and prove the normalized summary fingerprint is identical.

Also restart a partially populated range and prove successful prior seasons do not need deletion or mutation.

## 11. Success thresholds

M6C PASS requires:

```text
raw checksum failures = 0
normalization_error_count = 0 for every successfully extracted row in every season
next_state_error_count = 0 for every truly adjacent validated transition
full requested season range accounted for exactly once in the aggregate manifest
no unexplained excluded core state-bearing play family
no fabricated charting/state values added to increase coverage
no production canonical PlayerId fabricated from provider IDs
resume/reproducibility gate PASS
Ruff PASS
strict mypy PASS
full pytest PASS
clean exact-head tree
```

Extraction-error counts are not required to be zero. They are required to be explicit, explainable, fail-closed, and coverage-accounted.

Any new historical schema/extraction failure mode is audited before proceeding; the runner does not automatically broaden parsing semantics just to make the count green.

## 12. M6C exit decision

M6C is the final historical compatibility checkpoint for certified M6 V1 before M7.

If Gates A-C pass, M7 may begin on top of M0-M6 plus a proven full-history PBP compatibility corpus.

This does **not** claim that all production historical canonical rows have been backfilled. Production canonical persistence remains a separate operational capability that must use real M4 identity reconciliation and the certified M6 writer.

If the full-history sweep reveals a material M6 architecture defect, M6 is explicitly reopened and recertified. Provider-era compatibility fixes that do not change the locked F-5 semantics may be remediated inside M6C and validated before closure.
