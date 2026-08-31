# M7-B State Persistence Result

**Project:** The Daily Line — Daily NFL
**Milestone:** M7-B — Migration v8 + Immutable State Ledger
**Branch:** `checkpoint/m7-state-engine-v1`
**Validated head:** `45e4b2f84e39b38c5a2917c7e882c7a9abba6382`
**Result:** CLOSED / PASS

## Scope validated

M7-B established the shared persistence substrate for F-6 through F-10:

- forward-only schema migration v8;
- `state_snapshots` immutable semantic ledger;
- `state_snapshot_inputs` exact M5-compatible observation provenance;
- `state_snapshot_dependencies` explicit parent-state lineage;
- `state_snapshot_seals` atomic consumability boundary;
- deterministic canonical JSON and payload SHA-256;
- content-addressed snapshot identity;
- exact input/dependency membership;
- append-only storage and post-seal membership protection;
- parent `as_of` validation and sealed-parent requirement;
- explicit dependency-cycle rejection;
- idempotent replay and fail-closed conflict verification.

Migrations 1-7 were not rewritten.

## Local validation evidence

Environment:

```text
Python 3.12.10
E:\Daily-NFL\.venv\Scripts\python.exe
```

Focused M7-A/M7-B validation:

```text
40 passed
```

Full quality gate:

```text
Ruff: PASS
strict mypy: PASS — 104 source files
full pytest: PASS — 229 tests
git diff --check: PASS
working tree: clean
```

The first M7-B run exposed a test-expectation defect, not a persistence defect. A cycle insertion was correctly rejected by the dedicated database guard with:

```text
state snapshot dependency cycle is forbidden
```

The test had incorrectly expected the later generic post-seal-membership guard. The test was corrected to assert the stronger explicit cycle rejection; production persistence semantics were not weakened.

## Certified v7 -> v8 migration proof

The existing Gate-0 database created under schema v7 was upgraded in place:

```text
schema_version_before: 7
schema_version_after: 8
supported_schema_version: 8
foreign_keys_enabled: true
integrity_ok: true
```

Immediate check:

```text
schema_version_before: 8
schema_version_after: 8
supported_schema_version: 8
foreign_keys_enabled: true
integrity_ok: true
```

## Fresh 0 -> v8 proof

A fresh database initialized directly to schema v8:

```text
schema_version_before: 0
schema_version_after: 8
supported_schema_version: 8
foreign_keys_enabled: true
integrity_ok: true
```

Immediate check:

```text
schema_version_before: 8
schema_version_after: 8
supported_schema_version: 8
foreign_keys_enabled: true
integrity_ok: true
```

## Architecture decision after v8 closure

Migration v8 is now treated as immutable applied history. Family-specific state persistence discovered or implemented after M7-B must use later forward-only migrations rather than editing v8. This preserves the same migration discipline used throughout M0-M6C.

## Closure

```text
M7-B — CLOSED / PASS
```

M7-C Injury & Availability State is authorized to begin on top of this exact persistence authority.
