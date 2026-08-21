# M1 Architecture-Conformance Audit

**Project:** The Daily Line — Daily NFL  
**Milestone:** M1 — Canonical Domain Contracts  
**Audit date:** 2026-08-21  
**Audit branch:** `audit/m1-architecture-conformance`  
**Governing roadmap:** `docs/implementation/IMPLEMENTATION_ROADMAP_V1.md`  
**Architecture dependencies:** F-1, F-3, F-5  
**Certification status:** **M1 — ARCHITECTURE-CERTIFIED**

---

## 1. Certification Decision

M1 is certified as the canonical football-domain foundation for later Daily-NFL milestones.

The audit did not ask only whether domain classes existed. It required the M1 contract to represent the locked F-1 / F-3 / F-5 football ontology without provider coupling, causal leakage, identity ambiguity, or a foreseeable canonical-contract rewrite forced by already-planned architecture.

The pre-audit implementation had a sound core but omitted several architecture-level concepts. Those gaps were remediated on `audit/m1-architecture-conformance`, downstream provisional M2-M6 consumers were kept compatible, and the full repository quality gate passed.

Validated implementation head before certification-document-only commits:

```text
ff79d7a7ed7f3b27ca5135bf95accf4d74d34fa1
```

Local certification evidence:

```text
pytest: 116 passed in 1.17s
Ruff: All checks passed!
mypy: Success: no issues found in 66 source files
git status --short: clean
```

Final decision:

```text
M1 ARCHITECTURE-CONFORMANCE AUDIT: PASS
M1 DOMAIN REMEDIATION: PASS
M1 FULL-REPOSITORY COMPATIBILITY: PASS
M1 LOCAL QUALITY GATE: PASS
M1 — ARCHITECTURE-CERTIFIED
```

---

## 2. Governing M1 Contract

Roadmap dependencies:

```text
F-1 — NFL Domain Ontology
F-3 — Canonical Identity & Reconciliation
F-5 — Canonical Game / Drive / Play Architecture
```

Required M1 surface includes:

```text
season / phase / week
game identity
team-season identity
player identity
drive identity
play identity
possession / possession segment
period
pre-play state
PLAY_EXECUTION
play-design modifiers including PLAY_ACTION
play events
play result
participation
penalty
game result
ruleset version
```

Exit gate:

```text
canonical objects compile/import
enum semantics are tested
pre-play state cannot contain outcome fields by construction
PLAY_EXECUTION naming is enforced
```

Foundational ontology and identity concepts explicitly required by F-1/F-3/F-5 were treated as M1 obligations when omission would force a future canonical-contract rewrite. Learned state estimators, persistence/revision machinery, provider crosswalk execution, injury inference, and live orchestration remain later-milestone work.

---

## 3. Evidence Reviewed

Architecture / roadmap:

```text
docs/implementation/IMPLEMENTATION_ROADMAP_V1.md
docs/architecture/F00-F04_ARCHITECTURE_FOUNDATION_V1.md
docs/architecture/F05-F09_FOOTBALL_STATE_ARCHITECTURE_V1.md
```

M1 implementation:

```text
daily_nfl/domain/__init__.py
daily_nfl/domain/enums.py
daily_nfl/domain/game.py
daily_nfl/domain/identity.py
daily_nfl/domain/ids.py
daily_nfl/domain/play.py
daily_nfl/domain/temporal.py
```

Compatibility surfaces reviewed because they consume M1 contracts:

```text
daily_nfl/normalization/contracts.py
daily_nfl/normalization/nflverse.py
daily_nfl/normalization/persistence.py
daily_nfl/reconciliation/canonical.py
daily_nfl/reconciliation/__init__.py
```

Architecture-locking tests:

```text
tests/test_domain_contracts.py
```

Full-repository validation additionally exercised the existing persistence, provider, reconciliation, PIT, and normalization suites.

---

## 4. Final Conformance Matrix

| ID | Requirement | Final status | Evidence / remediation |
|---|---|---|---|
| M1-01 | Provider-neutral domain vocabulary | `SATISFIED` | Domain modules model football concepts rather than nflverse/provider columns. |
| M1-02 | Competition → season → phase → week hierarchy | `SATISFIED AFTER REMEDIATION` | Added opaque `CompetitionId`, explicit `Season` and `Week`; retained `SeasonWeek` compatibility value. |
| M1-03 | Game linked to Core event + competition | `SATISFIED AFTER REMEDIATION` | `Game` carries `competition_id`; `event_id` is the opaque Core-event reference and exposes `core_event_id`. |
| M1-04 | Game/result separation | `SATISFIED` | Final score, winner/tie, and realized overtime truth remain outside `Game`. |
| M1-05 | Schedule/rules references | `SATISFIED AFTER REMEDIATION` | `RulesetVersion` retained and optional `schedule_version` added. |
| M1-06 | Final football truth supports final timestamp | `SATISFIED AFTER REMEDIATION` | `GameResult.final_at` added with timezone-awareness validation. |
| M1-07 | Franchise separate from team-season | `SATISFIED` | Persistent franchise and season-scoped team identity remain distinct. |
| M1-08 | Person/player separate from team membership | `SATISFIED AFTER REMEDIATION` | Added explicit time-bounded `RosterStint`; `Player` remains independent of team membership. |
| M1-09 | Coaching assignment is structured/history-capable | `SATISFIED AFTER REMEDIATION AT ONTOLOGY LEVEL` | Added time-bounded `CoachingRole`; learned coaching state remains M7/F-9. |
| M1-10 | F-3 football-native ID vocabulary | `SATISFIED AFTER REMEDIATION` | Added roster-stint, coach-role, possession-segment, participation, penalty, injury-observation, and depth-chart-snapshot IDs. |
| M1-11 | Provider IDs never canonical | `SATISFIED` | Provider identifiers remain outside canonical domain identity. |
| M1-12 | Possession segment distinct from drive | `SATISFIED AFTER REMEDIATION` | Added explicit `PossessionSegment` / `PossessionSegmentId`. |
| M1-13 | Canonical drive ledger contract | `SATISFIED AFTER REMEDIATION` | Added provider-neutral `Drive`. |
| M1-14 | Canonical play ledger contract | `SATISFIED AFTER REMEDIATION` | Added provider-neutral `Play` linking game, sequence, segment, drive, and prior play. |
| M1-15 | Period semantics | `SATISFIED` | Regulation/overtime validation retained. |
| M1-16 | Protected pre-play causal state | `SATISFIED AFTER REMEDIATION` | Added planned segment/play-clock/previous-play/situational/personnel/formation/environment references without outcome fields. |
| M1-17 | Pre-play state structurally excludes outcomes/analytics | `SATISFIED` | Tests prohibit official/physical yards, completion, TD, INT, sack, first-down result, EPA/WPA/success fields. |
| M1-18 | Canonical execution object named `PLAY_EXECUTION` | `SATISFIED` | `PlayExecution` is the container; `PLAY_ACTION` is only a football design modifier. |
| M1-19 | Primary execution taxonomy matches locked F-5 | `SATISFIED` | Exact enum set is architecture-locked by tests. |
| M1-20 | Primary family separate from design mechanics | `SATISFIED` | `primary_play_type` and modifier set remain separate dimensions. |
| M1-21 | Locked play-design vocabulary representable | `SATISFIED AFTER REMEDIATION` | Added BOOT, NAKED_BOOT, DRAW, READ_OPTION, SPEED_OPTION, DROPBACK, QUICK_GAME, EMPTY and retained existing modifiers. |
| M1-22 | Invalid modifier combinations fail closed | `SATISFIED AFTER REMEDIATION` | Designed-QB-run/RUSH and SHOTGUN-vs-UNDER_CENTER constraints added; RPO/scrimmage constraints retained. |
| M1-23 | Ordered play-event stream | `SATISFIED` | Positive event sequence and first-class event identity retained. |
| M1-24 | Participation first-class | `SATISFIED AFTER REMEDIATION` | Added required `ParticipationId`. |
| M1-25 | Penalty first-class | `SATISFIED AFTER REMEDIATION` | Added required `PenaltyId`; disposition/enforcement semantics retained. |
| M1-26 | Physical vs official outcome separation | `SATISFIED AFTER REMEDIATION` | Added structured `ObservedPhysicalOutcome`; `PlayResult` remains official truth. |
| M1-27 | Derived analytics not canonical truth | `SATISFIED` | EPA/WPA/CPOE/success analytics remain outside canonical truth objects. |
| M1-28 | Provider-independent child identities | `SATISFIED AFTER REMEDIATION` | Added deterministic possession-segment/participation/penalty ID helpers. |
| M1-29 | Enum/domain semantics architecture-locked by tests | `SATISFIED AFTER REMEDIATION` | Expanded domain tests cover exact taxonomy, required vocabulary, invalid combinations, identity separation, and causal boundaries. |
| M1-30 | Existing provisional M2-M6 consumers remain compatible | `SATISFIED` | Full repository gate passed: 116 tests, Ruff clean, mypy clean across 66 source files. |

No blocking M1 item remains.

---

## 5. F-1 Certification Summary

The certified domain can represent the core hierarchy:

```text
Competition
  -> Season
    -> Season Phase / Week
      -> Game
        -> Possession Segment
          -> Drive
            -> Play
              -> Play Event
                -> Participation
```

`Game` remains distinct from `GameResult`. `Franchise` remains distinct from `TeamSeason`. `Person` and `Player` remain persistent identities while `RosterStint` represents team membership over time. Coaching assignment is explicit via `CoachingRole` without prematurely implementing the later coaching-state engine.

Player/unit latent state, injury-state inference, and depth-chart acquisition are deferred by architecture to later milestones rather than being invented inside M1.

---

## 6. F-3 Certification Summary

M1 now exposes the football-native identity vocabulary needed by later reconciliation and persistence layers while preserving the rule:

> External provider IDs never become The Daily Line's permanent canonical identity.

Canonical identities include franchise, team-season, player, roster stint, coach role, NFL game, possession segment, drive, play, play event, participation, injury observation, depth-chart snapshot, and penalty concepts.

External-ID crosswalk persistence, confidence, ambiguity handling, evidence provenance, and reconciliation history remain M4 certification scope.

---

## 7. F-5 Certification Summary

The certified event model preserves the causal structure:

```text
PLAY_STATE_BEFORE
        +
PLAY_EXECUTION
        +
PARTICIPATION / EVENTS
        ↓
PLAY_RESULT
        ↓
PLAY_STATE_AFTER
```

The protected pre-play object cannot contain realized outcome or derived-analytics fields. Primary play family and play-design mechanics are separate dimensions. `PLAY_ACTION` remains the football concept, never the container name. Participation and penalties have first-class canonical identity, and physical outcome can be represented separately from the official result.

Append-only provider revisions and accepted-current interpretation remain persistence/reconciliation responsibilities and are audited later.

---

## 8. Material Findings Remediated

1. **Competition absent from canonical game hierarchy — HIGH.** Added `CompetitionId`, `Season`, `Week`, and `Game.competition_id`.
2. **Possession-segment / drive / play ledger under-modeled — HIGH.** Added explicit ledger contracts.
3. **Roster stint missing — HIGH.** Added time-bounded `RosterStint` without contaminating persistent player identity.
4. **Participation/penalty records lacked canonical IDs — HIGH.** Added required IDs and deterministic child-ID helpers.
5. **F-5 play-design vocabulary incomplete — MEDIUM.** Expanded the modifier vocabulary to the locked V1 set.
6. **Physical outcome insufficiently separated from official outcome — HIGH.** Added `ObservedPhysicalOutcome`.
7. **Protected pre-play contract omitted planned causal context — MEDIUM.** Added optional causal context only; no outcomes.
8. **M1 tests did not fully lock the architecture vocabulary — MEDIUM.** Expanded architecture-contract tests.
9. **Coaching role existed only in future prose — MEDIUM.** Added time-bounded ontology-level `CoachingRole`.
10. **Ruff import ordering in expanded tests — LOW / MECHANICAL.** Corrected before final certification rerun.

All M1 findings are closed.

---

## 9. Explicit Deferrals — Not M1 Defects

The following remain intentionally outside M1 certification:

- player-state estimation;
- unit-state estimation;
- coaching/scheme statistical state;
- injury availability/effectiveness inference;
- depth-chart acquisition/snapshot persistence;
- provider capability/acquisition logic;
- external-ID crosswalk persistence/reconciliation decisions;
- append-only play observation/revision storage;
- broad drive/play provider normalization coverage;
- PIT selection/reconstruction;
- feature engineering;
- derived EPA/WPA/CPOE/success analytics;
- model/simulation code.

These items are certified in their dependency-ordered roadmap milestones.

---

## 10. Final Local Certification Evidence

Final rerun on `audit/m1-architecture-conformance` after the Ruff-only import correction:

```text
git pull --ff-only
Fast-forward to ff79d7a7ed7f3b27ca5135bf95accf4d74d34fa1

python -m pytest -q
116 passed in 1.17s

python -m ruff check .
All checks passed!

python -m mypy .
Success: no issues found in 66 source files

git status --short
<no output>
```

The full repository—not merely the M1 test file—was validated. This is important because M2-M6 already consume M1 contracts provisionally. The green full-repository gate demonstrates that strengthening the canonical ontology did not knowingly break those existing layers.

---

## 11. Certified Boundary and Next Milestone

```text
M0 — ARCHITECTURE-CERTIFIED
M1 — ARCHITECTURE-CERTIFIED
M2 — PROVISIONALLY IMPLEMENTED / NOT YET CERTIFIED
M3 — PROVISIONALLY IMPLEMENTED / NOT YET CERTIFIED
M4 — PROVISIONALLY IMPLEMENTED / NOT YET CERTIFIED
M5 — PROVISIONALLY IMPLEMENTED / NOT YET CERTIFIED
M6 — PROVISIONALLY IMPLEMENTED / NOT YET CERTIFIED
```

The next formal audit is:

```text
M2 — Persistence & Migration Foundation
Architecture dependencies: F-2, F-3, F-4, F-5
```

M2 certification must evaluate the persistence layer against the now-certified M1 ontology rather than treating the existing schema as authoritative.