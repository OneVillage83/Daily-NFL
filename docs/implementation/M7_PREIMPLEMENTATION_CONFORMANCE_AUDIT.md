# M7 Pre-Implementation Architecture Conformance Audit

**Project:** The Daily Line — Daily NFL
**Milestone:** M7 — State Engine V1
**Architecture:** F-6, F-7, F-8, F-9, F-10
**Certified base main:** `0dd515ec36f370ce70f67b3e771e1ceb4e36a149`
**Branch:** `checkpoint/m7-state-engine-v1`
**Status:** PRE-IMPLEMENTATION AUDIT COMPLETE — REMEDIATION REQUIRED

## 1. Purpose

This audit compares the certified M6C repository state against the locked M7 architecture before implementation begins.

The goal is to identify what can be reused, what is only a partial precursor, and what is genuinely missing so M7 can be implemented as a coherent production-planned V1 rather than accumulating ad hoc state features.

## 2. Existing certified foundation that M7 can reuse

### 2.1 Canonical identity foundation — PASS / REUSABLE

Existing canonical identity contracts already include:

- `TeamSeasonId`;
- `PersonId`;
- `PlayerId`;
- `RosterStintId`;
- `CoachRoleId`;
- `InjuryObservationId`;
- `DepthChartSnapshotId`;
- `GameId`.

Existing domain objects include persistent `Person`/`Player`, temporal `RosterStint`, and temporal `CoachingRole`.

This is a strong M7 dependency but is not itself a state engine.

### 2.2 Historical play evidence — PASS / REUSABLE

Certified M6 plus M6C provides:

- provider-neutral play state/execution/result contracts;
- participation;
- penalties;
- drive/possession transitions;
- exact raw provenance;
- 1999-2025 historical normalization compatibility.

This is the historical football evidence layer from which state estimators can derive performance/form/style observations.

### 2.3 PIT information boundary — PASS / REUSABLE

Certified M5 provides:

- `PredictionCutoff`;
- `PITInputRef`;
- exact availability clocks/method/confidence;
- leakage validation;
- deterministic content-addressed PIT snapshot manifests;
- exact input membership;
- immutable/sealed persistence semantics;
- `available_at <= prediction_time < kickoff` enforcement.

M7 should reuse these semantics for state inputs rather than inventing an incompatible availability model.

### 2.4 Persistence/migration constitution — PASS / REUSABLE

Current SQLite schema version is 7 with:

- contiguous migration history;
- fail-closed migration-name validation;
- append-only historical evidence;
- forward-only migration policy;
- immutable canonical identity/history protections.

M7 should add migration v8 only.

## 3. Gap matrix

| Architecture requirement | Current repository | Status before M7 | M7 remediation |
|---|---|---|---|
| Temporal Team State snapshots | No Team State contract/package/persistence | MISSING | Add F-6 contract, estimator, snapshot persistence |
| Intrinsic team vs game context separation | Architectural docs only | MISSING IN CODE | Enforce intrinsic input-kind boundary |
| Team quality vs style separation | Architectural docs only | MISSING IN CODE | Separate typed state dimensions |
| Feature-specific temporal evolution | PIT supports time, no state estimator | MISSING | Versioned per-signal update/decay config |
| Early-season priors | No state prior contract | MISSING | Prior input contract + uncertainty |
| Player State snapshots | Player identity exists only | MISSING | Add F-7 snapshot/estimator |
| Position-specific player families | No canonical state position vocabulary | MISSING | Add canonical state position enum/contracts |
| Talent/form/role/health/workload separation | No player state | MISSING | Separate typed dimensions |
| Probabilistic availability | PIT `INJURY` input kind exists, no estimator | MISSING | Add F-10 distribution contracts/estimator |
| Availability vs effectiveness separation | Docs only | MISSING | Separate persisted distributions |
| Injury observations | `InjuryObservationId` exists, no domain observation/persistence | PARTIAL PRECURSOR | Add canonical observation + repository |
| Injury episodes | None | MISSING | Add episode identity/revision model |
| Concurrent injury episodes | None | MISSING | Support many episodes per player |
| Replacement chains | None | MISSING | Dependency graph and unit recomputation |
| Unit State | None | MISSING | Add F-8 contracts/estimator |
| Unit configuration identity | None | MISSING | Add `UnitConfigurationId` and members |
| Configuration mixtures | None | MISSING | Normalized probability mixture contract |
| Continuity/synergy state | None | MISSING | Add typed unit dimensions/coverage |
| Player -> unit -> team lineage | No state graph | MISSING | Add state dependency ledger |
| Double-counting guard | None | MISSING | Default hierarchy enforcement |
| Coaching Role identity | `CoachingRole` exists | PARTIAL PRECURSOR | Reuse role identity |
| Coaching regime | None | MISSING | Add `CoachingRegimeId` + temporal configuration |
| Play-caller identity | Can be represented only as generic role today | PARTIAL | Explicit regime/play-caller references |
| Empirical scheme state | None | MISSING | Add F-9 state payload/estimator |
| Public label vs empirical scheme separation | None | MISSING | Separate observation metadata/state output |
| Game-state-conditioned coaching tendencies | None | MISSING | Conditional V1 tendency estimator |
| State snapshot immutable identity | PIT snapshots only | REUSABLE PATTERN, MISSING FOR STATE | Add state content hash/seal |
| Exact observation inputs | PIT snapshots only | REUSABLE PATTERN | Add state input ledger |
| State-to-state dependencies | None | MISSING | Add dependency edges/DAG validation |
| State coverage/missingness | PIT feature coverage only | REUSABLE PATTERN | Add state coverage contract |
| State uncertainty | No common state uncertainty contract | MISSING | Add validated uncertainty/distributions |
| Continuous rebuild semantics | Architecture docs only; M16 later | PARTIAL | M7 defines deterministic downstream dependency inspection only |

## 4. Key architectural conclusion

M7 should **not** be implemented as five unrelated rolling-stat modules.

The central production architecture is the immutable state-snapshot system plus an explicit dependency DAG. Team, player, unit, coaching, and injury state then become typed state families that share:

- deterministic identity;
- exact PIT-safe inputs;
- uncertainty;
- coverage;
- model/calculation version;
- dependency lineage;
- immutable persistence;
- idempotent replay.

Without this shared substrate, later M9 features, M11 models, M16 continuous recomputation, and the long-term world-model direction would need a structural rewrite.

## 5. M7 build order

The implementation order should be dependency-driven:

```text
M7-A  Common state contracts / IDs / uncertainty
M7-B  Migration v8 + state snapshot/input/dependency ledger
M7-C  Injury observation / episode / availability state
M7-D  Player State V1
M7-E  Unit State V1 + configuration mixtures
M7-F  Coaching regime / Scheme State V1
M7-G  Team State V1
M7-H  Dependency propagation / rebuild inspection
M7-I  PIT multi-snapshot validation
M7-J  Historical/real-data validation + certification
```

This sequence builds the shared invariants once and then layers state families in the architectural dependency order.

## 6. What M7 will not fake to satisfy validation

M7 must not:

- fabricate production historical PlayerIds for the M6C corpus;
- treat provider injury labels as canonical health truth;
- invent a medical diagnosis;
- treat active as fully healthy;
- infer unknown unit members as known starters;
- force a complete coaching/scheme history where source evidence is absent;
- use market/weather observations as intrinsic team evidence;
- claim rich position-specific estimates for eras/data where the evidence contract does not support them;
- hide missingness behind default zero values.

## 7. Pre-implementation decision

```text
Current certified base: SUFFICIENT TO BEGIN M7
Existing M7 implementation: NOT PRESENT
Architecture remediation required: YES
Schema migration required: YES — v8
M6/M6C reopening required: NO
Codex required at start: NO
```

The default executor remains Lane A. User-local execution will be used for exact-head tests, migrations, and real/historical validation. Codex should be reserved only if the implementation later becomes genuinely execution-heavy after the contracts are frozen.
