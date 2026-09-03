# M7-F Prevalidation / Remediation Record — 2026-09-02

**Project:** The Daily Line — Daily NFL  
**Milestone:** M7-F — F-9 Coaching & Scheme State V1  
**Branch:** `checkpoint/m7-state-engine-v1`  
**Migration under validation:** v12 — `m7_coaching_scheme_state_evidence_foundation`  
**Migration v12 status:** **NOT APPLIED / NOT FROZEN**

## 1. First local M7-F gate

Initial prevalidation candidate:

```text
0b2ffe000d18ac7d3d5a7cae3a243f0a8c4f198c
```

Observed local results:

```text
focused F-9 pytest: 28 passed / 1 failed
focused strict mypy: PASS — 3 source files
Ruff: 4 findings
migration v12: not applied
```

The single behavioral failure was:

```text
test_play_caller_change_creates_new_regime_without_changing_head_coach
```

The test supplied a revision whose `available_at` was `CHANGE - 1h` to a pure state build at `CHANGE - 2h`. The production builder rejected the observation because it was not PIT-available at the requested cutoff.

### Classification

**Test-fixture PIT timing defect — production fail-closed behavior was correct.**

The intended architectural boundary is:

```text
pure builder + explicitly supplied post-cutoff observation
    -> fail closed

repository as_of reconstruction
    -> filters observations not available by cutoff

known future-effective assignment
    -> may be known before effective_from
    -> does not replace currently active assignment early
```

No estimator, persistence, or migration semantics were weakened.

The four Ruff findings were static hygiene only:

- import ordering in `daily_nfl/domain/identity.py`;
- one E501 line in `daily_nfl/state/coaching.py`;
- two E501 lines in `daily_nfl/state/coaching_repository.py`.

## 2. Local remediation

The play-caller transition fixture was corrected from:

```text
available_at = CHANGE - 1h
```

to:

```text
available_at = CHANGE - 3h
```

while retaining:

```text
effective_from = CHANGE
```

This means the replacement is already known at the early snapshot, but the current play caller remains active until the actual effective time.

Formatting-only Ruff remediations were also applied.

User-created remediation commit:

```text
ee7450d9b980822cf82673f89d0f373aaa73f06f
```

Repeated local focused/static gate:

```text
focused F-9 pytest: 29 passed
Ruff affected surface: PASS
focused strict mypy: PASS — 3 source files
git diff --check: PASS
working tree: clean
local/remote branch SHA: exact match
```

## 3. Explicit PIT regression guard

After the focused gate became green, an explicit regression test was added so the fail-closed boundary cannot later be mistaken for a bug and weakened.

Test file:

```text
tests/test_m7_coaching_pit_guard.py
```

Regression contract:

```text
post-cutoff coaching assignment supplied directly to pure Coaching State builder
    -> ValueError
    -> "coaching assignment cannot be available after Coaching State as_of"
```

Regression-guard commit:

```text
546efd30a0920f2b01ccf434b97d57ef4ea8aefe
```

This commit is test-only. Production Coaching State code and migration v12 were not changed.

## 4. Historical migration compatibility review

M7-E Unit State tests were inspected before the full M7-F gate.

They already preserve the correct historical boundary:

- current repository schema may be `>= 11`;
- migration 11 is still identified exactly by version/name;
- the v10 -> v11 transition is replayed directly against migrations 1-10;
- prior migration history must remain unchanged.

No M7-E test maintenance is required merely because migration v12 now exists.

## 5. Current status / next gate

```text
M7-E: CLOSED / PASS
migration v11: immutable applied history

M7-F focused behavior: PASS at ee7450d before explicit regression addition
M7-F focused static gate: PASS at ee7450d
post-cutoff assignment regression: added at 546efd3
migration v12: NOT APPLIED / NOT FROZEN
M7-F formal closure: WITHHELD
M7-G: LOCKED
```

Next required validation:

1. pull the regression/documentation head;
2. run both F-9 focused test modules;
3. run full repository Ruff;
4. run full repository strict mypy;
5. run full repository pytest;
6. verify clean working tree and exact local/remote SHA;
7. only after the complete code gate is green, authorize real schema 11 -> 12 and fresh 0 -> 12 migration proofs.

If the full code gate finds a defect, migration v12 must remain unapplied until remediation is complete.
