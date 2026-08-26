# M7 State Engine V1 Progress Log

**Project:** The Daily Line — Daily NFL
**Milestone:** M7 — State Engine V1
**Branch:** `checkpoint/m7-state-engine-v1`
**Certified base:** `0dd515ec36f370ce70f67b3e771e1ceb4e36a149`
**Architecture:** F-6, F-7, F-8, F-9, F-10
**Status:** IN PROGRESS — PRE-IMPLEMENTATION ARCHITECTURE LOCKED

This file is the authoritative resume point while M7 is open. Final certification status remains governed by `ARCHITECTURE_CERTIFICATION_LOG.md`.

## 1. Governing documents

- `docs/architecture/F05-F09_FOOTBALL_STATE_ARCHITECTURE_V1.md`
- `docs/architecture/F10-F14_CONTEXT_FEATURE_TARGET_ARCHITECTURE_V1.md`
- `docs/implementation/IMPLEMENTATION_ROADMAP_V1.md`
- `docs/implementation/M7_STATE_ENGINE_V1_CONTRACT.md`
- `docs/implementation/M7_PREIMPLEMENTATION_CONFORMANCE_AUDIT.md`

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
schema version: 7
```

Reusable foundations:

- provider-neutral identity/domain contracts;
- immutable raw evidence/provenance;
- M4 reconciliation boundary;
- M5 PIT cutoff/input/snapshot machinery;
- M6 canonical play/participation/drive evidence;
- M6C full-history compatibility proof.

## 4. Pre-implementation audit result

The repo contains **no existing M7 state-engine implementation**.

Partial precursors:

- `PlayerId`, `TeamSeasonId`, `CoachRoleId`, `InjuryObservationId`, `DepthChartSnapshotId` exist;
- `CoachingRole` and `RosterStint` are temporal identity contracts;
- PIT snapshot hashing/input/sealing is a reusable architectural pattern.

Missing and required:

- common state package;
- state snapshot IDs/contracts;
- uncertainty/distribution contracts;
- migration v8;
- state snapshot/input/dependency persistence;
- injury observation/episode/availability state;
- player state;
- unit configuration/state;
- coaching regime/scheme state;
- team state;
- dependency DAG/double-counting guard;
- deterministic V1 estimators;
- PIT propagation validation.

## 5. Build sequence

```text
M7-A  Common state contracts / IDs / uncertainty
M7-B  Migration v8 + state snapshot/input/dependency ledger
M7-C  Injury observation / episode / availability
M7-D  Player State V1
M7-E  Unit State V1
M7-F  Coaching & Scheme State V1
M7-G  Team State V1
M7-H  Dependency propagation / rebuild inspection
M7-I  PIT multi-snapshot validation
M7-J  Historical/real-data validation + certification
```

## 6. Gate state

```text
M7 contract                       LOCKED
Pre-implementation audit          COMPLETE
Gate 0 local/static baseline      PENDING USER-LOCAL RUN
M7-A common contracts             NOT STARTED
M7-B migration/persistence        NOT STARTED
M7-C injury/availability          NOT STARTED
M7-D player state                 NOT STARTED
M7-E unit state                   NOT STARTED
M7-F coaching/scheme              NOT STARTED
M7-G team state                   NOT STARTED
M7-H dependency propagation       NOT STARTED
M7-I PIT propagation validation   NOT STARTED
M7-J final historical validation  NOT STARTED
M7 certification                  WITHHELD
```

## 7. Immediate next action

Before the first executable M7 commit, establish the exact local baseline on certified M6C `main` / M7 branch:

```text
Python 3.12.10 project venv
full pytest
Ruff
strict mypy
fresh/current SQLite schema check
clean exact branch SHA
```

After Gate 0 is recorded, implementation begins with **M7-A Common State Contracts / IDs / Uncertainty**, followed immediately by migration v8 and the shared snapshot ledger.

## 8. Update rule

Update this file whenever:

- a gate changes state;
- an architecture decision is added/changed;
- an executable authority changes;
- a defect is found/remediated;
- local validation is run;
- a new provider/data limitation is discovered;
- the resume point moves.
