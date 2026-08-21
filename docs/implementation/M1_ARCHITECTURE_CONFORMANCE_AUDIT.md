# M1 Architecture-Conformance Audit

**Project:** The Daily Line — Daily NFL  
**Milestone:** M1 — Canonical Domain Contracts  
**Audit date:** 2026-08-21  
**Audit branch:** `audit/m1-architecture-conformance`  
**Governing roadmap:** `docs/implementation/IMPLEMENTATION_ROADMAP_V1.md`  
**Architecture dependencies:** F-1, F-3, F-5  
**Certification status:** **NOT YET CERTIFIED — DOMAIN REMEDIATIONS IMPLEMENTED; LOCAL QUALITY GATE PENDING**

---

## 1. Audit Purpose

M1 defines the football ontology that every later persistence, provider, PIT, normalization, feature, model, and simulation layer depends on.

The audit therefore asks a stricter question than "do domain classes exist?":

> Can the current M1 contracts represent the locked F-1 / F-3 / F-5 football reality without provider coupling, causal leakage, identity ambiguity, or a foreseeable domain-contract rewrite when later planned layers are implemented?

M1 is not certified merely because M2-M6 code already consumes the current classes. Existing later code is provisional and must conform to the certified domain model, not vice versa.

Status vocabulary:

- `SATISFIED` — current contract matches the M1/F architecture.
- `SATISFIED AFTER REMEDIATION` — a material gap was corrected during this audit.
- `DEFERRED BY ARCHITECTURE` — the ontology reserves the concept, but implementation belongs to a later milestone.
- `BLOCKED` — M1 cannot be certified until resolved.

---

## 2. Governing M1 Contract

Roadmap dependencies:

```text
F-1 — NFL Domain Ontology
F-3 — Canonical Identity & Reconciliation
F-5 — Canonical Game / Drive / Play Architecture
```

Roadmap deliverables:

```text
season / phase / week
game identity
team-season identity
player identity
drive identity
play identity
possession
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

Roadmap exit gate:

```text
canonical objects compile/import
enum semantics are tested
pre-play state cannot contain outcome fields by construction
PLAY_EXECUTION naming is enforced
```

Additional M1 obligations are included when F-1/F-3/F-5 define foundational ontology or identity that would otherwise force a later canonical-contract rewrite. Learned state estimators, persistence/revision machinery, provider crosswalk execution, injury inference, and live orchestration remain later-milestone work.

---

## 3. Evidence Reviewed

Architecture / roadmap:

```text
docs/implementation/IMPLEMENTATION_ROADMAP_V1.md
docs/architecture/F00-F04_ARCHITECTURE_FOUNDATION_V1.md
docs/architecture/F05-F09_FOOTBALL_STATE_ARCHITECTURE_V1.md
```

M1 domain implementation:

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

Primary M1 tests:

```text
tests/test_domain_contracts.py
```

Representative downstream tests reviewed:

```text
tests/test_play_normalization.py
tests/test_play_normalization_persistence.py
tests/test_reconciliation_games.py
```

---

## 4. Conformance Matrix

| ID | Requirement | Status | Evidence / remediation |
|---|---|---|---|
| M1-01 | Provider-neutral domain vocabulary | `SATISFIED` | Domain modules contain canonical football concepts, not nflverse field names/provider IDs. |
| M1-02 | Competition → season → phase → week hierarchy | `SATISFIED AFTER REMEDIATION` | Added opaque `CompetitionId`, explicit `Season` and `Week` contracts while retaining `SeasonWeek` compatibility value. |
| M1-03 | Game linked to Core event + competition | `SATISFIED AFTER REMEDIATION` | `Game` now requires `competition_id`; `event_id` remains the opaque Core sporting-event reference and exposes `core_event_id`. |
| M1-04 | Game/result separation | `SATISFIED` | Final score/winner/overtime truth remains outside `Game`; audit tests explicitly prohibit result fields on `Game`. |
| M1-05 | Schedule/rules references | `SATISFIED AFTER REMEDIATION` | `RulesetVersion` retained; optional `schedule_version` added without placing final truth in schedule state. |
| M1-06 | Final football truth supports final timestamp | `SATISFIED AFTER REMEDIATION` | `GameResult.final_at` added as timezone-aware optional truth metadata. |
| M1-07 | Franchise separate from team-season | `SATISFIED` | Existing `Franchise` / `TeamSeason` split retained and tested. |
| M1-08 | Person/player separate from team membership | `SATISFIED AFTER REMEDIATION` | Added explicit time-bounded `RosterStint`; `Player` remains free of team membership. |
| M1-09 | Coaching identity/role can change historically | `SATISFIED AFTER REMEDIATION AT ONTOLOGY LEVEL` | Added time-bounded `CoachingRole` tied to persistent `Person` and `TeamSeason`. Learned coaching state remains M7/F-9. |
| M1-10 | F-3 football-native ID vocabulary | `SATISFIED AFTER REMEDIATION` | Added roster-stint, coach-role, possession-segment, participation, penalty, injury-observation, and depth-chart-snapshot ID types. |
| M1-11 | Provider IDs never canonical | `SATISFIED` | Domain ID types remain provider-independent; provider IDs stay outside domain entities. Crosswalk behavior remains M4. |
| M1-12 | Possession segment distinct from drive | `SATISFIED AFTER REMEDIATION` | Added explicit `PossessionSegment` and distinct `PossessionSegmentId`; retained lightweight `Possession` state compatibility object. |
| M1-13 | Canonical drive ledger contract | `SATISFIED AFTER REMEDIATION` | Added provider-neutral `Drive` with game/segment/team/start/end/result structure. |
| M1-14 | Canonical play ledger identity | `SATISFIED AFTER REMEDIATION` | Added provider-neutral `Play` linking game, sequence, segment, drive, and optional previous play. |
| M1-15 | Period contract | `SATISFIED` | Existing regulation/overtime validation retained. |
| M1-16 | Protected pre-play causal state | `SATISFIED AFTER REMEDIATION` | Existing outcome exclusion retained; added planned segment/play-clock/previous-play/kick/try/two-minute/overtime/personnel/formation/environment references. |
| M1-17 | Pre-play state excludes outcomes/analytics | `SATISFIED` | Structural field test expanded to official/physical yards, first down, completion, TD, INT, sack, EPA/WPA/success. |
| M1-18 | Canonical object named `PLAY_EXECUTION` | `SATISFIED` | `PlayExecution` remains the container; `PLAY_ACTION` only exists as a football design modifier. |
| M1-19 | Primary execution taxonomy matches locked F-5 set | `SATISFIED` | `PlayType` already matched; audit now tests the exact set. |
| M1-20 | Primary play family separate from design mechanics | `SATISFIED` | `PlayExecution.primary_play_type` + modifier set retained. |
| M1-21 | Locked play-design vocabulary representable | `SATISFIED AFTER REMEDIATION` | Added BOOT, NAKED_BOOT, DRAW, READ_OPTION, SPEED_OPTION, DROPBACK, QUICK_GAME, EMPTY while preserving existing modifiers. |
| M1-22 | Invalid modifier combinations fail closed | `SATISFIED AFTER REMEDIATION` | Added designed-QB-run/RUSH constraint and SHOTGUN vs UNDER_CENTER exclusivity; existing RPO/scrimmage constraints retained. |
| M1-23 | Ordered play event stream | `SATISFIED` | `PlayEvent.sequence` required positive; event identity is first-class. |
| M1-24 | Participation first-class | `SATISFIED AFTER REMEDIATION` | Added required `ParticipationId`; player/team/side/role/on-field contract retained. |
| M1-25 | Penalty first-class | `SATISFIED AFTER REMEDIATION` | Added required `PenaltyId`; disposition/team/player/yards/down/enforcement semantics retained. |
| M1-26 | Physical vs official outcome can coexist | `SATISFIED AFTER REMEDIATION` | Added structured `ObservedPhysicalOutcome`; `PlayResult` remains official truth and exposes compatibility accessor for physical yards. |
| M1-27 | Derived analytics not canonical truth | `SATISFIED` | EPA/WPA/success/CPOE are absent from canonical result/state objects. |
| M1-28 | Deterministic provider-independent event-child IDs | `SATISFIED AFTER REMEDIATION` | Added canonical possession-segment/participation/penalty derivation helpers; nflverse normalizer uses penalty + segment helpers. |
| M1-29 | Enum semantics tested | `SATISFIED AFTER REMEDIATION` | Tests now lock exact primary taxonomy, required modifier vocabulary, and invalid combinations. |
| M1-30 | M2-M6 consumers remain source-compatible | `LOCAL VALIDATION PENDING` | M6 normalizer updated for required M1 identifiers/physical-outcome contract; full repository gate still required. |

---

## 5. F-1 Audit

### F-1.1 Core hierarchy

**Before audit:** partial. Season/phase/week existed only as one compact value; competition was absent; drive/play had IDs but no ledger objects; possession segment was not explicit.

**After remediation:** the domain can represent:

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

The existing `SeasonWeek` and lightweight `Possession` objects remain for compatibility, but the architecture-native concepts are now explicit rather than conflated.

### F-1.2 Game separate from result

**Status:** satisfied. The audit strengthens tests so realized overtime/final outcome cannot migrate into `Game` accidentally.

### F-1.3 Franchise vs team-season

**Status:** satisfied.

### F-1.4 Person vs player stint

**Before audit:** `Person` and `Player` were separate and `Player` correctly omitted team membership, but the architecture's explicit roster-stint relationship did not exist.

**After remediation:** `RosterStint` represents time-bounded player/team-season membership without changing persistent person/player identity.

### F-1.5 / F-1.6 Player and unit state

**Status:** `DEFERRED BY ARCHITECTURE` to M7 (F-7/F-8). M1 provides identity/football-event ontology only; it does not invent learned state estimators.

### F-1.7 Coaching and scheme

M1 now provides structured person/team/role assignment through `CoachingRole`. Empirical coaching/scheme state and policy estimation remain F-9/M7 work.

### F-1.8 Injury report vs injury truth

**Status:** `DEFERRED BY ARCHITECTURE`. M1 reserves injury-observation identity; observation/state semantics are certified in later injury/provider/state milestones.

### F-1.9 Depth chart vs actual participation

**Status:** architecture distinction preserved. M1 has play `Participation` plus reserved depth-chart snapshot identity; provider/persistence semantics remain later work.

---

## 6. F-3 Audit

M1 is responsible for canonical identity vocabulary and provider independence, not the full M4 reconciliation engine.

### Provider IDs as crosswalks

**Status:** satisfied. No provider ID appears as a canonical domain entity identity.

### Football-native identities

The pre-audit ID module omitted several F-3 identities that would require later API changes. M1 now exposes foundational types for:

```text
franchise
team-season
player
roster stint
coach role
NFL game
possession segment
drive
play
play event
participation
injury observation
depth-chart snapshot
penalty
```

Generic `CompetitionId`, `EventId`, and `VenueId` are treated as opaque references to concepts ultimately owned by Daily-Data-Core rather than provider-derived NFL identities.

### Crosswalk/reconciliation decisions

Actual external-ID crosswalk persistence, confidence, ambiguity, source evidence, and revision history remain M4. M1 does not duplicate that implementation.

---

## 7. F-5 Audit

### Hierarchy and transition model

The strengthened contracts can represent the canonical ledger and retain the existing causal structure:

```text
PLAY_STATE_BEFORE
+ PLAY_EXECUTION
+ PARTICIPATION / EVENTS
-> PLAY_RESULT
-> PLAY_STATE_AFTER
```

### Game object

M1 now carries competition, Core-event link, season/week, ruleset, teams, venue, kickoff/status, neutral-site, and optional schedule-version reference while keeping realized game truth in `GameResult`.

### Pre-play causal boundary

The object can now preserve more of the planned pre-snap context while retaining structural exclusion of outcome-derived features.

### Execution taxonomy

The primary type set exactly matches locked F-5. `PLAY_ACTION` remains a modifier. The modifier vocabulary now covers every explicitly listed locked V1 mechanic.

### Events, participation, penalties

Each is a separate canonical dimension. Participation and penalty identities are now explicit so multiple same-play records cannot rely only on accidental composite uniqueness.

### Physical vs official outcome

The pre-audit contract had only `physical_yards_gained` alongside official fields. That was insufficient as a durable representation of F-5.13. The new `ObservedPhysicalOutcome` permits a separately structured physical event outcome while `PlayResult` remains official truth.

### Revisions

Append-only play/provider revisions are a persistence/reconciliation responsibility and remain M2/M4/M6 audit scope. M1 does not implement revision storage in domain dataclasses.

---

## 8. Findings and Remediations

### F-01 — competition absent from canonical game hierarchy

**Severity:** HIGH — REMEDIATED

Added `CompetitionId`, `Season`, `Week`, and `Game.competition_id`.

### F-02 — possession segment / drive / play ledger under-modeled

**Severity:** HIGH — REMEDIATED

Added explicit `PossessionSegment`, `Drive`, and `Play` contracts.

### F-03 — roster stint missing despite identity separation rule

**Severity:** HIGH — REMEDIATED

Added `RosterStint`; team membership remains outside `Player`.

### F-04 — participation/penalty records lacked canonical IDs

**Severity:** HIGH — REMEDIATED

Added required `ParticipationId` / `PenaltyId` and deterministic child-ID helpers.

### F-05 — F-5 play-design vocabulary incomplete

**Severity:** MEDIUM — REMEDIATED

Expanded `PlayDesignModifier` to include every explicitly listed locked V1 mechanic.

### F-06 — physical outcome not structurally separable from official outcome

**Severity:** HIGH — REMEDIATED

Added `ObservedPhysicalOutcome`; official and physical values can coexist without overloading one result field family.

### F-07 — protected pre-play contract omitted planned causal context

**Severity:** MEDIUM — REMEDIATED

Added optional segment, play clock, previous play, situational, personnel/formation, and environment-reference fields without adding outcomes.

### F-08 — M1 tests did not lock the architecture vocabulary

**Severity:** MEDIUM — REMEDIATED

Expanded tests to verify hierarchy/identity separation, exact primary taxonomy, required modifier vocabulary, first-class child IDs, invalid modifier combinations, and physical/official separation.

### F-09 — coaching role existed only as future prose

**Severity:** MEDIUM — REMEDIATED AT ONTOLOGY LEVEL

Added time-bounded `CoachingRole`. Learned coaching/scheme state remains deferred.

---

## 9. Explicit Deferrals — Not M1 Defects

The following are intentionally **not** implemented as part of M1 certification:

- player-state estimation;
- unit-state estimation;
- coaching/scheme statistical state;
- injury availability/effectiveness inference;
- depth-chart acquisition/snapshot persistence;
- provider capability/acquisition logic;
- external-ID crosswalk persistence/reconciliation decisions;
- append-only play observation/revision storage;
- drive/play provider normalization coverage;
- PIT selection/reconstruction;
- feature engineering;
- derived EPA/WPA/CPOE/success analytics;
- model/simulation code.

Those are certified in their roadmap milestones. M1 only ensures their future implementation can build on a correct canonical football ontology.

---

## 10. Required Local Certification Gate

After switching to the M1 audit branch, run:

```powershell
git fetch origin
git switch audit/m1-architecture-conformance
git pull --ff-only

python -m pytest -q
python -m ruff check .
python -m mypy .

git status --short
```

Certification conditions:

1. all repository tests pass;
2. Ruff passes;
3. strict mypy passes;
4. no unintended local changes are present;
5. any failure caused by the strengthened M1 contract is corrected rather than weakening the architecture to preserve a provisional later layer.

If the full gate passes, update this document to `M1 — ARCHITECTURE-CERTIFIED`, record the exact evidence in the durable checkpoint, merge the branch, and begin M2 certification against F-2/F-3/F-4/F-5.

---

## 11. Current Decision

```text
M1 ARCHITECTURE-CONFORMANCE AUDIT: COMPLETE
M1 DOMAIN REMEDIATION: IMPLEMENTED
M1 LOCAL QUALITY GATE: PENDING
M1 ARCHITECTURE CERTIFICATION: WITHHELD UNTIL LOCAL GATE PASSES
```
