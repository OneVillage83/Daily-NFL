# M2 Architecture-Conformance Audit

**Project:** The Daily Line — Daily NFL  
**Milestone:** M2 — Persistence & Migration Foundation  
**Audit date:** 2026-08-21  
**Audit branch:** `audit/m2-architecture-conformance`  
**Governing roadmap:** `docs/implementation/IMPLEMENTATION_ROADMAP_V1.md`  
**Architecture dependencies:** F-2, F-3, F-4, F-5  
**Validated code head:** `d6246696f29e263049f3bb07dd5eb5538e589c22`  
**Certification status:** **ARCHITECTURE-CERTIFIED**

---

## 1. Audit purpose

M2 is the persistence boundary beneath provider acquisition, reconciliation, PIT reconstruction, normalization, feature construction, and later modeling. Certification therefore requires more than the existence of SQLite tables.

The governing question is:

> Can a versioned Daily-NFL database preserve canonical football identity, immutable evidence, conflicting/revised observations, historical knowledge clocks, and the certified M1/F-5 event hierarchy without destructive migration or silent invention of historical facts?

The final answer after static audit, remediation, negative testing, full repository validation, and a real SQLite migration/check cycle is **yes**.

M3-M6 code remains provisional even where it consumes this schema. M2 certification establishes the persistence contract that those milestones must consume; it does not certify those later layers.

Status vocabulary used in this record:

- `SATISFIED` — persistence matched the governing architecture.
- `SATISFIED AFTER REMEDIATION` — an M2/F-architecture gap was corrected during this audit.
- `VALIDATED` — the requirement was exercised by the final local certification gate.
- `DEFERRED BY ARCHITECTURE` — implementation belongs to a later milestone.

---

## 2. Governing M2 contract

Architecture dependencies:

```text
F-2 — Data Source & Acquisition Architecture
F-3 — Canonical Identity & Reconciliation
F-4 — Historical Point-in-Time Architecture
F-5 — Canonical Game / Drive / Play Architecture
```

Roadmap deliverables:

```text
schema version
providers
raw evidence metadata
entity/provider external-ID crosswalk
games
schedule observations
drives
plays
play observations / revisions
participation observations
penalty observations
result truth
provenance clocks:
    effective_at
    published_at
    observed_at
    ingested_at
    available_at
```

Roadmap design constraints:

```text
append-only observations where history matters
no silent provider overwrite
external IDs never become canonical IDs
corrections remain traceable
migration versions explicit
```

Roadmap exit gate:

```text
clean DB initializes from zero
migration version is queryable
provenance fields exist
repeated / revised observations are representable
```

M2 must also persist the now-certified M1 ontology where F-3/F-5 make the relationship foundational. It must not duplicate later provider, reconciliation, PIT-selection, or normalization responsibilities.

---

## 3. Evidence reviewed

Architecture / roadmap:

```text
docs/implementation/IMPLEMENTATION_ROADMAP_V1.md
docs/architecture/F00-F04_ARCHITECTURE_FOUNDATION_V1.md
docs/architecture/F05-F09_FOOTBALL_STATE_ARCHITECTURE_V1.md
```

Persistence implementation:

```text
daily_nfl/persistence/__init__.py
daily_nfl/persistence/database.py
daily_nfl/persistence/schema.py
daily_nfl/persistence/migrations.py
daily_nfl/persistence/identity_schema.py
daily_nfl/persistence/pit_schema.py
daily_nfl/persistence/m2_conformance_schema.py
scripts/initialize_database.py
```

Compatibility surfaces:

```text
daily_nfl/normalization/persistence.py
daily_nfl/reconciliation/repository.py
daily_nfl/pit/*
```

Primary tests:

```text
tests/test_persistence.py
tests/test_migration_safety.py
tests/test_m2_persistence_conformance.py
tests/test_initialize_database_cli.py
tests/test_play_normalization_persistence.py
tests/test_reconciliation_schema.py
tests/test_reconciliation_history.py
tests/test_pit_schema_repository.py
tests/test_pit_snapshot.py
```

Executable certification evidence:

```text
docs/implementation/M2_LOCAL_VALIDATION_20260821.md
```

---

## 4. Conformance matrix

| ID | Requirement | Final status | Evidence / remediation |
|---|---|---|---|
| M2-01 | Versioned migration ledger | `SATISFIED AFTER REMEDIATION` | Existing ordered migrations retained; v4 `m2_architecture_conformance` added instead of rewriting historical DDL. |
| M2-02 | One governing current schema version | `SATISFIED AFTER REMEDIATION` | Current authority is `persistence.migrations.SCHEMA_VERSION`; migration-1 module exposes only `INITIAL_SCHEMA_VERSION`. |
| M2-03 | Clean DB initializes from zero | `VALIDATED` | Real disposable SQLite database migrated 0→4 successfully. |
| M2-04 | Foreign keys enabled | `VALIDATED` | Connection helper enables `PRAGMA foreign_keys = ON`; real DB gate reported `foreign_keys_enabled: true`. |
| M2-05 | Integrity check available | `VALIDATED` | Real migrate/check gates both reported `integrity_ok: true`. |
| M2-06 | Migration history fails closed if incomplete | `SATISFIED AFTER REMEDIATION` | Added ordered row-count/sequence/name validation; `MAX(version)` alone is no longer trusted. |
| M2-07 | Migration ledger itself is immutable | `SATISFIED AFTER REMEDIATION` | v4 adds update/delete rejection triggers and tests. |
| M2-08 | Check mode validates history without migrating | `VALIDATED` | `validate_schema_history()` is used by `initialize_database.py --check`; real check held schema 4→4. |
| M2-09 | Provider registry persisted | `SATISFIED` | Existing `providers` table retained; richer capability metadata remains M3. |
| M2-10 | Immutable raw evidence metadata persisted | `SATISFIED` | `raw_evidence` retains provider, source/category, checksum, object path, versions, clocks, method/confidence, and append-only guards. |
| M2-11 | Raw evidence precedes normalized observations by traceable reference | `SATISFIED` | Observation tables retain evidence references where applicable; normalized play persistence retains provenance. |
| M2-12 | Provider IDs remain external/crosswalk data | `SATISFIED` | Canonical IDs remain separate; external IDs live in crosswalk/observation fields. |
| M2-13 | External-ID crosswalk history representable | `SATISFIED` | Existing v2 crosswalk supports validity, method/confidence, verification, decision IDs, and supersession. |
| M2-14 | Reconciliation ambiguity/history auditable | `SATISFIED` | Existing decision ledger retains unresolved/ambiguous/conflict states and candidate details; execution remains M4. |
| M2-15 | Certified Game competition identity persisted | `SATISFIED AFTER REMEDIATION` | v4 adds `games.competition_id`; all new games require nonblank canonical competition identity. |
| M2-16 | Schedule observations remain separate and revisionable | `SATISFIED AFTER REMEDIATION` | Added actual kickoff, neutral-site, and schedule-version fields while status/kickoff revisions remain append-only observations. |
| M2-17 | Possession segment is distinct from drive | `SATISFIED AFTER REMEDIATION` | Added canonical `possession_segments` plus segment references from drives/plays; legacy `possessions` is compatibility/history only. |
| M2-18 | New drive/play rows require F-5 segment identity | `SATISFIED AFTER REMEDIATION` | v4 insert triggers reject missing `possession_segment_id`. |
| M2-19 | Play-event identity is first-class | `SATISFIED AFTER REMEDIATION` | Added canonical `play_events` identity ledger keyed to play + canonical sequence. |
| M2-20 | Participation identity is first-class | `SATISFIED AFTER REMEDIATION` | Added canonical `participations`; observations reference `participation_id`. |
| M2-21 | Penalty identity is first-class | `SATISFIED AFTER REMEDIATION` | Added canonical `penalties`; observations reference `penalty_id`. |
| M2-22 | Play provider corrections remain revisions of canonical play | `VALIDATED` | Append-only `play_observations` attach multiple revisions to one `play_id`; compatibility tests pass. |
| M2-23 | Participation observations carry required clocks | `SATISFIED AFTER REMEDIATION` | Added `effective_at` and `published_at`; observed/ingested/available clocks retained. |
| M2-24 | Penalty observations carry required clocks | `SATISFIED AFTER REMEDIATION` | Added `effective_at` and `published_at`; observed/ingested/available clocks retained. |
| M2-25 | Participation/penalty provider corrections are traceable | `SATISFIED AFTER REMEDIATION` | Added `provider_revision` to both observation tables. |
| M2-26 | Availability method/confidence retained | `SATISFIED` | Raw/schedule/play/participation/penalty/result observations preserve both. |
| M2-27 | Observations are append-only | `SATISFIED` | Existing observation guards retained; new canonical child ledgers are immutable. |
| M2-28 | Canonical result revisions retain source observations | `SATISFIED` | `game_results` + `game_result_sources` preserve revision and source-observation lineage. |
| M2-29 | Canonical game result retains final timestamp | `SATISFIED AFTER REMEDIATION` | Added `game_results.final_at`. |
| M2-30 | Legacy v1-v3 rows migrate without fabricated new facts | `VALIDATED` | v4 is additive; newly introduced identity columns remain NULL on legacy rows until explicit defensible backfill. |
| M2-31 | Newly introduced legacy identity links can be backfilled once | `VALIDATED` | Game competition and drive/play segment links permit one NULL→known transition, then reject later mutation. |
| M2-32 | Provisional M6 compatibility persists stronger M1/M2 identity | `VALIDATED` | Bridge writes segment/event/participation/penalty identities and child provenance without provider IDs becoming canonical identity. |
| M2-33 | Full repository remains compatible | `VALIDATED` | `124 passed in 2.30s`; Ruff PASS; strict mypy PASS across 68 source files; clean tree. |
| M2-34 | Real disposable DB migrate + check passes | `VALIDATED` | Local CLI gate migrated 0→4 and checked 4→4 with foreign keys/integrity true. |

---

## 5. F-2 audit — source and provenance persistence

M2 persists provider identity and observation provenance. The complete provider capability registry, acquisition adapters, immutable raw-file store implementation, licensing metadata richness, and nflverse acquisition remain M3 responsibilities.

The original schema already retained immutable raw-evidence metadata and protected it from update/delete. M2 preserves that evidence-first boundary.

Schedule, play, participation, penalty, and result observations can retain provider identity, raw-evidence reference, temporal availability, and revisions as applicable. The audit repaired participation/penalty clock and provider-revision gaps.

The schema does not destructively overwrite one provider-shaped row when providers disagree. Multiple observations attach to canonical identities, and reconciliation decisions remain separate.

---

## 6. F-3 audit — canonical identity persistence

The existing v1/v2 design correctly separated canonical IDs from provider external IDs, but certified M1 expanded the required NFL identity vocabulary.

M2 now persists the foundational F-5 event-ledger identities:

```text
game
possession segment
drive
play
play event
participation
penalty
```

The generic external-ID crosswalk remains separate. Full football-specific reconciliation is M4.

### Legacy identity rule

Migration v4 deliberately does **not** derive competition or possession-segment identity from legacy row position merely because a likely value can be guessed. Existing v1-v3 rows retain NULL in newly added identity fields until an explicit defensible reconciliation/backfill occurs.

The certification tests proved the intended transition contract:

1. legacy rows migrate without fabricated identity;
2. one explicit NULL→known backfill is permitted for the newly introduced reference;
3. later mutation is rejected with entity-specific immutability errors.

---

## 7. F-4 audit — temporal and revision persistence

Raw evidence, schedule observations, play observations, and game-result observations already carried historical timing fields where applicable. Participation and penalty observations lacked `effective_at` and `published_at` before this audit.

M2 adds both while retaining:

```text
observed_at
ingested_at
available_at
availability_method
availability_confidence
```

Observation tables remain append-only. Provider corrections produce additional observations/revisions rather than updates.

M2 stores the clocks; M5 determines defensible `available_at`, performs as-of selection, constructs PIT snapshots, and enforces leakage policy. M2 does not duplicate M5.

---

## 8. F-5 audit — football event-ledger persistence

### Possession segment vs legacy possession

Before M2 certification, persistence had only `possessions` and associated drives directly with that relation. That no longer matched the certified M1/F-5 hierarchy.

Migration v4 adds `possession_segments` as the architecture-native identity. Legacy `possessions` remains temporarily available for compatibility and historical rows; it is not treated as a replacement for F-5 possession segments.

### Child identities vs observations

`play_events`, `participations`, and `penalties` are canonical identity ledgers. Provider/revision-specific detail remains in immutable play/participation/penalty observation data. Corrections can therefore change interpretation without changing football-event identity when reconciliation determines the event is the same.

Certification also corrected a stale test expectation: a completed pass with a penalty correctly produces four canonical play events:

```text
SNAP
THROW
CATCH
PENALTY
```

The architecture was not weakened to satisfy the old three-event expectation.

### Results

Provider result observations and canonical result revisions remain separate. `final_at` is now persisted on canonical result truth.

---

## 9. Findings and remediations

### F-01 — certified Game competition identity could not be persisted

**Severity:** HIGH — REMEDIATED

Added `games.competition_id`; new writes fail if absent.

### F-02 — persistence conflated possession with possession segment

**Severity:** HIGH — REMEDIATED

Added architecture-native `possession_segments` plus required segment links for new drives/plays.

### F-03 — play-event / participation / penalty canonical identities were incomplete

**Severity:** HIGH — REMEDIATED

Added canonical identity ledgers and observation links for participation/penalty.

### F-04 — participation/penalty temporal clocks were incomplete

**Severity:** HIGH — REMEDIATED

Added `effective_at` and `published_at`, preserving observed/ingested/available timing, method, and confidence.

### F-05 — participation/penalty provider revisions were not explicit

**Severity:** MEDIUM — REMEDIATED

Added `provider_revision` to both observation tables.

### F-06 — schedule observation contract omitted certified schedule-state fields

**Severity:** MEDIUM — REMEDIATED

Added actual kickoff, neutral-site, and schedule-version fields to the append-only schedule observation ledger.

### F-07 — canonical result truth omitted final timestamp

**Severity:** MEDIUM — REMEDIATED

Added `game_results.final_at`.

### F-08 — migration history trusted only the maximum version

**Severity:** HIGH — REMEDIATED

Migration validation now checks contiguous rows and exact governing names before migration and in check mode.

### F-09 — migration ledger could be edited destructively

**Severity:** HIGH — REMEDIATED

Added append-only update/delete rejection triggers and tests.

### F-10 — rewriting migration 1 would destroy migration truth

**Severity:** HIGH — AVOIDED BY DESIGN

The audit adds migration 4 rather than changing historical migration semantics. `schema.py` is explicitly migration-1 DDL; the current version authority lives in `migrations.py`.

### F-11 — migrated legacy rows could be silently assigned guessed new identity

**Severity:** HIGH — REMEDIATED BY FAIL-CLOSED MIGRATION POLICY

Migration v4 leaves newly introduced identity columns NULL on legacy rows. One explicit backfill is allowed only for the new identity reference; all pre-existing canonical facts remain immutable.

---

## 10. Explicit deferrals — not M2 defects

The following are intentionally outside M2 certification:

- full provider capability registry and licensing/coverage metadata — M3;
- acquisition adapters and raw-store implementation — M3;
- football-specific identity reconciliation execution/backfills — M4;
- derivation policy for defensible `available_at` — M5;
- as-of state selection and PIT leakage engine — M5;
- complete provider PBP normalization semantics — M6;
- feature contracts, analytics, models, simulation, markets, recommendation gate.

M2 certifies that the database can preserve the evidence and identities those later layers need.

---

## 11. Executable certification gates

Final repository gate at validated code head `d6246696f29e263049f3bb07dd5eb5538e589c22`:

```text
pytest: 124 passed in 2.30s
Ruff: All checks passed!
mypy: Success: no issues found in 68 source files
git status --short: clean
```

Real disposable SQLite initialize gate:

```text
schema_version_before: 0
schema_version_after: 4
supported_schema_version: 4
foreign_keys_enabled: true
integrity_ok: true
mode: migrate
```

Real SQLite check-mode gate on the same database:

```text
schema_version_before: 4
schema_version_after: 4
supported_schema_version: 4
foreign_keys_enabled: true
integrity_ok: true
mode: check
```

Detailed executable evidence is preserved in `docs/implementation/M2_LOCAL_VALIDATION_20260821.md`.

Documentation-only commits after the validated code head record certification evidence and status; they do not alter the code/schema behavior that was exercised locally.

---

## 12. Final decision

```text
M2 ARCHITECTURE-CONFORMANCE AUDIT: PASS
M2 SCHEMA REMEDIATION: PASS
M2 MIGRATION-HISTORY HARDENING: PASS
M2 LOCAL QUALITY GATE: PASS
M2 REAL SQLITE INITIALIZE/CHECK GATE: PASS
M2 ARCHITECTURE CERTIFICATION: ARCHITECTURE-CERTIFIED
```

M3 — Raw Evidence & Provider Abstraction is the next certification target.
