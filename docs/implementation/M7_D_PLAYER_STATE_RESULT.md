# M7-D Player State V1 Result

**Project:** The Daily Line — Daily NFL
**Milestone:** M7-D — F-7 Player State V1
**Branch:** `checkpoint/m7-state-engine-v1`
**Status:** CLOSED / PASS
**Validated executable head:** `c117380cd591ddc89101f5a62a5c90847aeb4384`
**Schema after checkpoint:** 10

## Scope closed

M7-D implements the initial production-planned F-7 Player State architecture on top of the M7-C F-10 injury/availability state.

The closed V1 substrate includes:

- separate persistent talent, current form/performance, role/usage, workload, health/availability, and position-specific state dimensions;
- no universal one-number player rating requirement;
- explicit position families and position-specific extension vocabularies, including richer QB dimensions;
- F-10 injury/availability snapshot as an exact immutable parent dependency;
- separate availability, participation-if-active, and effectiveness-if-participates quantities;
- workload evidence preserved without inventing an unvalidated causal fatigue penalty;
- explicit low-sample uncertainty for rookies/sparse evidence;
- append-only versioned player-state evidence with deterministic metric and full-semantic checksums;
- latest-known revision selection at the PIT cutoff while preserving older revisions historically;
- prior-team talent persistence with current-team role/form/workload isolation;
- team filtering before revision selection so old-team corrections cannot hide current-team evidence;
- current target-game evidence excluded from pregame Player State;
- deterministic order-stable aggregation;
- immutable Player State snapshots persisted through the generic M7 state ledger;
- forward-only migration v10 for player-state evidence persistence.

## Validation sequence

Initial semantic candidate:

```text
661c1f6e3e0d66e4d147b467107127753c918b9b
```

Initial local run proved Player State behavior but exposed static-quality issues only:

```text
focused pytest: 21 passed
full pytest: 266 passed
Ruff: migration line length + test import formatting
strict mypy: one float exponentiation no-any-return
schema v10: NOT YET APPLIED
```

The production static issues were remediated without changing Player State semantics:

- migration error text was line-wrapped only;
- recency decay uses `math.exp2(...)` so strict mypy receives a concrete float result;
- Ruff-only test formatting was applied locally and committed.

Final validated head:

```text
c117380cd591ddc89101f5a62a5c90847aeb4384
```

Final local quality gate:

```text
focused pytest: 21 passed
Ruff: PASS
strict mypy: PASS — 112 source files
full pytest: 266 passed
git diff --check: PASS
working tree: clean
local/remote branch SHA: exact match
```

## Database proof

A real schema-v9 database created under the closed M7-C code was upgraded under the final M7-D head:

```text
local-data/m7/m7-gatec-final.db
schema_version_before: 9
schema_version_after: 10
supported_schema_version: 10
foreign_keys_enabled: true
integrity_ok: true
```

Immediate check:

```text
schema_version_before: 10
schema_version_after: 10
supported_schema_version: 10
foreign_keys_enabled: true
integrity_ok: true
```

Fresh initialization proof:

```text
local-data/m7/m7-gated-fresh.db
schema: 0 -> 10
check: 10 -> 10
foreign_keys_enabled: true
integrity_ok: true
```

Migration v10 is therefore applied immutable history and must not be edited by later M7 work. M7-E and later schema additions must use new forward-only migration versions.

## Architecture evidence

The final implementation preserves the required F-7 distinctions:

```text
persistent talent
!= current form/performance
!= team-conditioned role/usage
!= workload
!= health/availability
!= position-specific state
```

It also preserves the explicit dependency:

```text
F-10 Injury / Availability State
              ↓
       F-7 Player State
```

The Player State snapshot carries the exact sealed injury parent and exact PIT-safe player evidence inputs. Late legitimate injury information therefore produces a later immutable injury snapshot and a later Player State rather than rewriting an earlier state.

## Defects encountered and disposition

No architecture or estimator semantic defect was found by the local gate.

The gate found only static-quality defects:

1. one overlong migration error string;
2. one strict-mypy return-type issue caused by float exponentiation typing;
3. one Ruff-only blank-line/import formatting issue in the focused test file.

All were corrected without weakening tests, PIT rules, lineage, or estimator semantics.

## Exit result

**M7-D is CLOSED / PASS.**

M7-E may now begin. The next dependency is F-8 Unit State V1, where sealed Player State snapshots become explicit immutable parents and expected unit composition remains probabilistic until availability resolves.
