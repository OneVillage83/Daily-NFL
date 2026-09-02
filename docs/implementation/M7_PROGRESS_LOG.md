# M7 State Engine V1 Progress Log

**Project:** The Daily Line — Daily NFL
**Milestone:** M7 — State Engine V1
**Branch:** `checkpoint/m7-state-engine-v1`
**Certified base:** `0dd515ec36f370ce70f67b3e771e1ceb4e36a149`
**Architecture:** F-6, F-7, F-8, F-9, F-10
**Status:** IN PROGRESS — M7-E CLOSED / M7-F PREVALIDATION CANDIDATE

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

```text
F-6  Team State
F-7  Player State
F-8  Unit State
F-9  Coaching & Scheme State
F-10 Injury & Availability State
```

M7 does not own F-11/F-12 environment/recovery integration, M9 feature registry, predictive models, simulation, market pricing, Recommendation Gate, or the full M16 event router.

## 3. Certified foundation

```text
M6C certified main: 0dd515ec36f370ce70f67b3e771e1ceb4e36a149
M6C historical PBP compatibility: 1999-2025, 27/27 PASS
schema entering M7: 7
schema after M7-B: 8
schema after M7-C: 9
schema after M7-D: 10
schema after M7-E: 11
```

Reusable foundations include provider-neutral identity, immutable raw evidence/provenance, PIT snapshot/input machinery, canonical football history, common state contracts, the immutable state ledger, F-10 Injury State, F-7 Player State, and F-8 Unit State.

## 4. Closed checkpoints

### M7-A — Common state substrate

```text
validated head: 9de3b61b738f934061918342d22ee29923cdb43b
focused pytest: 26 passed
Ruff: PASS
strict mypy: PASS — 100 source files
full pytest: 215 passed
```

### M7-B — Immutable state ledger

```text
validated head: 45e4b2f84e39b38c5a2917c7e882c7a9abba6382
focused pytest: 40 passed
Ruff: PASS
strict mypy: PASS — 104 source files
full pytest: 229 passed
real DB: 7 -> 8, check 8 -> 8
fresh DB: 0 -> 8, check 8 -> 8
```

Migration v8 is immutable applied history.

### M7-C — F-10 Injury & Availability State

```text
validated head: a9e1284073ee9c7a8a48bccf12bac9b900c88fa6
focused pytest: 16 passed
Ruff: PASS
strict mypy: PASS — 108 source files
full pytest: 245 passed
real DB: 8 -> 9, check 9 -> 9
fresh DB: 0 -> 9, check 9 -> 9
```

Migration v9 is immutable applied history.

### M7-D — F-7 Player State V1

```text
validated head: c117380cd591ddc89101f5a62a5c90847aeb4384
focused pytest: 21 passed
Ruff: PASS
strict mypy: PASS — 112 source files
full pytest: 266 passed
real DB: 9 -> 10, check 10 -> 10
fresh DB: 0 -> 10, check 10 -> 10
```

Migration v10 is immutable applied history.

### M7-E — F-8 Unit State V1

First candidate `64215b1057f41deb37d5899f695f76f3d31ce390` passed 22 behavioral tests but exposed one Ruff line and 22 static typing errors. Those were classified as static implementation/test-hygiene defects only; no F-8 semantic gate was weakened.

Repeated candidate `ceaa74138474ec91306569fb4280b4c34640ddc9`:

```text
M7-D + M7-E focused pytest: 43 passed
affected-surface Ruff: PASS
affected-surface strict mypy: PASS — 4 source files
```

Final validated head:

```text
15be474abd3a0ac476bce9e770cf1bcc25d367fc
Ruff: PASS
strict mypy: PASS — 116 source files
full pytest: 288 passed
real DB: 10 -> 11, check 11 -> 11
fresh DB: 0 -> 11, check 11 -> 11
foreign_keys_enabled: true
integrity_ok: true
```

Migration v11 is immutable applied history.

## 5. Build sequence

```text
M7-A  Common state contracts / IDs / uncertainty             CLOSED / PASS
M7-B  Migration v8 + state snapshot/input/dependency ledger  CLOSED / PASS
M7-C  Injury observation / episode / availability             CLOSED / PASS
M7-D  Player State V1                                         CLOSED / PASS
M7-E  Unit State V1                                           CLOSED / PASS
M7-F  Coaching & Scheme State V1                              PREVALIDATION CANDIDATE
M7-G  Team State V1                                           NOT STARTED
M7-H  Dependency propagation / rebuild inspection             NOT STARTED
M7-I  PIT multi-snapshot validation                           NOT STARTED
M7-J  Historical/real-data validation + certification         NOT STARTED
```

## 6. M7-F — F-9 Coaching & Scheme State V1

### Locked architecture

```text
PERSON
  ↓
COACHING_STINT
  ↓
ROLE / RESPONSIBILITY
  ↓
COACHING_REGIME
```

and:

```text
PUBLIC_SCHEME_LABEL
!= EMPIRICAL_SCHEME_STATE
!= COACHING_EFFECTIVENESS
```

M7-F preserves:

- persistent Person identity separate from team-scoped CoachingStint identity;
- time-versioned role and responsibility observations;
- explicit head coach, coordinators, offensive play caller, and defensive play caller when known;
- deterministic new regime identity when staff/responsibility semantics change;
- unresolved play-caller responsibility as explicit unknown state;
- public scheme labels as descriptive evidence only;
- empirical offensive/defensive/special-teams/decision-policy evidence as a separate analytical layer;
- game-state-conditioned policy buckets rather than unconditional run/pass/blitz rates;
- base scheme separated from target-game-specific deviation;
- scheme/strategy separated from coaching effectiveness;
- current target-game behavioral evidence excluded from pregame state;
- exact PIT observation membership in the generic immutable state ledger;
- versioned/recalibratable V1 estimator constants;
- forward-only migration v12 because v11 is applied history.

### Prevalidation implementation

The branch now contains:

- additive `CoachingStintId` / `CoachingStint` canonical identity;
- additive coaching assignment/scheme/public-label observation IDs;
- migration v12 `m7_coaching_scheme_state_evidence_foundation`;
- `coaching_stints` canonical identity table;
- append-only `coaching_assignment_observations`;
- append-only `coaching_scheme_evidence_observations`;
- append-only `public_scheme_label_observations`;
- raw-provenance checks and semantic hashes;
- exact persistence of assignment knowledge `effective_at` separately from role interval `effective_from/effective_to`;
- DDL and Python parity limiting game-specific deviation to scheme/policy components;
- conditioned empirical tendency estimates retained as separate game-state buckets;
- provider-neutral semantic Coaching State payloads;
- public-label observations projected to semantic `(side, label)` payloads instead of carrying provider/provenance data into state;
- semantic coaching-regime identity independent of source/logical keys;
- future-effective higher assignment revisions that do not prematurely hide the current active assignment;
- repository reconstruction plus immutable Coaching State sealing;
- focused negative/regression tests for assignment revisions, future announcements, play-caller transitions, duplicate responsibilities, unconditional tendency misuse, target-game leakage, post-cutoff evidence, base/deviation separation, public-label separation, and immutable replay.

Migration v12 is **NOT APPLIED** and remains editable until focused/static and then full-repository validation pass.

### Prevalidation hardening decisions

1. **Conditioning is preserved, not averaged away.** Policy evidence is aggregated within exact game-state condition buckets to remain compatible with the long-term `π(a | s)` direction.
2. **Regime identity is semantic.** Observation IDs, provider metadata, and logical/source keys do not define a coaching regime.
3. **Public labels are not analytical truth.** Labels remain exact PIT inputs but the state payload contains only provider-neutral descriptive labels; they do not populate empirical scheme estimates.
4. **Future announcements do not rewrite current state.** A known future-effective assignment revision cannot suppress the currently effective assignment before its effective time.
5. **Ended latest revisions do not resurrect older history.** Fallback is restricted to the future-effective-revision case.
6. **Assignment clocks stay distinct.** Knowledge `effective_at` is persisted independently from the assignment's semantic effective interval.
7. **Same person/team relationship can support multiple roles/responsibilities under one CoachingStint identity.**

## 7. Gate state

```text
M7 contract                       LOCKED
Pre-implementation audit          COMPLETE
Gate 0 local/static baseline      CLOSED / PASS
M7-A common contracts             CLOSED / PASS
M7-B migration/persistence        CLOSED / PASS
M7-C injury/availability          CLOSED / PASS
M7-D player state                 CLOSED / PASS
M7-E unit state                   CLOSED / PASS
M7-F coaching/scheme              PREVALIDATION CANDIDATE
migration v12                     NOT APPLIED / NOT FROZEN
M7-G team state                   LOCKED
M7-H dependency propagation       NOT STARTED
M7-I PIT propagation validation   NOT STARTED
M7-J final historical validation  NOT STARTED
M7 certification                  WITHHELD
```

## 8. Immediate next action

Run the first local M7-F focused/static gate on the pinned branch head. Do **not** apply migration v12 yet.

If the focused/static gate is clean, advance to full-repository Ruff/mypy/pytest. Only after the full repository gate is clean may a real schema-v11 database be upgraded to v12 and a fresh 0 -> 12 initialization be used as migration proof.

M7-G must remain locked until M7-F closes. Team State will consume Unit State and Coaching State rather than bypassing them.

## 9. Update rule

Update this file whenever a gate changes state, an architecture decision changes, executable authority changes, a defect is found/remediated, local validation is run, a provider/data limitation is discovered, or the resume point moves.
