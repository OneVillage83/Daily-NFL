# M2 Architecture-Conformance Audit

**Project:** The Daily Line — Daily NFL  
**Milestone:** M2 — Persistence & Migration Foundation  
**Audit date:** 2026-08-21  
**Audit branch:** `audit/m2-architecture-conformance`  
**Governing roadmap:** `docs/implementation/IMPLEMENTATION_ROADMAP_V1.md`  
**Architecture dependencies:** F-2, F-3, F-4, F-5  
**Certification status:** **NOT YET CERTIFIED — SCHEMA REMEDIATIONS IMPLEMENTED; LOCAL QUALITY / DATABASE GATES PENDING**

---

## 1. Audit purpose

M2 is the persistence boundary beneath provider acquisition, reconciliation, PIT reconstruction, normalization, feature construction, and later modeling. The certification question is therefore stricter than whether SQLite tables exist:

> Can a versioned Daily-NFL database preserve canonical football identity, immutable evidence, conflicting/revised observations, historical knowledge clocks, and the certified M1/F-5 event hierarchy without destructive migration or silent invention of historical facts?

M2 is not certified because M3-M6 code already uses the current schema. Those layers remain provisional and must consume the certified persistence contract.

Status vocabulary:

- `SATISFIED` — existing persistence matched the governing architecture.
- `SATISFIED AFTER REMEDIATION` — an M2/F-architecture gap was corrected in this audit.
- `DEFERRED BY ARCHITECTURE` — implementation belongs to a later milestone.
- `LOCAL VALIDATION PENDING` — static implementation is present but requires executable evidence.
- `BLOCKED` — certification cannot proceed.

---

## 2. Governing M2 contract

Roadmap dependencies:

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

M2 also must persist the now-certified M1 ontology where F-3/F-5 make the relationship foundational. It does not duplicate later provider, reconciliation, PIT-selection, or normalization logic.

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

Compatibility surfaces reviewed:

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

---

## 4. Conformance matrix

| ID | Requirement | Status | Evidence / remediation |
|---|---|---|---|
| M2-01 | Versioned migration ledger | `SATISFIED AFTER REMEDIATION` | Existing ordered migrations retained; v4 `m2_architecture_conformance` added rather than rewriting historical DDL. |
| M2-02 | One governing current schema version | `SATISFIED AFTER REMEDIATION` | Current authority remains `persistence.migrations.SCHEMA_VERSION`; migration-1 module now labels only `INITIAL_SCHEMA_VERSION`. |
| M2-03 | Clean DB initializes from zero | `LOCAL VALIDATION PENDING` | Migration engine supports zero→v4; unit/CLI tests updated, local disposable-DB gate still required. |
| M2-04 | Foreign keys enabled | `SATISFIED` | Connection helper enables `PRAGMA foreign_keys = ON`; existing tests verify enforcement. |
| M2-05 | Integrity check available | `SATISFIED` | `PRAGMA integrity_check` helper retained; CLI reports result. |
| M2-06 | Migration history fails closed if incomplete | `SATISFIED AFTER REMEDIATION` | Added ordered row-count/sequence/name validation; `MAX(version)` alone is no longer trusted. |
| M2-07 | Migration ledger itself is immutable | `SATISFIED AFTER REMEDIATION` | v4 adds update/delete rejection triggers and tests. |
| M2-08 | Check mode validates history without migrating | `SATISFIED AFTER REMEDIATION` | `validate_schema_history()` is exported and used by `initialize_database.py --check`. |
| M2-09 | Provider registry persisted | `SATISFIED` | Existing `providers` table retained; richer capability metadata remains M3. |
| M2-10 | Immutable raw evidence metadata persisted | `SATISFIED` | `raw_evidence` retains provider, source URI/category, checksum, object path, schema/parser versions, clocks, availability method/confidence and append-only triggers. |
| M2-11 | Raw evidence precedes normalized observations by traceable reference | `SATISFIED` | Observation tables retain `evidence_id` foreign-key references where applicable; normalized play persistence retains provenance. |
| M2-12 | Provider IDs remain external/crosswalk data | `SATISFIED` | Canonical IDs remain separate; external IDs live in crosswalk/observation fields. |
| M2-13 | External-ID crosswalk history representable | `SATISFIED` | Existing v2 crosswalk schema supports validity, method/confidence, verification, decision IDs and supersession. |
| M2-14 | Reconciliation ambiguity/history auditable | `SATISFIED` | Existing decision ledger retains unresolved/ambiguous/conflict states and candidate details; execution remains M4. |
| M2-15 | Certified Game competition identity persisted | `SATISFIED AFTER REMEDIATION` | v4 adds `games.competition_id`; all new games require nonblank canonical competition identity. |
| M2-16 | Schedule observations remain separate and revisionable | `SATISFIED AFTER REMEDIATION` | Existing append-only schedule observations retained; added actual kickoff, neutral-site, schedule-version fields while status/kickoff revisions remain observations. |
| M2-17 | Possession segment is distinct from drive | `SATISFIED AFTER REMEDIATION` | Added canonical `possession_segments` and segment references from drives/plays; legacy `possessions` remains compatibility-only. |
| M2-18 | New drive/play rows require F-5 segment identity | `SATISFIED AFTER REMEDIATION` | v4 insert triggers reject missing `possession_segment_id`. |
| M2-19 | Play-event identity is first-class | `SATISFIED AFTER REMEDIATION` | Added canonical `play_events` identity ledger keyed to play + canonical sequence. Detailed provider interpretation remains in revisioned play observations. |
| M2-20 | Participation identity is first-class | `SATISFIED AFTER REMEDIATION` | Added canonical `participations`; participation observations now reference `participation_id`. |
| M2-21 | Penalty identity is first-class | `SATISFIED AFTER REMEDIATION` | Added canonical `penalties`; penalty observations now reference `penalty_id`. |
| M2-22 | Play provider corrections remain revisions of canonical play | `SATISFIED` | Existing append-only `play_observations` attach multiple provider revisions to one `play_id`; M6 compatibility test retained. |
| M2-23 | Participation observations carry four clocks | `SATISFIED AFTER REMEDIATION` | Added `effective_at` and `published_at`; existing observed/ingested/available retained. |
| M2-24 | Penalty observations carry four clocks | `SATISFIED AFTER REMEDIATION` | Added `effective_at` and `published_at`; existing observed/ingested/available retained. |
| M2-25 | Participation/penalty provider corrections are traceable | `SATISFIED AFTER REMEDIATION` | Added `provider_revision` to both observation tables. |
| M2-26 | Availability method/confidence retained | `SATISFIED` | Raw/schedule/play/participation/penalty/result observations preserve both. |
| M2-27 | Observations are append-only | `SATISFIED` | Existing observation triggers retained; new canonical child ledgers are also immutable. |
| M2-28 | Canonical result revisions retain source observations | `SATISFIED` | `game_results` + `game_result_sources` preserve revision and source-observation lineage. |
| M2-29 | Canonical game result retains final timestamp | `SATISFIED AFTER REMEDIATION` | Added `game_results.final_at` to represent certified M1 result truth. |
| M2-30 | Legacy v1-v3 rows migrate without fabricated new facts | `SATISFIED AFTER REMEDIATION` | v4 is additive; missing new identity columns remain NULL on legacy rows until explicit defensible backfill. |
| M2-31 | Newly introduced legacy identity links can be backfilled once | `SATISFIED AFTER REMEDIATION` | Game competition and drive/play segment links permit one NULL→known transition while all pre-existing facts are frozen; later changes fail closed. |
| M2-32 | Normalized M6 compatibility persists stronger M1/M2 identity | `SATISFIED AFTER REMEDIATION; LOCAL GATE PENDING` | Bridge writes segment/event/participation/penalty identities plus full child provenance without exposing provider IDs as canonical identity. |
| M2-33 | Full repository remains compatible | `LOCAL VALIDATION PENDING` | Full pytest/Ruff/mypy gate required before certification. |
| M2-34 | Real disposable DB migrate + check passes | `LOCAL VALIDATION PENDING` | `initialize_database.py` must be exercised in migrate and check modes on local SQLite. |

---

## 5. F-2 audit — source / provenance persistence

### Provider abstraction vs persistence

M2 persists provider identity and observation provenance. The complete capability registry, acquisition adapters, immutable raw-file store implementation, licensing metadata richness, and nflverse acquisition are M3 concerns and are not duplicated here.

### Raw evidence

The original schema already retained immutable raw-evidence metadata and protected it from update/delete. M2 preserves that evidence-first boundary.

### Normalized provenance

Schedule, play, participation, penalty, and result observations can all retain provider identity, raw evidence reference, temporal availability, and revisions as applicable. The audit specifically repaired participation/penalty clock and provider-revision gaps.

### Conflicting providers

The schema does not overwrite a single provider-shaped row. Multiple observations may attach to canonical identities. Reconciliation ledgers preserve decisions separately.

---

## 6. F-3 audit — canonical identity persistence

The existing v1/v2 design correctly separated canonical IDs from provider external IDs, but M1 certification expanded the required NFL identity vocabulary.

M2 now persists the foundational F-5 child identities needed by the event ledger:

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

Migration v4 deliberately does **not** derive competition or possession-segment identity from legacy row position merely because it can guess a likely value. Existing v1-v3 rows retain NULL in newly added identity fields until an explicit, defensible reconciliation/backfill occurs.

This prevents migration code from rewriting historical ontology without evidence.

---

## 7. F-4 audit — temporal / revision persistence

### Four clocks

Raw evidence, schedule observations, play observations and game-result observations already carried the four temporal clocks where applicable. Participation and penalty observations only carried observation/ingestion clocks before this audit.

M2 adds:

```text
effective_at
published_at
```

to participation/penalty observations while retaining:

```text
observed_at
ingested_at
available_at
availability_method
availability_confidence
```

### Append-only revisions

Observation tables remain append-only. Provider corrections produce additional observations/revisions rather than updates.

### Bitemporal responsibility

M2 stores the clocks; M5 determines defensible `available_at`, performs as-of selection, constructs PIT snapshots, and enforces leakage policy. M2 does not duplicate M5.

---

## 8. F-5 audit — football event ledger persistence

### Possession segment vs legacy possession

Before M2 certification, persistence had only `possessions` and associated drives directly with that relation. That no longer matched the certified M1/F-5 hierarchy.

The v4 migration adds `possession_segments` as the architecture-native identity. The legacy `possessions` table remains temporarily available for existing M6 compatibility and historical rows; it is not treated as a replacement for F-5 possession segments.

### Child identities vs observations

`play_events`, `participations`, and `penalties` are canonical identity ledgers. Provider/revision-specific detail remains in immutable play/participation/penalty observation data. This permits corrections to change interpretation without changing the football event identity when reconciliation determines it is the same event.

### Results

Provider result observations and canonical result revisions remain separate. `final_at` has been added to canonical result truth.

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

Added `effective_at` and `published_at`, preserving `observed_at`, `ingested_at`, `available_at`, method and confidence.

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

Added append-only triggers and tests.

### F-10 — rewriting migration 1 would destroy migration truth

**Severity:** HIGH — AVOIDED BY DESIGN

The audit adds migration 4 rather than changing historical migration semantics. `schema.py` is explicitly migration-1 DDL; the current version authority lives in `migrations.py`.

### F-11 — migrated legacy rows could be silently assigned guessed new identity

**Severity:** HIGH — REMEDIATED BY FAIL-CLOSED MIGRATION POLICY

Migration v4 leaves newly introduced identity columns NULL on legacy rows. A one-time explicit backfill is allowed only for the new identity reference; all pre-existing canonical facts remain immutable.

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

M2 only certifies that the database can preserve the evidence and identities those later layers need.

---

## 11. Required local certification gates

After switching to the M2 audit branch, the full repository gate must pass:

```powershell
git fetch origin
git switch audit/m2-architecture-conformance
git pull --ff-only
git status --short

python -m pytest -q
python -m ruff check .
python -m mypy .

git status --short
```

M2 additionally requires an actual disposable SQLite initialize/check cycle:

```powershell
$db = Join-Path $env:TEMP "daily-nfl-m2-cert.db"
Remove-Item $db -ErrorAction SilentlyContinue
python scripts/initialize_database.py --database $db
python scripts/initialize_database.py --database $db --check
Remove-Item $db -ErrorAction SilentlyContinue
```

Certification conditions:

1. all repository tests pass;
2. Ruff passes;
3. strict mypy passes;
4. working tree remains clean;
5. fresh database initializes to schema v4;
6. check mode validates schema v4, foreign keys, and integrity;
7. migration tests prove v1/v2/v3 upgrade paths and fail-closed corrupted history;
8. any failure caused by the stronger M2 contract is fixed rather than weakening the architecture to preserve provisional M3-M6 behavior.

---

## 12. Current decision

```text
M2 ARCHITECTURE-CONFORMANCE AUDIT: COMPLETE IN STATIC REVIEW
M2 SCHEMA REMEDIATION: IMPLEMENTED
M2 MIGRATION-HISTORY HARDENING: IMPLEMENTED
M2 LOCAL QUALITY GATE: PENDING
M2 REAL SQLITE INITIALIZE/CHECK GATE: PENDING
M2 ARCHITECTURE CERTIFICATION: WITHHELD UNTIL LOCAL GATES PASS
```
