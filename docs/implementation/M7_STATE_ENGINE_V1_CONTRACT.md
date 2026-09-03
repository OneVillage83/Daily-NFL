# M7 State Engine V1 Implementation Contract

**Project:** The Daily Line — Daily NFL
**Milestone:** M7 — State Engine V1
**Branch:** `checkpoint/m7-state-engine-v1`
**Certified dependency base:** M0-M6 + M6C
**Base main SHA:** `0dd515ec36f370ce70f67b3e771e1ceb4e36a149`
**Architecture dependencies:** F-6, F-7, F-8, F-9, F-10
**Status:** LOCKED PRE-IMPLEMENTATION CONTRACT

## 1. Purpose

M7 converts historical football evidence and point-in-time context into immutable, reproducible estimates of current football state.

The governing distinction is:

> **F-5 records what happened. F-6 through F-10 estimate what that evidence means now.**

M7 must build the production-planned V1 architecture in one pass. The estimators may remain deliberately simple and reproducible at first, but the domain, persistence, lineage, uncertainty, dependency, and snapshot contracts must not be an MVP that requires structural replacement later.

## 2. Governing architecture rules

M7 inherits the following locked rules.

1. Every state is temporal and evaluated at an explicit `as_of` timestamp.
2. Pregame state obeys `available_at <= prediction_time < kickoff`.
3. Later legitimate information creates a new immutable snapshot; it never mutates an earlier snapshot.
4. Provider observations populate state inputs but do not define the canonical state schema.
5. Intrinsic team state is separate from game-specific context.
6. Quality/effectiveness is separate from style/tendency.
7. Player talent, current form, health, role, workload, availability, and effectiveness are separate concepts.
8. Availability and conditional effectiveness are distinct distributions.
9. Unit composition is dynamic and may itself be a probability distribution before late availability resolves.
10. Player -> unit -> team dependency is explicit so downstream models cannot silently double count the same evidence.
11. Coaching identity, coaching regime, play-caller identity, empirical scheme, public scheme labels, and coaching effectiveness are distinct.
12. Coaching tendencies are conditioned on football game state rather than raw unconditional rates.
13. Injury observations are evidence about latent health state, not the health state itself.
14. No medical diagnosis may be invented from vague source language.
15. No post-cutoff injury/reporting correction may leak backward into an earlier state snapshot.
16. F-11 weather and market information are not intrinsic team state and are outside M7 state-estimation inputs except where a later matchup layer explicitly consumes them.

## 3. M7 state hierarchy

The V1 dependency graph is:

```text
PIT-SAFE OBSERVATIONS / PRIORS
            |
            +--> INJURY / AVAILABILITY STATE
            |             |
            |             v
            +--------> PLAYER STATE
                          |
                          v
                    UNIT STATE
                          |
             +------------+------------+
             |                         |
             v                         v
        TEAM STATE              COACHING STATE
             |                         |
             +------------+------------+
                          |
                          v
                    MATCHUP INPUTS
```

`MATCHUP STATE` itself remains a later integration layer. M7 produces the immutable state inputs that the matchup/model stack will consume.

## 4. Production package layout

M7 will add a dedicated provider-neutral state package rather than scattering state logic through PIT/provider modules.

Planned structure:

```text
daily_nfl/state/
    __init__.py
    contracts.py
    uncertainty.py
    injury.py
    player.py
    unit.py
    coaching.py
    team.py
    snapshot.py
    repository.py
    dependency.py
```

The exact split may consolidate files where that improves cohesion, but provider-specific loaders must not enter this package.

## 5. Canonical identifiers

M7 requires opaque canonical identifiers for state objects and temporal configurations.

At minimum:

```text
TeamStateId
PlayerStateId
UnitStateId
CoachingStateId
InjuryEpisodeId
InjuryAvailabilitySnapshotId
UnitConfigurationId
CoachingRegimeId
```

Existing canonical IDs such as `PlayerId`, `TeamSeasonId`, `PersonId`, `CoachRoleId`, `InjuryObservationId`, `DepthChartSnapshotId`, and `GameId` remain authoritative.

State IDs must never be provider IDs.

## 6. Common immutable state-snapshot envelope

All M7 state families share a common semantic envelope.

```text
STATE SNAPSHOT

snapshot_id
state_type
subject_id
team_season_id_if_applicable
game_id_if_context_specific
as_of

calculation_contract
model_version

state_payload
uncertainty
coverage

input_observation_ids
input_state_snapshot_ids

payload_sha256
pit_validation
created_at
```

Requirements:

- timezone-aware `as_of`;
- deterministic canonical serialization;
- deterministic content hash;
- immutable storage;
- exact input membership;
- explicit model/calculation version;
- explicit feature/data coverage and missingness;
- explicit uncertainty;
- PIT validation before persistence for pregame state;
- idempotent replay when all inputs and calculations are identical;
- fail closed when a stored snapshot with the same deterministic identity disagrees with its expected payload or dependencies.

## 7. Snapshot persistence architecture

M7 will introduce forward-only SQLite migration **v8**. Migrations 1-7 are immutable history and must not be rewritten.

### 7.1 Base snapshot ledger

A shared `state_snapshots` ledger will provide globally auditable snapshot identity and metadata.

Required logical columns:

```text
snapshot_id PRIMARY KEY
state_type
subject_type
subject_id
team_season_id NULLABLE
game_id NULLABLE
as_of
calculation_contract
model_version
state_payload_json
uncertainty_json
coverage_json
payload_sha256
pit_validation
created_at
```

### 7.2 Exact snapshot inputs

`state_snapshot_inputs` records each source observation used to create the snapshot.

Each input retains at minimum:

```text
snapshot_id
input_kind
input_id
source_table
available_at
availability_method
availability_confidence
provider/evidence identity when present
payload/raw SHA when present
```

This should reuse M5 `PITInputRef` semantics wherever possible rather than creating a second incompatible provenance vocabulary.

### 7.3 State-to-state dependencies

`state_snapshot_dependencies` explicitly records derived-state lineage such as:

```text
injury -> player
player -> unit
unit -> team
coaching -> team
```

The dependency graph must reject:

- self-dependencies;
- duplicate dependency edges;
- cycles when a complete dependency chain is persisted;
- child snapshots whose parent `as_of` is later than the child `as_of`;
- dependency use that violates the relevant prediction cutoff.

### 7.4 Atomic seal

A state snapshot is not valid merely because a row exists.

Persistence will atomically record:

1. base snapshot;
2. exact observation inputs;
3. exact parent-state dependencies;
4. typed state details where applicable;
5. seal/finalization marker.

An unsealed/incomplete state snapshot is not consumable.

### 7.5 Immutability

State snapshot rows, input membership, dependencies, and seals are append-only. New information creates a new snapshot ID.

## 8. Uncertainty and distributions

M7 must not reduce uncertainty to free text.

V1 will provide small reusable probability/distribution contracts sufficient for:

```text
probability in [0, 1]
expected value
variance / standard deviation when supportable
bounded interval when supportable
categorical configuration mixture
missing / unknown state
```

The contracts must validate finite numeric values and normalized probability mass.

Uncertainty structures are calculation outputs, not provider truth.

## 9. F-10 Injury & Availability State

### 9.1 Canonical injury observation

M7 will add a provider-neutral injury observation contract preserving:

```text
injury_observation_id
player_id
team_season_id
provider/source identity
reported_body_region
reported_injury_description
practice_status
game_status
source_text/confidence when present
raw evidence/provenance clocks
```

Practice and game status remain separate enums.

### 9.2 Injury episode

An `InjuryEpisodeId` groups observations believed to refer to the same underlying problem without inventing unsupported diagnoses.

The architecture must support:

- multiple concurrent episodes;
- body region;
- laterality when known;
- injury family when known;
- recurrence/related prior episode reference;
- explicit unknowns;
- versioned/revisable interpretation rather than silent mutation when later evidence clarifies the episode.

### 9.3 Injury availability snapshot

The persisted snapshot supports distinct quantities:

```text
P(active)
participation_distribution | active
effectiveness_distribution | participates, active
early_exit_uncertainty
health_uncertainty
```

Confirmed inactive can collapse `P(active)` to 0. Confirmed active may collapse participation availability toward known active status but must not imply full effectiveness.

### 9.4 V1 estimator policy

V1 may use a deterministic versioned baseline configuration for unresolved statuses, but probabilities are model configuration rather than football truth. They must be:

- explicit;
- versioned;
- replaceable;
- testable;
- recalibratable later.

No hidden constants embedded throughout business logic.

## 10. F-7 Player State

### 10.1 Generic player state

The V1 contract contains separate nested dimensions for:

```text
talent_state
form_state
role_state
health_state
workload_state
availability_state
uncertainty
```

A player state belongs to a canonical `PlayerId`, `TeamSeasonId`, and `as_of` timestamp.

Game-conditioned availability may reference a specific `GameId`; persistent talent must not become opponent-specific.

### 10.2 Position family

M7 must not force every position into one universal scalar rating.

The architecture will represent position family explicitly and permit position-specific state payloads for:

```text
QB
RB
WR
TE
OT
OG
C
EDGE
DT
LB
CB
S
K
P
RETURNER
OTHER
```

V1 only needs rich estimator logic for the data-supported families initially, but the contract must support the full locked family structure.

### 10.3 Temporal estimation

V1 estimators use versioned per-signal temporal parameters rather than one hard-coded `last N games` window.

The estimator interface must support:

- priors;
- observations with event/effective timestamps;
- observation availability timestamps;
- feature-specific decay/weight configuration;
- posterior/state estimate;
- uncertainty;
- coverage.

### 10.4 Rookies / low sample

The contract supports high-uncertainty priors and external prior inputs without pretending that low-sample NFL evidence has the same confidence as established-player evidence.

### 10.5 Team changes

Player talent and team-conditioned role/context remain separable so a team change can partially reinitialize role/context without discarding persistent talent information.

## 11. F-8 Unit State

### 11.1 Unit types

The V1 canonical `UnitType` vocabulary covers at least:

```text
QUARTERBACK_ROOM
OFFENSIVE_LINE
RECEIVING_CORPS
BACKFIELD
PASS_PROTECTION
RUN_BLOCKING
DEFENSIVE_FRONT
PASS_RUSH
RUN_DEFENSE_FRONT
LINEBACKER
COVERAGE
SECONDARY
FIELD_GOAL
PUNT
PUNT_COVERAGE
KICKOFF
KICK_COVERAGE
PUNT_RETURN
KICK_RETURN
```

Functional units may overlap.

### 11.2 Unit configuration

A `UNIT_CONFIGURATION` identifies a concrete combination of canonical players and functional roles. It is distinct from a timeless team/unit label.

### 11.3 Configuration distribution

Before availability resolves, unit state may be a normalized mixture over plausible configurations.

The persisted unit snapshot retains:

```text
member/configuration distribution
expected participation
intrinsic quality
continuity
synergy/interaction
health
scheme reference
uncertainty
input player-state IDs
```

### 11.4 No double counting

The default team-state build consumes unit-state outputs rather than re-adding the exact same player contributions independently.

Any specialized estimator that consumes multiple hierarchy levels must declare how overlapping evidence is residualized or otherwise prevented from double counting.

## 12. F-9 Coaching & Scheme State

### 12.1 Coaching regime

A `COACHING_REGIME` is a temporal configuration of staff and decision-making responsibility.

The regime can change when:

- head coach changes;
- coordinator changes;
- offensive play caller changes;
- defensive play caller changes;
- materially relevant responsibility changes midseason.

### 12.2 Coaching snapshot

The V1 snapshot retains:

```text
regime_id
head_coach_id
offensive_play_caller_id
defensive_play_caller_id
offensive_scheme_state
defensive_scheme_state
special_teams_state
decision_policy_state
adaptation_state
uncertainty
```

### 12.3 Scheme labels vs empirical state

Public descriptive labels are evidence/metadata only. Empirical scheme state is derived from observed behavior.

### 12.4 Game-state conditioning

V1 tendency estimation must support context buckets or an equivalent conditional representation so trailing/leading garbage-time behavior is not treated as neutral policy.

At minimum the contract supports conditioning by:

```text
down
distance band
score-state band
time/period band
field-position band
```

The exact V1 estimator can be simple/shrunk; the state representation cannot be unconditional-only.

## 13. F-6 Team State

### 13.1 Intrinsic team state

The persisted team snapshot separates:

```text
offensive quality
defensive quality
special-teams quality
style/tendency
roster availability summary
coaching-state reference
form
uncertainty
```

Game-specific weather/market state is excluded from intrinsic team state.

### 13.2 Temporal dimensions

The team estimator supports different update rates by dimension; it must not impose one universal rolling window.

### 13.3 Early-season priors

The contract supports prior-season and offseason priors with explicit uncertainty and decaying prior weight as current-season evidence accumulates.

### 13.4 Inputs

Default dependency path:

```text
player states -> unit states -> team state
coaching state -----------------> team state
```

Team state may also consume direct historical team-performance evidence where it represents residual/team-level information not already fully encoded by lower levels. Those dependencies must be explicit.

## 14. Rebuild / trigger semantics

M7 does not implement the full production event router; that is M16. M7 does define deterministic dependency semantics so later orchestration can know what must be rebuilt.

Examples:

```text
injury observation change
    -> injury availability
    -> player
    -> affected units
    -> team

coaching/play-caller change
    -> coaching state
    -> team

player role/depth change
    -> player
    -> units
    -> team
```

M7 will provide dependency inspection utilities sufficient to identify downstream invalidation/rebuild targets without adding a live queueing system.

## 15. Estimator V1 philosophy

The roadmap explicitly requires reproducible statistical state over premature complexity.

Therefore M7 V1 will prefer:

- deterministic Bayesian/shrinkage or exponentially weighted state updates;
- versioned configuration;
- transparent probability mixtures;
- explicit uncertainty;
- explicit missingness and coverage;
- deterministic hashing and exact replay;

instead of prematurely introducing deep sequence models, learned embeddings, or a world model.

The architecture must allow those later models to replace the estimator implementation without replacing the snapshot/persistence contracts.

## 16. Required failure-state tests

At minimum M7 certification requires tests proving:

1. naive datetimes are rejected;
2. nonfinite values/probabilities are rejected;
3. probability mixtures must normalize;
4. post-cutoff observation input is rejected;
5. parent state later than child `as_of` is rejected;
6. dependency cycles are rejected;
7. snapshot content identity is deterministic;
8. replay with identical payload/inputs/dependencies is idempotent;
9. replay with conflicting payload for the same identity fails closed;
10. persisted snapshots/inputs/dependencies are immutable;
11. confirmed inactive collapses availability to zero without mutating earlier snapshot;
12. confirmed active does not force effectiveness to 100%;
13. injury replacement propagates through player -> unit -> team dependencies;
14. unit configuration probabilities update when availability resolves;
15. team intrinsic state rejects market/weather input kinds;
16. style and quality remain separate fields;
17. coaching play-caller changes create a new regime/snapshot rather than rewriting the old one;
18. coaching tendency estimation is game-state conditioned;
19. double-counting guard rejects undeclared overlapping lower-level evidence in the default team build;
20. state snapshot input membership is exact and reproducible.

## 17. Required validation gates

### Gate 0 — architecture / static baseline

Before implementation changes:

- exact main/base SHA recorded;
- current code conformance matrix recorded;
- existing full pytest/Ruff/mypy baseline recorded locally;
- branch clean.

### Gate A — contracts + migration

- new domain/state contracts import;
- migration v8 applies from fresh DB and from certified v7 DB;
- migration ledger remains contiguous and name-validated;
- state snapshot immutability/sealing tests pass;
- no migrations 1-7 rewritten.

### Gate B — deterministic state estimators

- injury/availability estimator;
- player estimator;
- unit mixture estimator;
- coaching conditional-tendency estimator;
- team estimator;
- deterministic replay and uncertainty/coverage tests.

### Gate C — dependency propagation / PIT

Use a deterministic pregame fixture with at least two prediction timestamps.

Example:

```text
T-24h: starter questionable
T-90m: starter inactive
```

Prove:

- T-24h snapshot remains unchanged;
- new T-90m injury snapshot is created;
- player state changes;
- unit configuration mixture changes;
- team state changes;
- all dependencies are explicit;
- no post-cutoff source enters the earlier state.

### Gate D — historical/real-data compatibility

Run at least one small historical state-estimation validation against repository-supported real football evidence. The run must be reproducible and must not fabricate production player identity merely to make the gate green.

## 18. M7 exit gate

M7 is eligible for `ARCHITECTURE-CERTIFIED` only when:

```text
F-6 Team State contract: PASS
F-7 Player State contract: PASS
F-8 Unit State contract: PASS
F-9 Coaching/Scheme contract: PASS
F-10 Injury/Availability contract: PASS

state snapshots immutable: PASS
snapshot inputs exact: PASS
state dependencies explicit: PASS
PIT leakage tests: PASS
availability uncertainty propagation: PASS
player -> unit -> team propagation: PASS
coaching regime versioning: PASS
migration v8 fresh + v7 upgrade: PASS
historical/real-data validation: PASS
Ruff: PASS
strict mypy: PASS
full pytest: PASS
PR range/scope audit: PASS
clean exact-head tree: PASS
```

## 19. Explicit non-goals

M7 does not include:

- F-11 weather/stadium/surface integration;
- F-12 travel/rest/recovery integration;
- M9 production feature registry;
- M10 targets/labels;
- baseline predictive models;
- simulation;
- market pricing;
- Recommendation Gate;
- full M16 continuous event-routing infrastructure;
- deep sequence/world-model state estimators.

Those later milestones consume the M7 contracts.

## 20. Certification authority

The authoritative milestone status remains `docs/implementation/ARCHITECTURE_CERTIFICATION_LOG.md`.

While M7 is open, `docs/implementation/M7_PROGRESS_LOG.md` is the resume point for the active checkpoint. M7 remains uncertified until the formal conformance audit, local validation evidence, exact-head review, and controlled squash merge are complete.
