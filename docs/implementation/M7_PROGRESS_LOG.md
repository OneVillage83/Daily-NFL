# M7 State Engine V1 Progress Log

**Project:** The Daily Line — Daily NFL
**Milestone:** M7 — State Engine V1
**Branch:** `checkpoint/m7-state-engine-v1`
**Certified base:** `0dd515ec36f370ce70f67b3e771e1ceb4e36a149`
**Architecture:** F-6, F-7, F-8, F-9, F-10
**Status:** IN PROGRESS — M7-E CLOSED / M7-F STARTING

This file is the authoritative resume point while M7 is open. Final certification status remains governed by `ARCHITECTURE_CERTIFICATION_LOG.md`.

## 1. Governing documents

- `docs/architecture/F05-F09_FOOTBALL_STATE_ARCHITECTURE_V1.md`
- `docs/architecture/F10-F14_CONTEXT_FEATURE_TARGET_ARCHITECTURE_V1.md`
- `docs/implementation/IMPLEMENTATION_ROADMAP_V1.md`
- `docs/implementation/M7_STATE_ENGINE_V1_CONTRACT.md`
- `docs/implementation/M7_PREIMPLEMENTATION_CONFORMANCE_AUDIT.md`
- `docs/implementation/M7_GATE0_BASELINE_20260827.md`
- `docs/implementation/M7_A_COMMON_STATE_CONTRACTS_RESULT.md`
- `docs/implementation/M7_B_STATE_PERSISTENCE_RESULT.md`
- `docs/implementation/M7_C_INJURY_AVAILABILITY_RESULT.md`
- `docs/implementation/M7_D_PLAYER_STATE_RESULT.md`
- `docs/implementation/M7_E_UNIT_STATE_RESULT.md`

## 2. Locked scope

M7 owns:

```text
F-6  Team State
F-7  Player State
F-8  Unit State
F-9  Coaching & Scheme State
F-10 Injury & Availability State
```

M7 does not own F-11/F-12 environment/recovery integration, M9 feature registry, predictive models, simulation, market pricing, Recommendation Gate, or the full M16 event router.

## 3. Certified foundation

M7 begins from M6C-certified `main`:

```text
main SHA: 0dd515ec36f370ce70f67b3e771e1ceb4e36a149
M6C: ARCHITECTURE-CERTIFIED
historical PBP compatibility: 1999-2025, 27/27 PASS
schema before M7-B: 7
schema after M7-B: 8
schema after M7-C: 9
schema after M7-D: 10
schema after M7-E: 11
```

Reusable foundations:

- provider-neutral identity/domain contracts;
- immutable raw evidence/provenance;
- M4 reconciliation boundary;
- M5 PIT cutoff/input/snapshot machinery;
- M6 canonical play/participation/drive evidence;
- M6C full-history compatibility proof;
- M7-A state contracts/uncertainty substrate;
- M7-B immutable state persistence ledger;
- M7-C injury/availability state and PIT episode history;
- M7-D Player State with explicit F-10 parent lineage;
- M7-E Unit State with explicit sealed Player State lineage and residualized direct unit evidence.

## 4. Completed checkpoints

### M7-A — Common state substrate

Validated head:

```text
9de3b61b738f934061918342d22ee29923cdb43b
```

```text
focused pytest: 26 passed
Ruff: PASS
strict mypy: PASS — 100 source files
full pytest: 215 passed
```

### M7-B — Immutable state ledger

Validated head:

```text
45e4b2f84e39b38c5a2917c7e882c7a9abba6382
```

```text
focused pytest: 40 passed
Ruff: PASS
strict mypy: PASS — 104 source files
full pytest: 229 passed
real DB: 7 -> 8, check 8 -> 8
fresh DB: 0 -> 8, check 8 -> 8
```

Migration v8 is immutable applied history.

### M7-C — F-10 Injury & Availability State

Validated head:

```text
a9e1284073ee9c7a8a48bccf12bac9b900c88fa6
```

```text
focused pytest: 16 passed
Ruff: PASS
strict mypy: PASS — 108 source files
full pytest: 245 passed
real DB: 8 -> 9, check 9 -> 9
fresh DB: 0 -> 9, check 9 -> 9
```

Migration v9 is immutable applied history.

### M7-D — F-7 Player State V1

Validated head:

```text
c117380cd591ddc89101f5a62a5c90847aeb4384
```

```text
focused pytest: 21 passed
Ruff: PASS
strict mypy: PASS — 112 source files
full pytest: 266 passed
real DB: 9 -> 10, check 10 -> 10
fresh DB: 0 -> 10, check 10 -> 10
git diff --check: PASS
working tree: clean
local/remote branch SHA: exact match
```

Migration v10 is immutable applied history.

### M7-E — F-8 Unit State V1

First executable candidate:

```text
64215b1057f41deb37d5899f695f76f3d31ce390
```

First local focused/static gate:

```text
focused F-8 pytest: 22 passed
Ruff: 1 E501 in unit_repository.py
focused mypy: 22 errors
schema v11: NOT YET APPLIED
```

Classification: behavioral semantics PASS; blockers were static typing/hygiene and historical-test maintenance only. No F-8 architecture or estimator behavior was weakened.

Repeated focused/static candidate:

```text
ceaa74138474ec91306569fb4280b4c34640ddc9
```

```text
M7-D + M7-E focused pytest: 43 passed
affected-surface Ruff: PASS
affected-surface strict mypy: PASS — 4 source files
git diff --check: PASS
working tree: clean
local/remote branch SHA: exact match
```

Final validated executable/documentation head:

```text
15be474abd3a0ac476bce9e770cf1bcc25d367fc
```

Final repository gate:

```text
Ruff: PASS
strict mypy: PASS — 116 source files
full pytest: 288 passed
git diff --check: PASS
working tree: clean
local/remote branch SHA: exact match
```

Database proof:

```text
real M7-D DB: 10 -> 11, check 11 -> 11
fresh DB: 0 -> 11, check 11 -> 11
foreign_keys_enabled: true
integrity_ok: true
```

M7-E closed the F-8 substrate with health-neutral probabilistic role priors, Player State availability applied exactly once, exact sealed Player State parent dependencies, no raw-player re-ingestion, residualized direct unit evidence, explicit configuration uncertainty, explicit missing scheme fit, and immutable late-replacement propagation.

Migration v11 is immutable applied history.

## 5. Build sequence

```text
M7-A  Common state contracts / IDs / uncertainty             CLOSED / PASS
M7-B  Migration v8 + state snapshot/input/dependency ledger  CLOSED / PASS
M7-C  Injury observation / episode / availability             CLOSED / PASS
M7-D  Player State V1                                         CLOSED / PASS
M7-E  Unit State V1                                           CLOSED / PASS
M7-F  Coaching & Scheme State V1                              STARTING
M7-G  Team State V1                                           NOT STARTED
M7-H  Dependency propagation / rebuild inspection             NOT STARTED
M7-I  PIT multi-snapshot validation                           NOT STARTED
M7-J  Historical/real-data validation + certification         NOT STARTED
```

## 6. M7-F — F-9 Coaching & Scheme State V1 locked implementation boundary

M7-F must implement the locked F-9 architecture without collapsing personnel identity, scheme tendency, and coaching quality into one rating.

Required distinctions:

```text
PERSON
  ↓
COACHING_STINT
  ↓
ROLE
  ↓
COACHING_REGIME
```

and:

```text
PUBLIC_SCHEME_LABEL
!= EMPIRICAL_SCHEME_STATE
!= COACHING_EFFECTIVENESS
```

M7-F V1 must preserve:

- temporal coaching roles/stints and regime versions;
- explicit head coach, offensive play caller, defensive play caller, and coordinator responsibility where known;
- new regime/version when responsibility or play-caller identity changes midseason;
- public scheme labels as descriptive evidence only, never analytical truth;
- offensive and defensive tendency dimensions inferred from PIT-safe behavior;
- game-state-conditioned tendencies rather than unconditional run/pass/blitz rates;
- base scheme separated from game-specific/opponent-specific deviation;
- scheme/strategy separated from coaching effectiveness;
- current target-game evidence excluded from pregame state;
- explicit uncertainty and missing dimensions rather than fabricated scheme values;
- immutable Coaching State snapshots through the generic M7 state ledger;
- deterministic, versioned content identity and idempotent replay;
- exact observation lineage;
- forward-only migration v12 for any new coaching/scheme persistence because v11 is now immutable applied history.

V1 may use explicit deterministic estimators/priors where scientifically honest, but all constants and contracts must be versioned and recalibratable. Hierarchical priors and structural change-point detection remain extension points unless supported by present PIT evidence.

M7-F should not fabricate historical coach identity or play-caller assignments merely to populate a state. Unknown responsibility remains unknown.

## 7. Gate 0 evidence

Exact tested documentation head:

```text
fa22e63db79f49d9072f318df18cc38d20d30434
```

```text
Python 3.12.10
E:\Daily-NFL\.venv\Scripts\python.exe
Ruff: PASS
strict mypy: PASS — 95 source files
full pytest: 189 passed
git diff --check: PASS
working tree: clean
fresh database: 0 -> 7
check: 7 -> 7
foreign_keys_enabled: true
integrity_ok: true
```

Gate 0 is formally CLOSED / PASS.

## 8. Gate state

```text
M7 contract                       LOCKED
Pre-implementation audit          COMPLETE
Gate 0 local/static baseline      CLOSED / PASS
M7-A common contracts             CLOSED / PASS
M7-B migration/persistence        CLOSED / PASS
M7-C injury/availability          CLOSED / PASS
M7-D player state                 CLOSED / PASS
M7-E unit state                   CLOSED / PASS
M7-F coaching/scheme              STARTING
M7-G team state                   NOT STARTED
M7-H dependency propagation       NOT STARTED
M7-I PIT propagation validation   NOT STARTED
M7-J final historical validation  NOT STARTED
M7 certification                  WITHHELD
```

## 9. Immediate next action

Implement **M7-F Coaching & Scheme State V1** under F-9.

First implementation slice should establish:

1. canonical coaching-role / responsibility / regime observations and identities;
2. append-only PIT persistence through forward-only migration v12;
3. empirical scheme/tendency evidence with explicit game-state conditioning metadata;
4. immutable Coaching State construction that separates offensive scheme, defensive scheme, special-teams strategy, decision policy, adaptation, and coaching effectiveness;
5. exact PIT observation lineage and deterministic replay;
6. focused negative tests for regime changes, play-caller changes, unconditional-tendency misuse, post-cutoff evidence, target-game leakage, unknown responsibilities, and immutability.

M7-G must remain locked until M7-F is locally validated. Team State should consume Unit State and Coaching State rather than bypassing them.

## 10. Update rule

Update this file whenever:

- a gate changes state;
- an architecture decision is added/changed;
- an executable authority changes;
- a defect is found/remediated;
- local validation is run;
- a new provider/data limitation is discovered;
- the resume point moves.
