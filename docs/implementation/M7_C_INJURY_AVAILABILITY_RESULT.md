# M7-C Injury & Availability State Result

**Project:** The Daily Line — Daily NFL  
**Milestone:** M7-C — F-10 Injury & Availability State  
**Branch:** `checkpoint/m7-state-engine-v1`  
**Status:** CLOSED / PASS  
**Validated head:** `a9e1284073ee9c7a8a48bccf12bac9b900c88fa6`

## Scope

M7-C implements the locked F-10 architecture on top of the generic M7-A/M7-B state substrate.

Implemented behavior:

- canonical append-only injury observation stream;
- separate practice status, game designation, and official ACTIVE/INACTIVE confirmation;
- immutable versioned injury-episode interpretations;
- multiple simultaneous injury episodes;
- explicit unknown/vague injury representation without inventing diagnoses;
- probabilistic availability as `P(active)`;
- participation distribution conditional on being active;
- effectiveness distribution conditional on participation;
- separate early-exit uncertainty;
- explicit versioned V1 estimator assumptions;
- exact PIT-safe observation membership carried into the immutable state ledger;
- prior-game episode/history evidence may remain in lineage without overriding current-game status evidence;
- late ACTIVE/INACTIVE information creates a new state snapshot and never mutates earlier snapshots.

## Migration discipline

Migration v8 had already been physically applied and validated under M7-B, so M7-C did not rewrite it.

M7-C added forward-only migration v9:

```text
m7_injury_availability_foundation
```

Schema v9 adds append-only injury observations, injury episodes, versioned episode revisions, exact revision observation membership, and revision seals.

## Validation evidence

Substantive M7-C candidate validation:

```text
focused pytest: 16 passed
strict mypy: PASS — 108 source files
full pytest: PASS — 245 tests
schema upgrade: 8 -> 9
schema check: 9 -> 9
fresh schema: 0 -> 9
fresh schema check: 9 -> 9
foreign_keys_enabled: true
integrity_ok: true
git diff --check: PASS
```

Ruff initially found formatting-only issues in migration/test source. These were remediated without changing M7-C semantics.

Final formatting gate at `a9e1284073ee9c7a8a48bccf12bac9b900c88fa6`:

```text
Ruff: PASS
working tree: clean
local branch SHA: a9e1284073ee9c7a8a48bccf12bac9b900c88fa6
remote branch SHA: a9e1284073ee9c7a8a48bccf12bac9b900c88fa6
```

## Important architectural proofs

### Availability is not effectiveness

A confirmed ACTIVE player receives effectively known availability while participation/workload and effectiveness may remain below full expectation.

### Late inactive is a new information state

A later INACTIVE observation collapses `P(active)` to zero in a new snapshot. Earlier pre-inactive snapshots remain immutable.

### No hindsight leakage

Only observations with `available_at <= as_of` enter a historical injury state. Post-cutoff injury evidence cannot alter an earlier state.

### No diagnosis invention

A source saying only `leg` or `leg issue` remains that coarse. Tissue, grade, and specific diagnosis are not inferred without credible evidence.

### Injury history does not become current-game status

Episode/history evidence from prior games may remain valid causal context, but immediate practice/game/active status is selected from observations relevant to the current game.

## Closure

M7-C is formally **CLOSED / PASS**.

M7-D Player State V1 is authorized to begin. The F-10 injury-availability snapshot is an explicit immutable parent dependency of Player State rather than duplicated health logic.
