# Daily NFL

Daily NFL is the NFL modeling engine for **The Daily Line**. Its governing architecture is documented in `docs/architecture/`, and its implementation sequence is defined in `docs/implementation/IMPLEMENTATION_ROADMAP_V1.md`.

## Current status

- F-0 through F-24 architecture: complete and versioned
- M0 repository bootstrap: in progress
- M1 canonical domain contracts: next

## Engineering baseline

- Python 3.12
- explicit versioning and migrations
- immutable raw evidence/provenance
- strict point-in-time semantics
- pytest / Ruff / mypy quality gates
- provider-neutral football domain models

Daily NFL owns football intelligence. Sport-agnostic odds, weather, venue, travel, and shared infrastructure belong in **Daily-Data-Core**.

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
python -m pip install --upgrade pip
python -m pip install pip-tools==7.5.3
python -m piptools compile --resolver=backtracking --generate-hashes --strip-extras --allow-unsafe --output-file=requirements.txt requirements.in
python -m piptools compile --resolver=backtracking --generate-hashes --strip-extras --allow-unsafe --output-file=requirements-dev.txt requirements-dev.in
python -m pip install --require-hashes -r requirements-dev.txt
```

Then run:

```powershell
python -m pytest -q
python -m ruff check .
python -m mypy
```

Do not commit `.env`, local databases, generated model artifacts, or local raw datasets.

## Governing documents

Architecture index:

- `docs/architecture/README.md`

Implementation roadmap:

- `docs/implementation/IMPLEMENTATION_ROADMAP_V1.md`
