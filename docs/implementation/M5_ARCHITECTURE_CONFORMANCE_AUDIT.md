# M5 Architecture-Conformance Audit

**Project:** The Daily Line — Daily NFL  
**Milestone:** M5 — Historical PIT Engine  
**Architecture dependency:** F-4 — Historical Point-in-Time Architecture  
**Certified dependency base:** M0-M4  
**Validated executable code head:** `d553c3a46b36478b069eae97b7b52f283c97b47a`  
**Certification status:** **ARCHITECTURE-CERTIFIED**

---

## 1. Audit rule

The existing PIT package was treated as provisional evidence and F-4 remained authoritative. M5 could not certify if a historical reconstruction could admit information that was not defensibly knowable at the requested prediction timestamp.

M5 certifies historical information state, not later feature semantics. The richer feature registry/eras remain M9, prediction identity remains M10, and final walk-forward model evaluation remains M14.

---

## 2. Locked F-4 / M5 contract

M5 must provide:

- defensible `available_at` derivation with method and confidence;
- distinct `effective_at`, `published_at`, `observed_at`, and `ingested_at` clocks;
- knowledge-time and real-world-validity/bitemporal as-of helpers;
- a hard pregame cutoff before actual game start where retrospective start truth exists;
- standard horizons `T-168h`, `T-72h`, `T-24h`, `T-6h`, `T-90m`, and `T-15m`;
- no blanket exclusion of game-day information legitimately available before the cutoff;
- append-only observation/revision history;
- later corrections invisible to earlier cutoffs;
- fail-closed treatment of ambiguous historical revision timing;
- explicit rejection of current-game outcomes/stats/plays, realized current-game weather, later markets, future games/labels, end-of-season aggregates, and historically indefensible corrections;
- immutable feature-input snapshots with feature contract/version, canonical scalar values, coverage/missingness, PIT validation result, exact input provenance, provider/source versions where available, raw evidence/checksums, and acquisition-observation identity;
- explicit separation of retrospective event truth from historical pregame knowledge state.

---

## 3. Final conformance matrix

| ID | Requirement | Final status | Evidence / remediation |
|---|---|---|---|
| M5-01 | Standard horizons and pregame cutoff | `SATISFIED` | `PredictionCutoff` retains all six locked horizons and requires `prediction_time < kickoff`. |
| M5-02 | Game-day information allowed when legitimately known | `SATISFIED` | Eligibility is timestamp-based; Sunday/game-day is not blanket excluded. |
| M5-03 | Four temporal clocks remain distinct | `SATISFIED` | Effective/publication/observation/ingestion clocks remain separately modeled. |
| M5-04 | Earliest defensible `available_at` selected | `SATISFIED AFTER REMEDIATION` | High-confidence source/publication/archive/observation evidence is compared and earliest defensible knowledge time is selected. |
| M5-05 | Inferred report date has medium confidence and explicit opt-in | `SATISFIED AFTER REMEDIATION` | Inferred report date maps to `MEDIUM`; default strict policy excludes it unless intentionally enabled. |
| M5-06 | Unknown/ingestion-only timing excluded in strict PIT | `SATISFIED` | Strict derivation fails without defensible evidence; permissive ingestion fallback remains `UNKNOWN/LOW`. |
| M5-07 | Knowledge-time as-of selection | `SATISFIED` | Latest eligible `available_at` is selected per logical key. |
| M5-08 | Same-knowledge conflicting revisions fail closed | `SATISFIED AFTER REMEDIATION` | Observation/ingestion clocks no longer break a knowledge-time tie; conflicting payloads raise `PITSelectionConflictError`. |
| M5-09 | Same-content duplicates remain deterministic | `SATISFIED AFTER REMEDIATION` | Equal payload hashes use deterministic input identity without fabricating a change. |
| M5-10 | Bitemporal real-world validity + knowledge selection | `SATISFIED AFTER REMEDIATION` | `select_latest_bitemporal_as_of` requires `effective_at`, selects latest effective state, then latest knowable revision. |
| M5-11 | Late correction to older state cannot displace newer state | `SATISFIED AFTER REMEDIATION` | Dedicated bitemporal regression locks effective-state precedence. |
| M5-12 | Raw-backed inputs retain acquisition-observation provenance | `SATISFIED AFTER REMEDIATION` | Inputs/snapshots retain `evidence_id`, `evidence_observation_id`, provider namespace, and raw checksum. |
| M5-13 | Provider/source versions retained where available | `SATISFIED AFTER REMEDIATION` | Provider revision/schema/parser metadata is retained. |
| M5-14 | Snapshot stores feature contract/version/values | `SATISFIED AFTER REMEDIATION` | Generic M5 feature snapshot metadata is persisted and hashed without defining the later M9 registry. |
| M5-15 | Snapshot stores coverage/missingness/PIT result | `SATISFIED AFTER REMEDIATION` | Deterministic coverage report, missing features, and `PITValidationResult.PASS` are persisted. |
| M5-16 | Snapshot identity includes exact input provenance | `SATISFIED AFTER REMEDIATION` | Ordered input IDs, clocks, provider/source versions, payload/raw hashes, and acquisition-observation identity are hashed. |
| M5-17 | Snapshot membership is sealed and complete | `SATISFIED AFTER REMEDIATION` | v7 requires declared input count to match persisted membership before sealing. |
| M5-18 | Database rejects inconsistent certified raw provenance | `SATISFIED AFTER REMEDIATION` | v7 trigger requires raw content/acquisition observation/provider/checksum agreement. |
| M5-19 | Source after cutoff rejected | `SATISFIED` | Generic cutoff validator remains fail closed. |
| M5-20 | Current-game final score/stats/plays rejected | `SATISFIED AFTER REMEDIATION` | Current-game kinds require subject context and are explicitly rejected. |
| M5-21 | Actual current-game weather cannot replace forecast | `SATISFIED AFTER REMEDIATION` | Current-game actual weather is rejected. |
| M5-22 | Later/closing market quote rejected | `SATISFIED AFTER REMEDIATION` | Market quote timestamp is mandatory and must not exceed cutoff. |
| M5-23 | Future game/opponent data rejected | `SATISFIED AFTER REMEDIATION` | Source-game kickoff is mandatory and must precede cutoff. |
| M5-24 | Future season/week labels rejected | `SATISFIED AFTER REMEDIATION` | Dedicated `FUTURE_SEASON_WEEK_LABEL` input kind fails historical validation. |
| M5-25 | End-of-season aggregates rejected before completion | `SATISFIED AFTER REMEDIATION` | Completion time is mandatory and future completion fails. |
| M5-26 | Provider corrections require defensible historical context | `SATISFIED AFTER REMEDIATION` | Provider/revision and defensible pre-cutoff timing are required. |
| M5-27 | Schedule revision changes only after correction is knowable | `SATISFIED AFTER REMEDIATION` | Provider-scoped revision selection keeps v1 before v2's `available_at`. |
| M5-28 | Cross-provider disagreement cannot silently overwrite | `SATISFIED AFTER REMEDIATION` | Providers reconstruct independently; disagreement on canonical schedule state fails closed. Provider-specific `schedule_version` is retained as provenance and deliberately excluded from cross-provider canonical-state equality. |
| M5-29 | Agreeing providers retain every supporting input | `SATISFIED AFTER REMEDIATION` | `ScheduleStateAsOf.supporting_inputs` retains all selected provider provenance, including providers with different revision/version labels. |
| M5-30 | Pregame schedule state retains safe fields/provenance | `SATISFIED AFTER REMEDIATION` | Status, scheduled kickoff, venue, neutral site, provider schedule version, and provider revision remain available on selected state/provenance. |
| M5-31 | Retrospective actual kickoff is not pregame feature state | `SATISFIED AFTER REMEDIATION` | `actual_kickoff` is excluded from pregame schedule payload/hash. |
| M5-32 | Actual game start is a hard retrospective leakage boundary | `SATISFIED AFTER REMEDIATION` | Snapshot sealing refuses `prediction_time >= actual_kickoff`; conflicting actual-start truth also fails closed. |
| M5-33 | Append-only historical observations/snapshots | `SATISFIED` | Existing append-only ledgers remain; v7 is forward-only. |
| M5-34 | Forward migration preserves legacy PIT history | `SATISFIED — EXECUTED` | v6 legacy snapshot/seal preservation through v7 is covered by the passing 161-test suite. |
| M5-35 | M0-M4 certified contracts remain intact | `SATISFIED — EXECUTED` | Prior migrations remain unchanged; M3/M4 preservation tests pass under schema 7. |
| M5-36 | Deterministic historical reconstruction validator | `SATISFIED — EXECUTED` | `scripts/validate_m5_pit.py` proves early/later schedule state, sealed provenance, and deliberate leakage rejection. |
| M5-37 | Full repository quality gate | `SATISFIED — EXECUTED` | Ruff PASS; strict mypy PASS on 82 files; pytest 161 PASS; clean tree. |
| M5-38 | Feature availability eras | `DEFERRED BY ARCHITECTURE` | Exact feature registry/era semantics remain M9. |
| M5-39 | Walk-forward final model evaluation | `DEFERRED BY ARCHITECTURE` | Final chronological evaluation remains M14. |

---

## 4. Material findings and remediations

### F-01 — retrospective correction could leak through same `available_at`

**Severity:** CRITICAL — REMEDIATED

The provisional selector used observation/ingestion clocks after `available_at` to order revisions. A correction discovered later could therefore win a historical tie. M5 now treats different payloads at the same top knowledge time as unresolved historical ambiguity.

### F-02 — no explicit bitemporal state selection

**Severity:** HIGH — REMEDIATED

`effective_at` existed but did not control real-world-valid state reconstruction. M5 now separates effective state history from knowledge revision history.

### F-03 — raw content identity was insufficient provenance

**Severity:** HIGH — REMEDIATED

M3 separates immutable content identity from acquisition-observation identity. M5 now retains both through strict selection and immutable snapshot sealing.

### F-04 — leakage-critical context could fail open

**Severity:** HIGH — REMEDIATED

Market quotes, future/prior games, season-final aggregates, current-game outcome kinds, actual weather, and provider corrections now require enough context to evaluate leakage. Missing context is itself a strict-policy failure.

### F-05 — feature-input snapshot was not feature-complete

**Severity:** HIGH — REMEDIATED

M5 now stores feature contract/version/values/coverage/missingness/PIT result while deliberately leaving the full M9 feature registry for M9.

### F-06 — schedule providers could silently overwrite or falsely conflict

**Severity:** HIGH — REMEDIATED

Provider schedule revisions are selected independently. Canonical state disagreement blocks reconstruction. A final pre-certification review also removed provider-specific `schedule_version` from cross-provider canonical-state equality; the value remains retained as provenance. A dedicated 5-test repository regression passed at the validated executable head.

### F-07 — retrospective `actual_kickoff` risked becoming pregame data

**Severity:** CRITICAL — REMEDIATED

Actual game start is retrospective event truth. It is excluded from pregame state and used only as a snapshot-sealing leakage boundary.

### F-08 — availability evidence ranking was incomplete

**Severity:** MEDIUM — REMEDIATED

M5 chooses earliest defensible high-confidence knowledge evidence and classifies inferred report dates as medium confidence with explicit opt-in.

### F-09 — earlier milestone tests pinned final schema version

**Severity:** LOW — REMEDIATED

M3/M4 migration tests now validate preservation while allowing later forward migrations.

---

## 5. Fail-closed guarantees

M5 intentionally refuses to guess when:

- availability is after cutoff or cannot satisfy method/confidence policy;
- a raw-backed input lacks acquisition-observation/provider provenance;
- different payloads claim the same top knowledge timestamp;
- required bitemporal `effective_at` is absent;
- current-game result/stat/play is introduced pregame;
- actual current-game weather masquerades as a forecast;
- market quote timing is absent or later than cutoff;
- source-game kickoff is absent or not yet occurred;
- future season/week labels are injected;
- season-final aggregates lack completed-state timing;
- provider corrections lack provider/revision or defensible timing;
- providers disagree on canonical pregame schedule state;
- raw/acquisition/provider/checksum provenance disagrees;
- snapshot membership is incomplete;
- retrospective actual-start sources disagree;
- prediction time is at or after retrospective actual game start.

---

## 6. Executable certification evidence

Validated executable head:

```text
d553c3a46b36478b069eae97b7b52f283c97b47a
```

Exact environment and quality gate:

```text
Python 3.12.10
E:\Daily-NFL\.venv\Scripts\python.exe
targeted PIT repository regression: 5 passed in 0.57s
Ruff: All checks passed!
mypy: Success: no issues found in 82 source files
pytest: 161 passed in 3.64s
git status --short: clean
```

SQLite gate:

```text
fresh schema 0 -> 7: PASS
schema check 7 -> 7: PASS
foreign_keys_enabled: true
integrity_ok: true
```

Historical reconstruction gate:

```text
early observation: m5-schedule-v1 / SCHEDULED
later observation: m5-schedule-v2 / POSTPONED
later correction hidden at early cutoff: true
later correction visible at later cutoff: true
snapshot sealed: true
snapshot input count: 1
raw evidence retained: true
acquisition-observation retained: true
provider/revision/checksum retained: true
deliberate current-game leakage rejected: true
```

Full evidence is recorded in `docs/implementation/M5_LOCAL_VALIDATION_20260823.md`.

---

## 7. Explicit deferrals — not M5 defects

- exact feature registry and feature-availability eras — M9;
- prediction/model identity — M10;
- full play/drive normalization semantics — M6;
- final chronological/walk-forward model evaluation — M14;
- provider-specific historical availability mappings not exposed by source evidence — never fabricated by M5.

---

## 8. Final decision

```text
M5 F-4 STATIC ARCHITECTURE AUDIT: PASS
M5 AVAILABILITY DERIVATION: PASS
M5 BITEMPORAL / REVISION SEMANTICS: PASS
M5 STRICT LEAKAGE CONTEXT: PASS
M5 RAW / ACQUISITION PROVENANCE: PASS
M5 IMMUTABLE FEATURE SNAPSHOT CONTRACT: PASS
M5 SCHEDULE AS-OF / PROVIDER CONFLICT SEMANTICS: PASS
M5 RETROSPECTIVE ACTUAL-START BOUNDARY: PASS
M5 MIGRATION v7: PASS
M5 DETERMINISTIC VALIDATION UTILITY: PASS
M5 LOCAL QUALITY GATE: PASS
M5 SQLITE v7 GATE: PASS
M5 HISTORICAL RECONSTRUCTION GATE: PASS
M5 ARCHITECTURE CERTIFICATION: ARCHITECTURE-CERTIFIED
```

M5 is certified against F-4 at executable SHA `d553c3a46b36478b069eae97b7b52f283c97b47a`. Documentation-only commits after that SHA do not alter the executable behavior that was validated. If later evidence exposes an M5 defect, the milestone must be explicitly reopened and recertified rather than silently redefined.