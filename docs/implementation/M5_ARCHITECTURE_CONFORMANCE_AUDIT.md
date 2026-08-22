# M5 Architecture-Conformance Audit

**Project:** The Daily Line — Daily NFL  
**Milestone:** M5 — Historical PIT Engine  
**Architecture dependency:** F-4 — Historical Point-in-Time Architecture  
**Certified dependency base:** M0-M4  
**Certification status:** **NOT YET CERTIFIED — STATIC AUDIT / REMEDIATION IMPLEMENTED; EXECUTABLE GATES PENDING**

---

## 1. Audit rule

The existing PIT package was treated as provisional evidence. F-4 is authoritative. If a historical reconstruction can admit information that was not defensibly knowable at the requested prediction timestamp, M5 fails regardless of apparent model quality.

M5 certifies historical information state, not later feature semantics. The richer feature registry/eras remain M9, prediction identity remains M10, and walk-forward model evaluation remains M14.

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

## 3. Conformance matrix after remediation

| ID | Requirement | Status | Evidence / remediation |
|---|---|---|---|
| M5-01 | Standard horizons and pregame cutoff | `SATISFIED` | `PredictionCutoff` retains all six locked horizons and requires `prediction_time < kickoff`. |
| M5-02 | Game-day information allowed when legitimately known | `SATISFIED` | Eligibility remains timestamp-based; Sunday/game-day is not blanket excluded. |
| M5-03 | Four temporal knowledge clocks remain distinct | `SATISFIED` | PIT contracts retain effective/publication/observation/ingestion clocks separately. |
| M5-04 | Earliest defensible `available_at` selected | `SATISFIED AFTER REMEDIATION` | High-confidence source/publication/archive/observation evidence is compared and the earliest defensible clock is selected. |
| M5-05 | Inferred report date has medium confidence and explicit opt-in | `SATISFIED AFTER REMEDIATION` | Inferred report date now maps to `MEDIUM`; default strict policy still excludes it until explicitly enabled. |
| M5-06 | Unknown/ingestion-only timing excluded in strict PIT | `SATISFIED` | No defensible time raises in strict derivation; permissive ingestion fallback remains `UNKNOWN/LOW`. |
| M5-07 | Knowledge-time as-of selection | `SATISFIED` | Latest eligible `available_at` is selected per logical key. |
| M5-08 | Same-knowledge conflicting revisions fail closed | `SATISFIED AFTER REMEDIATION` | `observed_at`/`ingested_at` are no longer revision tie-breakers; differing/unknown payloads at the same top knowledge timestamp raise `PITSelectionConflictError`. |
| M5-09 | Duplicate same-content observations at same knowledge time remain deterministic | `SATISFIED AFTER REMEDIATION` | Equal payload hashes use deterministic input identity without fabricating a content change. |
| M5-10 | Real-world validity + knowledge-time bitemporal query | `SATISFIED AFTER REMEDIATION` | `select_latest_bitemporal_as_of` requires `effective_at`, selects latest effective state first, then latest knowable revision of that state. |
| M5-11 | Late correction to an older state cannot displace newer real-world state | `SATISFIED AFTER REMEDIATION` | Dedicated bitemporal regression fixture locks effective-state precedence. |
| M5-12 | Raw-backed PIT inputs retain acquisition-observation provenance | `SATISFIED AFTER REMEDIATION` | PIT inputs/snapshots carry `evidence_id`, `evidence_observation_id`, provider namespace, and raw checksum. Strict selection rejects incomplete raw provenance. |
| M5-13 | Provider/source versions retained where available | `SATISFIED AFTER REMEDIATION` | PIT inputs carry provider revision/schema/parser versions; schedule path prefers acquisition-observation versions and falls back to raw-content metadata. |
| M5-14 | Immutable feature snapshot stores contract/version/values | `SATISFIED AFTER REMEDIATION` | Generic M5 feature snapshot spec records contract/version and canonical scalar values without defining M9 feature semantics. |
| M5-15 | Immutable snapshot stores coverage/missingness/PIT result | `SATISFIED AFTER REMEDIATION` | Snapshot hash/persistence includes deterministic coverage report, missing features, and `PITValidationResult.PASS`. |
| M5-16 | Snapshot identity includes exact input provenance | `SATISFIED AFTER REMEDIATION` | Manifest hashes all ordered input IDs, clocks, availability evidence, provider/source versions, payload/raw hashes, and acquisition observation identity. |
| M5-17 | Snapshot membership is sealed and complete | `SATISFIED AFTER REMEDIATION` | v7 requires declared input count to equal persisted membership before sealing; legacy v6 history remains untouched. |
| M5-18 | Database rejects inconsistent raw provenance in certified snapshots | `SATISFIED AFTER REMEDIATION` | v7 trigger requires raw content/acquisition observation/provider/checksum to agree for raw-backed inputs. |
| M5-19 | Source after cutoff rejected | `SATISFIED` | Generic cutoff validator remains fail closed. |
| M5-20 | Current-game final score/stats/plays rejected | `SATISFIED AFTER REMEDIATION` | Current-game kinds require cutoff-game context and are explicitly rejected; missing context also fails. |
| M5-21 | Actual current-game weather cannot replace forecast | `SATISFIED AFTER REMEDIATION` | Actual weather requires subject context and current-game actual is rejected. |
| M5-22 | Later/closing market quote rejected | `SATISFIED AFTER REMEDIATION` | Market quote timestamp is mandatory under strict policy; post-cutoff quote is rejected. |
| M5-23 | Future game/opponent data rejected | `SATISFIED AFTER REMEDIATION` | Source game kickoff is mandatory and must precede cutoff. |
| M5-24 | Future season/week labels rejected | `SATISFIED AFTER REMEDIATION` | Dedicated `FUTURE_SEASON_WEEK_LABEL` kind always fails historical validation. |
| M5-25 | End-of-season aggregates rejected before completion | `SATISFIED AFTER REMEDIATION` | Completion timestamp is mandatory; future completion fails. |
| M5-26 | Provider corrections require defensible historical context | `SATISFIED AFTER REMEDIATION` | Corrections require provider/revision and defensible pre-cutoff availability. |
| M5-27 | Schedule revisions change only when correction becomes knowable | `SATISFIED AFTER REMEDIATION` | Provider-scoped schedule revision selection preserves earlier revision before later `available_at`. |
| M5-28 | Cross-provider schedule disagreement cannot silently overwrite | `SATISFIED AFTER REMEDIATION` | Providers are reconstructed independently; conflicting pregame-safe schedule state raises instead of prioritizing the newest source. |
| M5-29 | Agreeing providers retain all supporting source inputs | `SATISFIED AFTER REMEDIATION` | `ScheduleStateAsOf.supporting_inputs` retains every agreeing provider's selected provenance. |
| M5-30 | Pregame schedule state retains certified safe fields | `SATISFIED AFTER REMEDIATION` | Status, scheduled kickoff, venue, neutral site, schedule version, provider revision are retained. |
| M5-31 | Retrospective `actual_kickoff` is not exposed as pregame feature state | `SATISFIED AFTER REMEDIATION` | Actual kickoff is deliberately excluded from schedule-state payload/hash; it is retrospective truth only. |
| M5-32 | Actual game start is a hard retrospective leakage boundary | `SATISFIED AFTER REMEDIATION` | Snapshot sealing checks retrospective actual start when present and refuses `prediction_time >= actual_kickoff`; conflicting actual-start truth also fails closed. |
| M5-33 | Append-only historical observations/snapshots | `SATISFIED` | Existing append-only ledgers remain; v7 adds no destructive rewrite. |
| M5-34 | Forward migration preserves legacy PIT history | `STATIC TEST IMPLEMENTED; LOCAL GATE PENDING` | v6 legacy snapshot/seal survives v7 with new certification metadata left NULL rather than fabricated. |
| M5-35 | M0-M4 certified contracts remain intact | `STATIC REVIEW COMPLETE; LOCAL GATE PENDING` | v7 is forward-only; prior migrations unchanged. M3/M4 migration tests were made forward-compatible rather than pinning global schema forever. |
| M5-36 | Deterministic historical reconstruction validator | `IMPLEMENTED; LOCAL GATE PENDING` | `scripts/validate_m5_pit.py` reconstructs early/later schedule state, seals an early snapshot with acquisition provenance, and injects deliberate leakage. |
| M5-37 | Full repository quality gate | `LOCAL VALIDATION PENDING` | pytest / Ruff / strict mypy / clean tree required. |
| M5-38 | Feature availability eras | `DEFERRED BY ARCHITECTURE` | Exact feature registry/era semantics remain M9; M5 preserves missingness/coverage and must not fabricate historical availability. |
| M5-39 | Walk-forward final model evaluation | `DEFERRED BY ARCHITECTURE` | Chronological final evaluation is M14, not an M5 exit condition. |

---

## 4. Material findings and remediations

### F-01 — retrospective correction could leak through same `available_at`

**Severity:** CRITICAL — REMEDIATED

The provisional selector used observation/ingestion clocks after `available_at` to order revisions. A correction discovered months later could therefore win a historical tie even when both versions claimed the same historical knowledge timestamp. M5 now treats that as unresolved historical ambiguity unless the payloads are identical.

### F-02 — no explicit bitemporal state selection

**Severity:** HIGH — REMEDIATED

`effective_at` existed but was not used to reconstruct real-world-valid state. M5 now distinguishes knowledge history from real-world state history and chooses the latest effective state before selecting its latest knowable revision.

### F-03 — raw content identity was insufficient historical provenance

**Severity:** HIGH — REMEDIATED

M3 deliberately separated immutable content identity from acquisition-observation identity. M5 snapshots now retain both. A strict raw-backed PIT input without its acquisition observation/provider namespace is not eligible, and database sealing cannot bypass the raw evidence/provider/checksum relationship.

### F-04 — leakage-critical context could fail open

**Severity:** HIGH — REMEDIATED

Market quotes, future/prior games, season-final aggregates, current-game outcome kinds, actual weather, and provider corrections now require the temporal/context metadata needed to evaluate them. Missing context is itself a failure under strict PIT policy.

### F-05 — feature-input snapshot was not feature-complete

**Severity:** HIGH — REMEDIATED

The provisional snapshot stored source membership but not feature contract/version/values/coverage/missingness/PIT result. M5 now stores and hashes those generic fields while intentionally deferring the full M9 feature registry and era semantics.

### F-06 — schedule sources could silently overwrite one another

**Severity:** HIGH — REMEDIATED

Schedule revisions are now selected within provider namespace. The selected provider states are compared; disagreement blocks reconstruction rather than allowing whichever source happened to update last to become truth. Agreeing sources remain individually traceable.

### F-07 — retrospective `actual_kickoff` risked becoming a pregame feature

**Severity:** CRITICAL — REMEDIATED

Actual game start is retrospective event truth. It is excluded from pregame schedule state and its feature/input hash. It is used only when sealing a historical snapshot as a hard leakage boundary: a purported pregame prediction at or after actual start is invalid.

### F-08 — availability evidence ranking was incomplete

**Severity:** MEDIUM — REMEDIATED

M5 now chooses the earliest defensible high-confidence knowledge evidence and correctly classifies inferred report dates as medium confidence. Inferred timing remains excluded by default strict policy unless intentionally enabled.

### F-09 — earlier milestone tests pinned the repository's final schema version

**Severity:** LOW — REMEDIATED

M3/M4 migration tests now assert migration to the repository's current supported schema while still testing their own historical migration behavior. This avoids making later forward migrations look like regressions in earlier certified milestones.

---

## 5. Fail-closed behavior after remediation

M5 intentionally refuses to guess when:

- availability is after the cutoff or cannot meet strict method/confidence rules;
- raw-backed input lacks acquisition-observation/provider provenance;
- different payloads claim the same top knowledge timestamp;
- bitemporal state lacks `effective_at`;
- current-game result/stat/play enters a pregame snapshot;
- actual current-game weather is supplied as forecast information;
- market quote timestamp is missing or later than cutoff;
- source-game kickoff is missing or not yet occurred;
- future season/week labels are injected;
- end-of-season aggregate lacks completion time or was incomplete;
- provider correction lacks provider/revision or defensible timing;
- schedule providers disagree on pregame-safe canonical state;
- raw/acquisition/provider/checksum provenance disagrees;
- snapshot declared membership is incomplete;
- retrospective providers disagree on actual game start;
- prediction time is at or after retrospective actual game start.

---

## 6. Explicit deferrals — not M5 defects

- exact feature registry and feature-availability eras — M9;
- prediction/model identity fields — M10;
- football state semantics beyond PIT reconstruction — later state milestones;
- full play/drive normalization semantics — M6;
- final chronological/walk-forward model evaluation — M14;
- live provider-specific historical availability mappings not yet exposed by a provider — future provider expansion, never fabricated by M5.

---

## 7. Required executable certification evidence

Before M5 certification, the branch must produce:

```text
Python 3.12 environment
full pytest PASS
Ruff PASS
strict mypy PASS
clean working tree
schema version 7
fresh SQLite 0 -> 7 migrate PASS
SQLite 7 -> 7 check PASS
historical early-cutoff schedule revision = v1
historical later-cutoff schedule revision = v2
later correction hidden from earlier cutoff
later correction visible after its knowledge time
immutable feature snapshot sealed
raw evidence ID retained
acquisition-observation ID retained
provider/revision/checksum retained
deliberate current-game leakage rejected
same-knowledge conflicting correction unit fixture rejected
provider disagreement unit fixture rejected
actual-start boundary fixture rejected
```

The deterministic validation utility is `scripts/validate_m5_pit.py`.

---

## 8. Current decision

```text
M5 F-4 STATIC ARCHITECTURE AUDIT: COMPLETE
M5 AVAILABILITY DERIVATION REMEDIATION: IMPLEMENTED
M5 BITEMPORAL / REVISION SEMANTICS: IMPLEMENTED
M5 STRICT LEAKAGE CONTEXT: IMPLEMENTED
M5 RAW / ACQUISITION PROVENANCE: IMPLEMENTED
M5 IMMUTABLE FEATURE SNAPSHOT CONTRACT: IMPLEMENTED
M5 SCHEDULE AS-OF / PROVIDER CONFLICT: IMPLEMENTED
M5 RETROSPECTIVE ACTUAL-START BOUNDARY: IMPLEMENTED
M5 MIGRATION v7: IMPLEMENTED
M5 DETERMINISTIC VALIDATION UTILITY: IMPLEMENTED
M5 LOCAL QUALITY GATE: PENDING
M5 SQLITE v7 GATE: PENDING
M5 HISTORICAL RECONSTRUCTION GATE: PENDING
M5 ARCHITECTURE CERTIFICATION: WITHHELD UNTIL ALL EXECUTABLE GATES PASS
```
