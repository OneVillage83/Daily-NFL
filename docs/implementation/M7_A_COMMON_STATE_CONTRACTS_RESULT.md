# M7-A Common State Contracts / IDs / Uncertainty Result

**Project:** The Daily Line — Daily NFL
**Milestone:** M7 — State Engine V1
**Subphase:** M7-A — Common State Contracts / IDs / Uncertainty
**Branch:** `checkpoint/m7-state-engine-v1`
**Validated head:** `9de3b61b738f934061918342d22ee29923cdb43b`
**Status:** CLOSED / PASS

## Scope validated

M7-A introduced only the shared provider-neutral state substrate required by F-6 through F-10:

- opaque canonical state identifiers;
- state type / subject type vocabulary;
- immutable generic state-snapshot envelope;
- explicit expected/present/missing coverage;
- structured probability, moment, interval, categorical-distribution, and unknown/missingness uncertainty contracts;
- state input/dependency membership validation;
- focused failure-state tests.

M7-A did **not** add persistence migration v8 or implement injury, player, unit, coaching, or team estimators.

## Local validation

Certified project interpreter:

```text
Python 3.12.10
E:\Daily-NFL\.venv\Scripts\python.exe
```

Focused M7-A result:

```text
26 passed
```

Final full quality gate:

```text
Ruff: PASS
strict mypy: PASS — 100 source files
full pytest: PASS — 215 tests
git diff --check: PASS
working tree: clean
```

## Remediation history

The first candidate at `8f33a7158594b478665e44295bb1f958dd0bbc71` passed all semantic tests and strict mypy but Ruff found four quality issues:

- two import-order findings;
- Python 3.12 generic syntax modernization (`UP046`);
- a function call in a test-helper default argument (`B008`).

The generic/default-argument findings were corrected remotely, and Ruff's deterministic import sorter was then applied locally to exactly:

- `daily_nfl/domain/__init__.py`;
- `tests/test_state_contracts.py`.

The final validated head is `9de3b61b738f934061918342d22ee29923cdb43b`.

## Decision

```text
M7-A — CLOSED / PASS
M7-B — NEXT
```

M7-B may now add the forward-only schema-v8 state snapshot/input/dependency/seal ledger and deterministic persistence/replay implementation. Migrations 1-7 remain immutable.
