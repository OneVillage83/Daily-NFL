# Daily NFL

Daily NFL is the NFL modeling engine for **The Daily Line**. Its governing architecture is documented in `docs/architecture/`, and its implementation sequence is defined in `docs/implementation/IMPLEMENTATION_ROADMAP_V1.md`.

## Current status

- F-0 through F-24 architecture: complete and versioned
- M0 repository bootstrap / engineering constitution: architecture-conformance audit in progress
- M1 through M6: provisionally implemented; each milestone must be architecture-certified in order before later work is treated as closed
- Current M0 certification blocker: regenerate `requirements-dev.txt` from the current Python 3.12 dependency inputs with the pinned compiler toolchain, then run the clean quality gate

The durable project resume point is `docs/implementation/PROJECT_CHECKPOINT_LOG.md`. Milestone-specific conformance evidence belongs in `docs/implementation/`.

## Engineering baseline

- Python 3.12
- explicit versioning and migrations
- immutable raw evidence/provenance
- strict point-in-time semantics
- pytest / Ruff / strict mypy quality gates
- provider-neutral football domain models
- hashed dependency locks generated from explicit input files

Daily NFL owns football intelligence. Sport-agnostic odds, weather acquisition, venue/geospatial primitives, travel/rest primitives, generic provider/provenance infrastructure, and shared market infrastructure belong in **Daily-Data-Core**.

## Non-negotiable architecture rules

Implementation must preserve the locked F-0 through F-24 contracts. In particular:

- providers populate canonical contracts; providers do not define the football ontology;
- immutable raw evidence precedes normalization and feature engineering;
- provider IDs remain crosswalks and never become permanent canonical identity;
- ambiguous identity reconciliation must remain unresolved rather than silently fuzzy-matched;
- pregame inputs must satisfy `available_at <= prediction_time < kickoff`;
- there is no blanket exclusion of Sunday/game-day information if it was legitimately available before the prediction cutoff;
- historical observations/revisions remain traceable rather than being silently overwritten;
- football-only, market-only, and market-aware information lineage remains explicit;
- every supported prediction is retained and evaluated even if the Recommendation Gate returns PASS or AVOID;
- final model validation is chronological / walk-forward, not a random train/test split;
- probabilistic calibration and proper scoring take priority over short-window W/L or ROI.

## Agent / Codex policy

Read `AGENTS.md` before making repository changes.

The default execution hierarchy is:

1. ChatGPT thread implements directly when possible.
2. User runs exact local commands when local execution/inspection is the missing capability.
3. Codex is reserved for explicitly scoped, lengthy, execution-heavy work.

## Local setup

From PowerShell on Windows:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install "pip==26.1.2" "pip-tools==7.6.0"
python -m piptools compile --resolver=backtracking --generate-hashes --strip-extras --allow-unsafe --output-file=requirements.txt requirements.in
python -m piptools compile --resolver=backtracking --generate-hashes --strip-extras --allow-unsafe --output-file=requirements-dev.txt requirements-dev.in
python -m pip install --require-hashes -r requirements-dev.txt
```

Do not run an unpinned `python -m pip install --upgrade pip` before compiling the locks. `pip-tools` depends on pip internals; the compiler toolchain is intentionally pinned for reproducible lock generation.

Then run:

```powershell
python -m pytest -q
python -m ruff check .
python -m mypy .
```

Whenever `requirements.in` or `requirements-dev.in` changes, regenerate the corresponding compiled lock under Python 3.12 with the pinned compiler toolchain. Do not hand-edit compiled hash locks.

Do not commit `.env`, local databases, generated model artifacts, or local raw datasets.

## Governing documents

Architecture index:

- `docs/architecture/README.md`

Implementation roadmap:

- `docs/implementation/IMPLEMENTATION_ROADMAP_V1.md`

Project checkpoint:

- `docs/implementation/PROJECT_CHECKPOINT_LOG.md`

M0 conformance audit:

- `docs/implementation/M0_ARCHITECTURE_CONFORMANCE_AUDIT.md`
