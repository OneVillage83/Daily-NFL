# Daily NFL Architecture

This directory contains the governing architecture references for Daily NFL.

- [`F00-F04_ARCHITECTURE_FOUNDATION_V1.md`](./F00-F04_ARCHITECTURE_FOUNDATION_V1.md) — F-0 through F-4 foundation: scientific mission, domain ontology, data-source architecture, canonical identity/reconciliation, historical point-in-time rules, and continuous pregame monitoring through kickoff.
- [`F05-F09_FOOTBALL_STATE_ARCHITECTURE_V1.md`](./F05-F09_FOOTBALL_STATE_ARCHITECTURE_V1.md) — F-5 through F-9: canonical game/drive/play architecture, Team State Engine, Player State Engine, Unit State Engine, and Coaching & Scheme State Engine. Includes the locked `PLAY_EXECUTION` naming convention so the real football concept of play action remains an unambiguous play-design modifier.
- [`F10-F14_CONTEXT_FEATURE_TARGET_ARCHITECTURE_V1.md`](./F10-F14_CONTEXT_FEATURE_TARGET_ARCHITECTURE_V1.md) — F-10 through F-14: Injury & Availability State Engine, Weather/Stadium/Surface State Engine, Travel/Rest/Recovery State Engine, complete NFL feature taxonomy and feature-contract rules, Prediction Targets & Label Architecture, and the event-driven dependency-aware recalculation requirement.
- [`F15-F19_MODEL_SIMULATION_MARKET_EVALUATION_ARCHITECTURE_V1.md`](./F15-F19_MODEL_SIMULATION_MARKET_EVALUATION_ARCHITECTURE_V1.md) — F-15 through F-19: baseline-model ladder, advanced-model architecture, Monte Carlo/drive/play simulation roadmap, football-only vs market-only vs market-aware pricing architecture, calibration/backtesting constitution, champion/challenger research, shadow predictions, drift monitoring, and model-promotion requirements.
- [`F20-F24_RECOMMENDATION_LEARNING_EXTENSIONS_WORLD_MODEL_V1.md`](./F20-F24_RECOMMENDATION_LEARNING_EXTENSIONS_WORLD_MODEL_V1.md) — F-20 through F-24: Recommendation Gate, settlement and continuous-learning loop, NFL-specific extensions, NCAAF portability rules, and the long-term Football World Model research charter.

## Governing sequence

The Daily NFL architecture is now complete through **F-24**:

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

These V1 documents are the governing architecture references for implementation planning, Codex work, model research, and future Daily NCAAF portability decisions. Future changes should be versioned rather than silently rewriting historical architecture decisions.
