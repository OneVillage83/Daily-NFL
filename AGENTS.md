# Daily NFL Agent Operating Rules

This repository is governed by the architecture in `docs/architecture/` and by the implementation workflow below.

## Execution hierarchy

Work should be performed in this order:

1. **ChatGPT thread first**
   - The active ChatGPT project/thread is the primary implementation coordinator.
   - If the thread can safely create or edit code, tests, schemas, migrations, documentation, or GitHub files directly, it should do so.
   - Do not delegate work to Codex merely because it involves code.

2. **User-local command second**
   - If a task mainly requires access to the user's local machine, runtime, local database, filesystem, credentials, or installed tooling, prefer giving the user an exact command to run.
   - The user may return the command output to the thread for interpretation and next steps.

3. **Codex escalation only when justified**
   - Use Codex for lengthy, multi-file, repo-wide, execution-heavy, or iterative implementation work that is inefficient or impractical to perform safely from the thread.
   - Codex must receive an explicitly bounded task with exact scope, files/areas allowed to change, validation commands, and a definition of done.
   - Codex must not broaden scope into adjacent architecture, documentation, refactors, or features unless explicitly instructed.

## Codex scope discipline

Codex must:

- implement only the task explicitly assigned;
- avoid opportunistic refactors unless required for correctness;
- preserve the governing F-0 through F-24 architecture;
- preserve point-in-time semantics and provenance rules;
- preserve the `PLAY_EXECUTION` naming convention and keep football `PLAY_ACTION` as a real play-design concept, not a top-level schema object;
- preserve the separation between football-only, market-only, and market-aware models;
- preserve the rule that every supported prediction is stored/evaluated even if the Recommendation Gate returns PASS or AVOID;
- preserve immutable prediction/history semantics;
- avoid duplicating sport-agnostic responsibilities that belong in Daily-Data-Core;
- return a concise summary of files changed, checks run, failures, and any unresolved decisions.

## Architecture authority

The governing architecture files are:

- `docs/architecture/F00-F04_ARCHITECTURE_FOUNDATION_V1.md`
- `docs/architecture/F05-F09_FOOTBALL_STATE_ARCHITECTURE_V1.md`
- `docs/architecture/F10-F14_CONTEXT_FEATURE_TARGET_ARCHITECTURE_V1.md`
- `docs/architecture/F15-F19_MODEL_SIMULATION_MARKET_EVALUATION_ARCHITECTURE_V1.md`
- `docs/architecture/F20-F24_RECOMMENDATION_LEARNING_EXTENSIONS_WORLD_MODEL_V1.md`

If implementation pressure conflicts with those contracts, stop and return the conflict to the ChatGPT thread rather than silently changing the architecture.

## Engineering conventions

Reuse proven Daily-MLB engineering conventions where they are sport-neutral and appropriate:

- Python 3.12
- explicit schema migrations
- immutable raw evidence and checksums
- SQLite for the initial local/single-service implementation unless a later architecture decision changes it
- deterministic identifiers where specified by contracts
- pytest, Ruff, and mypy quality gates
- explicit versioning for models, features, parsers, rulesets, and artifacts
- fail-closed point-in-time validation

Do not copy MLB-specific domain code into Daily-NFL merely for convenience.

## Default decision rule

When deciding whether to use Codex, ask:

> Can the ChatGPT thread implement this safely itself, or can the user perform the required local step with a precise command?

If yes, do not escalate to Codex.
