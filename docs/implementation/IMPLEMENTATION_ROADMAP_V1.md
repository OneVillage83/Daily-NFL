# Daily NFL Implementation Roadmap V1

Status: Governing implementation plan derived from F-0 through F-24.

This roadmap converts the architecture into an implementation sequence while minimizing unnecessary Codex usage.

## Execution lanes

Every task belongs to one of three lanes.

### Lane A — ChatGPT thread direct

Default lane. Use when the active thread can safely create or edit repository files directly.

Typical work:

- architecture and implementation documentation
- Python modules with well-defined contracts
- domain dataclasses / enums / protocols
- SQL schemas and migrations
- deterministic pure functions
- provider interfaces
- feature definitions
- label definitions
- tests that can be specified from architecture
- GitHub file and documentation changes
- review and interpretation of command output

### Lane B — User-local command

Use when the missing capability is primarily local execution or inspection rather than implementation reasoning.

Typical work:

- create/activate a virtual environment
- install dependencies
- run pytest / Ruff / mypy
- run migration scripts against a local database
- inspect a local SQLite database
- execute nflreadpy against real datasets
- benchmark memory/runtime
- inspect local artifacts too large to move through GitHub
- run one-off validation scripts

The thread should provide an exact command and interpret the returned output.

### Lane C — Codex escalation

Use only when the work is genuinely execution-heavy, iterative, or broad enough that the thread/user-command workflow becomes inefficient.

Typical qualifying work:

- large multi-file refactors
- lengthy implementation loops requiring repeated local test/fix cycles
- broad provider ingestion implementations spanning many modules
- complex migration/refactor sequences over an existing live codebase
- large model-training pipeline implementations
- performance work requiring profiling and repeated code changes

Codex tasks must be narrowly scoped and explicitly authorized.

---

# Implementation strategy

The implementation follows dependency order, not F-number order mechanically.

The first production milestone is **not** the world model. It is a reproducible historical/pregame football data and feature system capable of generating a strong baseline prediction under strict PIT semantics.

The roadmap therefore progresses through:

1. repository/runtime foundation
2. canonical football truth
3. provider acquisition and provenance
4. historical PIT reconstruction
5. state engines
6. feature/target contracts
7. baseline models
8. simulation and market pricing
9. evaluation / Recommendation Gate / settlement
10. advanced research

---

# M0 — Repository Bootstrap & Engineering Constitution

Architecture dependencies: F-0, F-2, F-3, F-4, F-19

## Deliverables

- Python 3.12 project baseline
- package layout
- `.gitignore`
- `.python-version`
- dependency input files
- pytest / Ruff / mypy configuration
- `AGENTS.md`
- implementation README
- version module
- basic test package
- CI-ready quality-gate commands

## Default executor

**Lane A — ChatGPT thread direct**

## Local validation

**Lane B — user command**

Expected command family:

```powershell
python -m pytest -q
python -m ruff check .
python -m mypy
```

## Codex

Not justified.

## Exit gate

- package imports cleanly
- quality commands are defined
- no NFL/provider logic yet

---

# M1 — Canonical Domain Contracts

Architecture dependencies: F-1, F-3, F-5

## Deliverables

Core Daily-NFL domain types for:

- season / phase / week
- game identity
- team-season identity
- player identity
- drive identity
- play identity
- possession
- period
- pre-play state
- `PLAY_EXECUTION`
- play-design modifiers including football `PLAY_ACTION`
- play events
- play result
- participation
- penalty
- game result
- ruleset version

The provider-neutral schema must represent football rather than nflverse columns.

## Default executor

**Lane A**

## Local validation

**Lane B** — run unit tests and type checking.

## Codex

Not justified unless the domain model later requires a broad refactor after significant code exists.

## Exit gate

- canonical objects compile/import
- enum semantics are tested
- pre-play state cannot contain outcome fields by construction
- `PLAY_EXECUTION` naming is enforced

---

# M2 — Persistence & Migration Foundation

Architecture dependencies: F-2, F-3, F-4, F-5

## Deliverables

Initial SQLite schema and migrations for:

- schema version
- providers
- raw evidence metadata
- entity/provider external-ID crosswalk
- games
- schedule observations
- drives
- plays
- play observations/revisions
- participation observations
- penalty observations
- result truth
- provenance clocks (`effective_at`, `published_at`, `observed_at`, `ingested_at`, defensible `available_at`)

## Design constraints

- append-only observations where history matters
- no silent provider overwrite
- external IDs never become permanent canonical IDs
- corrections remain traceable
- migration versions explicit

## Default executor

**Lane A** for schema/migration code.

## Local validation

**Lane B** to initialize/migrate a real local SQLite DB and return schema/check output.

## Codex

Only if a future existing/live schema makes migration work large and iterative.

## Exit gate

- clean DB initializes from zero
- migration version is queryable
- provenance fields exist
- repeated/revised observations are representable

---

# M3 — Raw Evidence & Provider Abstraction

Architecture dependencies: F-2

## Deliverables

- provider protocol/interfaces
- provider capability registry
- immutable raw evidence store contract
- SHA-256 checksum generation
- normalized acquisition result envelope
- parser/provider schema version fields
- licensing metadata fields
- provider observation timestamps

## Initial provider

`nflverse` / `nflreadpy` becomes the first NFL foundational provider behind an adapter.

The NFL domain must never directly import provider-specific loaders outside the provider adapter layer.

## Default executor

**Lane A** for protocols, raw-store machinery, and adapter contracts.

## Local validation

**Lane B** for commands that actually invoke `nflreadpy`, inspect returned schemas, and test small historical windows.

## Codex

Possible **only** for a large ingestion implementation spanning many nflverse datasets after the adapter contract is locked.

## Exit gate

- one tiny dataset can be acquired through the provider abstraction
- raw evidence is checksummed and immutable
- normalized records retain provenance

---

# M4 — Identity & Reconciliation Engine

Architecture dependencies: F-3

## Deliverables

- canonical ID generation
- provider crosswalk persistence
- GSIS external-ID mapping support
- team/franchise reconciliation rules
- game reconciliation rules
- player reconciliation rules
- unresolved-identity representation
- match confidence / method
- no silent fuzzy matching

## Default executor

**Lane A**

## Local validation

**Lane B** using small provider samples.

## Codex

Only if a large historical reconciliation/backfill tool becomes execution-heavy.

## Exit gate

- ambiguous matches remain unresolved
- provider IDs can change without changing canonical identity
- reconciliation decisions are auditable

---

# M5 — Historical PIT Engine

Architecture dependencies: F-4

## Deliverables

- defensible `available_at` derivation
- availability method/confidence
- bitemporal/as-of query helpers
- prediction-time information boundary
- immutable feature input snapshots
- PIT leakage validators
- standard research horizons (`T-168h`, `T-72h`, `T-24h`, `T-6h`, `T-90m`, `T-15m/final` as configured)
- explicit rule: game-day information is valid if available before the prediction cutoff/kickoff

## Required leakage checks

At minimum:

- no source after prediction timestamp
- no current-game final score/stats/EPA
- no post-cutoff injury/depth information
- no post-cutoff weather forecast
- no actual weather substituted for prior forecast
- no later market quote / closing line in earlier feature set
- no future opponent/game information
- no end-of-season statistics used midseason
- no historical provider correction without defensible availability

## Default executor

**Lane A** for engine and tests.

## Local validation

**Lane B** against tiny historical fixtures and later real data.

## Codex

Possible only if reconstruction/backfill tooling becomes large and iterative.

## Exit gate

- a historical game can be reconstructed as-of a specified prediction timestamp
- intentionally leaked fixtures fail closed

---

# M6 — Canonical Play/Drive Normalization

Architecture dependencies: F-5

## Deliverables

Normalize provider PBP into:

- `PLAY_STATE_BEFORE`
- `PLAY_EXECUTION`
- modifiers (`PLAY_ACTION`, RPO, screen, etc.)
- play events
- participation
- penalties
- physical outcome where supportable
- official result
- `PLAY_STATE_AFTER`
- drives/possession transitions

## Default executor

**Lane A** for normalization framework and small mappings.

## User-local

**Lane B** for schema inspection and fixture extraction.

## Codex

Likely justified later for a broad production-grade nflverse PBP normalization implementation after contracts and representative fixtures are locked.

## Exit gate

- representative plays normalize deterministically
- penalties/revisions do not corrupt pre-play state
- provider rows are not exposed directly to downstream features

---

# M7 — State Engine V1

Architecture dependencies: F-6, F-7, F-8, F-9, F-10

## Deliverables

Initial state engines for:

- team
- QB/player
- unit
- coaching/scheme
- injury/availability

V1 should favor reproducible statistical state over premature complexity.

## State outputs

Immutable snapshots with:

- `as_of`
- model/calculation version
- input observation IDs
- uncertainty
- feature/data coverage

## Default executor

**Lane A** for state interfaces and initial simple estimators.

## Local validation

**Lane B** for historical runs.

## Codex

Only for lengthy implementations once the V1 state contracts are frozen.

## Exit gate

- state snapshots can be reproduced from PIT inputs
- player → unit → team dependency is explicit
- availability uncertainty propagates rather than becoming a binary injury count

---

# M8 — Environment & Recovery Integration

Architecture dependencies: F-11, F-12

## Boundary

Sport-agnostic acquisition/storage for odds, weather, venue, and travel should live in **Daily-Data-Core**.

Daily-NFL consumes contracts and derives NFL-specific matchup features.

## Deliverables in Daily-NFL

- environment input contract
- roof/play-environment handling
- NFL field-relative wind derivation hooks
- recovery context input contract
- exact rest-hour features
- NFL-specific player/unit recovery transforms

## Default executor

**Lane A**

## User-local

**Lane B** for integration checks when Data Core is implemented.

## Codex

Not initially justified.

## Exit gate

- Daily-NFL does not duplicate Data Core acquisition
- weather remains forecast-snapshot/PIT-safe
- rest/travel exposure is represented without hard-coded betting folklore

---

# M9 — Feature Registry & Feature Contracts

Architecture dependencies: F-13

## Deliverables

Machine-readable feature definitions covering the F-13 families.

Each feature stores:

- semantic definition
- entity scope
- unit/type
- source dependencies
- calculation method
- lookback
- PIT availability rule
- feature-era support
- missingness semantics
- uncertainty semantics
- version
- market-information allowance

## Initial contracts

- `NFL_BASELINE_V1`
- `NFL_ROSTER_ADVANCED_V1`
- later `NFL_SNAP_ADVANCED_V1`
- later `NFL_MODERN_V1`

Football-only and market-aware contracts remain explicit.

## Default executor

**Lane A**

## Codex

Not justified for contract definition.

## Exit gate

- every production feature is registered
- no ambiguous `rolling_*` feature without exact semantics
- market lineage cannot enter football-only features recursively

---

# M10 — Targets, Labels & Prediction Envelope

Architecture dependencies: F-14

## Deliverables

- target registry
- label registry/versioning
- game outcome truth
- margin / total / score labels
- 3-way game result labels
- market-settlement labels separate from football truth
- prediction envelope
- horizon metadata
- immutable prediction snapshots

## Default executor

**Lane A**

## Local validation

**Lane B** for historical label-generation checks.

## Exit gate

- one game truth can generate many line/quote settlements without changing football truth
- corrected labels are versioned
- predictions are never overwritten by later reruns

---

# M11 — Baseline Modeling Stack

Architecture dependencies: F-15

## Build order

1. B0 league/home baseline
2. B1 dynamic team-strength model
3. B1-QB adjusted variant
4. B2 regularized statistical models
5. B3 gradient-boosted tabular benchmark
6. B4 coherent probabilistic distribution baseline
7. market-only external benchmark

## Default executor

**Lane A** for baseline definitions, dataset contracts, scoring code, and simple implementations.

## User-local

**Lane B** for training/evaluation commands and model artifacts.

## Codex

May become appropriate for the full training/orchestration pipeline once several models and artifacts must be coordinated.

## Exit gate

- walk-forward baseline metrics exist
- football-only and market-only baselines are compared separately
- predictive distributions are scored, not only point estimates

---

# M12 — Simulation V1

Architecture dependencies: F-17

## Initial scope

Start with S0 statistical distribution simulation.

Then promote only when justified:

- S1 score-level
- S2 drive-level
- S3 play-level

## Deliverables

- seeded Monte Carlo engine
- configurable precision target
- joint margin/total or score sampling
- win/tie/loss probabilities
- spread/total probability surfaces
- push probabilities
- simulation artifact/version metadata

## Default executor

**Lane A** for S0/S1.

## User-local

**Lane B** for performance/precision benchmarks.

## Codex

Likely justified for large S2/S3 implementations after contracts are stable.

## Exit gate

- deterministic seeded reproduction
- Monte Carlo error reported
- distribution calibration evaluated

---

# M13 — Market & Fair-Price Integration

Architecture dependencies: F-18

## Boundary

Raw sportsbook collection belongs in Daily-Data-Core.

Daily-NFL consumes market snapshots for pricing/evaluation.

## Deliverables

- model fair probability
- market raw implied probability
- versioned no-vig fair probability input
- probability edge
- wager EV
- fair odds formatting
- line-shopping evaluation across books
- market-only benchmark
- market-aware model contract

## Default executor

**Lane A**

## Exit gate

- football-only prediction can be priced against multiple immutable book quotes
- probability edge and EV are never conflated
- current/closing market leakage rules enforced

---

# M14 — Evaluation & Calibration Constitution in Code

Architecture dependencies: F-19

## Deliverables

- chronological split utilities
- walk-forward evaluator
- log loss
- Brier
- CRPS / distribution metrics
- MAE/RMSE diagnostics
- calibration curves/buckets
- subgroup evaluation
- CLV metrics
- champion/challenger registry
- shadow prediction support
- experiment registry
- promotion gate

## Default executor

**Lane A** for metric/evaluation library.

## User-local

**Lane B** for full historical evaluation runs.

## Codex

Potentially justified for large experiment orchestration and reporting systems.

## Exit gate

- no random split is the final validation path
- every champion promotion is reproducible
- shadow predictions can be settled prospectively

---

# M15 — Recommendation Gate & Settlement

Architecture dependencies: F-20, F-21

## Deliverables

- deterministic Gate V1
- `BET / LEAN / PASS / AVOID`
- reason codes
- edge stability
- model disagreement inputs
- market staleness/data-quality checks
- recommendation lifecycle
- football result ledger
- market settlement ledger
- performance ledger
- PASS/AVOID settlement/evaluation

## Default executor

**Lane A**

## Exit gate

- Gate can never suppress creation/storage of a prediction
- every eligible prediction remains learnable
- later quotes supersede rather than rewrite earlier recommendations

---

# M16 — Continuous Pregame Orchestration

Architecture dependencies: F-4, F-10, F-11, F-20, F-21

## Deliverables

Dependency-aware event routing:

```text
injury -> player -> unit -> team -> matchup -> prediction -> value/gate
weather -------------------------> matchup -> prediction -> value/gate
odds -----------------------------------------------------> value/gate
```

The pipeline should recompute only affected downstream artifacts.

## Default executor

Architecture/orchestrator contract: **Lane A**.

Full production implementation may qualify for **Lane C** if it becomes a large multi-module execution loop.

## Exit gate

- late pregame data can trigger new snapshots through kickoff
- earlier snapshots remain immutable
- odds-only changes do not rebuild unrelated football states

---

# M17 — NFL-Specific Enrichment

Architecture dependencies: F-22

Candidates:

- richer roster/list semantics
- practice-squad elevations
- transaction stream
- draft/offseason priors
- advanced special teams
- fourth-down policy
- clock management
- rule-change modules
- international game context
- Next Gen / tracking feature eras

## Executor

Default **Lane A/B** by feature.

Use **Lane C** only for large enrichment ingestion pipelines.

---

# M18 — Daily NCAAF Second Implementation

Architecture dependencies: F-23

Do not begin shared-football code extraction first.

Build Daily-NCAAF against the same conceptual contracts, then compare actual implementations.

Only proven-common behavior should move into a shared football package.

## Executor

Separate project plan after NFL baseline foundation is functioning.

---

# M19 — Advanced Models & Football World Model Research

Architecture dependencies: F-16, F-24

Research progression:

- hierarchical/state-space models
- advanced GBDT
- multi-task distributions
- player/unit interaction models
- graph models
- sequence models
- mixtures of experts
- ensembles
- WM-0 through WM-7 world-model curriculum

Every challenger must pass F-19.

## Executor

Contract/research design: **Lane A**.

Training-heavy/repo-wide implementations are the clearest **Lane C / Codex** candidates.

---

# Immediate build order

The recommended near-term sequence is:

```text
M0  Repository Bootstrap
M1  Canonical Domain Contracts
M2  Persistence / Migrations
M3  Raw Evidence / Provider Abstraction
M4  Identity / Reconciliation
M5  PIT Engine
M6  Play / Drive Normalization
M7  State Engine V1
M9  Feature Registry
M10 Targets / Labels
M11 Baseline Models
```

M8 environment/recovery integration can proceed in parallel once Daily-Data-Core exposes the required contracts.

---

# Codex escalation checklist

Before Codex receives a task, all answers below should be yes:

1. Is the task too lengthy/iterative to perform efficiently from the thread?
2. Is local execution/refactoring genuinely required rather than merely convenient?
3. Has the governing architecture already resolved the design decisions?
4. Is the task scope narrow and explicit?
5. Are allowed files/modules identified?
6. Are validation commands specified?
7. Is the definition of done objective?

If not, keep the task in Lane A or Lane B.

---

# Current next action

Begin **M0 — Repository Bootstrap & Engineering Constitution**, then proceed directly into **M1 — Canonical Domain Contracts**.
