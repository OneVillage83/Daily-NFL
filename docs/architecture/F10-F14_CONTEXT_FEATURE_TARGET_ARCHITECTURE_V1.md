# Daily NFL Architecture V1 — F-10 through F-14

**Status:** Governing architecture reference  
**Repository:** `OneVillage83/Daily-NFL`  
**Scope:** Injury & Availability State, Weather/Stadium/Surface State, Travel/Rest/Recovery State, NFL Feature Taxonomy & Feature Contract, Prediction Targets & Label Architecture  
**Depends on:** F-0 through F-9

---

## Governing PIT Rule

All pregame state, features, and prediction artifacts must satisfy:

```text
available_at <= prediction_time < kickoff
```

There is no arbitrary “game-day” or “Sunday” exclusion. Any information legitimately available before the prediction timestamp may be used. Later information creates a new immutable state/prediction snapshot rather than mutating an earlier one.

Continuous pregame monitoring remains a Daily NFL requirement through kickoff.

---

# F-10 — Injury & Availability State Engine

The Injury & Availability State Engine converts timestamped injury evidence into probabilistic player availability, expected participation, expected effectiveness, and downstream unit/team impact.

An injury report is not the player’s true injury state. It is an observation about an underlying latent state.

```text
INJURY OBSERVATIONS
        ↓
INJURY EPISODE
        ↓
HEALTH STATE
        ↓
AVAILABILITY DISTRIBUTION
        ↓
PARTICIPATION DISTRIBUTION
        ↓
EFFECTIVENESS DISTRIBUTION
        ↓
PLAYER STATE
        ↓
UNIT / TEAM STATE
```

## F-10.1 Core concept

Do not model injury status as a single categorical team penalty:

```text
PLAYER
injury_status = QUESTIONABLE
```

Instead, preserve all available evidence and estimate the underlying state.

Two players can both be officially listed `QUESTIONABLE` while representing very different probabilities and expected impacts.

Example:

```text
Player A
Questionable
Full practice Friday
Minor issue
Played normally last week
```

versus:

```text
Player B
Questionable
Did not practice all week
Recently aggravated injury
```

The designation is identical. The inferred football state is not.

## F-10.2 Three separate questions

For every injured player, Daily NFL should eventually estimate three distinct quantities.

### Availability

```text
P(active)
```

### Participation conditional on being active

```text
P(participation | active)
```

Participation may be represented through position-relevant workload such as:

```text
offensive snaps
defensive snaps
routes
carries
targets
pass-rush reps
coverage reps
special-teams snaps
```

### Effectiveness conditional on participation

```text
P(effectiveness | participation, active)
```

Conceptually:

```text
Expected Contribution
=
P(active)
× expected participation conditional on active
× expected effectiveness conditional on participation
```

This is superior to assigning fixed values such as:

```text
QUESTIONABLE = -1.5 points
```

## F-10.3 NFL reporting remains observational

Official injury/practice/game-status reporting is stored as a timestamped observation stream.

Canonical observation:

```text
INJURY_OBSERVATION

observation_id
player_id
team_season_id

provider
source_id

observed_at
published_at
available_at

reported_body_region
reported_injury_description

practice_status
game_status

source_text
confidence
raw_evidence_id
```

Previous observations are never overwritten by later reports.

## F-10.4 Practice status and game status are separate

Practice participation:

```text
DID_NOT_PARTICIPATE
LIMITED
FULL
UNKNOWN
```

Game designation:

```text
OUT
DOUBTFUL
QUESTIONABLE
NO_DESIGNATION
UNKNOWN
```

They encode different information and must remain separate.

## F-10.5 Injury episode

Multiple observations can refer to the same underlying injury problem.

```text
INJURY_EPISODE

injury_episode_id
player_id

body_region
laterality_if_known
injury_family_if_known

episode_start
episode_end
first_observed_at

source_description

recurrence_flag
related_prior_episode_id

resolution_state
confidence
```

Daily NFL must not invent medical diagnoses. If the reliable source says `hamstring`, store hamstring. If it says `leg`, store leg. Do not infer a specific tissue/grade without credible evidence.

## F-10.6 Multiple simultaneous injuries

The architecture permits multiple concurrent injury episodes:

```text
PLAYER HEALTH STATE
│
├── injury episode A
├── injury episode B
└── illness / other episode
```

Do not collapse multiple conditions into a binary `injured = true` flag.

## F-10.7 Player health state

```text
PLAYER_HEALTH_STATE

player_id
as_of

injury_episode_ids

availability_probability
expected_participation_distribution
expected_effectiveness_distribution
reaggravation_or_early_exit_uncertainty
health_uncertainty

model_version
```

V1 can begin with availability and expected snap/role share while preserving the architecture required for later effectiveness and early-exit modeling.

## F-10.8 Late inactives

Pregame monitoring remains active through kickoff.

Example:

```text
T-24h
P(active) = 0.68
```

Later:

```text
T-90m
ACTIVE confirmed
P(active) -> effectively 1
```

or:

```text
INACTIVE confirmed
P(active) -> 0
```

The change triggers downstream recomputation:

```text
PLAYER STATE rebuild
        ↓
UNIT STATE rebuild
        ↓
TEAM STATE rebuild
        ↓
MATCHUP rebuild
        ↓
prediction rerun
```

Earlier snapshots remain immutable.

## F-10.9 Active does not equal healthy

A player can be officially active while still carrying reduced expected workload or effectiveness.

Therefore keep separate:

```text
AVAILABILITY STATE
```

and:

```text
EFFECTIVENESS STATE
```

through kickoff.

## F-10.10 Return-to-play ramp

The architecture supports a returning-player ramp:

```text
Week 1 back: 45 snaps
Week 2:      61 snaps
Week 3:      normal workload
```

Candidate inputs:

```text
previous workload
current practice participation
injury family
position
historical player workload
time missed
recent game usage
```

The effect should be learned rather than hard-coded.

## F-10.11 Early-exit probability

For props and player-level forecasting, the system may later estimate:

```text
P(finishes expected workload)
```

separately from:

```text
P(starts / is active)
```

This is especially relevant for returning players, but it must be learned from historical evidence.

## F-10.12 Injury history

Potential PIT-safe inputs include:

```text
prior same-region episodes
games missed
time since previous episode
recent workload
historical return patterns
```

Later diagnoses may not retroactively alter the pregame information state.

## F-10.13 Injury impact is positional

The effect of losing a player depends on the role and the surrounding unit.

Examples:

```text
QB1
LT
CB1
EDGE1
C
K
WR4
```

must not be treated as equivalent contributions to one undifferentiated team injury score.

## F-10.14 Replacement cascade

Example — WR1 unavailable:

```text
WR1 availability -> 0
        ↓
WR2 expected role ↑
WR3 expected role ↑
TE route share may ↑
RB target share may ↑
personnel distribution may change
scheme may change
```

Example — LT unavailable:

```text
LT OUT
  ↓
OL configuration changes
TE blocking usage may change
RB protection usage may change
QB pressure expectation changes
play-calling may change
```

F-10 therefore propagates through F-7 Player State, F-8 Unit State, F-6 Team State, and F-9 Coaching/Scheme State where appropriate.

## F-10.15 Injury information hierarchy

Potential evidence includes:

```text
official inactive designation
official game status
official practice participation
reserve transactions
roster transactions
credible team announcements
reliable injury reporting
historical workload
actual recent participation
```

No source is silently promoted to universal truth. Each observation retains provenance and confidence.

## F-10.16 No hindsight leakage

Example:

```text
Sunday 10:00 AM — Player questionable
Sunday 1:00 PM  — Kickoff
Monday          — MRI reveals significant injury
```

The Monday diagnosis cannot enter Sunday's historical pregame model.

Historical reconstruction preserves what was knowable at the prediction timestamp.

## F-10.17 Injury snapshot

```text
INJURY_AVAILABILITY_SNAPSHOT

snapshot_id
player_id
game_id
as_of

injury_episode_ids

availability_probability
participation_distribution
effectiveness_distribution
early_exit_uncertainty

source_observation_ids

availability_model_version
effectiveness_model_version

PIT_validation
created_at
```

Snapshots are immutable.

## F-10.18 Trigger architecture

Meaningful changes in any of the following can trigger new injury/player state:

```text
practice status
game status
injury description
roster state
inactive list
starter designation
credible participation information
```

New information creates a new state/prediction snapshot; previous snapshots remain historically intact.

### F-10 status

**LOCKED V1.**

---

# F-11 — Weather / Stadium / Surface State Engine

The generic weather/venue infrastructure should live primarily in `Daily-Data-Core`. Daily NFL owns football-specific environmental transformations and interactions.

Governing principle:

> Weather is game context, not intrinsic team quality.

A team's true offensive state does not change because rain begins. Its expected performance in a particular matchup may change.

## F-11.1 Three layers

```text
VENUE
  +
SURFACE STATE
  +
ATMOSPHERIC STATE
        ↓
GAME ENVIRONMENT
```

## F-11.2 Static venue state

Recommended Core-owned representation:

```text
VENUE

venue_id
name

latitude
longitude
elevation

timezone

indoor_outdoor_class
roof_type
wall_type_if_relevant

field_orientation

primary_surface_family

relevant_geometry
home_organization
```

## F-11.3 Dynamic game environment

```text
GAME_ENVIRONMENT_SNAPSHOT

event_id
as_of

weather_forecast_id
roof_state
surface_state

temperature
humidity
dew_point

wind_speed
wind_gust
wind_direction

precipitation_probability
precipitation_type
precipitation_intensity

visibility
pressure

environment_uncertainty
```

Fields are populated only where defensible source coverage exists.

## F-11.4 Weather forecast snapshots

```text
WEATHER_FORECAST_SNAPSHOT

issued_at
observed_at
available_at

forecast_valid_at

provider
stadium_coordinate

temperature
wind
gust
precipitation
visibility
pressure
other supported fields
```

Every forecast update is retained.

## F-11.5 Forecast is not actual weather

These are separate objects:

```text
Saturday forecast
Sunday updated forecast
actual observed game conditions
```

A Saturday prediction uses the forecast available Saturday. A Sunday 12:45 PM prediction may use the newer Sunday forecast. Actual game weather is stored later as outcome/context truth and never backfilled into earlier prediction snapshots.

## F-11.6 Forecast uncertainty

Eventually represent forecast distributions and information quality, not only point estimates:

```text
temperature distribution
wind distribution
precipitation probability
forecast disagreement
forecast age
```

Example:

```text
18 mph ± 2
```

and:

```text
18 mph ± 10
```

are different information states.

## F-11.7 Field-relative wind

Preserve provider-reported raw wind:

```text
wind_direction_degrees
wind_speed
wind_gust
```

Then derive:

```text
FIELD_RELATIVE_WIND

longitudinal_component
crossfield_component
```

Future simulation can apply headwind/tailwind/crosswind relative to field direction and possession direction where appropriate.

Potentially affected football components include:

```text
field goals
punts
deep passes
kickoffs
```

Magnitude should be learned empirically.

## F-11.8 Roof state

Do not equate retractable-roof capability with the game condition.

```text
ROOF_CAPABILITY = RETRACTABLE

ROOF_GAME_STATE =
OPEN
CLOSED
UNKNOWN
```

Roof designation may become known late, so it is part of the continuous pregame monitoring stream.

## F-11.9 Indoor weather

Separate:

```text
EXTERIOR_WEATHER
```

from:

```text
PLAYING_ENVIRONMENT
```

If the roof is closed, exterior wind should not automatically enter the gameplay model.

## F-11.10 Surface state

A binary grass/turf flag is not sufficient for the long-term architecture.

```text
SURFACE_STATE

surface_family
surface_product_or_subtype
installation_age_if_known

wetness_state
snow_state
ice_state
surface_temperature_if_available

recent_precipitation
roof_state
maintenance_state_if_known

confidence
```

## F-11.11 Surface interactions

Candidate interactions include:

```text
surface × player
surface × position
surface × weather
surface × injury state
surface × speed profile
```

They are candidate predictive relationships, not assumed causal effects.

## F-11.12 Temperature

Store continuous raw temperature values. Avoid imposing arbitrary thresholds such as `cold = temperature < 40` as the primary representation.

Diagnostic buckets can be derived later.

## F-11.13 Precipitation

Keep distinct:

```text
probability
type
intensity
accumulation
```

because different combinations encode materially different environments.

## F-11.14 Environmental interactions

Examples for later modeling:

```text
QB deep passing × wind

kicker range × wind × temperature

receiver profile × precipitation

run/pass tendencies × environment
```

These should be learned from data rather than embedded as handicapping folklore.

## F-11.15 Weather-triggered reruns

Potential material change triggers:

```text
forecast change exceeds threshold
roof designation changes
precipitation state changes materially
wind or gust forecast changes materially
severe weather alert arrives
surface state changes
```

Then:

```text
GAME_CONTEXT rebuilt
        ↓
MATCHUP_STATE rebuilt
        ↓
prediction rerun
```

Thresholding should prevent insignificant forecast noise from generating unnecessary predictions.

### F-11 status

**LOCKED V1.**

---

# F-12 — Travel / Rest / Recovery State Engine

Daily NFL should represent travel and recovery exposures precisely and estimate their effects empirically rather than embedding conventional betting narratives as assumptions.

Do not begin with rules such as:

```text
West Coast teams are bad at 1 PM
```

or:

```text
short weeks cost X points
```

Instead measure the underlying exposure.

## F-12.1 Three layers

```text
SCHEDULE FACTS
        ↓
TRAVEL EXPOSURE
        ↓
RECOVERY STATE
```

Schedule facts are generally observable/deterministic. Travel exposure is measurable or inferable. Recovery state is partially latent.

## F-12.2 Schedule facts

Inputs:

```text
previous_game_kickoff
current_game_kickoff

previous_game_venue
current_game_venue

home_or_away
bye_week
overtime_flag
international_flag
```

Derived features can include:

```text
hours_between_games
calendar_days_rest

distance_between_venues

time_zones_crossed
direction_of_travel
altitude_change

local_kickoff_time
body_clock_proxy

consecutive_road_game_count
```

## F-12.3 Exact rest duration

Primary representation should be:

```text
hours_since_previous_game
```

not only broad categories such as `6 days rest` or `short week`.

A Sunday afternoon to Thursday evening transition differs from Sunday night to Thursday evening even when both are commonly called a short week.

## F-12.4 Travel leg

```text
TRAVEL_LEG

team_season_id

origin
destination

origin_venue_id
destination_venue_id

departure_time_if_known
arrival_time_if_known

distance

timezone_delta
altitude_delta

international

source
inferred_flag
uncertainty
```

If actual departure/arrival information is unavailable, do not invent it. Mark schedule-derived inference explicitly.

## F-12.5 Road-trip state

Football travel may span multiple games and locations.

```text
TRAVEL_SEQUENCE

games_away_from_home

days_away_if_known
cumulative_distance
consecutive_time_zone_changes

international_segment
return_home
```

## F-12.6 Circadian features

Potential inputs:

```text
home_base_timezone
previous_location_timezone
game_timezone

local_kickoff
equivalent_home_body_clock_kickoff

eastward_shift
westward_shift
```

The predictive effect must be validated after controlling for team/opponent strength and other confounders.

## F-12.7 Recovery is player-conditioned

Two players share the same flight and schedule but may have radically different workload exposure.

Example:

```text
Player A: 95 snaps last game
Player B: 14 snaps last game
```

Therefore later player recovery can depend on:

```text
recent workload
+
rest interval
+
travel exposure
+
injury state
+
historical workload
```

and feed F-7 Player State.

## F-12.8 Overtime workload

Avoid reducing overtime to `OT = yes`.

Potentially relevant measures include:

```text
extra offensive snaps
extra defensive snaps
individual extra snaps
additional time of possession
game duration
```

A short overtime and a very long overtime are different recovery events.

## F-12.9 Position-specific recovery

Recovery effects may vary by position:

```text
QB
OL
RB
WR
EDGE
CB
```

The architecture must allow position/player-level workload models rather than only one team fatigue score.

## F-12.10 Bye week

Store the categorical diagnostic `BYE = true`, but also preserve underlying quantities such as:

```text
hours_since_previous_game
coaching preparation interval where measurable
```

Benefits may vary by coaching, age, injuries, roster, and season timing and should be learned.

## F-12.11 Thursday / Monday effects

Do not make a fixed `Thursday penalty` or `Monday bonus` the causal representation.

Store:

```text
rest
travel
previous kickoff time
current kickoff time
workload
```

Calendar-day labels may remain as diagnostics.

## F-12.12 Schedule transitions

Candidate state categories:

```text
AWAY -> AWAY
AWAY -> HOME
HOME -> AWAY
HOME -> HOME

international -> domestic
high altitude -> low altitude
low altitude -> high altitude
```

Representation does not imply an assumed effect.

## F-12.13 PIT schedule versioning

Travel/recovery features depend on the schedule actually known at the prediction timestamp.

If a game is rescheduled:

```text
old schedule observation
new schedule observation
```

must both remain in history.

## F-12.14 Recovery snapshot

```text
RECOVERY_CONTEXT_SNAPSHOT

snapshot_id
team_season_id
game_id
as_of

hours_rest

previous_game
previous_venue

travel_distance
timezone_shift
altitude_shift

road_sequence_state

overtime_workload
cumulative_recent_workload

player_recovery_summary

uncertainty

source_ids
calculation_version
```

## F-12.15 No baked-in penalty

Locked principle:

> Daily NFL stores travel, rest, and recovery exposure first and estimates predictive effect empirically.

Do not hard-code rules such as:

```text
3 time zones = -1.5 points
```

unless future validated research supports that relationship.

### F-12 status

**LOCKED V1.**

---

# F-13 — Complete NFL Feature Taxonomy & Feature Contract

F-13 defines what information may enter a model, what every feature means, where it came from, and exactly when it was available.

A feature is not merely a dataframe column.

## F-13.1 Feature definition contract

Every feature requires machine-readable metadata.

```text
FEATURE_DEFINITION

feature_id
feature_name
semantic_definition

entity_scope

data_type
units

source_dependencies
calculation_method
lookback_definition

as_of_semantics
availability_rule

minimum_history
supported_eras

null_semantics
uncertainty_semantics

feature_version
contract_version
```

This prevents ambiguous future features such as `off_epa_rolling` whose lookback, context filters, EPA implementation, and PIT cutoff are unknown.

## F-13.2 Feature lineage

Every feature value should support traceable lineage:

```text
RAW OBSERVATIONS
        ↓
NORMALIZED FACTS
        ↓
DERIVED METRIC
        ↓
STATE ESTIMATE
        ↓
MATCHUP FEATURE
```

Example:

```text
plays
 ↓
QB pressure outcomes
 ↓
QB pressure-response metric
 ↓
QB current state
 ↓
QB pressure sensitivity × opponent pass-rush state
 ↓
matchup feature
```

## F-13.3 Feature family A — Game / schedule

```text
home_or_away
season
week
phase
neutral_site
kickoff_time
hours_rest
venue
ruleset
division_game
conference_game
playoff_state
```

## F-13.4 Feature family B — Team offense

```text
latent offensive strength
passing efficiency
rushing efficiency
dropback efficiency
early-down efficiency
late-down efficiency
red-zone efficiency
goal-line efficiency
short-yardage efficiency
explosive-play rate
negative-play rate
turnover propensity
pace
drive efficiency
points-per-drive state
```

Prefer state estimates over raw season averages when possible.

## F-13.5 Feature family C — Team defense

```text
latent defensive strength
pass defense
run defense
pressure state
sack conversion
turnover creation
explosive-play prevention
early-down defense
late-down defense
red-zone defense
goal-line defense
short-yardage defense
drive prevention state
```

## F-13.6 Feature family D — Special teams

```text
field-goal state
extra-point state
kick distance distribution
punt state
punt-return state
kick-return state
coverage state
blocked-kick state
field-position contribution
```

## F-13.7 Feature family E — Quarterback

Candidate dimensions:

```text
QB latent talent
accuracy
CPOE-style state
EPA/dropback state
decision-making proxy
pressure performance
clean-pocket performance
sack avoidance
turnover propensity
deep passing
intermediate passing
short passing
scrambling
designed rushing
play-action performance
screen performance
health
mobility
recent workload
```

Care is required to avoid blind double-counting of highly correlated constructs.

## F-13.8 Feature family F — Skill players

WR / TE:

```text
route participation
target earning
yards per route
separation proxies
catch-probability performance
YAC state
air-yard profile
deep-threat profile
slot/outside usage
blocking contribution
red-zone usage
```

RB:

```text
carry share
route share
target share
rush efficiency
yards-after-contact proxies
explosive-run rate
short-yardage state
goal-line usage
pass protection
receiving state
```

## F-13.9 Feature family G — Offensive line

```text
expected starters
individual player states
pass-protection state
run-blocking state
continuity
combination experience
injury substitutions
pressure-allowed proxies
time-to-pressure proxies
scheme fit
```

## F-13.10 Feature family H — Defensive personnel

Pass rush:

```text
pressure generation
quick pressure
edge pressure
interior pressure
sack conversion
```

Coverage:

```text
CB state
safety state
coverage-unit state
man/zone performance
deep coverage
slot coverage
explosive-pass prevention
```

Run defense:

```text
front strength
box efficiency
short-yardage state
run disruption
```

## F-13.11 Feature family I — Injury / availability

```text
P(active)
expected snaps
expected role
effectiveness uncertainty
return-from-injury state
unit disruption
replacement quality
depth uncertainty
```

Do not rely only on injury count.

## F-13.12 Feature family J — Depth / continuity

```text
starting-lineup continuity
OL continuity
receiving-unit continuity
secondary continuity
QB-center continuity
roster churn
starter replacement count
shared snaps
coaching continuity
```

## F-13.13 Feature family K — Coaching / scheme

```text
neutral pass policy
personnel usage
formation usage
motion
play action
RPO
screen usage
tempo
run concepts
pass depth
blitz policy
coverage policy
front usage
fourth-down policy
red-zone policy
opponent adaptation
```

The football concept `play action` remains distinct from the canonical F-5 `PLAY_EXECUTION` object.

## F-13.14 Feature family L — Matchup interactions

Daily NFL should model interactions rather than only side-by-side team ratings.

Examples:

```text
QB pressure sensitivity × opponent pressure ability

OL pass protection × opponent pass rush

receiver deep ability × opponent deep coverage

run-blocking profile × defensive front

short-yardage offense × short-yardage defense
```

## F-13.15 Feature family M — Situational state

Potential context-specific states:

```text
early downs
third down
fourth down
red zone
goal line
short yardage
backed up
two-minute
leading
trailing
neutral score state
```

Small samples require shrinkage/hierarchical methods.

## F-13.16 Feature family N — Play distributions

Mean EPA alone is insufficient.

Two teams may have similar average efficiency while having different distributions.

Represent where useful:

```text
success distribution
yardage distribution
explosive rate
negative-play rate
turnover tail
drive-outcome distribution
```

## F-13.17 Feature family O — Turnovers and variance

Separate observed turnover outcomes from estimated underlying tendency.

Candidate concepts:

```text
interception-worthy behavior
fumble events
fumble recovery outcomes
turnover propensity
turnover luck or residual
```

where source coverage permits.

## F-13.18 Feature family P — Penalties / discipline

Potential features:

```text
penalty frequency
accepted penalty rate
offensive holding
false starts
defensive pass interference
pre-snap penalties
automatic-first-down penalties
penalty EPA or yardage
team/coach persistent components
```

Context and officiating effects must be handled carefully.

## F-13.19 Feature family Q — Weather / venue

```text
temperature
wind
gusts
field-relative wind
precipitation
visibility
roof
surface
elevation
environment uncertainty
```

## F-13.20 Feature family R — Travel / recovery

```text
rest hours
travel distance
timezone movement
body-clock kickoff
altitude movement
road sequence
recent overtime workload
recent player workloads
bye state
```

## F-13.21 Feature family S — Season priors

Early-season state may use PIT-safe priors such as:

```text
previous-season state
returning player value
QB continuity
coaching continuity
roster turnover
free-agent changes
draft additions
age curves
```

Future prospect models can contribute rookie priors.

## F-13.22 Feature family T — Tracking / modern data

Modern contracts may include where coverage/licensing permits:

```text
Next Gen Stats
time to throw
separation
air yards
expected completion
rush yards over expectation
speed
pressure timing
play-level participation
formation
```

Coverage differs by era, so feature-era contracts are required rather than synthetic backward filling.

## F-13.23 Feature family U — Officials

Experimental family:

```text
officiating crew
penalty tendency estimates
specific foul distributions
```

This family should receive strong shrinkage and strict out-of-sample validation because overfitting risk is high.

## F-13.24 Feature family V — Market data

Allowed only in explicitly market-aware models:

```text
opening spread
current spread
opening total
current total
moneyline
book dispersion
line movement
market consensus
no-vig probability
time since open
```

These are prohibited from `FOOTBALL_ONLY` models.

## F-13.25 Feature family W — Data quality

The model should be allowed to know the quality of the information state.

Potential features:

```text
source_coverage_pct
missing_feature_count
availability_uncertainty
identity_confidence
weather_age
lineup_uncertainty
```

This helps distinguish a nominally identical probability produced under strong versus weak evidence.

## F-13.26 Feature eras

Initial contract ladder:

```text
NFL_BASELINE_V1
```

Broad historical coverage.

```text
NFL_ROSTER_ADVANCED_V1
```

Adds richer roster/depth information.

```text
NFL_SNAP_ADVANCED_V1
```

Adds snap/participation state.

```text
NFL_MODERN_V1
```

Adds modern tracking/advanced data.

```text
NFL_WORLD_V1
```

Future spatial/sequence/world-model representations.

Do not fabricate unavailable historical inputs just to force all eras into one feature matrix.

## F-13.27 Football-only vs market-aware contracts

Every feature contract must declare:

```text
market_information_allowed: TRUE | FALSE
```

Examples:

```text
NFL_MODERN_FOOTBALL_ONLY_V1
NFL_MODERN_MARKET_AWARE_V1
```

Both should be evaluated separately.

## F-13.28 Missingness semantics

Distinguish explicitly:

```text
TRUE_ZERO
UNKNOWN
NOT_APPLICABLE
NOT_AVAILABLE_IN_THIS_ERA
PROVIDER_FAILURE
IDENTITY_UNRESOLVED
```

Never apply indiscriminate `fillna(0)` across the NFL system.

## F-13.29 No duplicate information without lineage

If a downstream state estimate already summarizes a set of lower-level features, including both the state estimate and all source features requires an explicit reason.

Feature dependency graphs must expose how information flows so the system can detect or at least audit double counting.

## F-13.30 Feature contract test

Every feature proposed for production must answer:

```text
What does it mean?
Why might it predict the target?
Was it available at prediction time T?
Can it be reconstructed historically?
What is its source?
What seasons/eras support it?
What does missingness mean?
Could it leak the target/result?
Does it duplicate another state estimate?
Can it be reproduced exactly?
```

If these cannot be answered, the feature does not enter production training.

### F-13 status

**LOCKED V1.**

---

# F-14 — Prediction Targets & Label Architecture

Daily NFL should model football outcomes first and sportsbook propositions second.

The goal is a coherent probabilistic game model capable of answering many markets, not dozens of disconnected binary classifiers.

## F-14.1 Ground truth vs betting label

Keep separate:

```text
FOOTBALL OUTCOME TRUTH
```

and:

```text
SPORTSBOOK MARKET SETTLEMENT
```

Sportsbook rules must never redefine the underlying football event truth.

## F-14.2 Canonical game result

```text
GAME_OUTCOME

game_id

home_points_final
away_points_final

home_points_regulation
away_points_regulation

overtime_played

home_win
away_win
tie

period_scores

result_finalized_at
result_version
```

A regular-season tie remains a tie in football truth even if a particular betting market has different grading rules.

## F-14.3 Primary joint target

The long-term central game model should estimate the joint scoring distribution:

```text
P(home_points, away_points)
```

or produce simulated samples:

```text
Simulation 1: 27-20
Simulation 2: 24-27
Simulation 3: 31-17
...
Simulation N
```

The joint distribution naturally contains:

```text
win probability
tie probability
margin
total
team totals
alternate spreads
alternate totals
```

while preserving correlation between team scores.

## F-14.4 Core game targets

```text
HOME_POINTS
AWAY_POINTS

MARGIN = home_points - away_points

TOTAL = home_points + away_points

GAME_RESULT = HOME_WIN | TIE | AWAY_WIN
```

## F-14.5 Win probability

Derived from the score distribution:

```text
P(home_points > away_points)
P(home_points = away_points)
P(home_points < away_points)
```

Postseason rulesets can constrain the final outcome space appropriately.

## F-14.6 Spread probability

For arbitrary home spread `s`:

```text
P(home_points + s > away_points)
P(home_points + s = away_points)
P(home_points + s < away_points)
```

One margin distribution can answer many spread lines without training a unique model for each quote.

## F-14.7 Total probability

For total line `L`:

```text
P(home_points + away_points > L)
P(home_points + away_points = L)
P(home_points + away_points < L)
```

## F-14.8 Team totals

Derived from marginal score distributions:

```text
P(home_points > home_team_total_line)
P(away_points > away_team_total_line)
```

with push probabilities where appropriate.

## F-14.9 Segment targets

Once quarter/half scoring state is sufficiently reliable, support:

```text
1Q score
1H score
2H score
quarter totals
first-half spread
first-half moneyline
```

Some segment markets may ultimately benefit from dedicated temporal models.

## F-14.10 Drive-level targets

Future drive model:

```text
DRIVE_OUTCOME

TOUCHDOWN
FIELD_GOAL
PUNT
TURNOVER
DOWNS
MISSED_FIELD_GOAL
END_HALF
SAFETY
OTHER
```

plus:

```text
drive_points
drive_yards
drive_duration
plays
starting_field_position
ending_field_position
```

This enables:

```text
Drive Simulator
     ↓
Game Simulator
```

## F-14.11 Play-level targets

Future sequence/world models may estimate:

```text
next play family
yards gained
completion
turnover
pressure
sack
first down
touchdown
clock consumed
next state
```

consistent with the F-5 state-transition architecture:

```text
P(state_next | state_current, execution, participants, context)
```

## F-14.12 Player statistical targets

Future player markets may include:

QB:

```text
pass attempts
completions
pass yards
pass touchdowns
interceptions
rush attempts
rush yards
```

RB:

```text
carries
rush yards
targets
receptions
receiving yards
touchdowns
```

WR / TE:

```text
routes
targets
receptions
receiving yards
touchdowns
```

Defensive/kicking targets may be added where model quality and market demand justify them.

## F-14.13 Participation before props

Player prop architecture should model the dependency chain explicitly:

```text
P(active)
   ↓
P(snaps | active)
   ↓
P(opportunities | snaps)
   ↓
P(statistic | opportunities)
```

Example for receiving yards:

```text
active
 ↓
routes
 ↓
targets
 ↓
catches
 ↓
yards
```

This connects F-10 availability and F-7 player state directly to prop forecasting.

## F-14.14 Sportsbook settlement layer

Example football truth:

```text
SF 24
DAL 21
```

Market A:

```text
SF -3
```

may grade `PUSH`.

Market B:

```text
SF -2.5
```

may grade `WIN`.

Same football truth, different settlement.

Canonical settlement:

```text
MARKET_SETTLEMENT

market_snapshot_id
market_type
line
price
book

rules_version

outcome = WIN | LOSS | PUSH | VOID | OTHER
```

## F-14.15 Book-specific rules

Underlying sports truth remains universal. Settlement rules can vary by sportsbook/market.

`MARKET_RULESET` belongs in `Daily-Data-Core` and becomes especially important for:

```text
player props
minimum participation rules
postponements
void rules
stat corrections
other book-specific grading behavior
```

## F-14.16 Closing line

The closing line is normally evaluation information for earlier snapshots, not a feature.

For a T-24 prediction:

```text
closing spread
```

can later be used to calculate CLV, but cannot enter the T-24 model.

A T-2m market-aware model may use the market actually available at T-2m.

The eligibility rule remains:

```text
available_at <= prediction_time
```

## F-14.17 Market labels generated per quote

One football event may have many quotes:

```text
49ers -2.5 -110
49ers -3   +100
49ers -3.5 +110
```

across multiple books and timestamps.

Daily NFL stores one canonical game truth and generates settlement labels against each market observation.

## F-14.18 Prediction target registry

```text
PREDICTION_TARGET

target_id
target_family
entity_scope

definition
unit
outcome_space

ruleset
label_generator_version
supported_model_type
```

Examples:

```text
NFL_GAME_HOME_POINTS_V1
NFL_GAME_AWAY_POINTS_V1
NFL_GAME_MARGIN_V1
NFL_GAME_TOTAL_V1
NFL_GAME_RESULT_3WAY_V1
NFL_DRIVE_OUTCOME_V1
NFL_PLAYER_PASS_YARDS_V1
```

## F-14.19 Label registry

```text
LABEL

label_id
target_id

event_id

label_value
label_status

derived_at

source_truth_version
label_generator_version
```

Recommended states:

```text
PROVISIONAL
FINAL
CORRECTED
VOID
```

## F-14.20 Stat corrections

Never mutate labels invisibly.

Example:

```text
69 receiving yards -> 68 receiving yards
```

creates a traceable new truth/label version.

Predictions remain immutable. Settlement may be recomputed according to the relevant ruleset.

## F-14.21 Postponed / cancelled / abandoned events

Support explicit non-training/non-settled states:

```text
NO_CONTEST
CANCELLED
POSTPONED
NOT_SETTLED
```

Do not force every scheduled game into win/loss training data.

## F-14.22 Prediction horizons

The same game can produce multiple valid historical predictions:

```text
T-168h
T-72h
T-24h
T-6h
T-90m
T-final
```

Each uses its own information set, features, uncertainty, and market context where allowed.

This enables measurement of information gain over time.

## F-14.23 Continuous model snapshots

Example:

```text
Prediction A
T-6h
SF win probability = 56%
```

Then a late inactive update arrives:

```text
Prediction B
T-90m
SF win probability = 59%
```

Both remain valid historical predictions. B never overwrites A.

## F-14.24 Prediction envelope

```text
PREDICTION

prediction_id
game_id

generated_at
information_cutoff
prediction_horizon

model_id
model_version

feature_contract
feature_snapshot_ids

prediction_family

distribution_artifact

mean
median
variance
quantiles

home_win_probability
tie_probability
away_win_probability

expected_home_points
expected_away_points
expected_margin
expected_total

epistemic_uncertainty
aleatoric_uncertainty

data_quality_state

market_information_used

simulation_seed_if_applicable
code_version
```

## F-14.25 Football-only prediction

```text
market_information_used = FALSE
```

Produces an independent football fair distribution.

## F-14.26 Market-aware prediction

```text
market_information_used = TRUE
```

Produces a distribution conditioned on both football information and allowed market information.

Both are retained and evaluated.

## F-14.27 Ensemble

Future architecture:

```text
Football-only model
       +
Market-aware model
       +
other model families
       ↓
Calibrated Ensemble
```

Weights and model versions must be explicit. No invisible blending.

## F-14.28 Evaluation metrics by target

Game-result probability:

```text
Log Loss
Brier Score
Calibration
```

Score/margin/total distributions:

```text
CRPS
log predictive density
coverage
quantile calibration
MAE / RMSE as secondary diagnostics
```

Market evaluation:

```text
fair-price calibration
CLV
ROI
yield
drawdown
performance by edge bucket
performance by uncertainty bucket
```

Probabilistic accuracy remains the primary objective.

## F-14.29 Conditional calibration

Calibration must also be evaluated by subgroup:

```text
favorite / underdog
home / away
probability bucket
spread range
total range
season
prediction horizon
weather regime
injury uncertainty
model version
market
```

A model can appear calibrated overall while containing severe subgroup bias.

## F-14.30 Recommendation Gate remains downstream

Required flow:

```text
FOOTBALL MODEL
     ↓
PREDICTIONS FOR EVERY ELIGIBLE GAME/MARKET
     ↓
FAIR PRICES
     ↓
MARKET COMPARISON
     ↓
EDGE
     ↓
RISK / UNCERTAINTY
     ↓
RECOMMENDATION GATE
     ↓
BET / LEAN / PASS / AVOID
```

Do not generate predictions only for markets the Recommendation Gate likes.

Every supported prediction is still:

```text
stored
evaluated
settled
included in learning/performance analysis
```

including PASS/AVOID outputs.

## F-14.31 Long-term target hierarchy

### Generation 1

```text
Game Outcome
Margin
Total
Scores
```

### Generation 2

```text
Drive Outcomes
Team Totals
1H / 1Q
```

### Generation 3

```text
Player Volume
Player Props
```

### Generation 4

```text
Play State Transitions
```

### Generation 5

```text
Football World Model

P(next state | current state, execution, players, environment)
```

The architecture should support this progression without a foundational redesign.

### F-14 status

**LOCKED V1.**

---

# F-10 through F-14 Integrated Dependency Graph

```text
                 EXTERNAL PROVIDERS
                         │
                         ▼
                  RAW EVIDENCE
                         │
                         ▼
               CANONICAL IDENTITY
                         │
                         ▼
               F-5 FOOTBALL LEDGER
                         │
          ┌──────────────┼──────────────┐
          │              │              │
          ▼              ▼              ▼
      PLAYERS          UNITS        COACHING
       F-7             F-8            F-9
          ▲              ▲              │
          │              │              │
       INJURY            │              │
        F-10 ────────────┘              │
          │                             │
          └─────────────┬───────────────┘
                        ▼
                   TEAM STATE
                      F-6
                        │
              ┌─────────┴─────────┐
              │                   │
              ▼                   ▼
         ENVIRONMENT           RECOVERY
            F-11                 F-12
              │                   │
              └─────────┬─────────┘
                        ▼
                   MATCHUP STATE
                        │
                        ▼
                FEATURE CONTRACT
                      F-13
                        │
                        ▼
                     MODELS
                        │
                        ▼
              TARGET DISTRIBUTIONS
                      F-14
                        │
                ┌───────┴───────┐
                ▼               ▼
          FAIR PRICES        SIMULATION
                │
                ▼
             MARKET
                │
                ▼
               EDGE
                │
                ▼
        RECOMMENDATION GATE
                │
                ▼
       BET / LEAN / PASS / AVOID
```

---

# Cross-Cutting Requirement — Event-Driven Dependency-Aware Recalculation

Daily NFL should not blindly rerun the entire modeling stack on a fixed timer whenever any input changes.

The system should understand which node in the state graph changed and recompute only affected downstream artifacts.

## Injury example

```text
NEW INJURY REPORT
      ↓
identify affected player(s)
      ↓
rebuild affected Player State
      ↓
rebuild affected Unit State
      ↓
rebuild affected Team / Matchup State
      ↓
rerun affected Prediction(s)
```

## Weather example

```text
MATERIAL WEATHER CHANGE
      ↓
identify affected stadium/game
      ↓
new Environment Snapshot
      ↓
rebuild Matchup State
      ↓
rerun affected Prediction(s)
```

## Odds example

```text
NEW ODDS
      ↓
DO NOT rebuild football player/unit/team state
      ↓
update market quote / fair-price comparison
      ↓
recompute edge, value, and Recommendation Gate
```

A sportsbook moving a line from `-2.5` to `-3` is not a reason to recompute player talent or offensive-line state.

## Dependency graph

```text
                    STATE GRAPH

 Injury ───────► Player ───► Unit ───► Team ───┐
                                               │
 Coaching ─────────────────────────────────────┤
                                               ▼
 Weather ────────────────────────────────► Matchup
                                               │
 Travel ─────────────────────────────────►     │
                                               ▼
                                           Prediction
                                               │
 Odds ─────────────────────────────────────────►
                                               ▼
                                          Value / Gate
```

This requirement should influence future cache invalidation, artifact lineage, orchestration, and event-bus design.

---

# Locked Decisions from F-10 through F-14

1. Injury reports are observations, not latent injury truth.
2. Availability, expected participation, and expected effectiveness are separate quantities.
3. Player health state is probabilistic until legitimate pregame information resolves uncertainty.
4. Official game-day information arriving before kickoff is valid for later pregame snapshots.
5. Earlier prediction snapshots are immutable.
6. Injury effects propagate through player, unit, team, matchup, and potentially scheme state rather than a single team injury score.
7. Weather is context, not intrinsic team quality.
8. Forecast snapshots and actual weather remain separate.
9. Roof capability and actual roof state are separate.
10. Outdoor weather and the actual playing environment are separate.
11. Travel/rest/recovery exposures are represented directly before estimating their predictive effect.
12. No folklore-based travel or rest penalties are hard-coded without validated evidence.
13. Recovery can be player- and position-conditioned.
14. Every feature requires semantic, temporal, provenance, missingness, era, and version metadata.
15. Feature lineage must remain auditable from raw evidence through model input.
16. Feature contracts are versioned by information era.
17. Football-only and market-aware feature contracts remain explicitly separate.
18. Missingness states are semantically distinct and must not be blindly zero-filled.
19. Daily NFL models football outcome truth separately from sportsbook settlement.
20. The long-term primary game target is a coherent joint scoring distribution or equivalent simulation distribution.
21. Margin, totals, moneyline, alternate lines, and team totals should be derived from that coherent distribution where possible.
22. Player props should model participation/opportunity dependencies before final statistics.
23. Sportsbook settlement is generated per quote/ruleset from one canonical football truth.
24. Closing market information is evaluation data for earlier snapshots unless it was genuinely available to that prediction.
25. Prediction horizons create separate immutable predictions for the same future game.
26. Every eligible game/market prediction remains stored and evaluated regardless of Recommendation Gate output.
27. Recommendation Gate remains downstream of prediction, fair pricing, market comparison, edge, risk, and uncertainty.
28. State recomputation should be event-driven and dependency-aware rather than blindly full-stack on every data change.
29. New odds alone should usually recompute market/value/gate layers, not football-state layers.
30. The architecture must support progression from game models to drive models, player props, play-transition models, and eventually a football-native world model without foundational redesign.

---

# Next Architecture Block

The next planned block is:

```text
F-15  Baseline Model Architecture
F-16  Advanced Model Architecture
F-17  Simulation Engine
F-18  Betting-Market Model Architecture
F-19  Calibration & Evaluation Framework
```

Those sections will convert the state/feature/target contracts defined through F-14 into concrete mathematical and model families.