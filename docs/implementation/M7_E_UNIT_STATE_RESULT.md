# M7-E Unit State V1 Result

**Project:** The Daily Line — Daily NFL
**Milestone:** M7-E — F-8 Unit State V1
**Branch:** `checkpoint/m7-state-engine-v1`
**Status:** CLOSED / PASS
**Validated executable head:** `15be474abd3a0ac476bce9e770cf1bcc25d367fc`
**Schema after checkpoint:** 11

## Scope closed

M7-E implements the initial production-planned F-8 Unit State architecture on top of the closed M7-D Player State substrate.

The closed V1 substrate includes:

- provider-neutral functional unit types spanning offense, defense, and special teams;
- dynamic unit configurations rather than one permanent roster-level unit identity;
- health-neutral `ROLE_PRIOR_ONLY` probabilistic configuration observations;
- Player State availability applied exactly once to convert configuration priors into pregame posterior configuration probabilities;
- exact sealed Player State parent dependencies;
- no reopening or independent re-ingestion of player raw evidence inside Unit State;
- direct unit evidence for continuity, experience together, role compatibility, synergy, and recent performance;
- explicit residualization against Player State for role compatibility, synergy, and recent performance to prevent double counting;
- separate intrinsic member quality, member form, residual recent unit performance, continuity, experience, role compatibility, synergy, health, and scheme-fit dimensions;
- scheme fit explicitly unknown until a legitimate F-9 coaching/scheme parent exists;
- target-game direct unit evidence excluded from pregame Unit State;
- conflicting configuration sources fail closed;
- late player availability changes create later Unit State snapshots and can shift probability toward replacement configurations without rewriting earlier states;
- immutable Unit State snapshots persisted through the generic M7 state ledger;
- forward-only migration v11 for unit configuration and unit-state evidence persistence.

## Validation sequence

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

The behavioral semantics were green. Static blockers were classified as implementation typing/hygiene issues rather than architecture defects:

1. Player/Unit snapshot variable shadowing in the repository confused generic inference;
2. the test helper returned `StateSnapshotEnvelope[object]` instead of the exact `UnitStatePayload` type;
3. one deterministic-identity test used loose `dict[str, object]` kwargs expansion;
4. one Ruff-only line exceeded the line-length limit;
5. historical M7-D migration tests still assumed schema 10 had to remain the repository tip.

Remediation preserved F-8 behavior and migration semantics:

- repository variable names were separated by state family;
- repository return typing was made exact;
- test generics were tightened;
- loose kwargs typing was removed;
- Ruff-only formatting was corrected;
- M7-D migration tests were converted into historical v9 -> v10 boundary tests so later valid migrations do not invalidate prior certification evidence.

Repeated focused/static candidate:

```text
ceaa74138474ec91306569fb4280b4c34640ddc9
```

Repeated focused/static local gate:

```text
M7-D + M7-E focused pytest: 43 passed
affected-surface Ruff: PASS
affected-surface strict mypy: PASS — 4 source files
git diff --check: PASS
working tree: clean
local/remote branch SHA: exact match
```

A documentation-only progress commit then advanced the branch without changing executable F-8 code.

Final validated head:

```text
15be474abd3a0ac476bce9e770cf1bcc25d367fc
```

Final full-repository quality gate:

```text
Ruff: PASS
strict mypy: PASS — 116 source files
full pytest: 288 passed
git diff --check: PASS
working tree: clean
local/remote branch SHA: exact match
```

## Database proof

A real schema-v10 database created under the closed M7-D code was upgraded under the final M7-E head:

```text
local-data/m7/m7-gated-fresh.db
schema_version_before: 10
schema_version_after: 11
supported_schema_version: 11
foreign_keys_enabled: true
integrity_ok: true
```

Immediate check:

```text
schema_version_before: 11
schema_version_after: 11
supported_schema_version: 11
foreign_keys_enabled: true
integrity_ok: true
```

Fresh initialization proof:

```text
local-data/m7/m7-gatee-fresh.db
schema: 0 -> 11
check: 11 -> 11
foreign_keys_enabled: true
integrity_ok: true
```

Migration v11 is therefore applied immutable history and must not be edited by later M7 work. M7-F and later schema additions must use new forward-only migration versions.

## Architecture evidence

The final implementation preserves the required F-8 dependency:

```text
F-10 Injury / Availability
            ↓
      F-7 Player State
            ↓
       F-8 Unit State
```

The Unit State snapshot carries exact sealed Player State parents and only direct unit/configuration evidence as observation inputs. It does not independently replay player raw evidence.

The implementation also preserves the required distinction:

```text
member talent / quality
!= member form
!= continuity / experience together
!= role compatibility
!= interaction / synergy
!= residual recent unit performance
!= health / availability
!= scheme fit
```

Configuration uncertainty remains explicit before availability resolves. A late inactive Player State can eliminate configurations containing that player and shift posterior probability toward valid replacement configurations in a new immutable Unit State.

## Double-counting guard

F-8 closes a major downstream modeling risk by making the dependency graph explicit:

```text
PLAYER STATES
     ↓
UNIT STATE MODEL
     ↓
TEAM STATE
```

Direct unit evidence that could overlap player-level quality must declare residualization against Player State. Health-neutral configuration priors are then adjusted by Player State availability exactly once.

## Defects encountered and disposition

No F-8 architecture or estimator semantic defect was found by local validation.

The initial gate exposed only static typing/hygiene and historical-test-maintenance issues. All were corrected without weakening PIT rules, lineage, residualization, configuration semantics, or test expectations.

## Exit result

**M7-E is CLOSED / PASS.**

M7-F may now begin. The next dependency is F-9 Coaching & Scheme State V1. Because schema v11 is now applied immutable history, any M7-F persistence additions must use forward-only migration v12.
