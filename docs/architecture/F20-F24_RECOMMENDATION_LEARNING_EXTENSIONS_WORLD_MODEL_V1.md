# Daily NFL Architecture V1 — F-20 through F-24

Status: **LOCKED V1**

This document completes the governing Daily NFL architecture from F-0 through F-24. It covers the Recommendation Gate, settlement and continuous learning loop, NFL-specific extensions, NCAAF portability rules, and the long-term Football World Model research charter.

The governing system-wide principles remain unchanged:

- Every supported game/market receives a prediction before any recommendation decision.
- BET / LEAN / PASS / AVOID are downstream recommendation states, never filters on whether predictions exist.
- PASS and AVOID predictions remain stored, settled, evaluated, calibrated, and included in future research.
- Point-in-time eligibility remains `available_at <= prediction_time < kickoff` for pregame models.
- Historical predictions are immutable; later information creates new snapshots rather than rewriting the past.
- Football-only, market-only, and market-aware modeling remain explicitly separated and auditable.
- Model promotion is governed by F-19 scientific evaluation, not by short-term ROI alone.

---

# F-20 — Recommendation Gate Architecture

## Mission

F-20 does **not** decide what Daily NFL predicts. Its job is to determine whether an already-generated prediction and a specific current market quote constitute a sufficiently strong, reliable, and risk-aware opportunity to recommend.

```text
FOOTBALL STATE
      ↓
MODEL
      ↓
PROBABILITY DISTRIBUTION
      ↓
FAIR PRICE
      ↓
MARKET COMPARISON
      ↓
EDGE / EV
      ↓
UNCERTAINTY / RISK
      ↓
F-20 RECOMMENDATION GATE
      ↓
BET / LEAN / PASS / AVOID
```

The forbidden architecture is:

```text
Recommendation Gate
      ↓
decide which games deserve predictions
```

Every supported prediction exists first.

## F-20.1 Prediction and recommendation are separate objects

`PREDICTION` remains a model artifact containing the game distribution, model/version, feature snapshots, information cutoff, uncertainty, and related provenance.

`RECOMMENDATION_DECISION` references an existing prediction plus a specific market quote and stores the downstream decision.

Conceptual recommendation object:

```text
RECOMMENDATION_DECISION

recommendation_id
prediction_id
market_quote_id

as_of

model_probability
market_probability
probability_edge
expected_value

model_uncertainty
data_uncertainty
model_disagreement
quote_age
edge_stability

gate_version
decision
reason_codes

created_at
```

Immutable.

## F-20.2 Canonical recommendation states

Initial states:

- `BET` — sufficient evidence exists to recommend the wager.
- `LEAN` — the model favors the side, but the opportunity does not satisfy full BET criteria.
- `PASS` — no sufficiently attractive risk-adjusted edge.
- `AVOID` — apparent numerical value may exist, but one or more conditions make the opportunity especially unreliable or unsuitable.

Possible AVOID drivers include severe information uncertainty, stale quotes, unresolved critical availability, material model disagreement, poor calibration regions, or low-quality data coverage.

## F-20.3 PASS/AVOID never erase the forecast

Example:

```text
BUF -3
Model cover probability = 51.8%
Gate decision = PASS
```

The 51.8% prediction is still stored and later settled/evaluated.

This enables scientific evaluation of whether the Gate adds value relative to all predictions.

## F-20.4 Gate inputs

The Gate may consume downstream information such as:

- model probability
- market fair probability
- probability edge
- expected value
- current price and line
- model uncertainty
- input/data uncertainty
- injury and lineup uncertainty
- weather uncertainty
- data quality
- model disagreement
- calibration-region evidence
- prediction horizon
- quote freshness/staleness
- market dispersion
- edge stability
- quote/provider quality

Future candidates may include liquidity proxies, sportsbook-specific information quality, and historical Gate performance.

## F-20.5 Edge stability

Final edge magnitude alone is insufficient.

Example A:

```text
T-24h  +4.1%
T-6h   +4.0%
T-90m  +4.2%
```

Example B:

```text
T-24h  +8.5%
T-6h   +2.0%
T-90m  +4.2%
```

Both may finish near +4.2%, but their information histories differ.

Track an `EDGE_HISTORY` with quantities such as:

```text
edge_mean
edge_variance
direction_changes
largest_revision
recent_revision
```

The empirical system determines whether stability is predictive; it is not assumed automatically.

## F-20.6 Model disagreement

An ensemble probability can conceal important disagreement.

Example:

```text
GBDT       61%
StateSpace 60%
Simulation 62%
```

is a different state from:

```text
GBDT       67%
StateSpace 52%
Simulation 64%
```

even if both ensembles output approximately 61%.

Expose model disagreement metrics such as prediction range, prediction standard deviation, and pairwise disagreement.

## F-20.7 Information uncertainty

`P(win)=58%` with confirmed lineups and high data coverage differs materially from `P(win)=58%` with unresolved QB/OL availability and unstable weather.

The Gate must be allowed to distinguish these cases without rewriting the original model probability.

## F-20.8 Calibration-aware Gate

F-19 subgroup/calibration evidence can inform F-20. If a model has historically been less reliable in a specific state, the Gate may reduce recommendation confidence while preserving the original prediction.

## F-20.9 Structured reason codes

Recommended initial reason-code families:

```text
EDGE_BELOW_THRESHOLD
EV_BELOW_THRESHOLD
HIGH_MODEL_DISAGREEMENT
HIGH_AVAILABILITY_UNCERTAINTY
STALE_MARKET
LOW_DATA_QUALITY
CALIBRATION_RISK
LINE_MOVED_PAST_VALUE
STRONG_EDGE_HIGH_CONFIDENCE
```

Multiple reason codes may apply.

## F-20.10 Transparent Gate V1

Gate V1 should be explicit and deterministic. Conceptually:

```text
if severe_data_quality_failure:
    AVOID
elif EV >= threshold and uncertainty <= threshold and quote_fresh:
    BET
elif edge_positive_but_below_full_threshold:
    LEAN
else:
    PASS
```

The thresholds are research parameters validated using historical/prospective evidence. Transparency gives us a stable control before introducing a learned Gate.

## F-20.11 Learned Gate later

Once enough timestamped predictions exist, test `RULE_GATE` vs `LEARNED_GATE`.

Possible learned outcomes may include future calibration quality, positive CLV, expected realized value, or risk-adjusted value. The learned Gate must not merely optimize which historical selections happened to win.

## F-20.12 Threshold optimization

Gate thresholds are tuned on prior validation data, not final test periods. Evaluate tradeoffs among probabilistic quality, CLV, bet frequency, risk, and ROI.

The business does not dictate the scientific threshold.

## F-20.13 Market movement after a recommendation

If `SF -2.5 -110` generates BET and the market later moves to `SF -4 -110`, the original BET remains historically intact. The new quote receives a new opportunity decision, which may be PASS.

Never rewrite the earlier recommendation.

## F-20.14 Recommendation lifecycle

Possible lifecycle:

```text
CREATED
ACTIVE
SUPERSEDED
CLOSED
SETTLED
```

`SUPERSEDED` means a newer prediction/quote exists, not that the prior decision was wrong.

## F-20.15 Bet sizing is separate

Keep:

```text
Recommendation Gate
```

separate from:

```text
Bankroll / Bet-Sizing Engine
```

The Gate answers whether the opportunity merits a recommendation. The sizing engine answers how much to risk.

Future research may evaluate flat staking, fractional Kelly, uncertainty-adjusted Kelly, portfolio optimization, and correlation-aware exposure limits.

## F-20.16 Correlated exposure

Examples such as team ML, team spread, team total, QB props, and game totals may be strongly correlated. A future portfolio-risk layer must model those shared factors instead of treating recommendations as independent.

### F-20 status

**LOCKED V1.**

---

# F-21 — Settlement & Continuous Learning Loop

## Mission

F-21 closes the system:

```text
PREDICTION
     ↓
RECOMMENDATION
     ↓
GAME
     ↓
FOOTBALL TRUTH
     ↓
MARKET SETTLEMENT
     ↓
MODEL EVALUATION
     ↓
GATE EVALUATION
     ↓
RESEARCH / RETRAINING
```

## F-21.1 Three separate ledgers

Maintain distinct:

```text
FOOTBALL RESULT LEDGER
MARKET SETTLEMENT LEDGER
MODEL PERFORMANCE LEDGER
```

Football truth, sportsbook grading, and model performance are related but not interchangeable.

## F-21.2 Football result ledger

Canonical game truth contains final score, period scores, overtime, winner/tie, finalization state, corrections, and eventually drive/play/player outcomes.

## F-21.3 Market settlement ledger

For each quote evaluated:

```text
MARKET_SETTLEMENT

quote_id
prediction_id
market
selection
line
price
book

WIN
LOSS
PUSH
VOID

settlement_rule_version
settled_at
```

## F-21.4 Settle PASS/AVOID opportunities too

This is mandatory for research. If a prediction exists for a market quote, the system can evaluate what happened whether the Gate returned BET, LEAN, PASS, or AVOID.

This enables comparisons such as:

```text
ALL model edges
vs
BET subset
vs
LEAN subset
vs
PASS subset
vs
AVOID subset
```

## F-21.5 Closing-market truth

Preserve closing quote, closing consensus, and closing no-vig probability separately from game result.

This yields two distinct learning questions:

1. Did the model beat the market?
2. Did the model predict football correctly?

## F-21.6 Corrections are versioned

Official stat/result corrections create new result/settlement versions. Never silently overwrite historical truth.

Store original value, correction source, correction time, revised value, and dependent recalculations where applicable. Predictions remain unchanged.

## F-21.7 Learning dataset lineage

Research joins may combine:

```text
prediction
+ feature snapshot
+ football truth
+ market snapshot
+ closing market
+ recommendation decision
```

without destroying provenance.

## F-21.8 Retraining policy

Do not automatically retrain after every game. Support versioned policies such as weekly, every N games, monthly, season-boundary, drift-triggered, or research-only retraining.

## F-21.9 No self-reinforcing Gate loop

Never train future models only on BET selections. The Gate is a decision layer, not the definition of reality. Valid training data must preserve the full historical prediction/truth universe appropriate to the model.

## F-21.10 Negative research results are retained

Failed feature families and model hypotheses remain recorded so future research does not repeatedly rediscover the same negative result.

Conceptual record:

```text
RESEARCH_DECISION

hypothesis
experiment_id
result
decision

PROMOTE
REJECT
RETEST
DEFER
```

## F-21.11 Provider-quality learning

Evaluate providers for latency, coverage, accuracy, correction rates, identity failures, and PIT fidelity. Data-source selection should become evidence-based.

## F-21.12 Feature and concept drift

Monitor both feature distributions and the relationship `P(Y|X)` over time. Football evolves through rules, strategy, player usage, scoring environment, kickoff changes, and other structural changes.

`ruleset_version` remains part of the causal/temporal context.

## F-21.13 Retraining is not promotion

A retrained model becomes a Challenger first. F-19 promotion gates still apply.

## F-21.14 Shadow learning loop

```text
Champion
      ↓
public predictions

Challengers
      ↓
shadow predictions

ALL
      ↓
settlement
      ↓
evaluation
```

This creates prospective evidence for model research.

## F-21.15 Continuous improvement cycle

```text
OBSERVE
   ↓
MODEL
   ↓
PREDICT
   ↓
SETTLE
   ↓
MEASURE
   ↓
DIAGNOSE
   ↓
RESEARCH
   ↓
CHALLENGE
   ↓
PROMOTE
   ↓
OBSERVE...
```

## F-21.16 No rewriting historical published predictions

If a future model version is better, it does not replace what Daily NFL actually predicted historically. Retrospective backtests are stored separately from historical public predictions.

### F-21 status

**LOCKED V1.**

---

# F-22 — NFL-Specific Extensions

F-22 contains NFL-specific concepts that should not be pushed prematurely into Daily Data Core or a shared football package.

## F-22.1 Competition structure

Represent AFC/NFC, divisions, regular season, Wild Card, Divisional Round, Conference Championships, and Super Bowl explicitly.

## F-22.2 Division familiarity

Candidate evidence may include repeated meetings, coaching continuity, QB continuity, scheme familiarity, and roster overlap. Do not hard-code assumptions such as division games always being closer; test them.

## F-22.3 NFL roster mechanics

NFL-specific adapters should preserve semantics for active roster, practice squad, injured reserve, PUP, NFI, suspensions, elevations, activations, waivers, and related mechanisms.

## F-22.4 Practice-squad elevation

Practice-squad elevation can materially affect depth, special teams, and replacement assumptions even though it is not a normal acquisition. Preserve the event semantics.

## F-22.5 Transaction timeline

Track signed, released, waived, claimed, traded, elevated, activated, placed on reserve, and related transactions with effective and availability timestamps.

## F-22.6 Salary-cap / contract context

Contract/cap information belongs primarily in long-term/offseason roster-state research, not the initial pregame model. Potential future features include contract status, guarantees, cap constraints, expiring players, and franchise-tag state only where predictive value is demonstrated.

## F-22.7 Draft priors

Rookie priors may use draft position, position, age, college production, athletic testing, and prospect-model outputs. NFL evidence gradually overwhelms the prior as data accumulates.

## F-22.8 Free-agency priors

Player talent may partially persist after a team change while role, scheme, QB, OL, coaching, and teammates change. This reinforces the distinction between talent state and team-conditioned state.

## F-22.9 Tracking / Next Gen extensions

Modern enriched eras may incorporate speed, separation, time to throw, route geometry, defender spacing, rush timing, expected completion, and expected rushing outcomes where historically available and licensed.

## F-22.10 Participation extensions

Play-level participation can strengthen actual personnel-package, unit-configuration, matchup-assignment, and snap-specific player-state modeling.

## F-22.11 Advanced special-teams model

Long-term special-teams architecture may include field-goal distance distributions, kicker state, holder/snapper state, punt hang time/distance, return field position, kickoff geometry, coverage quality, and weather interactions.

## F-22.12 Fourth-down decision modeling

F-9 coaching policy can model probabilities of go/punt/field-goal conditional on game state. This becomes both coaching-state evidence and future simulation policy.

## F-22.13 Timeout and clock management

Candidate features include timeout preservation, timeout waste, late-half aggression, clock conservation, delay management, and challenge behavior. These require shrinkage and strong out-of-sample validation.

## F-22.14 NFL officiating

Officials/crew tendencies remain an experimental feature family subject to strict validation because these signals can overfit easily.

## F-22.15 Rule-change engine

NFL-specific rules need effective dates, version identifiers, and affected play families. Historical simulation must use the correct era's rules for kickoffs, overtime, extra points, clock behavior, onside kicks, and related changes.

## F-22.16 International games

International effects should be decomposed through travel, time zones, venue familiarity, surface, rest, and schedule sequencing rather than represented as one arbitrary fixed penalty.

## F-22.17 Playoffs

Possible differences in opponent quality, coaching behavior, fourth-down aggression, player usage, rest, and rules should be modeled through underlying mechanisms rather than arbitrary playoff multipliers.

## F-22.18 Offseason model

A future offseason state engine may produce Week 1 priors from previous-season state, retained snaps, QB continuity, coaching changes, draft, free agency, injuries, and age curves.

### F-22 status

**LOCKED V1.**

---

# F-23 — NCAAF Portability & College-Football Extensions

## Governing portability rule

Do **not** extract shared football code merely because we expect NFL and NCAAF to share concepts. Build Daily NCAAF as the second implementation, compare both systems, and extract only abstractions proven common by actual implementations.

## F-23.1 Likely shared conceptual layer

Potentially shared concepts include Game, Drive, Play, Play Execution, Participation, Player State, Unit State, Team State, Coaching State, Environment, Travel, Feature Contracts, Predictions, Simulation, and Evaluation.

Conceptual similarity does not automatically imply shared code today.

## F-23.2 NCAAF competition identity

College requires explicit FBS/FCS, conference, conference-championship, bowl, College Football Playoff, and neutral-site structures. Conference membership itself is historical/versioned.

## F-23.3 Program identity

College uses `Program` rather than NFL `Franchise`. A program may include school identity, athletic-department context, conference history, and stadium history.

## F-23.4 Player identity complexity

Identity must survive transfers, school changes, position changes, jersey-number changes, redshirts, and eligibility-year changes.

## F-23.5 Transfer portal

Transfers preserve some underlying talent while changing role, scheme, competition level, teammates, QB, OL, and coaching context. F-7's talent vs team-conditioned-state separation is directly reusable conceptually.

## F-23.6 Roster turnover

College offseason priors require stronger emphasis on returning production/starters, QB continuity, transfer additions/losses, recruiting, graduation, and NFL-draft departures.

## F-23.7 Recruiting priors

For players with limited college evidence, recruiting ratings, position, athletic testing, and high-school production where reliable may serve as priors with explicitly high uncertainty.

## F-23.8 Eligibility state

College player state may require eligibility year, redshirt status, medical eligibility where available, and transfer eligibility.

## F-23.9 Injury information quality

College injury reporting is less uniform across programs/eras. F-10's conceptual engine remains applicable but with more missingness, provider disagreement, program-specific reporting patterns, and uncertainty.

## F-23.10 Depth-chart uncertainty

Continue separating published depth chart, expected-starter probability, and actual participation.

## F-23.11 Strength-of-schedule adjustment

Opponent adjustment is especially critical because college opponent quality varies dramatically. Hierarchical strength-of-schedule modeling should be a central NCAAF design principle.

## F-23.12 Conference / level hierarchy

Possible hierarchical partial pooling:

```text
National
  ↓
FBS/FCS
  ↓
Conference
  ↓
Team
```

Conference effects remain historically versioned due to realignment.

## F-23.13 Blowout / garbage-time modeling

Large college score differentials require game-state-aware evaluation of performance and starter substitutions so garbage-time evidence does not contaminate underlying team/player state.

## F-23.14 Player substitutions

Participation-aware modeling must distinguish backup-heavy blowout snaps from evidence about starters.

## F-23.15 Coaching turnover

Track head coach, OC, DC, play caller, and relevant staff-history priors. College coaching transitions may be more frequent and structurally important.

## F-23.16 Scheme diversity

College football contains substantial scheme diversity, including tempo extremes, option concepts, spread systems, heavy personnel, Air-Raid-like systems, and QB-run-heavy offenses. Empirical scheme state may therefore be especially valuable.

## F-23.17 Home environment

Potential home-context factors include stadium, crowd, altitude, travel, campus environment, and surface. Do not collapse all programs into a single home-field constant without testing.

## F-23.18 Neutral-site ambiguity

Bowls, kickoff classics, rivalry games, conference championships, and playoff games may be officially neutral but not geographically/fan neutral. Future research can test campus distance, regional proximity, or similar variables where data support them.

## F-23.19 Schedule heterogeneity

FBS-vs-FCS games, strength disparities, uneven byes, independents, and conference/nonconference scheduling make opponent adjustment essential.

## F-23.20 College ruleset

NCAAF rules may differ from NFL in clock, overtime, roster rules, down mechanics, kickoffs, replay, eligibility, and related areas. `ruleset_version` remains mandatory.

## F-23.21 College market architecture

Maintain the same discipline:

```text
NCAAF FOOTBALL_ONLY
NCAAF MARKET_ONLY
NCAAF MARKET_AWARE
```

Measure market efficiency by team, conference, market type, and time-to-kickoff instead of assuming NFL-like behavior.

## F-23.22 Shared-code extraction rule

After Daily NCAAF exists:

```text
Daily-NFL
      ↘
   truly shared?
      ↗
Daily-NCAAF
```

If both implement the same semantic behavior, extract it into a shared football package. If the behavior is meaningfully different, leave it sport-specific.

### F-23 status

**LOCKED V1.**

---

# F-24 — Future Football World Model

## Long-term mission

F-24 is the research destination, not the first production model.

The goal is to model football as an evolving probabilistic world consisting of players, units, coaching policy, game state, environment, and interacting physical events.

The structured F-0 through F-23 architecture is the substrate and scientific control for this future system.

## F-24.1 World-state representation

At time `t`, world state `W_t` may contain:

```text
score
clock
field position
down/distance
timeouts
possession

player configuration
player latent states
unit states

coach policy
scheme

fatigue
health

environment
```

## F-24.2 Action policy

Coaching decisions can be represented as:

`A_t ~ π(A_t | W_t)`

Possible actions include run, dropback pass, play-action pass, RPO, screen, punt, field goal, fourth-down attempt, and eventually richer play-design choices.

## F-24.3 Execution layer

```text
PLAY DESIGN
      +
PLAYER STATES
      +
UNIT INTERACTIONS
      +
ENVIRONMENT
      ↓
EXECUTION
```

## F-24.4 Outcome transition

The world model targets:

`P(W_{t+1} | W_t, A_t)`

Possible transitions include yards, completion, pressure, sack, turnover, score, clock movement, field position, next down, and eventually injury events.

## F-24.5 Multi-scale hierarchy

```text
Career
  ↓
Season
  ↓
Week
  ↓
Game
  ↓
Drive
  ↓
Play
  ↓
Event
```

Slow-changing latent states and rapidly changing game states must coexist.

## F-24.6 Player latent state

Future player representations may include talent, health, fatigue, mobility, speed, role, mechanical state, and decision-state proxies where measurable. Some components will be directly observed; others will be inferred latent variables.

## F-24.7 Unit latent state

Unit state can encode coordination, continuity, scheme fit, communication, and interaction strength beyond summing individual player ratings.

## F-24.8 Coach policy model

F-9 evolves into a policy model `πθ(a|s)` capable of predicting likely decisions and eventually supporting counterfactual simulations of alternative decisions.

## F-24.9 Environment model

F-11 becomes an external physical state containing wind, temperature, precipitation, surface, roof, and other legitimate environmental conditions that influence execution probabilities.

## F-24.10 Tracking / spatial encoder

Future tracking representations may include all player positions, ball location, velocities, accelerations, and orientation where available. This could enable learned representations of coverage spacing, rush lanes, blocking geometry, receiver leverage, and open-field pursuit angles.

## F-24.11 Video / biomechanics research layer

Long-term multimodal research may incorporate pose, movement mechanics, release mechanics, route mechanics, blocking posture, change-of-direction, and fatigue-related mechanical changes where data can be processed legally, reliably, and reproducibly.

This is enrichment, not an initial-system dependency.

## F-24.12 Event encoder

Within a play:

```text
SNAP
 ↓
PROTECTION
 ↓
PRESSURE
 ↓
THROW / RUN
 ↓
CONTACT
 ↓
RESULT
```

can become an event sequence instead of one flat row. This is why F-5 preserves play events separately.

## F-24.13 Drive and game composition

Play transitions compose into drives; drive transitions compose into games:

`P(play events) → P(drive) → P(game)`

## F-24.14 Generative simulation

Instead of only asking "Who wins?", the model generates plausible game scenarios and derives all supported market probabilities from the resulting joint distribution.

## F-24.15 Counterfactual simulation

Potential scenario questions include:

- What if QB1 is inactive?
- What if WR1 plays only 50% of expected snaps?
- What if the roof is open?
- What if wind reaches 25 mph?
- What if a coaching staff becomes more aggressive on fourth down?

The same world model can generate conditional distributions under altered states.

## F-24.16 Causal caution

Predictive counterfactual scenarios are not automatically causal estimates. The architecture must distinguish predictive scenario simulation from causal inference unless causal assumptions are actually justified.

## F-24.17 World-model curriculum

Recommended progression:

```text
WM-0  play-state encoder
WM-1  next-play outcome prediction
WM-2  next-state distribution
WM-3  drive sequence model
WM-4  full-game generative simulator
WM-5  player/unit graph integration
WM-6  tracking / spatial model
WM-7  multimodal video / mechanics
```

Do not jump directly to WM-7.

## F-24.18 Pretraining

The model may learn generic football representations from large amounts of play history before task-specific optimization for score, win probability, or betting-market outputs.

## F-24.19 Structured models remain permanent controls

The Football World Model does **not** eliminate structured models. Structured state engines provide interpretability, auditability, fallbacks, controls, and ablation baselines. The world model joins the Champion/Challenger/ensemble architecture.

## F-24.20 Football-only discipline survives

A Football World Model can remain completely market-free (`FOOTBALL_ONLY`). A separate market-aware system may combine world-model representations with market state. The same audit boundary established in F-0/F-13/F-18 remains intact.

## F-24.21 Uncertainty remains mandatory

Advanced models still produce probability distributions and explicit epistemic, aleatoric, and input uncertainty. Sophistication does not justify deterministic single-point forecasts.

## F-24.22 Evaluation remains governed by F-19

The World Model must beat credible baselines and existing Champions under PIT-safe proper scoring, calibration, stability, and market-discrimination evaluation. Visual realism or architectural novelty is not sufficient evidence.

## F-24.23 Explainability

Future probability changes should remain traceable to meaningful state changes where possible. Example:

```text
LT becomes inactive
      ↓
expected protection quality declines
      ↓
pressure probability rises
      ↓
QB efficiency distribution changes
      ↓
team scoring distribution shifts
      ↓
win / spread / total probabilities update
```

## F-24.24 End-state architecture

```text
                    FOOTBALL WORLD STATE
                             │
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                  ▼
      PLAYERS              UNITS             COACHES
          │                  │                  │
          └──────────────────┼──────────────────┘
                             ▼
                       MATCHUP GRAPH
                             │
                        ENVIRONMENT
                             │
                             ▼
                       CURRENT STATE
                             │
                             ▼
                       COACH POLICY
                             │
                             ▼
                      PLAY EXECUTION
                             │
                             ▼
                        PLAY EVENTS
                             │
                             ▼
                       NEXT STATE
                             │
                             ▼
                           DRIVE
                             │
                             ▼
                           GAME
                             │
                             ▼
                    JOINT OUTCOME DISTRIBUTION
                             │
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                  ▼
        WIN               MARGIN             TOTAL
          │                  │                  │
          └──────────────────┼──────────────────┘
                             ▼
                       FAIR PRICES
                             │
                             ▼
                          MARKET
                             │
                             ▼
                        EDGE / EV
                             │
                             ▼
                  RECOMMENDATION GATE
```

### F-24 status

**LOCKED V1 as the long-term Football World Model research charter.**

---

# F-0 through F-24 — Complete Daily NFL Architecture

The full architecture now divides naturally into six layers:

```text
LAYER 1 — TRUTH & EVIDENCE
F-0 → F-5

LAYER 2 — FOOTBALL STATE
F-6 → F-12

LAYER 3 — FEATURES & TARGETS
F-13 → F-14

LAYER 4 — MODELING & SIMULATION
F-15 → F-17

LAYER 5 — MARKET / RECOMMENDATION / LEARNING
F-18 → F-21

LAYER 6 — EXTENSIONS & FUTURE RESEARCH
F-22 → F-24
```

Full operating loop:

```text
RAW EVIDENCE
      ↓
PIT TRUTH
      ↓
PLAYER / UNIT / TEAM / COACH STATE
      ↓
MATCHUP + ENVIRONMENT + RECOVERY
      ↓
FEATURE CONTRACT
      ↓
BASELINE + ADVANCED MODELS
      ↓
SIMULATION
      ↓
FOOTBALL PROBABILITY DISTRIBUTION
      ↓
FAIR PRICE
      ↓
SPORTSBOOK MARKET
      ↓
EDGE / EV
      ↓
RECOMMENDATION GATE
      ↓
BET / LEAN / PASS / AVOID
      ↓
GAME RESULT
      ↓
SETTLEMENT
      ↓
CALIBRATION / CLV / PERFORMANCE
      ↓
CHAMPION / CHALLENGER RESEARCH
      ↓
MODEL IMPROVEMENT
      ↓
repeat
```

## Locked final principles

1. Every supported game/market receives a prediction before the Recommendation Gate acts.
2. BET/LEAN/PASS/AVOID are recommendation outcomes, not prediction-existence filters.
3. PASS and AVOID predictions remain stored, settled, calibrated, and learned from.
4. Recommendation and bet sizing remain separate systems.
5. Football truth, market settlement, and model performance remain separate ledgers.
6. Historical predictions are never rewritten after model upgrades or new information.
7. Retraining never implies automatic Champion promotion.
8. Champion/Challenger and shadow predictions create prospective research evidence.
9. NFL-specific behavior stays in Daily-NFL unless a second implementation proves it belongs in shared football code.
10. Daily NCAAF is the proving ground for true football portability.
11. The Football World Model is a research destination built progressively on top of structured architecture, not a replacement for scientific controls.
12. All future complexity remains subordinate to PIT correctness, reproducibility, calibration, and out-of-sample evidence.
