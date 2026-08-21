# Daily NFL Penalty Event & Discipline Architecture V1

**Status:** Governing extension to F-5 / F-6 / F-13  
**Scope:** Penalty-event truth, partial-event retention, discipline state, and future penalty-derived features  
**Depends on:** `F05-F09_FOOTBALL_STATE_ARCHITECTURE_V1.md`, `F10-F14_CONTEXT_FEATURE_TARGET_ARCHITECTURE_V1.md`

## Purpose

F-5 already establishes two governing rules:

1. penalties are first-class football events; and
2. physical outcome and official outcome must remain separable when evidence permits.

This document makes those rules operational for nflverse `no_play` rows and defines how penalty information should feed future team, player, unit, coaching, feature, simulation, and world-model layers.

The governing rule is:

> **Failure to reconstruct a complete `PLAY_STATE_BEFORE` must never imply that a valid penalty fact is discarded.**

Missing state and missing event truth are different conditions.

---

# 1. Canonical retention hierarchy

Every provider PBP row is assigned to the highest-fidelity representation that can be supported without guessing.

```text
RAW PROVIDER ROW
      │
      ├── complete causal state available
      │       ↓
      │   FULL CANONICAL PLAY
      │
      ├── complete state unavailable, but penalty/event facts available
      │       ↓
      │   PARTIAL CANONICAL EVENT / PENALTY OBSERVATION
      │
      └── no supportable football fact beyond provenance
              ↓
          RAW EVIDENCE ONLY
```

This hierarchy is intentionally fail-closed. It preserves real football facts while refusing to fabricate missing state.

## 1.1 Full canonical play

When supportable, retain the normal F-5 chain:

```text
PLAY_STATE_BEFORE
    ↓
PLAY_EXECUTION
    ↓
EVENTS / PENALTIES / PARTICIPATION
    ↓
PHYSICAL OUTCOME where supportable
    ↓
OFFICIAL RESULT
    ↓
PLAY_STATE_AFTER
```

## 1.2 Partial canonical penalty/event

When a row contains a defensible penalty fact but lacks enough evidence for a complete `PLAY_STATE_BEFORE`, preserve the event with all supportable fields and explicit unknowns.

A partial event may retain:

```text
game_id
provider_play_id
provider_drive_id if available
provider provenance / raw evidence ID
provider revision
period if available
clock if available

penalized team
penalized player if available
penalty type
accepted / declined / offsetting
penalty yards
automatic first down
loss of down
nullifies play
enforcement spot if available
raw description / structured provider fields
```

It must **not** invent:

```text
pre-play score
field position
down/distance
possession
physical yards
post-play state
EPA / WPA
```

when the evidence does not support those values.

---

# 2. Penalty fact model

Penalty truth should not be reduced to a boolean.

The canonical penalty fact should preserve, where available:

```text
PENALTY_EVENT

penalty_observation_id
play_id or partial-event identity

game_id
team_season_id
player_id_if_known

penalty_type
disposition:
    ACCEPTED
    DECLINED
    OFFSETTING

yards
automatic_first_down
loss_of_down
nullifies_play
enforcement_spot

provider_id
provider_play_id
raw_evidence_id
provider_revision

observed_at
ingested_at
available_at
availability_method
availability_confidence
```

Provider corrections remain append-only observations rather than destructive updates.

## 2.1 Penalized team and beneficiary team

Two analytical perspectives must be retained:

```text
PENALTY COST
    → team committing the infraction

PENALTY BENEFIT
    → opponent receiving the enforcement/drive benefit
```

The beneficiary may often be derivable as the opposing team in an accepted two-team NFL game, but declined and offsetting penalties must not be treated as equivalent to accepted penalties.

Future feature construction should distinguish:

- penalties committed;
- accepted penalties committed;
- penalty yards conceded;
- automatic first downs conceded;
- drive extensions conceded;
- penalties drawn / benefited from;
- enforcement yards received;
- automatic first downs received;
- drive extensions received.

---

# 3. `no_play` semantics

`play_type == "no_play"` is not equivalent to "no information."

Many such rows represent penalties that nullified the official play result. Therefore:

> **`no_play` means the official play result is nullified; it does not mean the penalty event or physical football execution never happened.**

The system should preserve the penalty fact even if full causal state is unavailable.

## 3.1 Physical outcome vs official outcome

Where evidence permits:

```text
PHYSICAL EXECUTION
    e.g. runner gains 21 yards

OFFICIAL OUTCOME
    e.g. offensive holding, gain nullified
```

These are separate signals.

The physical execution may inform player/unit performance while the official outcome informs drive result, team discipline, and penalty cost.

Base nflverse PBP does not always preserve the physical yards of a penalty-nullified play. The system must therefore leave `physical_yards_gained = UNKNOWN` unless a defensible source provides it.

Do not backfill physical yards from description text or incompatible score/state fields without an explicit, versioned parser and validation evidence.

---

# 4. Discipline as a football state

Penalty behavior is not merely a box-score statistic. It is a temporal component of team, player, unit, and coaching state.

A future discipline state may be represented conceptually as:

```text
DISCIPLINE_STATE(entity, timestamp, information_set)
```

and may exist at:

- team level;
- offense / defense / special-teams unit level;
- position-group level;
- player level;
- coaching/scheme level.

This state must be point-in-time safe and constructed only from penalty observations available before the prediction timestamp.

---

# 5. Initial penalty feature families

The feature registry should eventually support the following families with explicit lookbacks, denominators, PIT rules, and missingness semantics.

## 5.1 Volume and rate

```text
penalties_per_game
accepted_penalties_per_game
penalties_per_snap
penalties_per_drive
penalty_yards_per_game
penalty_yards_per_snap
penalty_yards_per_drive
```

Raw counts should not be the only representation; rates normalize for pace and opportunity.

## 5.2 Side-of-ball / unit decomposition

```text
offensive_penalty_rate
defensive_penalty_rate
special_teams_penalty_rate

OL_penalty_rate
secondary_penalty_rate
special_teams_unit_penalty_rate
```

Position/unit attribution depends on reliable participation and player identity and may be introduced progressively.

## 5.3 Penalty type decomposition

Examples include:

```text
false_start_rate
offensive_holding_rate
defensive_holding_rate
DPI_rate
illegal_contact_rate
offsides_rate
neutral_zone_infraction_rate
roughing_rate
personal_foul_rate
special_teams_penalty_type_rates
```

Penalty vocabularies must be normalized and versioned rather than compared as raw provider strings indefinitely.

## 5.4 First-down and drive effects

```text
automatic_first_downs_conceded
first_downs_received_by_penalty
drive_extending_penalties_conceded
drive_extending_penalties_received
third_down_drive_extensions_conceded
fourth_down_drive_extensions_conceded
drive_killing_offensive_penalties
```

A defensive holding on 3rd-and-long should not be treated as equivalent to a low-leverage five-yard penalty simply because the enforcement yards match.

## 5.5 Nullified-play effects

```text
nullified_successful_plays
nullified_first_downs
nullified_explosive_plays
nullified_touchdowns
nullified_offensive_yards_where_physical_outcome_is_known
```

These features separate execution quality from procedural/discipline failure.

## 5.6 Situation / leverage decomposition

When causal state is available:

```text
red_zone_penalty_rate
goal_line_penalty_rate
third_down_penalty_rate
fourth_down_penalty_rate
two_minute_penalty_rate
one_score_game_penalty_rate
late_game_penalty_rate
high_leverage_penalty_rate
```

When causal state is unavailable, the observation remains usable for non-contextual penalty features but must not be assigned fabricated situational context.

## 5.7 Player and repeat-offender features

When player identity is reliable:

```text
player_penalties_per_snap
player_penalty_yards_per_snap
player_penalty_type_distribution
repeat_penalty_rate
recent_penalty_trend
```

These signals should be regularized for sample size and role opportunity.

---

# 6. Advanced penalty impact metrics

After reliable state reconstruction and baseline EPA/WPA models exist, derive impact rather than relying only on enforcement yards.

Candidate metrics:

```text
penalty_EPA_conceded
penalty_EPA_received
penalty_WPA_conceded
penalty_WPA_received

leverage_weighted_penalty_rate
expected_drive_extension_cost
expected_points_lost_to_penalties
expected_points_gained_from_opponent_penalties
red_zone_penalty_EPA
third_down_penalty_EPA
```

These are **derived analytics**, not football truth, and must remain versioned separately from the underlying penalty observations.

A five-yard penalty that creates an automatic first down can carry much greater value than a five-yard penalty on an otherwise low-leverage play.

---

# 7. Team modeling interpretation

Penalty modeling should distinguish at least three latent concepts:

```text
DISCIPLINE
    tendency to commit avoidable infractions

AGGRESSIVENESS / STYLE
    scheme or technique choices that may increase certain penalty risk

CONTEXTUAL PENALTY COST
    actual game-state consequence of the infractions
```

Do not assume a high penalty count always means the same underlying team weakness.

Examples:

- a secondary may incur more DPI while playing aggressive man coverage;
- an offensive line may incur false starts under communication/travel/noise stress;
- a pass rush may generate offsides or roughing penalties from aggressive get-off;
- special-teams penalties may indicate unit-specific discipline rather than overall team discipline.

The model should eventually learn which penalty families are persistent, opponent-dependent, personnel-dependent, coaching-dependent, or largely noisy.

---

# 8. Opponent / beneficiary modeling

A team may systematically benefit from opponent penalties because of style or matchup pressure.

Candidate future features include:

```text
opponent_penalties_drawn_per_game
opponent_penalty_yards_received_per_game
defensive_pass_interference_drawn_rate
automatic_first_downs_received_rate
drive_extensions_received_rate
```

These should not be naively interpreted as pure "luck." Some may contain repeatable offensive or defensive style signals, while others may regress heavily toward league average. Their predictive persistence must be tested empirically.

---

# 9. Temporal / PIT requirements

Every penalty-derived pregame feature must obey the same historical PIT law as all other Daily NFL features:

```text
available_at <= prediction_time < kickoff
```

For a future game, no penalty from that game itself may enter the pregame state.

Historical provider corrections may only enter a reconstructed snapshot when their defensible `available_at` permits it.

Rolling/decay features must specify exact semantics rather than ambiguous labels such as `recent_penalties`.

Examples of explicit contracts:

```text
accepted_penalties_per_100_snaps_last_8_games
penalty_yards_per_drive_ewma_half_life_4_games
third_down_drive_extension_penalty_rate_season_to_date
```

---

# 10. Persistence implications

The existing persistence design already supports first-class `penalty_observations` linked to a canonical play and allows player identity to be optional.

For partial penalty-event retention, implementation should prefer the smallest schema change necessary.

A recommended M6B approach is:

1. create/retain a canonical play/event shell for the provider row using deterministic game-relative ordering;
2. leave unavailable drive/possession/state fields null where schema permits;
3. persist the structured penalty observation with provenance;
4. persist an explicit partial-event contract/version rather than pretending it is a full normalized play;
5. preserve the raw provider row through immutable raw evidence;
6. keep duplicate/revision handling append-only and idempotent.

A dedicated schema migration is required only if existing nullable fields/observation contracts cannot represent this safely.

Beneficiary-team identity may initially be derived from game participants plus penalty disposition; add a stored beneficiary field only if later evidence shows that derivation is insufficient or ambiguous.

---

# 11. Provider coverage limitations

Provider structured penalty fields may not capture every nuance of multi-penalty plays, enforcement order, or all physical outcomes.

Therefore:

- preserve raw evidence;
- preserve structured provider fields exactly as extracted;
- never silently collapse multiple known penalties into one canonical fact;
- if provider data exposes only one structured penalty for a complex row, mark coverage limitations rather than inventing additional structured facts;
- later providers or validated parsers may enrich the same canonical event through new append-only observations.

---

# 12. Validation requirements

Penalty ingestion is not complete merely because rows parse.

Required validation includes:

- accepted / declined / offsetting semantics;
- penalty yards;
- automatic first downs;
- loss of down when available;
- nullified plays;
- player/team identity where available;
- duplicate provider revisions;
- multiple penalties on one play where provider evidence supports them;
- special-teams penalties;
- offensive vs defensive penalties;
- penalty-only rows lacking full pre-play state;
- overtime and late-game penalties;
- exact idempotency on repeated ingestion.

Coverage reports should distinguish:

```text
full canonical plays
partial penalty events retained
non-penalty partial events retained
raw-only administrative rows
meaningful football facts lost
normalization errors
```

The target is:

```text
meaningful penalty facts lost = 0
```

not necessarily:

```text
100% of provider rows become full canonical plays
```

---

# 13. Relationship to future milestones

## M6

M6 owns correct extraction, canonical event identity, partial penalty retention, and official-vs-physical separation.

## M7

M7 may introduce temporal team/player/unit/coaching discipline state from retained observations.

## M9

M9 registers exact penalty feature contracts, lookbacks, denominators, missingness, and PIT semantics.

## M11+

Baseline and advanced models determine which penalty features materially improve out-of-sample prediction and calibration.

## M12 / M17 / M19

Drive/play simulation and future world models may model penalty hazard conditional on team, player, unit, scheme, down/distance, field position, game state, officials if reliable data is available, and other context.

Penalty generation should only be simulated once historical penalty truth and context are validated sufficiently to support it.

---

# 14. Governing summary

The Daily NFL penalty architecture follows these laws:

1. **Penalties are first-class football events.**
2. **A missing full play state must not erase a valid penalty fact.**
3. **`no_play` does not mean `no information`.**
4. **Physical execution and official outcome remain separate when evidence permits.**
5. **Offending-team cost and beneficiary-team value are both analytically relevant.**
6. **Situational/leverage features require real causal state; they must never be fabricated.**
7. **Penalty observations remain PIT-safe, versioned, and provenance-backed.**
8. **Penalty impact analytics such as EPA/WPA are derived and versioned separately from truth.**
9. **Future models should test persistence and predictive value rather than assume all penalty tendencies are stable.**
10. **The historical ingestion target is zero lost meaningful penalty facts, not forced full-state normalization of every raw row.**
