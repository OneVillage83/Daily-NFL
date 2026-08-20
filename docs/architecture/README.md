# Daily NFL Architecture

This directory contains the governing architecture references for Daily NFL.

- [`F00-F04_ARCHITECTURE_FOUNDATION_V1.md`](./F00-F04_ARCHITECTURE_FOUNDATION_V1.md) — F-0 through F-4 foundation: scientific mission, domain ontology, data-source architecture, canonical identity/reconciliation, historical point-in-time rules, and continuous pregame monitoring through kickoff.
- [`F05-F09_FOOTBALL_STATE_ARCHITECTURE_V1.md`](./F05-F09_FOOTBALL_STATE_ARCHITECTURE_V1.md) — F-5 through F-9: canonical game/drive/play architecture, Team State Engine, Player State Engine, Unit State Engine, and Coaching & Scheme State Engine. Includes the locked `PLAY_EXECUTION` naming convention so the real football concept of play action remains an unambiguous play-design modifier.
- [`F10-F14_CONTEXT_FEATURE_TARGET_ARCHITECTURE_V1.md`](./F10-F14_CONTEXT_FEATURE_TARGET_ARCHITECTURE_V1.md) — F-10 through F-14: Injury & Availability State Engine, Weather/Stadium/Surface State Engine, Travel/Rest/Recovery State Engine, complete NFL feature taxonomy and feature-contract rules, Prediction Targets & Label Architecture, and the event-driven dependency-aware recalculation requirement.
- [`F15-F19_MODEL_SIMULATION_MARKET_EVALUATION_ARCHITECTURE_V1.md`](./F15-F19_MODEL_SIMULATION_MARKET_EVALUATION_ARCHITECTURE_V1.md) — F-15 through F-19: baseline-model ladder, advanced-model architecture, Monte Carlo/drive/play simulation roadmap, football-only vs market-only vs market-aware pricing architecture, calibration/backtesting constitution, champion/challenger research, shadow predictions, drift monitoring, and model-promotion requirements.

Future F-series architecture documents should be versioned and added here as the Daily NFL engine develops.

Next planned block: F-20 through F-24 — Recommendation Gate, Settlement & Learning Loop, NFL-specific extensions, NCAAF portability/extensions, and the future Football World Model.
