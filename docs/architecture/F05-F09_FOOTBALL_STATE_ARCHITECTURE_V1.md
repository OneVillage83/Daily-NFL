# Daily NFL Architecture — F-5 through F-9

**Version:** 1.0  
**Status:** Locked V1 architecture foundation  
**Repository:** `OneVillage83/Daily-NFL`  
**Depends on:** `F00-F04_ARCHITECTURE_FOUNDATION_V1.md`

## Purpose

F-0 through F-4 established the scientific charter, domain ontology, provider architecture, canonical identity system, historical point-in-time rules, and continuous pregame monitoring requirements for Daily NFL.

F-5 through F-9 define the football-native state representation that future feature engineering, state estimation, simulation, and prediction models will consume.

The governing principle is:

> **The canonical schema must represent football itself, not mirror the column layout of nflverse, ESPN, the NFL, or any future provider.**

Provider observations populate the canonical model. They do not define it.

A second governing principle carries forward from F-4:

> **Every pregame state is evaluated as of an explicit prediction timestamp. Continuous monitoring remains active through kickoff. New information may update later prediction snapshots if it was legitimately available before that snapshot and before kickoff. Earlier snapshots remain immutable.**

---

# F-5 — Canonical Game / Drive / Play Architecture

F-5 defines the football event ledger: what occurred on the field, in what sequence, under what state, with which participants, and with what official and physical consequences.

## F-5.1 Canonical hierarchy

```text
GAME
 │
 ├── PERIOD
 │
 ├── POSSESSION SEGMENT
 │     │
 │     └── DRIVE
 │           │
 │           └── PLAY
 │                 │
 │                 ├── PLAY STATE BEFORE
 │                 ├── PARTICIPATION
 │                 ├── PLAY EXECUTION
 │                 ├── EVENTS
 │                 ├── RESULT
 │                 └── PLAY STATE AFTER
 │
 └── GAME RESULT
```

`POSSESSION SEGMENT` and `DRIVE` remain distinguishable because turnovers, returns, safeties, penalties, untimed downs, special-teams transitions, and other edge cases can make a single generic possession object ambiguous.

## F-5.2 State-transition representation

Every football play is fundamentally represented as:

```text
STATE(t)
   +
EXECUTION(t)
   +
PARTICIPANTS(t)
   +
ENVIRONMENT(t)
       ↓
OUTCOME(t)
       ↓
STATE(t+1)
```

Example:

```text
Before Play
KC ball
2nd & 7
KC 42
11:43 Q2
KC +3
11 personnel
shotgun
3 WR / 1 RB / 1 TE

        ↓

Execution
play-action pass

        ↓

Outcome
completion
12 yards
first down

        ↓

Next State
KC ball
1st & 10
BUF 46
11:05 Q2
KC +3
```

This state-transition structure is intentionally compatible with future sequence models and football world-model development.

## F-5.3 Canonical game object

Approximate canonical fields:

```text
NFL_GAME

game_id
core_event_id

competition_id
season
season_phase
week

ruleset_version

home_team_season_id
away_team_season_id

venue_id
neutral_site

scheduled_kickoff
actual_kickoff

game_status

overtime_possible
overtime_occurred

schedule_version
```

Schedule state and final result remain separate objects. A rescheduled kickoff changes the schedule observation; it does not create a new football event.

## F-5.4 Ruleset versioning

NFL rules change over time. The simulation and feature layers must know which football rules governed the game.

Examples include changes to:

```text
kickoffs
touchbacks
onside kicks
overtime
extra points
clock administration
roster/game-day rules
```

Therefore each game carries a `ruleset_version` or equivalent versioned rules reference.

## F-5.5 Play state before

`PLAY_STATE_BEFORE` is a protected causal-state object.

Approximate fields:

```text
PLAY_STATE_BEFORE

play_id

period
game_clock
play_clock_if_available

possession_team_id
defensive_team_id

down
distance

yardline
yards_to_goal

home_score
away_score

timeouts_home
timeouts_away

drive_id
possession_segment_id

kickoff_state
try_state

two_minute_state
overtime_state

previous_play_id
```

Contextual observations may attach when available:

```text
offensive_personnel
defensive_personnel

offensive_formation
defensive_front
coverage_shell_if_observed

motion
shift
shotgun
no_huddle

weather_snapshot_id
surface_state_id
```

Historical coverage will vary. Missing information is preferable to fabricated information.

## F-5.6 Protected causal boundary

`PLAY_STATE_BEFORE` must never contain outcome-derived information such as:

```text
yards_gained
completion_result
touchdown
interception
sack
EPA
WPA
success_flag
first_down_result
```

Those belong to result or derived-analytics layers.

This boundary prevents future-information contamination when training models that predict what happens next.

## F-5.7 Play execution classification

### Naming correction

The canonical object is **not** called `PLAY_ACTION`.

That name is prohibited because **play action** is itself a real football concept and play-design modifier. Calling the schema object `PLAY_ACTION` would create ambiguity between:

```text
PLAY_ACTION object
```

and:

```text
play-action pass
play-action boot
other play-action concepts
```

The governing object is therefore:

```text
PLAY_EXECUTION
```

with a primary type plus design modifiers.

### Primary execution type

```text
PLAY_EXECUTION

primary_play_type:
    PASS
    RUSH
    SCRAMBLE
    SACK
    KNEEL
    SPIKE
    PUNT
    FIELD_GOAL
    KICKOFF
    EXTRA_POINT
    TWO_POINT
    PENALTY_ONLY
    TIMEOUT
    ADMINISTRATIVE
    OTHER
```

`primary_play_type` describes the dominant execution/result family. It is not intended to encode the complete concept of the play.

### Play-design modifiers

A separate modifier layer captures actual football concepts such as:

```text
PLAY_ACTION
RPO
SCREEN
BOOT
NAKED_BOOT
DRAW
READ_OPTION
SPEED_OPTION
DESIGNED_QB_RUN
DROPBACK
QUICK_GAME
EMPTY
MOTION
SHIFT
UNDER_CENTER
SHOTGUN
```

The exact vocabulary can expand as charting/tracking coverage improves.

This allows canonical composite concepts such as:

```text
PLAY_ACTION_PASS
PLAY_ACTION_BOOT_PASS
RPO_PASS
RPO_RUN
SCREEN_PASS
DESIGNED_QB_RUN
DROPBACK_PASS
```

If future charting legitimately identifies a run concept that should carry a play-action-like modifier, the schema can represent that without confusing the top-level object name.

The important rule is:

> **Primary play family and play-design mechanics are separate dimensions.**

This prevents the taxonomy from becoming mutually exclusive when football concepts overlap.

### Additional execution descriptors

Possible fields include:

```text
pass_depth_intent
pass_direction

run_direction
run_gap
run_concept

dropback_type

play_action_modifier
rpo_modifier
screen_modifier

shotgun
under_center

motion_type
shift_type

punt_type
kick_type
```

## F-5.8 Play event stream

A play can contain multiple meaningful football events, so the canonical architecture supports an ordered event stream.

```text
PLAY
  ↓
EVENT 1
EVENT 2
EVENT 3
...
```

Example passing sequence:

```text
SNAP
DROPBACK
PRESSURE
THROW
TARGET
CATCH
TACKLE
```

Another example:

```text
SNAP
DROPBACK
THROW
INTERCEPTION
RETURN
FUMBLE
RECOVERY
```

Long-term, this permits modeling transitions such as:

```text
play state
 ↓
snap
 ↓
protection
 ↓
pressure
 ↓
throw decision
 ↓
ball flight
 ↓
catch
 ↓
YAC
```

rather than only `play → result`.

## F-5.9 Play participation

Each play supports play-level participation:

```text
PLAY_PARTICIPATION

play_id
player_id
team_id

side_of_ball
role

on_field
```

Observed or inferred responsibilities may include:

```text
passer
rusher
target
receiver

pass_blocker
route_runner

pass_rusher
coverage_defender
tackler

kicker
punter
returner
```

Provider participation data is normalized into the canonical participation model; provider-specific IDs or field names do not define the internal schema.

## F-5.10 Play result

Official play results are stored separately from the pre-play state.

```text
PLAY_RESULT

yards_gained

first_down
touchdown
safety

completion
incompletion
interception

sack
fumble
fumble_lost

penalty
penalty_yards

kick_result

possession_changed
score_change

drive_continues
```

## F-5.11 Derived analytics are not football truth

Metrics such as EPA or WPA are model-derived measurements and therefore belong in a distinct layer:

```text
PLAY_ANALYTICS

EPA
WPA
success_probability
success_flag
expected_yards
completion_probability
CPOE
air_yards
YAC
...
```

The underlying football event must remain usable if the analytical model is later replaced or improved.

## F-5.12 Penalties are first-class events

Do not reduce penalties to `penalty = true`.

```text
PLAY_PENALTY

penalty_id
play_id

team_id
player_id_if_known

penalty_type

accepted
declined
offsetting

yards

automatic_first_down
loss_of_down

nullifies_play

enforcement_spot
```

This supports separation between what physically occurred and what officially counted.

## F-5.13 Physical outcome vs official outcome

Where evidence permits, preserve both:

```text
OBSERVED_PHYSICAL_OUTCOME
```

and

```text
OFFICIAL_SCORING_OUTCOME
```

This is especially valuable for:

```text
penalty-nullified plays
replays
reviews
accepted penalties
offsetting penalties
```

A physically informative play should not disappear from performance analysis solely because its official statistical result was nullified.

## F-5.14 Corrections and revisions

Provider corrections never silently overwrite historical evidence.

```text
play_id
   ↓
play_observation_v1
play_observation_v2
play_observation_v3
```

Canonical reconciliation determines the current accepted interpretation while preserving all prior observations and provenance.

## F-5.15 Drive object

Approximate drive structure:

```text
DRIVE

drive_id
game_id

offense_team_id
defense_team_id

start_play_id
end_play_id

start_period
end_period

start_clock
end_clock

start_field_position
end_field_position

play_count
first_downs

result
points
turnover
```

Derived drive analytics may include:

```text
drive_success_rate
drive_EPA
points_per_drive
yards_per_drive
available_yards_pct
explosive_play_count
```

## F-5.16 Pregame current-game barrier

For a pregame prediction of Game G at prediction time `T`, where `T < kickoff`, features may use completed play history that was already available at `T`.

No play from Game G itself may enter that pregame feature snapshot.

Once kickoff occurs, current-game plays belong to a future **live/in-game model** that may reuse the same canonical event schema under a different information boundary.

## F-5.17 F-5 data flow

```text
RAW PROVIDER PLAY
        ↓
NORMALIZER
        ↓
CANONICAL PLAY
        │
        ├── State Before
        ├── Participation
        ├── Play Execution
        ├── Events
        ├── Result
        └── State After
        ↓
DERIVED ANALYTICS
        ↓
HISTORICAL PLAYER / UNIT / TEAM / COACHING EVIDENCE
```

**F-5 Status: LOCKED V1**

---

# F-6 — Team State Engine

The Team State Engine estimates the latent football state of a team at a particular time.

The governing question is not:

> What are this team's season statistics?

It is:

> What is this team's estimated football state at timestamp T, given the information legitimately available at T?

## F-6.1 Team state is temporal

Represent team state as:

```text
TEAM_STATE(team_id, timestamp, information_set)
```

rather than a timeless team rating.

A team's state can materially change from Week 1 to Week 4 to Week 9 to Week 17 even though franchise identity remains unchanged.

## F-6.2 Team-state decomposition

```text
TEAM STATE
│
├── Offensive State
├── Defensive State
├── Special Teams State
├── Roster Availability State
├── Style State
├── Coaching State
├── Form State
├── Environment Adaptation State
└── Uncertainty
```

A second critical split is:

```text
INTRINSIC TEAM STATE
        +
GAME CONTEXT
        ↓
MATCHUP STATE
```

Team quality must not be contaminated by opponent- or game-specific conditions.

## F-6.3 Offensive state

Possible latent dimensions:

```text
overall offensive strength

passing
rushing

early-down efficiency
late-down efficiency

dropback efficiency
designed-run efficiency

explosive-play generation
negative-play avoidance

turnover tendency

red-zone performance
goal-line performance
short-yardage performance

third-down behavior
fourth-down behavior

pace
neutral-situation tendencies
```

These should evolve toward distributions or learned state parameters rather than static rolling averages.

## F-6.4 Defensive state

```text
overall defensive strength

pass defense
rush defense

pressure generation
pressure conversion
sack conversion

explosive-play prevention
turnover creation

early-down defense
third-down defense

red-zone defense
goal-line defense
short-yardage defense
```

F-8 will represent the functional units that generate much of this team-level behavior.

## F-6.5 Special teams state

Special teams remain explicit:

```text
field goals
extra points

punting
punt coverage

kickoffs
kick coverage

punt returns
kick returns

blocked kicks
```

Field-position effects compound across a football game and must not be buried in a generic team rating.

## F-6.6 Quality and style are distinct

A team may run frequently without being good at running.

Therefore separate:

```text
QUALITY / EFFECTIVENESS FEATURES
```

from:

```text
TENDENCY / STYLE FEATURES
```

For example:

```text
neutral pass rate = style
EPA/dropback = performance
```

This distinction is necessary for valid matchup modeling.

## F-6.7 Opponent adjustment

Raw performance must be conditioned on opponent strength and game context.

Conceptually:

```text
observed performance
        ↓
opponent adjustment
        ↓
game-context adjustment
        ↓
latent underlying strength
```

The long-term goal is joint estimation rather than one-off manual adjustments.

## F-6.8 Temporal weighting and state evolution

The architecture must not hard-code one universal window such as `last 3 games` or `season average`.

Different signals evolve at different rates:

```text
QB efficiency           faster
OL composition          immediate / fast
injury availability     immediate
coaching identity       slow
team talent baseline    slow
```

A simple conceptual state update is:

```text
S_t = alpha_t * O_t + (1 - alpha_t) * S_(t-1)
```

Advanced models may learn nonlinear state transitions and feature-specific decay rates.

## F-6.9 Early-season priors

Week 1 and early-season estimates require priors such as:

```text
prior-season state
returning personnel
QB continuity
coaching continuity
roster turnover
draft
free agency
age curves
preseason information
```

Offseason uncertainty should be explicit. As current-season evidence accumulates, prior influence should decline.

## F-6.10 Immutable team-state snapshot

```text
TEAM_STATE_SNAPSHOT

team_state_id
team_season_id

as_of
feature_contract

offense_state
defense_state
special_teams_state

style_state

roster_availability_state_id
coaching_state_id

uncertainty

input_observation_ids
model_version
```

Every prediction references exact team-state snapshots.

## F-6.11 Continuous state-change triggers

Team/matchup state may be recomputed when pregame monitoring detects meaningful new information, including:

```text
injury status changes
player ruled inactive
player activated
depth chart changes
starter changes
trade or roster transaction
coaching information changes
material weather update
material market update
```

However, weather and market information do not alter **intrinsic** team state. They alter game context and therefore matchup/prediction state.

## F-6.12 Team-state output

```text
Team A Intrinsic State
        +
Team B Intrinsic State
        +
Game Context
        ↓
MATCHUP ENGINE
```

**F-6 Status: LOCKED V1**

---

# F-7 — Player State Engine

The Player State Engine models a player as an evolving latent system rather than a row of season statistics.

## F-7.1 Persistent talent vs current state

Conceptually:

```text
PLAYER TALENT
      +
CURRENT FORM
      +
HEALTH
      +
ROLE
      +
MATCHUP
      ↓
EXPECTED CONTRIBUTION
```

A player's current expected contribution is conditional on far more than season average performance.

## F-7.2 Generic player-state dimensions

```text
PLAYER_STATE

player_id
as_of

team_season_id
position

talent_baseline
current_performance

usage
role

health
availability_probability

workload
fatigue

recent_form

uncertainty
```

Position-specific state models extend this generic contract.

## F-7.3 Position-specific state models

Do not force all positions into one universal player rating.

Planned families include:

```text
QB STATE
RB STATE
WR STATE
TE STATE
OT STATE
OG STATE
C STATE

EDGE STATE
DT STATE
LB STATE
CB STATE
S STATE

K STATE
P STATE
RETURNER STATE
```

Each position contributes to football through different mechanics and therefore requires different latent variables.

## F-7.4 Quarterback state

Quarterbacks warrant especially rich representation.

Possible QB dimensions:

```text
baseline passing talent
decision quality
accuracy
pressure response
sack avoidance
scramble ability
designed-run value
explosive-play generation
turnover propensity
short/intermediate/deep profile
play-action performance
RPO performance
timing
current health
mobility state
uncertainty
```

Matchup interactions eventually include relationships such as:

```text
QB pressure sensitivity
        ×
opponent pass rush
```

and:

```text
QB deep passing profile
        ×
opponent deep coverage
```

rather than merely `QB rating vs defense rating`.

## F-7.5 Health and availability are probabilistic

Game-day information may legitimately arrive close to kickoff.

Before status is known:

```text
P(active) = x
```

After confirmed inactive/active information arrives before kickoff:

```text
active = known
```

The player-state distribution and downstream prediction are then updated in a new timestamped snapshot.

There is no Sunday-data prohibition. The governing rule remains:

```text
available_at <= prediction_time < kickoff
```

## F-7.6 Availability and effectiveness are separate

The model must distinguish:

```text
P(player participates)
```

from:

```text
P(player is fully effective | participates)
```

Therefore the eventual state should support:

```text
availability_probability
conditional_snap_distribution
conditional_effectiveness_distribution
```

Conceptually:

```text
Expected Contribution
=
P(active)
×
E[Contribution | active]
```

This is materially stronger than applying a fixed point deduction to a categorical injury label.

## F-7.7 Role state

Talent is insufficient without expected usage.

Possible role variables:

```text
snap share
route share
target share
carry share

pass-block share

pass-rush share
coverage share

special-teams participation

goal-line usage
third-down role
```

This separates actual talent change from usage/role change.

## F-7.8 Workload and fatigue

Candidate workload signals include:

```text
recent snaps
routes
carries
targets
pressures faced
pass-rush reps

days rest
travel
overtime games
consecutive high-workload games
```

The architecture stores candidate signals and lets the model learn their effect rather than assuming one in advance.

## F-7.9 Replacement-chain effects

When a starter becomes unavailable, the effect is not simply `subtract starter value`.

Example:

```text
WR1 unavailable
       ↓
WR2 role expands
WR3 role expands
TE routes change
personnel distribution changes
target distribution changes
scheme may adapt
```

Depth and replacement chains therefore propagate through player, unit, team, and scheme states.

## F-7.10 Immutable player-state snapshot

```text
PLAYER_STATE_SNAPSHOT

player_state_id
player_id

team_season_id
as_of

position

talent_state
form_state
role_state
health_state
workload_state

availability_distribution

uncertainty

input_observation_ids
model_version
```

## F-7.11 New players and rookies

Rookies and low-sample players require high-uncertainty priors.

Candidate prior information may include:

```text
draft position
college production
combine / athletic testing
age
position
prospect model outputs
```

Uncertainty must remain higher than for established NFL players until evidence accumulates.

## F-7.12 Players changing teams

A player's underlying talent can partially persist when changing teams, while context changes sharply:

```text
new scheme
new teammates
new QB
new OL
new coaching
new role
```

Therefore separate:

```text
PLAYER TALENT STATE
```

from:

```text
TEAM-CONDITIONED PLAYER STATE
```

The latter partially reinitializes when team context changes.

**F-7 Status: LOCKED V1**

---

# F-8 — Unit State Engine

Football performance frequently emerges from groups operating together. Player state alone is therefore insufficient.

## F-8.1 Primary functional-unit families

Offense:

```text
Quarterback Room
Offensive Line
Receiving Corps
Backfield
Pass Protection Unit
Run Blocking Unit
```

Defense:

```text
Defensive Front
Pass Rush Unit
Run Defense Front
Linebacker Unit
Coverage Unit
Secondary
```

Special teams:

```text
Field Goal Unit
Punt Unit
Punt Coverage
Kickoff Unit
Kick Coverage
Return Units
```

These units intentionally overlap. A player may participate in multiple functional units.

## F-8.2 Unit configurations are dynamic

There is not one permanent `2026 Team X offensive line`.

Different combinations are different unit configurations.

```text
UNIT_CONFIGURATION
```

must identify the actual or expected combination of participating players.

Example:

```text
LT A / LG B / C C / RG D / RT E
```

is a different configuration from:

```text
LT A / LG B / C C / RG F / RT E
```

## F-8.3 Expected unit lineup is a distribution

Before final availability is known, unit composition may be uncertain.

Example:

```text
Starter RG active: 60%
Backup RG active/starting: 40%
```

The expected unit state becomes a mixture over plausible configurations.

When late pregame information resolves the uncertainty, the mixture collapses toward the known configuration and a new prediction snapshot is generated.

## F-8.4 Unit-state components

```text
UNIT_STATE

member composition
expected participation

individual talent aggregate
continuity
experience together
role compatibility
interaction / synergy
scheme fit
recent performance
health
uncertainty
```

The key additional variable relative to player state is **interaction/synergy**.

## F-8.5 Offensive-line state

An offensive line is not merely the sum of five independent player ratings.

Candidate dimensions include:

```text
individual pass blocking
individual run blocking
communication
continuity
adjacent-pair experience
center-QB continuity
injury substitutions
scheme fit
```

Matchup output is conditional on the opponent:

```text
OL intrinsic state
      +
opponent pass-rush state
      ↓
expected protection state
```

## F-8.6 Receiving-unit state

A receiving unit interacts through:

```text
spacing
speed
route tree
coverage stress
target competition
personnel grouping
```

An elite deep threat may improve teammates' opportunities even on plays where that player is not targeted.

## F-8.7 Coverage-unit state

Potential coverage configuration includes:

```text
CB1
CB2
nickel
safeties
LB coverage personnel
```

plus:

```text
coverage family
matchup assignments
```

The matchup then becomes:

```text
receiving unit
       ×
coverage unit
```

## F-8.8 Pass protection vs pass rush

This is a major long-term matchup family.

```text
PASS PROTECTION
│
├── OL talent
├── RB/TE protection
├── QB pocket behavior
├── protection scheme
└── communication

        VS

PASS RUSH
│
├── edge rush
├── interior rush
├── blitz personnel
├── pressure design
└── defensive scheme
```

Potential model outputs:

```text
P(pressure)
P(quick pressure)
P(sack | pressure)
time-to-pressure distribution
```

Those feed the QB/pass model.

## F-8.9 Unit continuity

Track continuity explicitly through measures such as:

```text
shared snaps
shared games
consecutive starts
combination frequency
personnel churn
```

Whether continuity has predictive value is an empirical question to test, not an effect to hard-code.

## F-8.10 Immutable unit-state snapshot

```text
UNIT_STATE_SNAPSHOT

unit_state_id

team_season_id
unit_type

as_of

member_distribution

intrinsic_quality
continuity_state
synergy_state
health_state

scheme_state_id

uncertainty

input_player_state_ids
input_observation_ids
model_version
```

## F-8.11 Avoid double counting

If player states feed a unit-state model and unit state feeds team state, downstream models must not blindly include all three levels as independent evidence.

Preferred dependency graph:

```text
PLAYER STATES
     ↓
UNIT STATE MODEL
     ↓
TEAM STATE
```

Lower-level features may still be exposed to specialized models, but the dependency graph and residualization strategy must be explicit.

## F-8.12 Matchup matrix

Home offense versus away defense:

```text
QB passing         ↔ coverage
OL protection      ↔ pass rush
run blocking       ↔ defensive front
receiving corps    ↔ secondary
short-yardage      ↔ short-yardage defense
```

and the inverse for away offense versus home defense.

This becomes the foundation for football-native matchup modeling rather than simple trend comparison.

**F-8 Status: LOCKED V1**

---

# F-9 — Coaching & Scheme State Engine

Coaching and scheme are first-class football state because players do not independently determine personnel, play selection, tempo, aggression, formations, motion, coverage, blitzing, fourth-down choices, and situational strategy.

## F-9.1 Coach identity and stint

Canonical hierarchy:

```text
PERSON
  ↓
COACHING_STINT
  ↓
ROLE
```

Possible roles include:

```text
Head Coach
Offensive Coordinator
Defensive Coordinator
Special Teams Coordinator
QB Coach
OL Coach
Position Coaches
```

The person persists across time; coaching stint and team role are temporal.

## F-9.2 Coaching regime

The more useful state object is often:

```text
COACHING_REGIME
```

Example:

```text
Head Coach A
OC B
DC C
QB Coach D
```

If the offensive play caller or coordinator changes midseason, the team receives a new regime/version even if the head coach remains unchanged.

## F-9.3 Public scheme labels vs empirical scheme state

Labels such as:

```text
West Coast offense
3-4 defense
```

may be stored as descriptive observations, but they do not define the analytical scheme state.

Separate:

```text
PUBLIC_SCHEME_LABEL
```

from:

```text
EMPIRICAL_SCHEME_STATE
```

The empirical state is inferred from actual behavior.

## F-9.4 Offensive scheme state

Candidate dimensions include:

```text
neutral pass rate
early-down tendencies

personnel distribution

shotgun rate
under-center rate

motion
shift

play-action rate
screen usage
RPO usage

run-direction tendencies
run-concept tendencies

pass-depth distribution

tempo
no-huddle

red-zone tendencies
goal-line tendencies

third-down tendencies
fourth-down aggression
```

These must be conditioned on game state where appropriate.

## F-9.5 Defensive scheme state

Candidate dimensions:

```text
front usage
box count

blitz rate
simulated pressure

man/zone tendency
coverage families

single-high / two-high
press tendency

pressure by down/distance

run-fit behavior

red-zone tendencies
third-down tendencies
```

Historical feature contracts determine which dimensions are legitimately available for each era.

## F-9.6 Scheme is not coaching quality

Separate:

```text
SCHEME / STRATEGY
```

from:

```text
EXECUTION / COACHING EFFECTIVENESS
```

Potential coaching-effectiveness dimensions include:

```text
decision quality
adjustment quality
timeout management
fourth-down decisions
challenge behavior
personnel deployment
```

A theoretically sound strategy can still be executed poorly.

## F-9.7 Game-state conditioning

Play-calling tendencies must be conditioned on the state of the game.

A team that runs heavily while leading by 17 late in the fourth quarter should not automatically be classified as a run-heavy neutral offense.

The target quantity is closer to:

```text
P(play decision | down, distance, score, time, field position, personnel, opponent)
```

rather than unconditional run/pass rate.

## F-9.8 Opponent-specific adaptation

Distinguish:

```text
BASE SCHEME
```

from:

```text
GAME-SPECIFIC DEVIATION
```

Example:

```text
baseline blitz rate = 24%
expected blitz rate vs weak OL = 34%
```

The degree to which a coaching staff adapts to opponent characteristics can itself become a learned coaching attribute.

## F-9.9 Scheme change detection

Do not rely solely on public reporting that says a scheme changed.

The engine should eventually detect structural change points using behavior such as:

```text
personnel distribution changes
formation changes
tempo changes
pass tendency changes
coverage changes
blitz changes
motion changes
player usage changes
play-design changes
```

A statistically detected scheme shift may become useful before broader market consensus fully reacts.

## F-9.10 New coaching regimes

New coaching staffs should not initialize every state to zero.

Use hierarchical priors informed by:

```text
coach history
prior coordinator roles
coaching tree
expected personnel
previous scheme families
league baselines
```

while increasing uncertainty until current-team evidence accumulates.

## F-9.11 Play-caller identity

Time-version the actual decision maker:

```text
offensive_play_caller
defensive_play_caller
```

because head-coach identity is not necessarily the same thing as play-caller identity, and responsibilities can change during a season.

## F-9.12 Immutable coaching-state snapshot

```text
COACHING_STATE_SNAPSHOT

coaching_state_id

team_season_id
as_of

regime_id

head_coach_id
offensive_play_caller_id
defensive_play_caller_id

offensive_scheme_state
defensive_scheme_state
special_teams_state

decision_policy_state
adaptation_state

uncertainty

input_observation_ids
model_version
```

## F-9.13 Scheme interacts with player value

A player's expected contribution is conditional on scheme and role.

```text
PLAYER TALENT
      ×
SCHEME
      ×
ROLE
      ↓
EXPECTED PERFORMANCE
```

A player may therefore have unchanged physical talent but materially different expected production after changing teams or coaching regimes.

## F-9.14 Coaching as a policy model

Long-term, coaching can be represented as a policy:

```text
π(a_t | s_t)
```

where:

- `s_t` = football state
- `a_t` = coaching decision
- `π` = probability distribution over available actions

In plain language:

> Given this down, distance, score, time, personnel, field position, and opponent, what is this staff likely to call or decide?

That naturally separates:

```text
COACH POLICY
      ↓
ACTION / PLAY DESIGN

PLAYER + UNIT STATE
      ↓
EXECUTION / OUTCOME
```

This is the desired long-term architecture for sequence simulation and a football-native world model.

**F-9 Status: LOCKED V1**

---

# F-5 through F-9 dependency graph

```text
                F-4 INFORMATION STATE
                         │
                         ▼
                  F-7 PLAYER STATES
                         │
                         ▼
                   F-8 UNIT STATES
                         │
             ┌───────────┴───────────┐
             ▼                       ▼
       F-6 TEAM STATE         F-9 COACH / SCHEME
             │                       │
             └───────────┬───────────┘
                         ▼
                   MATCHUP STATE
                         │
                         ▼
                    GAME MODEL
                         │
                         ▼
                SCORE DISTRIBUTION
                         │
                         ▼
                  MARKET PRICING
```

Historical football evidence enters from the event ledger:

```text
F-5 PLAY LEDGER
      ↓
Historical Player Evidence
      ↓
Historical Unit Evidence
      ↓
Historical Team Evidence
      ↓
Historical Coaching Evidence
      ↓
Current State Estimation
```

The governing distinction is:

> **F-5 records what happened. F-6 through F-9 estimate what that evidence means now.**

---

# Continuous pregame monitoring interaction

The F-0 through F-4 continuous-monitoring rule now propagates through these state engines.

Example:

```text
Wednesday
QB questionable
↓
Player state changes
↓
Unit / team / matchup state updates
↓
Prediction snapshot

Friday
QB full practice
↓
New player state
↓
New prediction snapshot

Sunday morning
Material weather update
↓
Game context changes
↓
New prediction snapshot

~90 minutes before kickoff
Inactive list / confirmed availability
↓
Availability uncertainty collapses
↓
Unit composition changes
↓
Team + matchup state changes
↓
New prediction snapshot

Late pregame
Final monitored odds / weather / roster state
↓
Final pregame prediction snapshot

Kickoff
────────────────────────────
Pregame information boundary
```

There is no blanket prohibition on Sunday or game-day data.

The governing rule for every snapshot is:

```text
available_at <= prediction_time < kickoff
```

An earlier prediction remains frozen and reproducible. Later legitimately available information creates a new snapshot rather than rewriting the earlier one.

---

# Locked architecture decisions from F-5 through F-9

1. Canonical football state is provider-independent.
2. Pre-snap state and post-play outcome are separate causal objects.
3. The top-level play classification object is `PLAY_EXECUTION`, not `PLAY_ACTION`.
4. **Play action** remains an actual football design modifier/concept and can combine with primary play families such as `PLAY_ACTION_PASS`.
5. Primary play type and design mechanics are separate dimensions.
6. Play events may be represented as ordered sub-events rather than one flattened row.
7. Physical play outcome and official scoring outcome may both be preserved.
8. EPA, WPA, success, and similar values are derived analytics, not canonical football truth.
9. Team state is temporal and separated from game-specific context.
10. Style/tendency and quality/effectiveness are different concepts.
11. Player talent, health, role, usage, workload, availability, and effectiveness are separate state dimensions.
12. Player availability and conditional effectiveness are probabilistic until resolved.
13. Unit performance includes composition, continuity, role fit, and interaction/synergy.
14. Unit configuration uncertainty propagates through pregame predictions until participation becomes known.
15. Player → unit → team dependency must be explicit to avoid double counting.
16. Coaching personnel, coaching regime, empirical scheme, play-caller identity, and coaching effectiveness are distinct objects.
17. Coaching tendencies must be conditioned on game state.
18. Scheme may adapt to opponent and may undergo detectable structural change points.
19. Continuous monitoring may regenerate player, unit, team, matchup, and prediction states through kickoff.
20. No information first available after the relevant prediction timestamp may enter that snapshot.

---

# Next architecture block

The next planned architecture sections are:

```text
F-10  Injury & Availability State
F-11  Weather / Stadium / Surface
F-12  Travel / Rest / Recovery
F-13  Complete NFL Feature Taxonomy
F-14  Prediction Targets & Label Architecture
```

F-10 should build directly on the F-7/F-8 distinction between availability, effectiveness, role, replacement chains, and unit reconfiguration. F-13 will then consolidate F-0 through F-12 into the first explicit NFL feature contracts that implementation can target.
