# M0 Architecture-Conformance Audit

**Project:** The Daily Line — Daily NFL  
**Milestone:** M0 — Repository Bootstrap & Engineering Constitution  
**Audit date:** 2026-08-21  
**Audit branch:** `audit/m0-architecture-conformance`  
**Governing roadmap:** `docs/implementation/IMPLEMENTATION_ROADMAP_V1.md`  
**Architecture dependencies:** F-0, F-2, F-3, F-4, F-19  
**Certification status:** **NOT YET CERTIFIED — BLOCKED ON DEPENDENCY-LOCK REFRESH + FINAL CLEAN LOCAL VALIDATION**

---

## 1. Audit Purpose

This audit is the first formal milestone certification pass for Daily NFL.

The goal is not to ask whether M0 code/files merely exist. The goal is to determine whether the M0 engineering foundation matches the intended endpoint established by the locked architecture and is safe to treat as a stable dependency for M1 through M6.

The audit uses the following status vocabulary:

- `SATISFIED` — requirement is present and consistent with the architecture.
- `SATISFIED AFTER REMEDIATION` — a defect was found and corrected during this audit.
- `PARTIAL` — some required behavior/contract exists but is incomplete.
- `BLOCKED` — certification cannot be granted until the item is resolved.
- `DEFERRED BY ARCHITECTURE` — the governing principle is established at M0, but implementation belongs to a later milestone.
- `NOT APPLICABLE TO RETROACTIVE CERTIFICATION` — sequencing language that described the original build order rather than a permanent system property.

M0 is not certified until all blocking items are closed and the final validation gate passes.

---

# 2. Governing M0 Contract

The roadmap defines M0 as **Repository Bootstrap & Engineering Constitution** with architecture dependencies:

```text
F-0
F-2
F-3
F-4
F-19
```

Roadmap deliverables:

```text
Python 3.12 project baseline
package layout
.gitignore
.python-version
dependency input files
pytest / Ruff / mypy configuration
AGENTS.md
implementation README
version module
basic test package
CI-ready quality-gate commands
```

Roadmap exit gate:

```text
package imports cleanly
quality commands are defined
no NFL/provider logic yet
```

Because this is a retroactive audit after M1-M6 implementation already exists, the original `no NFL/provider logic yet` sequencing condition is interpreted as:

> The M0 engineering scaffold itself must remain independent of provider-specific or NFL-domain implementation details and must not require those details to define its engineering rules.

It is **not** interpreted as a requirement to delete later milestone code.

---

# 3. Repository Evidence Reviewed

M0-scoped repository evidence reviewed during this audit:

```text
.python-version
.gitignore
pyproject.toml
requirements.in
requirements.txt
requirements-dev.in
requirements-dev.txt
AGENTS.md
README.md
daily_nfl/__init__.py
daily_nfl/version.py
tests/test_package.py
docs/implementation/IMPLEMENTATION_ROADMAP_V1.md
docs/architecture/F00-F04_ARCHITECTURE_FOUNDATION_V1.md
docs/architecture/F15-F19_MODEL_SIMULATION_MARKET_EVALUATION_ARCHITECTURE_V1.md
```

The repository tree was also reviewed to confirm package/test/document structure and the absence of a hidden alternative M0 configuration path.

---

# 4. M0 Deliverable Conformance Matrix

| ID | Requirement | Status | Evidence / finding |
|---|---|---|---|
| M0-01 | Python 3.12 project baseline | `SATISFIED` | `.python-version` contains `3.12`; Ruff targets `py312`; mypy targets Python 3.12. |
| M0-02 | Package layout | `SATISFIED` | `daily_nfl/` is a real package with `__init__.py`; package root exposes version metadata only. |
| M0-03 | `.gitignore` | `SATISFIED` | Ignores caches, virtual environments, `.env`, SQLite/local DBs, `local-data/`, `data/local/`, generated artifacts, build output, and editor/OS files. |
| M0-04 | `.python-version` | `SATISFIED` | Explicitly pinned to `3.12`. |
| M0-05 | Dependency input files | `SATISFIED` | `requirements.in` and `requirements-dev.in` exist with explicit direct pins. |
| M0-06 | Compiled dependency locks reproduce current inputs | `BLOCKED` | `requirements-dev.in` includes `nflreadpy==0.1.5`, but `requirements-dev.txt` contains no `nflreadpy` entry. The lock is stale relative to its input. |
| M0-07 | pytest configuration | `SATISFIED` | `pyproject.toml` defines `tests` as test path and standard pytest options. |
| M0-08 | Ruff configuration | `SATISFIED` | Python 3.12 target, line length, and lint rule families are explicitly configured. |
| M0-09 | mypy configuration | `SATISFIED` | Strict mypy enabled for `daily_nfl` and `tests`, with unreachable-code warnings and error codes. |
| M0-10 | `AGENTS.md` engineering constitution | `SATISFIED AFTER REMEDIATION` | Existing execution/Codex rules were strong but did not explicitly encode several M0-level F-3/F-4/F-19 invariants or dependency-lock discipline. Audit branch now does. |
| M0-11 | Implementation README | `SATISFIED AFTER REMEDIATION` | README status and pip-tools bootstrap version were stale. Audit branch now reflects certification workflow, current status, architecture invariants, and `pip-tools==7.6.0`. |
| M0-12 | Version module | `SATISFIED` | `daily_nfl/version.py` defines `__version__ = "0.1.0"`; package root re-exports it. |
| M0-13 | Basic test package | `SATISFIED` | `tests/` exists and includes package/version smoke coverage plus later milestone tests. |
| M0-14 | Package import smoke test | `SATISFIED IN CODE; FINAL RUN PENDING` | `tests/test_package.py` imports `daily_nfl.__version__` and asserts the version. Final clean-environment execution remains part of certification. |
| M0-15 | CI-ready quality-gate commands | `SATISFIED` | README and `AGENTS.md` define `pytest`, Ruff, and strict mypy commands. A hosted GitHub Actions workflow is not required by the M0 roadmap. |
| M0-16 | M0 scaffold avoids provider coupling | `SATISFIED` | Root package/version/configuration do not import nflverse or provider modules. Later milestone packages coexist without defining the M0 scaffold. |

---

# 5. F-0 Conformance at M0 Scope

F-0 defines the scientific constitution of Daily NFL. M0 does not implement the future modeling stack, but it must establish engineering rules that prevent later code from violating F-0 accidentally.

## F-0.1 Probability-distribution mission

**Status:** `SATISFIED AFTER REMEDIATION`

The audit branch now explicitly states that Daily NFL estimates calibrated probability distributions rather than merely picks/winners.

Actual score/margin/total distributions are later-milestone responsibilities.

## F-0.2 Predict everything; recommend selectively

**Status:** `SATISFIED`

`AGENTS.md` already protected the requirement that every supported prediction remains stored/evaluated even when the Recommendation Gate returns PASS or AVOID. The audit branch strengthens this by explicitly separating forecast creation from recommendation outcomes.

Implementation is deferred to the prediction/Recommendation Gate milestones.

## F-0.5 Football-only vs market-aware separation

**Status:** `SATISFIED`

The engineering constitution protects football-only, market-only, and market-aware lineage separation.

Actual model lineage implementation is deferred to feature/model/market milestones.

## F-0.6 Uncertainty as first-class information

**Status:** `SATISFIED AFTER REMEDIATION`

The engineering constitution now names uncertainty and reproducible metadata as first-class modeling requirements.

Actual uncertainty representation is deferred to later state/model/simulation milestones.

## F-0.7 Continuous research architecture

**Status:** `SATISFIED`

The repository is explicitly governed by versioned architecture, milestone boundaries, typed contracts, explicit migrations, and reproducible tests rather than a one-off picks script.

## F-0.8 Reproducibility

**Status:** `BLOCKED`

Positive evidence:

- Python version is pinned.
- direct dependencies are pinned;
- compiled dependencies use generated hashes;
- package version exists;
- architecture requires versioned parsers/models/features/rulesets/artifacts;
- `AGENTS.md` now explicitly requires reproducibility metadata and lock discipline.

Blocking defect:

```text
requirements-dev.in:  nflreadpy==0.1.5
requirements-dev.txt: no nflreadpy entry
```

Therefore a clean environment installed strictly from the committed hash lock does not reproduce the declared development/validation environment.

M0 cannot be certified until this is fixed.

---

# 6. F-2 Conformance at M0 Scope

F-2 governs provider/source architecture. Most implementation belongs to M3, but M0 must establish the correct repository and engineering boundary.

## Provider abstraction

**Status:** `SATISFIED AT CONSTITUTION LEVEL`

The repository constitution states that providers populate canonical contracts and do not define the architecture.

M3 certification will later inspect the actual provider protocols/adapters.

## Raw evidence first

**Status:** `SATISFIED AT CONSTITUTION LEVEL`

`AGENTS.md` requires immutable raw evidence and checksums before downstream use. The README repeats the rule.

M3 certification will later inspect the implementation itself.

## Provenance and licensing

**Status:** `SATISFIED AFTER REMEDIATION AT CONSTITUTION LEVEL`

The audit branch explicitly requires provider/schema/version/source/licensing/attribution metadata to remain part of provenance.

Actual provider metadata structures are an M3 concern.

## Conflicting providers / no silent overwrite

**Status:** `SATISFIED AT CONSTITUTION LEVEL`

The audit branch protects observation/revision history from silent overwrite.

Explicit multi-provider reconciliation implementation is M4/M3 scope.

## Daily-Data-Core boundary

**Status:** `SATISFIED`

README and `AGENTS.md` clearly state that cross-sport infrastructure belongs in Daily-Data-Core and NFL-native intelligence belongs in Daily-NFL.

This boundary must be rechecked whenever later milestones introduce generic odds/weather/travel/provider infrastructure.

---

# 7. F-3 Conformance at M0 Scope

F-3 implementation belongs primarily to M4, but M0 must lock the identity philosophy.

## Provider IDs are crosswalks

**Status:** `SATISFIED`

The constitution explicitly protects provider-neutral canonical identity.

## No silent fuzzy matching

**Status:** `SATISFIED AFTER REMEDIATION`

This was present in the architecture but not stated explicitly enough in the M0 agent constitution. The audit branch now requires ambiguous identity to remain unresolved rather than silently choosing the closest candidate.

## Reconciliation provenance/history

**Status:** `SATISFIED AFTER REMEDIATION AT CONSTITUTION LEVEL`

The audit branch requires method, confidence, provenance, and reconciliation history to remain auditable.

M4 will certify the actual code/schema behavior.

---

# 8. F-4 Conformance at M0 Scope

F-4 is a scientific validity requirement. M5 owns the detailed PIT engine, but M0 must make it impossible for later contributors to interpret PIT casually.

## Prediction cutoff

**Status:** `SATISFIED AFTER REMEDIATION`

The M0 constitution now states the governing pregame condition explicitly:

```text
available_at <= prediction_time < kickoff
```

## No blanket Sunday/game-day exclusion

**Status:** `SATISFIED AFTER REMEDIATION`

The audit branch explicitly records that game-day data is legitimate if it was defensibly available before the relevant prediction cutoff.

## Four temporal clocks

**Status:** `SATISFIED AFTER REMEDIATION AT CONSTITUTION LEVEL`

The audit branch explicitly protects:

```text
effective_at
published_at
observed_at
ingested_at
```

and a defensible derived `available_at` with method/confidence.

M2/M5 will certify persistence and selection behavior.

## Append-only revisions / bitemporal thinking

**Status:** `SATISFIED AFTER REMEDIATION AT CONSTITUTION LEVEL`

Historical truth and historical knowledge state are explicitly distinguished; destructive rewriting is prohibited where history matters.

## Fail-closed leakage

**Status:** `SATISFIED`

`AGENTS.md` already required fail-closed PIT validation; the audit branch retains and contextualizes that rule.

Actual leakage fixtures are M5 certification scope.

---

# 9. F-19 Conformance at M0 Scope

F-19's evaluator implementation belongs to M14, but M0 must establish the scientific evaluation constitution before model code is written.

## No random train/test split as final validation

**Status:** `SATISFIED AFTER REMEDIATION`

The audit branch explicitly states that authoritative final validation is chronological / walk-forward.

## Proper probabilistic scoring and calibration

**Status:** `SATISFIED AFTER REMEDIATION`

The constitution now makes probability quality/calibration primary and treats W/L, CLV, EV, and ROI as downstream evidence rather than substitutes.

## Reproducible model promotion

**Status:** `SATISFIED AFTER REMEDIATION AT CONSTITUTION LEVEL`

The agent rules now require reproducible promotion against appropriate baselines under equivalent historical information constraints.

M14 will certify implementation of metrics, walk-forward evaluation, experiment registry, champion/challenger, and promotion gates.

---

# 10. Findings

## Blocking finding B-01 — development lock does not match dependency input

Severity: **BLOCKER**

Current direct input:

```text
requirements-dev.in
    nflreadpy==0.1.5
```

Current generated lock:

```text
requirements-dev.txt
    nflreadpy entry absent
```

Impact:

- clean `--require-hashes` installation is not guaranteed to reproduce the declared environment;
- the M6B validation dependency is not captured in the committed development lock;
- F-0 reproducibility is violated at the environment layer;
- M0 cannot be architecture-certified.

Required remediation:

Regenerate `requirements-dev.txt` under Python 3.12 using the current committed dependency inputs. Do **not** manually add hashes or dependency lines.

## Finding F-02 — README bootstrap version drift

Severity: **MEDIUM — REMEDIATED ON AUDIT BRANCH**

Before audit:

```text
README: pip-tools==7.5.3
requirements-dev.in: pip-tools==7.6.0
```

Remediation:

README now uses `pip-tools==7.6.0`.

## Finding F-03 — README implementation status drift

Severity: **MEDIUM — REMEDIATED ON AUDIT BRANCH**

Before audit, README still stated:

```text
M0 repository bootstrap: in progress
M1 canonical domain contracts: next
```

That was materially stale after M1-M6 implementation.

Remediation:

README now states that M0 is undergoing formal conformance certification and M1-M6 remain provisional until audited in order.

## Finding F-04 — engineering constitution did not explicitly encode all M0 architecture dependencies

Severity: **MEDIUM — REMEDIATED ON AUDIT BRANCH**

`AGENTS.md` already protected several critical decisions, but F-3 no-silent-fuzzy-match, F-4 exact PIT cutoff/four clocks/game-day clarification, F-19 chronological final evaluation, and dependency-lock rules were not explicit enough for an engineering constitution.

Remediation:

Added explicit non-negotiable architecture and dependency-lock sections.

## Finding F-05 — no hosted CI workflow

Severity: **NONE / NOT A M0 DEFECT**

No `.github/workflows/` CI workflow is currently present.

The M0 roadmap requires **CI-ready quality-gate commands**, not hosted CI itself. The commands are explicitly defined and therefore this is not a certification blocker.

A hosted workflow may be added later if desired, but it should not be invented as an architecture requirement that the roadmap did not specify.

## Finding F-06 — no installable package metadata in `pyproject.toml`

Severity: **NONE / NOT A M0 DEFECT**

`pyproject.toml` currently acts as tool configuration rather than a full Python packaging manifest.

M0 requires package layout and clean imports, not publication to PyPI or editable installation metadata. The repo-local package structure and import smoke test satisfy the defined M0 endpoint.

If packaging/distribution becomes an operational requirement later, it should be added intentionally rather than retroactively treated as missing architecture.

---

# 11. Required Final Local Validation

After checking out the audit branch, regenerate the dev lock under Python 3.12 and run the full M0 gate.

PowerShell:

```powershell
git fetch origin
git switch audit/m0-architecture-conformance

.\.venv\Scripts\Activate.ps1
python --version
python -m pip install --upgrade pip
python -m pip install pip-tools==7.6.0

python -m piptools compile --resolver=backtracking --generate-hashes --strip-extras --allow-unsafe --output-file=requirements-dev.txt requirements-dev.in

python -m pip install --require-hashes -r requirements-dev.txt

python -c "import daily_nfl, nflreadpy; print('daily_nfl', daily_nfl.__version__); print('nflreadpy import OK')"

python -m pytest -q
python -m ruff check .
python -m mypy .

git diff -- requirements-dev.txt
```

Expected conditions for certification:

1. Python reports a 3.12.x interpreter.
2. `pip-compile` completes successfully.
3. `requirements-dev.txt` now includes `nflreadpy==0.1.5` and all required hashes/transitive dependencies.
4. `pip install --require-hashes -r requirements-dev.txt` succeeds.
5. `daily_nfl` imports and reports `0.1.0`.
6. `nflreadpy` imports successfully.
7. pytest passes.
8. Ruff passes.
9. mypy passes.
10. The only intended generated-code change is the refreshed dependency lock unless the resolver reveals a legitimate dependency conflict that must be investigated.

The regenerated `requirements-dev.txt` should then be committed to the audit branch.

---

# 12. Certification Decision

## Current decision

```text
M0 ARCHITECTURE-CONFORMANCE AUDIT: COMPLETE
M0 ARCHITECTURE CERTIFICATION: WITHHELD
```

Reason:

```text
BLOCKER B-01
requirements-dev.txt is stale relative to requirements-dev.in
```

All other M0-scoped architecture/documentation defects discovered by this audit have been remediated on the audit branch.

## Certification rule

Once B-01 is closed and the clean Python 3.12 quality gate passes, M0 may be stamped:

```text
M0 — ARCHITECTURE-CERTIFIED
```

At that point:

- update `PROJECT_CHECKPOINT_LOG.md` with the certification evidence;
- update this document with the final validation output and certification commit;
- merge the M0 audit branch;
- begin the **M1 architecture-conformance audit** against F-1, F-3, and F-5.

Do not begin formal M1 certification before M0 is closed.
