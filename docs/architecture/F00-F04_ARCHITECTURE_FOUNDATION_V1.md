# Daily NFL Architecture Foundation

**The Daily Line — Daily NFL**  
**F-0 through F-4 — Version 1.0**

## Purpose

This document records the governing architecture decisions for Daily NFL before implementation begins. It is intended to prevent later code from silently redefining the scientific, data, identity, or historical point-in-time assumptions of the product.

Daily NFL is a sport-specific intelligence engine under The Daily Line. Cross-sport infrastructure belongs in `Daily-Data-Core`; football-native modeling belongs in `Daily-NFL`.

> **Critical PIT clarification:** There is no blanket prohibition on “Sunday data.” A prediction snapshot may use any information whose defensible availability timestamp is at or before that snapshot’s prediction time. Daily NFL will continuously monitor pregame inputs and create or update prediction snapshots as information changes until kickoff. Information first available after kickoff is excluded from pregame predictions.

---

# Governing Decisions

| Decision | Locked Rule | Owner |
|---|---|---|
| Repository boundary | Sport-agnostic infrastructure belongs in `Daily-Data-Core`; football intelligence belongs in `Daily-NFL`. | Core / NFL |
| Prediction philosophy | Estimate calibrated probability distributions, not merely pick winners. | Daily-NFL |
| Coverage rule | Predict every eligible supported game/market; Recommendation Gate decides BET / LEAN / PASS / AVOID. | Core + NFL |
| Provider rule | Providers populate canonical contracts; providers never define the architecture. | Core + NFL |
| Evidence rule | Immutable raw evidence precedes normalization and feature engineering. | Daily-Data-Core |
| Identity rule | Internal canonical IDs are primary; all provider IDs are crosswalks. | Core + NFL |
| PIT rule | Every feature must be defensible as available by the prediction snapshot timestamp. | Core + NFL |
| Pregame monitoring | Continuously observe injuries, inactives, weather, roster/depth changes, market movement, and other relevant changes until kickoff. | Core + NFL |
| History rule | Retrospective event truth and historical knowledge state are distinct concepts. | Daily-NFL |
| Evaluation rule | Primary final validation uses chronological / walk-forward evaluation, not random train/test splits. | Daily-NFL |

---

# Repository Boundary: Daily-Data-Core vs Daily-NFL

The Daily Line should have one shared cross-sport platform and separate sport-native intelligence engines. `Daily-MLB` is a useful reference implementation, but reusable components should be extracted selectively rather than cloned wholesale.

## Daily-Data-Core owns

- provider/provenance framework
- immutable raw evidence storage
- checksums and raw-artifact addressing
- run/job lifecycle
- generic identity and provider crosswalk primitives
- odds, sportsbooks, markets, and market snapshots
- implied probability, no-vig, and generic fair-market utilities
- weather acquisition and forecast snapshots
- venues, geospatial coordinates, and time zones
- travel and rest primitives
- generic prediction records
- Recommendation Gate contract
- settlement and performance ledger
- generic observation/revision semantics
- common acquisition reliability metadata

## Daily-NFL owns

- NFL seasons, phases, weeks, schedules, and games
- franchises and team-seasons
- rosters and roster stints
- NFL player/team/coach reconciliation rules
- injuries, practice participation, inactives, and depth charts
- possessions, drives, plays, events, and participation
- player state
- unit state
- coaching and scheme state
- football matchup state
- football feature contracts
- football model targets
- football prediction models
- football simulation
- football-specific evaluation

`Daily-MLB` already demonstrates several reusable ideas worth extracting into the Core: canonical run IDs, immutable raw provider payloads, checksums, odds/weather collectors, migrations, snapshot persistence, exports, and failure capture. Baseball-specific state, player identity rules, stadium effects, Statcast, lineups, pitchers, and baseball features remain in `Daily-MLB`.

---

# F-0 — Scientific Mission & Modeling Philosophy

**Status: LOCKED V1**

## F-0.1 Primary mission

Daily NFL exists to estimate the **true probability distribution of future NFL outcomes using only information legitimately available at the prediction time**.

Sports betting is the immediate application. The deeper modeling problem is:

> Given everything legitimately knowable at prediction time T, what distribution of possible football games can occur?

The system therefore should not be designed as a collection of isolated yes/no pick generators. It should evolve toward a probabilistic representation of the game capable of supporting multiple markets from a coherent underlying state.

Primary outputs eventually include:

- `P(home win)` / `P(away win)`
- expected home score
- expected away score
- score distribution
- margin distribution
- total distribution
- probability of covering any supported spread
- probability of clearing any supported total
- team-total distributions
- first-half / first-quarter distributions
- player-stat distributions
- drive-level and scoring-event distributions
- alternative-line probabilities
- eventually same-game dependency structures

The long-term architecture should permit football world modeling without forcing that level of complexity into the initial baseline.

## F-0.2 Predict everything; recommend selectively

Every eligible NFL game receives predictions. Every supported market receives a prediction whenever its minimum data contract is satisfied.

The Recommendation Gate occurs **after** prediction, value, uncertainty, and risk evaluation:

```text
Prediction
    ↓
Probability Distribution
    ↓
Fair Price
    ↓
Sportsbook Market Price
    ↓
Edge
    ↓
Uncertainty / Risk
    ↓
Recommendation Gate
    ↓
BET / LEAN / PASS / AVOID
```

`PASS` and `AVOID` predictions are not discarded. They remain first-class observations and must be stored, settled, and included in calibration, CLV, gate-effectiveness, and profitability analysis.

This allows later questions such as:

- Did the Recommendation Gate improve ROI compared with blindly betting model edge?
- Are PASS predictions better or worse calibrated than BET predictions?
- Which uncertainty classes cause false positive edges?
- Does the gate improve performance consistently or only in certain market regimes?

## F-0.3 Optimization hierarchy

The model-quality hierarchy is:

1. Data correctness
2. Point-in-time correctness
3. Probability calibration
4. Distributional accuracy
5. Generalization
6. Market discrimination
7. Closing-line value
8. Betting profitability

W/L record alone is insufficient.

Evaluation should include, as appropriate:

- log loss
- Brier score
- calibration error / calibration curves
- CRPS or other distributional scoring rules
- interval coverage
- MAE/RMSE for score or margin where appropriate
- CLV
- ROI
- performance by confidence/uncertainty band
- performance by market type, season, month, favorite/underdog status, venue context, and model era

## F-0.4 Football is a hierarchical state system

A team is not adequately represented by one scalar rating.

Daily NFL should ultimately represent interacting state across:

- quarterback
- offensive line
- running-back room
- receiving unit
- tight ends
- defensive front
- pass rush
- linebackers
- secondary
- coverage unit
- special teams
- coaching
- scheme
- personnel usage
- injuries / availability
- roster depth
- rest
- travel
- environment
- opponent interactions

These states create team behavior; team behavior produces plays and drives; plays and drives create score distributions and game outcomes.

Long-term modeling direction:

```text
Player State Models
        ↓
Unit Models
        ↓
Matchup Models
        ↓
Play / Drive Models
        ↓
Game Simulation
        ↓
Market Probabilities
```

## F-0.5 Separate football information from market information

Daily NFL should preserve at least two explicit forecasting tracks.

### Football-only fair model

Uses football/context information but does not use the sportsbook market as a feature source.

Outputs independent estimates such as:

- win probability
- score distribution
- margin distribution
- total distribution

### Market-aware model / ensemble

May incorporate information such as:

- opening price
- market consensus
- line movement
- sportsbook disagreement
- timing of price changes
- future liquidity/reliability proxies

Markets contain genuine information. Ignoring them entirely would discard signal. But their influence must remain explicit so the system never compares a sportsbook line against a disguised copy of itself.

Every prediction should identify whether it is:

- `FOOTBALL_ONLY`
- `MARKET_AWARE`
- `ENSEMBLE`

## F-0.6 Uncertainty is first-class

A point estimate is insufficient.

For every forecast, Daily NFL should eventually preserve relevant forms of:

- predictive variance
- model uncertainty
- input uncertainty
- availability uncertainty
- injury/lineup uncertainty
- data-quality uncertainty
- simulation uncertainty

Two forecasts with the same 63% mean probability but radically different uncertainty are not equivalent betting situations.

The Recommendation Gate should be able to use uncertainty explicitly.

## F-0.7 Continuous research architecture

Daily NFL must be designed for continuous improvement rather than freezing when a profitable baseline is achieved.

Expected progression:

```text
Baseline Team Models
      ↓
Richer Feature Engineering
      ↓
Player / Unit State Models
      ↓
Play and Drive Models
      ↓
Sequence Models
      ↓
Tracking / Spatial / Mechanical Models
      ↓
Football World Model
```

New research should augment the architecture without requiring wholesale replacement of the platform.

## F-0.8 Reproducibility

Every published prediction should eventually be reproducible from:

- model version
- code version / commit
- feature-contract version
- source dataset versions
- raw evidence identifiers/checksums
- feature snapshot
- prediction timestamp
- market snapshot
- configuration
- random/simulation seed where applicable

The system must be capable of explaining why a prediction existed in the form it did at that point in time.

---

# F-1 — NFL Domain Ontology

**Status: LOCKED V1**  
Detailed play schema is deferred to F-5.

## F-1.1 Core hierarchy

The fundamental football hierarchy is:

```text
Competition
   ↓
Season
   ↓
Season Phase
   ↓
Week
   ↓
Game
   ↓
Possession
   ↓
Drive
   ↓
Play
   ↓
Play Event
   ↓
Participation
```

This hierarchy is a model of football reality, not a mirror of any one provider schema.

## F-1.2 Game is separate from result

A `Game` represents the scheduled sporting event.

Example game fields:

- internal game ID
- competition
- season
- season phase
- week
- home team-season
- away team-season
- venue
- scheduled kickoff
- actual kickoff
- status
- neutral-site flag

The result is a separate state/object containing fields such as:

- final home score
- final away score
- overtime state
- winner
- final timestamp

Final-result information must not live in a form that can accidentally enter a pregame feature query.

## F-1.3 Franchise is separate from team-season

Historical identity should distinguish a persistent franchise from its season-specific competitive state.

```text
Franchise
    ↓
Team Season
```

A team-season can contain season-specific name, abbreviation, conference, division, home venue, roster context, and coaching regime without destroying franchise continuity.

## F-1.4 Person is separate from player stint

A person is persistent. Their team relationship changes.

The architecture therefore distinguishes:

- person
- player identity
- roster stint
- team-season membership

A person may have multiple roster stints across teams and seasons without receiving a new canonical person identity.

## F-1.5 Player state

A player's current state is not merely a season average.

Long-term player state may include:

- talent baseline
- current performance
- role
- snap share
- usage
- health
- practice participation
- workload
- fatigue
- matchup context
- position
- position-specific skill state
- uncertainty

Player state always means state **as of prediction time**.

## F-1.6 Unit state

Football requires explicit unit modeling.

Initial unit concepts include:

- quarterback
- offensive line
- receiving unit
- backfield
- defensive front
- pass rush
- linebacker unit
- secondary
- coverage unit
- special teams

Matchups can therefore represent interactions such as pass protection vs pass rush, receiving separation vs coverage ability, rushing efficiency vs front integrity, and similar football-native relationships.

## F-1.7 Coaching and scheme are modeled entities/state

Coaching should not be reduced to free-text notes.

The system should support staff identity and role, including:

- head coach
- offensive coordinator
- defensive coordinator
- special-teams coordinator
- later position coaches where useful

Scheme state may eventually include:

- offensive tendencies
- defensive tendencies
- pace / tempo
- neutral pass rate
- motion
- play action
- personnel usage
- blitz rate
- coverage families
- fourth-down aggression
- red-zone behavior

Coaching changes and regime changes must be explicit historical events.

## F-1.8 Injury report is not injury truth

An injury report is an observation, not a direct measurement of exact player ability.

Example observed information:

```text
Player X
Hamstring
Limited Practice
Questionable
```

is distinct from a latent estimate of player availability/performance state.

Daily NFL may eventually infer a `PLAYER_AVAILABILITY_STATE` using injury observations, practice participation, snap history, inactive status, role, historical injury patterns, and future richer information.

## F-1.9 Depth chart is not actual participation

Published depth charts and observed on-field participation are separate data families.

The system should retain both rather than treating depth-chart order as truth about actual snap allocation.

## F-1.10 Football state graph

Conceptually:

```text
                GAME
                  │
        ┌─────────┴─────────┐
        │                   │
      TEAM A              TEAM B
        │                   │
  players/units/coaches  players/units/coaches
        │                   │
 health/scheme/usage    health/scheme/usage
        │                   │
        └─────────┬─────────┘
                  │
               MATCHUPS
                  │
              ENVIRONMENT
                  │
              GAME STATE
                  │
               DRIVES
                  │
                PLAYS
                  │
               RESULT
```

---

# F-2 — Data Source & Acquisition Architecture

**Status: LOCKED V1**

## F-2.1 Provider abstraction

`nflverse` / `nflreadpy` should be major initial providers and historical bootstrap sources, not the architecture itself.

Models and domain services should request capabilities from provider interfaces rather than importing a specific provider library throughout the codebase.

```text
NFL Application
      ↓
Domain Service
      ↓
Provider Interface
      ↓
Provider Adapter(s)
```

This permits later replacement, fallback, commercial data, official sources, or multi-provider reconciliation without rewriting the model layer.

## F-2.2 Provider capability registry

Each provider/dataset should have machine-readable metadata including, where applicable:

- provider
- dataset
- entity coverage
- field coverage
- earliest season
- latest season
- update cadence
- expected latency
- historical availability
- PIT fidelity
- reliability tier
- schema version
- license
- attribution requirements
- cost class

Different datasets have different historical coverage and must not be treated as if the 1999 information environment were equivalent to the modern NFL information environment.

## F-2.3 Source tiers

### Tier A — Foundational historical NFL data

Initial emphasis may include nflverse/nflreadpy data for:

- play-by-play
- schedules
- players
- rosters
- weekly rosters
- player/team statistics
- injuries where available
- depth charts where available
- snap counts
- participation
- Next Gen Stats where available
- advanced position statistics / charting where licensing permits

### Tier B — Daily Data Core

Daily NFL consumes cross-sport inputs from `Daily-Data-Core`, including:

- odds
- sportsbooks
- markets
- market snapshots
- implied probability / no-vig
- weather forecasts and snapshots
- venues
- coordinates
- time zones
- travel
- rest
- generic provider provenance
- immutable raw evidence
- run lifecycle
- settlement

### Tier C — Live NFL state

Provider adapters must eventually support continuously updated information such as:

- schedule updates
- transactions
- practice reports
- injury designations
- depth-chart changes
- inactive lists
- roster state
- starting personnel information where available
- game status

The provider may change; the canonical contract may not.

### Tier D — Enrichment

Future enrichment can include:

- Next Gen Stats
- richer participation
- charting
- advanced position metrics
- tracking-derived data
- film/computer vision
- biomechanics/mechanical state

Dataset licensing and attribution are data attributes, not forgotten documentation notes.

## F-2.4 Raw evidence first

All provider acquisition follows:

```text
Provider
   ↓
RAW RESPONSE
   ↓
Immutable Evidence Store
   ↓
Normalization
   ↓
Canonical NFL Schema
   ↓
Feature Engineering
```

Never design a pipeline that goes directly from provider payload to feature table while discarding the original evidence.

## F-2.5 Provenance on normalized observations

Normalized observations should be traceable to fields such as:

- source provider
- source dataset
- source record ID
- source published timestamp
- source observed timestamp
- ingestion timestamp
- raw SHA-256
- raw artifact ID/location
- provider schema version
- parser version
- license ID

The system must be able to answer, “Where did this value come from?”

## F-2.6 Conflicting providers are not silently overwritten

If two providers disagree, retain both observations and reconcile them into a canonical state using explicit rules.

Canonical reconciliation should be able to retain:

- source observations
- chosen canonical state
- confidence
- resolution method/rule

Provider disagreement may itself later be useful information.

## F-2.7 Acquisition flow

```text
                EXTERNAL DATA
                     │
     ┌───────────────┼────────────────┐
     │               │                │
 NFL providers     Core odds       Core weather
     │               │                │
     └───────────────┼────────────────┘
                     │
               RAW EVIDENCE
                     │
                CHECKSUM
                     │
               NORMALIZATION
                     │
               RECONCILIATION
                     │
               NFL CANONICAL DB
                     │
              PIT STATE BUILDER
                     │
              FEATURE FACTORY
                     │
                  MODELS
```

---

# F-3 — Canonical Identity & Reconciliation

**Status: LOCKED V1**

## F-3.1 Governing identity rule

> External provider IDs must never become The Daily Line's permanent canonical identity.

Provider IDs are crosswalks into internal entities.

GSIS and other high-quality IDs will be heavily used, but no external provider controls the permanent ontology.

## F-3.2 Core canonical identities

`Daily-Data-Core` should own generic cross-sport identities such as:

- sport ID
- competition ID
- organization ID
- person ID
- venue ID
- event ID
- provider ID
- observation ID
- market ID
- sportsbook ID

## F-3.3 NFL identities

`Daily-NFL` extends the Core with football-native identities such as:

- franchise ID
- team-season ID
- player ID
- roster-stint ID
- coach-role ID
- NFL game ID
- drive ID
- play ID
- play-event ID
- injury-observation ID
- depth-chart-snapshot ID
- participation ID

## F-3.4 External ID crosswalk

The crosswalk framework should support records conceptually containing:

```text
entity_id
provider
provider_entity_type
external_id
valid_from
valid_to
match_method
match_confidence
verified
```

One internal person can therefore map to GSIS, ESPN, PFR, PFF, OTC, or future provider identities without multiplying the actual person entity.

## F-3.5 Never fuzzy-match silently

Ambiguous identity reconciliation must fail into an explicit unresolved state rather than silently selecting the closest match.

Unresolved identity records should preserve:

- candidate matches
- matching evidence
- confidence
- provider
- source row/raw evidence

This is required to prevent subtle historical contamination.

## F-3.6 Game identity

A Core sporting event and an NFL game representation can be linked while external provider event/game IDs remain crosswalks.

For example:

```text
CORE EVENT
  event_id
      │
NFL GAME
  game_id
      │
provider crosswalks:
  nflverse_game_id
  odds_provider_event_id
  future commercial IDs
```

Natural fingerprints such as season, week, teams, date, and venue may assist matching, but they are reconciliation evidence—not permanent identity—because schedules can change.

## F-3.7 Play identity and revisions

A football play receives an internal `play_id`.

Provider play identifiers, sequence number, drive, and contextual information help reconcile it.

If a provider later corrects or revises the play, the architecture should preserve revisions/observations attached to the same canonical football play when appropriate rather than accidentally creating a different play.

## F-3.8 Core vs NFL responsibility

The generic entity/provider/external-identity/crosswalk/confidence/provenance framework belongs in `Daily-Data-Core`.

Football-specific reconciliation rules belong in `Daily-NFL`, including:

- GSIS player reconciliation
- franchise history
- roster/depth person matching
- NFL game matching
- drive/play reconciliation

---

# F-4 — Historical Point-in-Time Architecture

**Status: LOCKED V1**

F-4 is a governing scientific constraint. If PIT reconstruction is wrong, historical model results are not considered valid regardless of apparent profitability.

## F-4.1 Governing question

Every historical prediction must answer:

> What could Daily NFL legitimately have known at this exact prediction time?

That is different from asking what is known today about the historical game.

## F-4.2 Prediction-time rule — corrected and locked

There is **no blanket prohibition on Sunday data, game-day data, or late pregame data**.

For a prediction snapshot at time `T`, the system may use any input whose defensible `available_at <= T`, subject to the feature contract and real-world validity rules.

Therefore information such as the following is valid for a later pregame snapshot if it was genuinely available before that snapshot was created:

- Sunday morning injury updates
- official inactive lists released before kickoff
- late roster/depth changes
- Sunday/game-day weather forecast updates
- pregame market movement
- last-minute but public quarterback/player status changes
- venue/roof/status updates when timestamped and known

The prohibition is instead:

> **Never use information that was not yet available at the prediction snapshot timestamp. Never use information first available after kickoff in a pregame prediction.**

This means an early snapshot remains historically frozen while a later snapshot may legitimately contain additional pregame information.

## F-4.3 Continuous pregame monitoring

Daily NFL is not a once-per-day static model.

Like the Daily MLB architecture, it must continuously monitor material data streams before game time.

Conceptually:

```text
Pregame monitoring begins
        ↓
Acquire / observe sources repeatedly
        ↓
Detect material changes
        ↓
Persist new observation with timestamps
        ↓
Reconcile canonical state
        ↓
Determine affected feature snapshots/games
        ↓
Recompute affected prediction(s)
        ↓
Re-evaluate edge / uncertainty / Recommendation Gate
        ↓
Continue until kickoff lock
```

Monitoring targets eventually include:

- injury reports
- practice participation
- status changes
- transactions
- depth charts
- official inactives
- starting personnel information where available
- weather forecasts
- roof/venue state where relevant
- odds and market movement
- sportsbook availability
- schedule/kickoff changes
- other material football/context signals

The architecture should support change-driven recomputation rather than requiring blind full-system rebuilds for every update.

## F-4.4 Four temporal clocks

Where possible, observations preserve four separate clocks:

### `effective_at`
When the fact/state became true in football reality.

### `published_at`
When the source states the information became public/published.

### `observed_at`
When The Daily Line acquisition system first observed it.

### `ingested_at`
When The Daily Line persisted it.

These timestamps must not be treated as interchangeable.

## F-4.5 `available_at`

For modeling, each input should have an explicit or derivable:

```text
available_at
```

This represents the earliest defensible timestamp at which the model could have known the information.

Also preserve:

- availability method
- availability confidence

Possible methods include:

- source timestamp — high confidence
- archived release timestamp — high confidence
- our first observation timestamp — high confidence for production monitoring
- inferred report timestamp — medium confidence
- unknown — low confidence / generally excluded from strict PIT training

## F-4.6 Append-only revisions

Historical state must not be invisibly overwritten.

If a player is active in one observation and later released/inactive in another, preserve the revision history.

Similarly, corrected provider data should be represented as new observations/versions with temporal provenance rather than destructive updates that erase what was previously known.

## F-4.7 Bitemporal thinking

The architecture distinguishes:

- **real-world history** — when something was true
- **knowledge history** — when The Daily Line could know it

These clocks can differ.

A fact may have been true before it became public. Pregame modeling may only use the information once it crossed the knowledge boundary.

## F-4.8 Standard prediction horizons

For research and historical reconstruction, Daily NFL should support standardized forecast horizons such as:

- `T-168h` — early week
- `T-72h` — midweek
- `T-24h` — day before
- `T-6h` — game day
- `T-90m` — late pregame / inactive-list era
- `T-15m` — final pregame model lock candidate

These are research/reference snapshots, not a rule that production may only update at these times.

Production monitoring can update whenever material information changes until kickoff.

Standard horizons allow measurement of information value over time, for example:

- improvement from injury information between T-72 and T-24
- value of official inactive information near T-90m
- value of updated game-day weather
- information gained from market movement
- changes in calibration and edge as kickoff approaches

## F-4.9 Historical reconstruction

For game `G` and prediction time `T`, every input must satisfy its feature contract and be defensibly available by `T`.

Conceptually:

```text
FOR EVERY INPUT:
    available_at <= prediction_time
```

plus real-world validity/as-of rules.

Nothing that became available later may leak backward into that snapshot.

## F-4.10 Example — T-24 snapshot

Suppose kickoff is Sunday 1:00 PM and the reconstructed prediction time is Saturday 1:00 PM.

The snapshot may use information known by Saturday 1:00 PM, including:

- all completed prior games
- team/player performance through prior games
- roster state known by then
- injury/practice observations published by then
- weather forecast available by then
- market observations available by then
- schedule, venue, travel, and rest information known by then

It may not use information first published/observed after Saturday 1:00 PM.

Importantly, this does **not** imply that Sunday information is globally disallowed. A later Sunday snapshot may use Sunday information if it was available before that later prediction time.

## F-4.11 Kickoff boundary

For all pregame products, kickoff is the final hard temporal boundary unless a separate live-betting/in-game product is explicitly created in the future.

Pregame models may not use:

- plays from the current game
- current-game snap counts
- current-game box score/statistics
- final score
- postgame injury diagnoses
- postgame corrections that were not knowable pregame
- actual realized weather when only forecast weather was knowable before kickoff, except as an evaluation/result field

A future in-game product would have a different state contract and is out of scope for this pregame architecture.

## F-4.12 Weather leakage

Actual observed game weather is not automatically equivalent to the forecast that was available before the game.

Historical feature reconstruction should use the forecast available at the relevant prediction time whenever the production system would have used a forecast.

If historical forecast snapshots cannot be defensibly reconstructed:

1. obtain a historical forecast archive where possible;
2. omit the feature from strict PIT training/evaluation; or
3. label the experiment explicitly as non-PIT.

Do not silently substitute realized weather for a pregame forecast.

## F-4.13 Injury/inactive leakage

Final weekly injury status is not automatically valid for an earlier prediction snapshot.

Each observation must be timestamped.

Official inactive information can be extremely valuable and should be used in late pregame snapshots when released before kickoff; it simply cannot be backfilled into earlier snapshots that predate its release.

## F-4.14 Market leakage and closing line

Market information is timestamp-specific.

At prediction time `T`, the model may use:

- opening market information if already available
- market snapshots observed up to `T`
- movement through `T`
- sportsbook disagreement through `T`

It may not use a market state first observed after `T`.

The closing line may be stored later as an evaluation reference for CLV. It may also be used by a model whose explicit prediction timestamp actually occurs at/near close and whose market-aware contract allows it. It must never leak backward into earlier snapshots.

## F-4.15 Retrospective truth vs historical knowledge

A modern dataset describing a historical game may contain corrected or enriched information that was not available before the historical kickoff.

Therefore Daily NFL distinguishes:

```text
RETROSPECTIVE EVENT TRUTH
```

from:

```text
HISTORICAL KNOWLEDGE STATE
```

A 2026 file describing a 2023 game does not prove every field inside it was knowable before that 2023 game.

This distinction governs strict historical PIT training and evaluation.

## F-4.16 Feature availability eras

Because NFL data coverage changes over time, Daily NFL should maintain explicit feature-availability eras rather than pretending all seasons have modern information density.

Conceptually:

- early play-by-play foundation era
- roster/depth enriched era
- snap-count enriched era
- Next Gen Stats enriched era
- modern participation/charting/tracking enriched era

Exact boundaries are dataset-specific and belong in the provider capability registry / feature contracts.

Different model contracts may therefore coexist, such as:

### `NFL_BASELINE_V1`
- schedule
- play-by-play aggregates
- team strength
- QB history
- basic roster state where defensible
- rest
- venue
- permitted market/context features

### `NFL_ADVANCED_V1`
- baseline features
- richer snap participation
- richer position state
- depth-chart state
- injury/availability state

### `NFL_MODERN_V1`
- advanced features
- NGS
- richer charting
- richer matchup features
- modern participation

### Future `NFL_WORLD_V1`
- tracking
- spatial representations
- mechanics
- sequence state
- play/drive world-model inputs

Missing historical information is handled by explicit feature contracts/eras, not by leaking modern information backward.

## F-4.17 Leakage tests

Before a historical feature bundle is accepted for training/evaluation, automated tests should fail closed on conditions such as:

1. source availability after prediction timestamp
2. current-game final score present in pregame input
3. current-game player/team statistics present in pregame input
4. current-game EPA/play outcomes present in pregame input
5. post-prediction roster changes leaked backward
6. post-prediction injury/inactive updates leaked backward
7. later depth-chart revisions leaked backward
8. post-prediction weather forecasts leaked backward
9. realized weather masquerading as forecast
10. later/closing market data leaked into an earlier snapshot
11. end-of-season aggregate used in a midseason prediction
12. future opponent/game information improperly included
13. future-season/week labels used during training in a way that leaks outcomes
14. provider correction with unknown historical availability admitted to a strict PIT contract without explicit authorization

Violations should **FAIL CLOSED**, not warn-and-continue.

## F-4.18 Immutable feature snapshots

Each prediction should eventually reference an immutable feature snapshot containing at least:

- prediction ID
- game ID
- prediction timestamp
- feature contract
- feature version
- feature values
- input observation IDs
- provider/source versions
- raw evidence/checksums where applicable
- coverage report
- missing features
- PIT validation result

This permits exact reconstruction of historical model inputs.

## F-4.19 Walk-forward evaluation

Final football evaluation should use chronological / rolling-origin methods.

Conceptually:

```text
Train on past
    ↓
Predict future
    ↓
Advance clock
    ↓
Refresh/retrain according to production policy
    ↓
Predict next future period
```

Examples include season-level and ultimately week-by-week walk-forward simulations.

Random train/test splits may be useful for limited exploratory diagnostics but are not the governing final estimate of real-world forecasting performance.

## F-4.20 PIT architecture

```text
                     RAW HISTORY
                          │
                    OBSERVATIONS
                          │
              ┌───────────┴───────────┐
              │                       │
         EFFECTIVE TIME          AVAILABLE TIME
              │                       │
              └───────────┬───────────┘
                          │
                   PIT STATE ENGINE
                          │
                 prediction_time = T
                          │
                   AS-OF JOINS ONLY
                          │
                   FEATURE SNAPSHOT
                          │
                   LEAKAGE TESTS
                          │
                       MODEL
```

---

# Continuous Pregame Monitoring Contract

The following principle applies across The Daily Line and is explicitly adopted by Daily NFL:

> A sporting event is a changing information environment until the pregame cutoff. The system must continuously observe relevant data streams, timestamp changes, preserve prior states, and update affected predictions when new legitimate information becomes available.

The system therefore distinguishes **prediction snapshots**, not one mutable prediction with no history.

Example:

```text
T-72h prediction v1
    ↓ new injury report
T-24h prediction v2
    ↓ weather changes
T-6h prediction v3
    ↓ official inactives
T-90m prediction v4
    ↓ late market movement
T-15m final pregame prediction v5
    ↓
KICKOFF — pregame state locks
```

Earlier snapshots are not overwritten. They are retained for information-value research, calibration, market comparison, and reproducibility.

Material changes may also trigger intermediate updates between these reference horizons.

---

# Decisions Deferred to F-5 through F-9

The following are intentionally not fully frozen in this document:

- exact game/drive/play/event canonical schemas
- exact field-by-field play ontology
- team state calculations
- player state calculations
- unit state calculations
- coaching/scheme state calculations
- exact football feature definitions
- model families and hyperparameters
- simulation details

These are the next architecture layer:

- **F-5 — Game / Drive / Play Canonical Schemas**
- **F-6 — Team State Engine**
- **F-7 — Player State Engine**
- **F-8 — Unit State Engine**
- **F-9 — Coaching & Scheme State**

---

# V1 Lock

F-0 through F-4 are considered the governing V1 foundation for Daily NFL.

Later changes are allowed as evidence and research improve, but they should be made explicitly through versioned architecture changes rather than by silently changing implementation behavior.
