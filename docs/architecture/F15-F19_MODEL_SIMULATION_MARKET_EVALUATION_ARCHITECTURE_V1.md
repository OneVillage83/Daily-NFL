# Daily NFL Architecture — F-15 through F-19

**Version:** 1.0  
**Status:** Governing Architecture — Locked V1  
**Scope:** Baseline Models → Advanced Models → Simulation Engine → Betting-Market Models → Calibration / Evaluation

---

## Governing Principle

Daily NFL does not search for one magical “best model.” It builds a ladder of increasingly sophisticated models, requires every new layer to prove incremental value out-of-sample, and ultimately combines complementary models into a calibrated probabilistic forecasting system.

No model may bypass the architecture established in F-0 through F-14. Point-in-time correctness, feature contracts, provenance, uncertainty, reproducibility, immutable prediction snapshots, and information cutoffs remain mandatory.

The modeling chain is:

```text
Approved PIT State
    ↓
F-13 Feature Contract
    ↓
F-15 Baseline Models
    ↓
F-16 Advanced Models
    ↓
F-17 Simulation Engine
    ↓
Football Probability Distribution
    ↓
F-18 Market / Fair-Price Layer
    ↓
Edge / EV
    ↓
Recommendation Gate
    ↓
F-19 Calibration / Evaluation
    ↓
Model Improvement Cycle
```

---

# F-15 — Baseline Model Architecture

## F-15.1 Purpose of the baseline ladder

The baseline system serves three purposes:

1. Establish what “good” actually means.
2. Detect leakage, broken features, and unnecessary complexity.
3. Create serious benchmarks that advanced models must beat.

A complicated model that cannot reliably outperform a strong simple model is not an improvement.

## F-15.2 Baseline ladder

```text
B0  League / Home-Field Baseline
        ↓
B1  Dynamic Team-Strength / Elo-Type Baseline
        ↓
B1-QB  Team Strength + QB Adjustment
        ↓
B2  Regularized Statistical Baseline
        ↓
B3  Gradient-Boosted Tabular Baseline
        ↓
B4  Coherent Probabilistic Distribution Baseline

External Comparator:
MARKET-ONLY BENCHMARK
```

B0 through B4 are football-only models. They do not use sportsbook prices or market movement.

## F-15.3 B0 — Null / league baseline

Inputs may include:

```text
league scoring environment
home / away
season
neutral-site indicator
```

Outputs:

```text
league-average home points
league-average away points
base home-win probability
base margin
base total
```

This answers: what would Daily NFL predict if it knew almost nothing about the two teams?

Every serious model should comfortably outperform B0.

## F-15.4 B1 — Dynamic team-strength baseline

Maintain a time-varying team strength:

```text
TEAM_STRENGTH(team, t)
```

Conceptually:

```math
R_{t+1}=R_t+K(Observed-Expected)
```

Candidate adjustments include:

```text
opponent strength
margin of victory
home-field effect
season transition
QB change
time decay
```

The architecture is not permanently tied to classical Elo; Elo-like models are reference baselines for dynamic latent team strength.

## F-15.5 QB-adjusted team-strength benchmark

A separate benchmark should add QB state:

```text
TEAM_STRENGTH
      +
QB_STATE
```

This prevents a team-rating benchmark from taking many games to recognize a major quarterback change.

It also creates an explicit experiment:

```text
team-only strength
vs
team + QB strength
```

## F-15.6 B2 — Regularized statistical baselines

Candidate interpretable families:

```text
Logistic Regression → win probability
Ridge Regression    → margin / total / score
Elastic Net         → margin / total / score
```

Candidate distributional benchmarks may include:

```text
Gaussian
Student-t
Poisson-type
Negative-binomial-type
```

No distribution family is assumed correct in advance; alternatives compete on out-of-sample probabilistic scoring.

## F-15.7 Why simple models remain permanently useful

Simple models remain scientific controls even after advanced models exist.

If a deep model barely beats ridge, the advanced architecture may be adding little true information. If the advanced model materially and repeatedly outperforms ridge, that is evidence that richer nonlinear interactions matter.

## F-15.8 B3 — Gradient-boosted tabular baseline

The first serious production challenger should be a strong gradient-boosted tabular model using only approved F-13 features and validated F-6 through F-12 state objects.

Candidate engines include:

```text
LightGBM
XGBoost
CatBoost
```

This benchmark exists because advanced state-space, graph, sequence, and world-model approaches should have to beat a competent nonlinear tabular system.

## F-15.9 Initial benchmark heads

Create direct benchmark heads for:

```text
HOME_POINTS_MODEL
AWAY_POINTS_MODEL
MARGIN_MODEL
TOTAL_MODEL
HOME_WIN_MODEL
```

The direct win model is a useful diagnostic, but the long-term canonical production probability should come from a coherent game distribution so win, spread, total, and score probabilities cannot contradict one another arbitrarily.

## F-15.10 B4 — Coherent probabilistic distribution baseline

One initial formulation:

```math
\hat M=f_M(X)
```

```math
\hat T=f_T(X)
```

where `M` is margin and `T` is total.

Estimate the joint residual distribution from training-period residuals only:

```math
(\epsilon_M,\epsilon_T)
```

Simulation draw:

```math
M^*=\hat M+\epsilon_M
```

```math
T^*=\hat T+\epsilon_T
```

Then:

```math
H^*=\frac{T^*+M^*}{2}
```

```math
A^*=\frac{T^*-M^*}{2}
```

This immediately creates a coherent distribution for:

```text
home win probability
tie probability
spread cover / push / loss
full-game total
team totals
score intervals
alternate lines
```

## F-15.11 Distributional alternatives

Test rather than assume:

```text
Gaussian residuals
Student-t residuals
empirical residual bootstrap
conditional residual distributions
quantile models
```

## F-15.12 Preserve residual dependency

Margin and total residuals must not be independently sampled unless independence is empirically justified.

The same principle later applies to:

```text
home scoring ↔ away scoring
QB volume ↔ receiver volume
team pace ↔ opponent pace
```

Football outcomes are connected.

## F-15.13 Market-only external benchmark

Maintain a separate market benchmark:

```text
MARKET_ONLY_V1
```

It can use:

```text
consensus moneyline
consensus spread
consensus total
no-vig market probability
```

This is not a football-only model. It exists to answer the harder question:

> Does Daily NFL predict football better than, or add information beyond, the betting market?

## F-15.14 Prediction horizons

Production is event-driven, but research evaluation should preserve standardized checkpoints such as:

```text
T-168h
T-72h
T-24h
T-6h
T-90m
T-final
```

Compare:

```text
one multi-horizon model
vs
horizon-specialized models
```

Calibration must always be reported by horizon.

## F-15.15 Era-aware baselines

Each feature contract requires its own baseline family:

```text
NFL_BASELINE_V1
NFL_ROSTER_ADVANCED_V1
NFL_SNAP_ADVANCED_V1
NFL_MODERN_V1
```

A modern enriched model must not be compared against a historical model pretending those features existed in earlier seasons.

## F-15.16 Model registry

Every model artifact must preserve:

```text
model_id
model_family
model_version

target_contract
feature_contract

training_start
training_end
training_information_cutoff

hyperparameters
random_seed

code_commit
training_dataset_hash

calibration_version
artifact_checksum

created_at
```

## F-15.17 Baseline acceptance rule

No advanced model earns promotion because ROI looked attractive over a short interval.

It must demonstrate meaningful out-of-sample improvement over appropriate baselines using proper probabilistic metrics, calibration, stability, and reproducibility.

**F-15: LOCKED V1**

---

# F-16 — Advanced Model Architecture

## F-16.1 Advanced modeling ladder

```text
A1  Hierarchical / State-Space Models
A2  Advanced Gradient-Boosted Models
A3  Multi-Task Distribution Models
A4  Player / Unit Interaction Models
A5  Graph Matchup Models
A6  Drive / Sequence Models
A7  Mixture-of-Experts
A8  Ensembles
A9  Football World Model
```

No advanced architecture receives credit for complexity alone.

## F-16.2 A1 — Hierarchical / state-space models

Estimate evolving latent state rather than arbitrary rolling averages.

Conceptually:

```math
S_t=g(S_{t-1})+\eta_t
```

```math
Y_t=h(S_t,X_t)+\epsilon_t
```

where:

- `S_t` is latent football ability/state.
- `Y_t` is observed performance.
- `η_t` represents true state evolution.
- `ε_t` represents noisy observed outcomes.

This naturally supports:

```text
changing team quality
partial pooling
small samples
rookies
injury transitions
season transitions
uncertainty
```

## F-16.3 Hierarchical structure

Potential hierarchy:

```text
League
  ↓
Team
  ↓
Unit
  ↓
Player
```

A low-sample player therefore draws information from position, unit, team, and league priors rather than being treated as fully known after a handful of snaps.

## F-16.4 Posterior / latent-state uncertainty

Prefer state distributions where possible rather than single point ratings.

Example:

```text
QB latent state distribution
```

can feed directly into the uncertainty propagation architecture of F-10 and F-17.

## F-16.5 A2 — Advanced gradient boosting

The B3 model may remain a strong permanent ensemble member.

Advanced variants may incorporate:

```text
learned state estimates
matchup interactions
feature-selection constraints
monotonic constraints where scientifically justified
distributional objectives
multi-horizon features
```

## F-16.6 A3 — Multi-task models

Instead of completely independent models:

```text
shared football representation
          ↓
 ┌────────┼─────────┐
 ↓        ↓         ↓
home     away      game
score    score     result
```

Later shared heads may include:

```text
drive volume
QB volume
player usage
```

Multi-task learning is a challenger because it may improve coherence across related outcomes.

## F-16.7 Joint distribution models

Long term, Daily NFL should estimate something equivalent to:

```math
P(H,A\mid X)
```

Possible model families include:

```text
mixture distributions
distributional neural networks
quantile models
copula-based models
Bayesian posterior predictive distributions
```

They compete using proper scoring rules and calibration rather than architectural preference.

## F-16.8 A4 — Player / unit interaction models

Use the structured state architecture directly:

```text
LT              ↔ EDGE
OL              ↔ pass rush
WR unit         ↔ coverage unit
run blocking    ↔ defensive front
QB tendencies   ↔ pressure / coverage scheme
```

This is preferable to treating every team as one scalar offense rating against one scalar defense rating.

## F-16.9 A5 — Graph matchup models

Football can be represented naturally as a graph:

```text
players = nodes

relationships =
    teammate
    opponent
    blocker / rusher
    receiver / coverage
    QB / receiver
```

Conceptual game graph:

```text
HOME PLAYERS
     ↓
HOME UNITS
     ↓
MATCHUP EDGES
     ↓
AWAY UNITS
     ↓
AWAY PLAYERS
```

Graph neural models are valid future research directions only if they outperform strong baselines.

## F-16.10 A6 — Sequence models

F-5 supplies:

```text
STATE(t)
PLAY_EXECUTION(t)
RESULT(t)
STATE(t+1)
```

That produces natural play → drive → game sequences.

Potential research families include:

```text
RNN / LSTM-type models
Transformers
state-space sequence models
```

The scientific question is whether sequence structure improves calibrated future-state predictions beyond aggregate features.

## F-16.11 A7 — Mixture-of-experts

Experts may specialize by:

```text
feature era
prediction horizon
roster certainty
game style
information quality
```

A learned gating model determines contribution.

Do not create arbitrary experts without evidence that regimes genuinely require different functions.

## F-16.12 A8 — Ensemble architecture

Long-term production may combine:

```text
State-Space Model
        │
GBDT Model
        │
Distribution Model
        │
Simulation Model
        │
Sequence Model
        │
        ▼
CALIBRATED ENSEMBLE
```

Ensemble weights must be learned using out-of-sample predictions and may later depend on horizon, feature coverage, or uncertainty.

Never simply average models because they exist.

## F-16.13 No hidden market contamination

Market-information lineage must propagate recursively.

If a learned state model used sportsbook information, that state cannot silently enter a `FOOTBALL_ONLY` model.

Every learned artifact should carry:

```text
market_information_used = TRUE / FALSE
```

and retain lineage to the market snapshots used.

## F-16.14 Ablation requirement

Every major advanced component should be testable through ablation:

```text
Full Model
minus Injury Engine
minus Travel / Recovery
minus Coaching / Scheme
minus Unit Interactions
minus Weather / Environment
```

Measure at least:

```text
Δ Log Loss
Δ Brier
Δ CRPS
Δ calibration
Δ CLV
```

This reveals which systems truly contribute predictive information.

## F-16.15 Complexity budget

Model promotion considers:

```text
accuracy
calibration
stability
latency
operational reliability
explainability
maintenance burden
```

A tiny metric improvement that creates fragile production infrastructure may not deserve promotion.

## F-16.16 A9 — Football world-model pathway

Long-term architecture:

```text
PLAYER STATE
      +
UNIT STATE
      +
COACH POLICY
      +
GAME STATE
      +
ENVIRONMENT
       ↓
P(NEXT FOOTBALL STATE)
```

Conceptually:

```math
P(S_{t+1}\mid S_t,A_t,P_t,E_t)
```

The world model is a destination, not the first production model.

**F-16: LOCKED V1**

---

# F-17 — Simulation Engine Architecture

## F-17.1 Simulation ladder

```text
S0  Distribution Sampling
S1  Score-Level Simulation
S2  Drive-Level Simulation
S3  Play-Level Football Simulation
S4  Future Spatial / World Simulation
```

The simulator evolves with the models; Daily NFL does not need to simulate every tackle on day one.

## F-17.2 S0 — Statistical distribution simulation

```text
Approved Features
      ↓
Predicted Margin / Total
      ↓
Joint Residual Distribution
      ↓
Monte Carlo Outcomes
```

Immediate outputs:

```text
P(win)
P(tie)
P(spread cover)
P(push)
P(over)
P(under)
score intervals
alternate-line surfaces
```

## F-17.3 S1 — Score-level simulation

```text
Home score distribution
        ×
Away score distribution
        ×
Dependency structure
        ↓
Joint score simulation
```

The simulation must preserve game-level dependence rather than independently sampling team scores without justification.

## F-17.4 S2 — Drive-level simulator

State includes:

```text
score
clock
period
possession
field position
timeouts
```

For each possession:

```text
START FIELD POSITION
        ↓
DRIVE MODEL
        ↓
TD / FG / PUNT / TURNOVER / DOWNS / MISSED FG / END HALF / SAFETY / OTHER
        ↓
TIME CONSUMED
        ↓
NEW GAME STATE
```

Repeat until the applicable historical or current ruleset ends the game.

## F-17.5 Drive-model inputs

```text
offensive state
defensive state
QB state
OL / protection
receiver unit
run unit
coaching policy
starting field position
score differential
time remaining
environment
recovery / fatigue state
```

## F-17.6 S3 — Play-level simulation

```text
GAME STATE
      ↓
COACH POLICY
      ↓
PLAY_EXECUTION
      ↓
PLAYER / UNIT INTERACTIONS
      ↓
PLAY RESULT
      ↓
NEXT GAME STATE
```

Use the locked `PLAY_EXECUTION` naming convention from F-5; `PLAY_ACTION` remains reserved for the actual football play-action concept.

## F-17.7 Pre-snap action generation

Example state:

```text
2nd & 7
own 43
9:44 Q3
trailing by 4
```

Coach-policy model might estimate:

```text
PASS   52%
RUSH   38%
OTHER  10%
```

Then conditional design/modifier probabilities can represent:

```text
play action
screen
RPO
motion
other design elements
```

## F-17.8 Injury uncertainty propagation

At T-6h:

```text
WR1 P(active)=0.67
```

Outer simulation can sample active/inactive status, build the resulting player/unit/team configuration, then simulate the football game.

Thus uncertainty about availability becomes uncertainty in the score and betting distribution naturally.

## F-17.9 Weather uncertainty propagation

Where valid forecast distributions exist, simulate from them rather than treating every future game as occurring at one deterministic forecast value.

Possible uncertain states include:

```text
wind
precipitation
temperature
roof state if unresolved
```

## F-17.10 Separate aleatoric and epistemic uncertainty

### Aleatoric uncertainty

Randomness inherent to football:

```text
turnovers
field-goal outcomes
catch outcomes
drive results
```

### Epistemic uncertainty

Uncertainty in our knowledge/model:

```text
player health
team strength
model parameters
weather
rookies
small samples
```

Conceptually:

```text
DRAW A POSSIBLE FOOTBALL WORLD
        ↓
SIMULATE RANDOM GAME INSIDE THAT WORLD
```

## F-17.11 Nested simulation

Outer loop:

```text
draw latent team / player state
draw availability
draw environment
draw model / parameter state
```

Inner loop:

```text
simulate game randomness
```

This creates a fuller predictive distribution than one undifferentiated noise term.

## F-17.12 Monte Carlo precision rule

Do not permanently hard-code one simulation count.

For a Bernoulli event:

```math
SE(\hat p)=\sqrt{\frac{p(1-p)}{N}}
```

The engine may continue until Monte Carlo standard error falls below a configured threshold for important probabilities.

## F-17.13 Reproducibility

Every simulation artifact stores:

```text
simulation_id
prediction_id

engine_version
ruleset_version

number_of_simulations
random_seed

input_state_ids
model_versions

environment_snapshot
created_at
```

Same inputs, code, versions, and seed should reproduce the result within the deterministic guarantees of the implementation.

## F-17.14 Rules engine

Simulation rules must be versioned by game:

```text
quarter length
clock rules
timeouts
scoring
kickoffs
overtime
tries
```

Historical simulations use the rules that applied to that historical game.

## F-17.15 Common-random-number research

When comparing model versions, matched random streams may be used to reduce Monte Carlo noise and isolate the effect of the model change.

This is research infrastructure, not a production requirement.

## F-17.16 Simulation summary artifact

```text
GAME_SIMULATION_SUMMARY

prediction_id
N

home_win_probability
tie_probability
away_win_probability

home_score_mean
away_score_mean

margin_mean
total_mean

score_quantiles
margin_quantiles
total_quantiles

spread_probability_surface
total_probability_surface
team_total_surface

simulation_standard_errors
scenario_breakdown
```

## F-17.17 Raw simulation storage

Do not automatically persist millions of rows for every prediction.

Persist:

```text
summary statistics
quantiles
histogram / distribution artifacts
seed
engine version
```

Optionally retain full samples for research, debugging, or validation.

## F-17.18 Simulation validation

Compare simulator outputs with actual football reality across:

```text
score distributions
margin distributions
total distributions
possession counts
drive outcomes
turnovers
scoring rates
```

Accurate win probabilities generated for structurally wrong reasons still deserve investigation.

**F-17: LOCKED V1**

---

# F-18 — Betting-Market Model & Fair-Price Engine

## F-18.1 Ownership boundary

```text
Daily-NFL
    = football probabilities / distributions

Daily-Data-Core
    = sportsbook observations / normalization / market infrastructure

Daily NFL Value Layer
    = comparison of football price vs market price
```

## F-18.2 Three distinct probabilities

Always distinguish:

```text
P_model
P_market_raw
P_market_fair
```

- `P_model`: Daily NFL model probability.
- `P_market_raw`: price-implied probability containing bookmaker margin.
- `P_market_fair`: estimated no-vig market probability.

Do not call all three simply “probability” in storage or model logic.

## F-18.3 Immutable sportsbook quote

From Daily Data Core:

```text
SPORTSBOOK_QUOTE

event_id
sportsbook

market
selection
line
price

observed_at
available_at

provider
source_quality
```

## F-18.4 Preserve every sportsbook separately

```text
Book A
Book B
Book C
Book D
```

remain independent observations.

Derived products may include:

```text
consensus
book dispersion
best available line
best available price
```

Never destroy the original quote history to create consensus.

## F-18.5 Versioned de-vig methods

The Core should support versioned de-vig methods rather than silently treating one algorithm as ground truth.

Possible methods include:

```text
multiplicative normalization
additive methods where applicable
power methods
other validated market models
```

Persist:

```text
DEVIG_METHOD
DEVIG_VERSION
```

## F-18.6 Market consensus pipeline

```text
BOOK QUOTES
      ↓
NORMALIZATION
      ↓
DE-VIG
      ↓
QUALITY / STALENESS FILTER
      ↓
CONSENSUS MARKET DISTRIBUTION
```

Possible weighting schemes:

```text
equal book weights
historical information-quality weights
market freshness weights
book-specific calibration weights
```

Simple consensus remains a benchmark; sophistication must prove value.

## F-18.7 Market-only model

```text
MARKET_ONLY_V1
```

Inputs may include:

```text
consensus spread
consensus total
consensus moneyline
```

Output: market-derived game distribution.

This allows direct evaluation of:

```text
FOOTBALL_ONLY
vs
MARKET_ONLY
vs
MARKET_AWARE
```

## F-18.8 Football-only fair probability

Example:

```text
P(SF covers -3)=0.562
```

The canonical football fair probability is 56.2%, generated without using the sportsbook quote being evaluated.

## F-18.9 Probability edge

```math
Edge_P=P_{model}-P_{market,fair}
```

Example:

```text
model fair probability = 56.2%
market fair probability = 52.0%
probability edge       = 4.2 percentage points
```

Probability edge must remain distinct from expected wager value.

## F-18.10 Expected value

For decimal odds `d` and model win probability `p`:

```math
EV=pd-1
```

Store separately:

```text
probability_edge
expected_value
market_price
```

Do not overload one generic `edge` field.

## F-18.11 Fair odds

Model probability may be converted to decimal/American fair odds for display, but probability remains the canonical internal representation.

## F-18.12 Probability surfaces

One game distribution should provide:

```text
P(team -1.5)
P(team -2)
P(team -2.5)
P(team -3)
P(team -3.5)
...
```

and total surfaces such as:

```text
P(over 42)
P(over 42.5)
P(over 43)
...
```

The system should not train a separate football model for every sportsbook line.

## F-18.13 Push probability

For integer lines, estimate the full state:

```text
WIN
PUSH
LOSS
```

rather than forcing every market into a binary label.

## F-18.14 Line shopping

Evaluate every current quote against the same model distribution.

Example:

```text
Book A: SF -3 -110
Book B: SF -2.5 -115
Book C: SF -3 +100
```

The value engine identifies the best line and best price without changing the football forecast.

## F-18.15 Market-aware model

Separately:

```text
FOOTBALL FEATURES
       +
MARKET STATE
       ↓
MARKET_AWARE MODEL
```

Candidate market inputs:

```text
opening line
current line
movement
consensus
book dispersion
time to kickoff
```

Every such prediction must preserve exactly which market observations were part of its information set.

## F-18.16 Market-residual framing

A useful challenger architecture may directly model where the market is systematically mispriced conditional on football state.

Conceptually:

```math
\Delta=Fair_{true}-Fair_{market}
```

Then learn:

```text
football state
+
market state
    ↓
expected market residual
```

This is a candidate value-discovery model, not an automatic production winner.

## F-18.17 Avoid circular evaluation

If market quote X entered a market-aware prediction, that exact information must be identifiable when evaluating the prediction against a market.

No hidden circularity is permitted.

## F-18.18 Closing line

Closing information is valuable for evaluation and CLV, but it cannot enter an earlier prediction if it was not available at that prediction timestamp.

The governing PIT rule remains:

```text
available_at <= prediction_time
```

## F-18.19 Market movement is a time series

Persist:

```text
OPEN
  ↓
snapshot
  ↓
snapshot
  ↓
snapshot
  ↓
CLOSE
```

not merely opening and closing values.

This later permits research into:

```text
movement velocity
direction
book leadership
dispersion convergence
response to new information
```

## F-18.20 Market-information value study

Explicitly compare:

```text
Football only
      ↓
+ opening market
      ↓
+ current market
      ↓
+ full movement history
```

Measure incremental predictive value at every step.

This tells us how much intelligence Daily NFL independently discovers versus how much it inherits from market consensus.

## F-18.21 Initial production market scope

Start with:

```text
Moneyline
Full-Game Spread
Full-Game Total
```

Then expand to:

```text
Team Totals
1H / 1Q
Player Props
```

once underlying distributions are sufficiently reliable.

## F-18.22 Same-game correlation

Later prop and same-game markets must use joint distributions.

Example dependency:

```text
QB passing yards
      ↔
WR receiving yards
      ↔
team scoring
      ↔
game total
      ↔
team win probability
```

Do not independently multiply probabilities for correlated legs.

## F-18.23 Recommendation Gate remains downstream

F-18 produces:

```text
FAIR PRICE
MARKET PRICE
PROBABILITY EDGE
EXPECTED VALUE
UNCERTAINTY
```

F-20 will decide whether that information becomes a published BET / LEAN / PASS / AVOID recommendation.

Every supported prediction remains stored and evaluated regardless of the Gate result.

**F-18: LOCKED V1**

---

# F-19 — Calibration, Backtesting & Evaluation Constitution

## F-19.1 Governing evaluation principle

A useful probabilistic system must be both:

```text
CALIBRATED
+
SHARP / DISCRIMINATIVE
```

A model predicting 50% for everything can avoid extreme mistakes while providing little useful information. Daily NFL seeks probabilities that are appropriately decisive while remaining statistically honest.

## F-19.2 No random train/test split as final validation

Final evaluation is chronological:

```text
TRAIN PAST
     ↓
VALIDATE FUTURE
     ↓
TEST LATER FUTURE
```

Example:

```text
Train through 2022
Validate 2023
Test 2024

advance

Train through 2023
Validate 2024
Test 2025
```

Eventually, week-by-week rolling evaluation should reproduce actual production behavior.

## F-19.3 Nested time-aware model selection

Use:

```text
OUTER LOOP
    true future evaluation

INNER LOOP
    model / hyperparameter / calibration selection
```

The outer test period cannot influence:

```text
feature selection
hyperparameters
calibration
ensemble weights
```

## F-19.4 Production-style historical replay

Gold-standard backtest:

```text
At historical timestamp T:

reconstruct knowledge available at T
build states
build feature snapshots
load only eligible past training data
fit / update model according to production policy
generate prediction
store immutable prediction
advance historical clock
```

This should eventually become the authoritative research replay environment.

## F-19.5 Evaluation dimensions

Every result should be sliceable by:

```text
model
model version
feature contract
feature era
season
week
prediction horizon
market type
probability bucket
home / away
favorite / underdog
spread range
total range
weather regime
injury uncertainty
data-quality state
```

## F-19.6 Classification metrics

For binary outcomes:

### Log Loss

```math
-[y\log p+(1-y)\log(1-p)]
```

### Brier Score

```math
(p-y)^2
```

Use proper scoring rules so models are rewarded for honest predictive probabilities.

## F-19.7 Distribution metrics

For score, margin, and total distributions, track metrics such as:

```text
CRPS
log predictive score
quantile loss
interval coverage
sharpness
```

For joint home/away score distributions, investigate suitable multivariate proper scores such as energy-based scores.

## F-19.8 MAE / RMSE are diagnostics, not the constitution

Continue tracking:

```text
score MAE
margin MAE
total MAE
RMSE
```

but they do not fully evaluate forecast uncertainty and therefore must not become the sole model-selection criterion.

## F-19.9 Calibration diagnostics

For predictions such as:

```text
55%
60%
65%
```

ask whether those events occur at approximately those frequencies over sufficiently large samples.

Track:

```text
reliability plots
calibration intercept
calibration slope
probability-bucket outcomes
cumulative calibration diagnostics
```

## F-19.10 Do not rely on one calibration metric

Expected Calibration Error may be reported descriptively but must not become the sole calibration gate.

Use multiple diagnostics because binning choices and sample size can materially affect summary calibration statistics.

## F-19.11 Calibration layer

Raw model probabilities may require post-hoc calibration.

Candidate methods include:

```text
logistic / Platt-type calibration
isotonic regression
other validated monotonic / probabilistic calibrators
```

Calibration must be fit only on past held-out data.

Never calibrate on the same future test period used to report final performance.

## F-19.12 Calibration by prediction horizon

Potentially maintain:

```text
T-168h calibrator
T-24h calibrator
T-90m calibrator
```

or one shared conditional calibration system.

Choose empirically; always report calibration by horizon.

## F-19.13 Distribution calibration

Evaluate:

```text
Do 80% intervals contain ~80% of outcomes?
Do 50% intervals contain ~50%?
Are residuals centered?
Are tails too narrow or too wide?
Are totals systematically under-dispersed?
```

## F-19.14 Simulator calibration

Validate not only game winners but simulated football mechanisms:

```text
home-win rates
tie rates
TD rates
turnover rates
drive counts
score distributions
```

A simulator that reaches acceptable win probabilities through unrealistic mechanics should be investigated.

## F-19.15 Sharpness / discrimination

Among equally calibrated models, prefer the model that can legitimately distinguish stronger from weaker probability states rather than clustering every prediction near 50%.

## F-19.16 Market evaluation

After probability quality, evaluate:

```text
CLV
expected value
ROI
yield
win rate
push rate
drawdown
```

ROI is commercially important but remains noisy and downstream of forecast quality.

## F-19.17 Closing-line value

Compare:

```text
prediction-time market quote
vs
closing market quote
```

for both line value and price value.

CLV provides useful evidence independent of whether one specific game happened to win.

## F-19.18 Realistic odds backtesting

Never backtest against a line that was not actually available at the prediction timestamp.

Use:

```text
actual sportsbook
actual quote
actual timestamp
```

from Daily Data Core.

This prevents execution hindsight.

## F-19.19 Recommendation Gate evaluation

Because every prediction is stored:

```text
ALL PREDICTIONS
      ↓
BET subset
LEAN subset
PASS subset
AVOID subset
```

we can empirically test whether the Gate adds value.

Questions include:

```text
Does BET outperform ALL predictions?
Does PASS identify lower-quality opportunities?
Does AVOID identify dangerous uncertainty?
Does the Gate improve calibration?
Does it improve CLV?
Does it improve risk-adjusted realized results?
```

## F-19.20 Subgroup robustness

Actively inspect failure states such as:

```text
large favorites
extreme weather
backup QBs
rookie QBs
high injury uncertainty
international games
short weeks
very low totals
very high totals
playoffs
```

Strong aggregate performance must not hide catastrophic subgroups.

## F-19.21 Performance uncertainty

Reported metrics should eventually include uncertainty intervals where appropriate:

```text
Log Loss ± interval
Brier ± interval
ROI ± interval
CLV ± interval
```

Resampling and statistical procedures should respect football's temporal/grouped dependence rather than treating every observation as perfectly independent.

## F-19.22 Model comparison

A tiny numerical improvement is not automatically meaningful.

Model improvements must be examined for:

```text
persistence
stability
out-of-sample behavior
cross-season behavior
cross-horizon behavior
```

## F-19.23 Champion / Challenger architecture

Production maintains:

```text
CHAMPION MODEL
```

Research models run as:

```text
CHALLENGERS
```

A challenger earns promotion only after sufficient prospective and/or strict out-of-sample evidence.

## F-19.24 Shadow predictions

Models not used publicly should still be allowed to generate:

```text
SHADOW PREDICTIONS
```

Shadow predictions are:

```text
timestamped
immutable
settled
evaluated
```

This produces genuine prospective evidence rather than endlessly re-optimizing historical backtests.

## F-19.25 Model promotion gate

A challenger must demonstrate:

```text
no PIT violation
no leakage
reproducibility
improvement in proper probabilistic scores
acceptable or improved calibration
stable subgroup behavior
adequate evidence / sample size
acceptable operational latency
no unexplained dependence on one season
understood ablation results
intact feature provenance
```

ROI alone is insufficient.

## F-19.26 Model retirement

Models may be retired because of:

```text
model drift
data-source loss
feature-contract obsolescence
calibration deterioration
better replacement
```

Historical artifacts remain immutable for auditability.

## F-19.27 Drift monitoring

Production monitoring should include:

```text
input drift
state drift
prediction drift
calibration drift
outcome drift
market-relationship drift
```

The model must not silently assume the NFL's scoring and strategic environment is stationary forever.

## F-19.28 Model performance ledger

Every prediction should eventually join:

```text
PREDICTION
    ↓
RESULT
    ↓
SETTLEMENT
    ↓
CALIBRATION
    ↓
MARKET RESULT
    ↓
MODEL PERFORMANCE
```

No prediction disappears because it was embarrassing.

## F-19.29 Research leaderboard

Internally maintain a model leaderboard similar to:

```text
Model               LogLoss   Brier   CRPS   CLV
-------------------------------------------------
League Baseline
Elo
QB-Adjusted Elo
Ridge
GBDT
State Space
Simulation
Ensemble
Market Only
```

Always slice by season, horizon, and feature era where relevant.

## F-19.30 Reproducible experiment artifact

Every research experiment should preserve:

```text
experiment_id
hypothesis

model_versions
feature_contracts

training_periods
validation_periods
test_periods

hyperparameters
random_seeds

metrics
subgroup_results

artifact_hashes
code_commit

conclusion
```

## F-19.31 Scientific order of evidence

Daily NFL's evaluation hierarchy is:

```text
1. PIT / data correctness
2. Proper probabilistic scoring
3. Calibration
4. Sharpness / discrimination
5. Distribution accuracy
6. Stability across seasons and horizons
7. Market discrimination / CLV
8. Betting expected value
9. Realized ROI
```

ROI matters commercially, but it appears near the end because realized betting outcomes contain substantial variance.

**F-19: LOCKED V1**

---

# System State After F-19

```text
                       RAW DATA
                          │
                          ▼
                 F-0–F-4 FOUNDATION
                          │
                          ▼
                F-5 FOOTBALL LEDGER
                          │
         ┌────────────────┼────────────────┐
         ▼                ▼                ▼
       F-7              F-8              F-9
     Players            Units          Coaching
         ▲                │                │
         │                │                │
       F-10───────────────┘                │
      Injuries                              │
         │                                  │
         └──────────────► F-6 TEAM STATE ◄──┘
                              │
                 ┌────────────┴────────────┐
                 ▼                         ▼
              F-11                       F-12
          Environment                  Recovery
                 │                         │
                 └────────────┬────────────┘
                              ▼
                          MATCHUP
                              │
                              ▼
                         F-13 FEATURES
                              │
                              ▼
                         F-15 BASELINES
                              │
                              ▼
                        F-16 ADVANCED
                              │
                              ▼
                       F-17 SIMULATION
                              │
                              ▼
                      GAME DISTRIBUTION
                              │
                 ┌────────────┴────────────┐
                 ▼                         ▼
           FOOTBALL FAIR              F-18 MARKET
              PRICE                        │
                 └────────────┬────────────┘
                              ▼
                         EDGE / EV
                              │
                              ▼
                   RECOMMENDATION GATE
                              │
                              ▼
                 BET / LEAN / PASS / AVOID
                              │
                              ▼
                      ACTUAL RESULTS
                              │
                              ▼
                        F-19 EVALUATION
                              │
                              ▼
                     MODEL IMPROVEMENT
                              │
                              └──────────────► cycle
```

---

# Locked Cross-Cutting Decisions from F-15 through F-19

1. Advanced models must beat strong reproducible baselines; complexity alone is not improvement.
2. Football-only, market-only, and market-aware models are separate auditable model families.
3. The serious baseline includes a strong nonlinear tabular benchmark, not just Elo or linear regression.
4. Canonical production probabilities should ultimately come from coherent predictive distributions.
5. Residual and outcome dependency must be preserved where empirically relevant.
6. Learned states inherit market-information lineage recursively.
7. Advanced components require ablation testing.
8. Simulation evolves from distribution sampling toward drive-, play-, and eventually world-level simulation.
9. Injury, roster, environment, and parameter uncertainty may propagate through simulation rather than collapsing into fixed deterministic inputs.
10. Aleatoric and epistemic uncertainty are conceptually distinct.
11. Simulation uses versioned historical/current NFL rulesets.
12. Monte Carlo sample count may be driven by required precision rather than one fixed number.
13. Sportsbook quotes remain immutable and book-specific before consensus derivation.
14. Probability edge, market price, and wager expected value are separate quantities.
15. Market movement is a timestamped time series, not merely open/close fields.
16. Closing lines can evaluate earlier predictions but cannot leak backward into them.
17. Same-game and prop systems must respect correlation through joint distributions.
18. Final model evaluation is chronological and PIT-correct; random train/test splitting is not the final standard.
19. Proper probabilistic scoring and calibration come before realized ROI in the model-quality hierarchy.
20. Recommendation Gate performance is evaluated because predictions for BET, LEAN, PASS, and AVOID are all retained.
21. Champion/challenger and shadow-prediction infrastructure is required for prospective model research.
22. Model promotion requires correctness, probabilistic improvement, calibration, robustness, reproducibility, and operational viability—not short-run profit alone.
23. Model artifacts, experiments, and historical predictions remain immutable and reproducible.
24. Continuous drift monitoring and a permanent performance ledger are required production capabilities.

---

# Next Architecture Block

The next logical block is:

```text
F-20 Recommendation Gate
F-21 Settlement & Learning Loop
F-22 NFL-Specific Extensions
F-23 NCAAF Portability / Extensions
F-24 Future Football World Model
```

This will complete the initial F-0 through F-24 Daily NFL architecture before implementation planning.