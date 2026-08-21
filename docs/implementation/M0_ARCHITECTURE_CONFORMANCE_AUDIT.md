# M0 Architecture-Conformance Audit

**Project:** The Daily Line — Daily NFL  
**Milestone:** M0 — Repository Bootstrap & Engineering Constitution  
**Audit date:** 2026-08-21  
**Audit branch:** `audit/m0-architecture-conformance`  
**Governing roadmap:** `docs/implementation/IMPLEMENTATION_ROADMAP_V1.md`  
**Architecture dependencies:** F-0, F-2, F-3, F-4, F-19  
**Certification status:** **NOT YET CERTIFIED — BLOCKED ON HASHED DEPENDENCY-LOCK REFRESH + CLEAN-ENVIRONMENT VALIDATION**

---

## 1. Audit Purpose

This audit is the first formal milestone certification pass for Daily NFL. The question is not whether M0 files merely exist; it is whether the engineering foundation matches the intended endpoint established by the locked architecture and is safe to treat as a stable dependency for later milestones.

Status vocabulary:

- `SATISFIED` — requirement is present and consistent with the architecture.
- `SATISFIED AFTER REMEDIATION` — a defect was found and corrected during this audit.
- `BLOCKED` — certification cannot be granted until the item is resolved.
- `DEFERRED BY ARCHITECTURE` — governing principle is established at M0, implementation belongs later.
- `NOT APPLICABLE TO RETROACTIVE CERTIFICATION` — original sequencing language, not a permanent system property.

M0 is not certified until every blocking item is closed and the clean-environment validation gate passes.

---

## 2. Governing M0 Contract

Roadmap architecture dependencies:

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

Because this is a retroactive audit after M1-M6 implementation already exists, `no NFL/provider logic yet` is interpreted as a sequencing constraint: the M0 engineering scaffold itself must remain independent of provider-specific or NFL-domain implementation details. It is not a requirement to delete later milestone code.

---

## 3. Repository Evidence Reviewed

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

The full repository tree was also reviewed for package/test/document structure and hidden alternative configuration paths.

---

## 4. M0 Deliverable Conformance Matrix

| ID | Requirement | Status | Evidence / finding |
|---|---|---|---|
| M0-01 | Python 3.12 project baseline | `SATISFIED` | `.python-version` is `3.12`; Ruff and mypy target 3.12. |
| M0-02 | Package layout | `SATISFIED` | `daily_nfl/` is a real package; root package exposes version metadata only. |
| M0-03 | `.gitignore` | `SATISFIED` | Caches, environments, secrets, DBs, local data, artifacts, build output, editors/OS files are excluded. |
| M0-04 | `.python-version` | `SATISFIED` | Explicit Python 3.12 pin. |
| M0-05 | Dependency input files | `SATISFIED` | `requirements.in` and `requirements-dev.in` exist with explicit direct pins. |
| M0-06 | Compiled dev lock reproduces current input | `BLOCKED` | Committed `requirements-dev.txt` predates `nflreadpy==0.1.5`; final hashed refresh is still required. |
| M0-07 | pytest configuration | `SATISFIED` | `pyproject.toml` defines test path/options. |
| M0-08 | Ruff configuration | `SATISFIED` | Python 3.12 target and lint policy explicit. |
| M0-09 | mypy configuration | `SATISFIED` | Strict mypy enabled for package/tests. |
| M0-10 | `AGENTS.md` constitution | `SATISFIED AFTER REMEDIATION` | Audit added explicit scientific/provider/identity/PIT/evaluation and lock-toolchain invariants. |
| M0-11 | Implementation README | `SATISFIED AFTER REMEDIATION` | Status, architecture rules, and pinned compiler bootstrap corrected. |
| M0-12 | Version module | `SATISFIED` | `daily_nfl/version.py` defines `0.1.0`; root package re-exports it. |
| M0-13 | Basic test package | `SATISFIED` | `tests/` exists with package smoke coverage plus later milestone tests. |
| M0-14 | Package import smoke test | `SATISFIED IN CODE; CLEAN RUN PENDING` | `tests/test_package.py` verifies package version. |
| M0-15 | CI-ready quality-gate commands | `SATISFIED` | README/AGENTS define pytest, Ruff, mypy. Hosted CI is not required by M0. |
| M0-16 | M0 scaffold avoids provider coupling | `SATISFIED` | Root package/version/config do not import provider modules. |

---

## 5. F-0 Conformance at M0 Scope

M0 establishes the scientific engineering constitution; later milestones implement the model stack.

- Probability-distribution mission: `SATISFIED AFTER REMEDIATION`.
- Predict everything; recommend selectively: `SATISFIED AT CONSTITUTION LEVEL`.
- Football-only / market-only / market-aware separation: `SATISFIED AT CONSTITUTION LEVEL`.
- Uncertainty as first-class information: `SATISFIED AFTER REMEDIATION AT CONSTITUTION LEVEL`.
- Continuous research architecture: `SATISFIED`.
- Reproducibility: `BLOCKED` only on final hashed lock refresh + clean environment validation.

The package/runtime/version/tooling structure otherwise supports the F-0 reproducibility direction.

---

## 6. F-2 Conformance at M0 Scope

- Provider abstraction philosophy: `SATISFIED AT CONSTITUTION LEVEL`.
- Raw evidence first: `SATISFIED AT CONSTITUTION LEVEL`.
- Provenance/licensing metadata discipline: `SATISFIED AFTER REMEDIATION AT CONSTITUTION LEVEL`.
- No silent provider overwrite: `SATISFIED AT CONSTITUTION LEVEL`.
- Daily-Data-Core vs Daily-NFL boundary: `SATISFIED`.

Actual provider code will be certified at M3.

---

## 7. F-3 Conformance at M0 Scope

- Provider IDs remain crosswalks: `SATISFIED`.
- No silent fuzzy matching: `SATISFIED AFTER REMEDIATION`.
- Reconciliation confidence/method/provenance/history remains auditable: `SATISFIED AFTER REMEDIATION AT CONSTITUTION LEVEL`.

Actual identity/reconciliation behavior will be certified at M4.

---

## 8. F-4 Conformance at M0 Scope

The M0 constitution explicitly protects:

```text
available_at <= prediction_time < kickoff
```

and also protects:

- no blanket Sunday/game-day exclusion;
- distinct `effective_at`, `published_at`, `observed_at`, `ingested_at` clocks where available;
- defensible `available_at` with method/confidence;
- historical truth vs historical knowledge state;
- append-only/traceable revisions;
- fail-closed leakage validation.

Status: `SATISFIED AT CONSTITUTION LEVEL` after remediation. Actual PIT implementation is certified at M5.

---

## 9. F-19 Conformance at M0 Scope

The M0 constitution now requires:

- chronological / walk-forward final validation;
- proper probabilistic scoring and calibration as primary evidence;
- W/L, CLV, EV, ROI as downstream evidence;
- reproducible model promotion against appropriate baselines under identical historical information constraints.

Status: `SATISFIED AFTER REMEDIATION AT CONSTITUTION LEVEL`. Evaluation implementation is certified later at M14.

---

## 10. Findings

### B-01 — committed dev lock is stale

Severity: **BLOCKER**

```text
requirements-dev.in:  nflreadpy==0.1.5
committed requirements-dev.txt: nflreadpy absent
```

The lock must be regenerated under the pinned Python 3.12 compiler toolchain with hashes and all transitive dependencies.

### F-02 — README bootstrap version/toolchain drift

Severity: **MEDIUM — REMEDIATED**

The README previously used stale `pip-tools==7.5.3` and then used an unpinned pip upgrade. The local validation attempt showed that upgrading pip from `26.1.2` to `26.2.1` breaks `pip-tools==7.6.0` with an import of removed pip internals.

The audit branch now pins the compiler pair:

```text
pip==26.1.2
pip-tools==7.6.0
```

and explicitly forbids an unpinned pip upgrade before lock compilation.

### F-03 — README implementation status drift

Severity: **MEDIUM — REMEDIATED**

README now reflects the architecture-certification workflow rather than claiming M0 is merely in progress and M1 is next.

### F-04 — M0 constitution lacked explicit architecture invariants

Severity: **MEDIUM — REMEDIATED**

`AGENTS.md` now explicitly encodes the relevant F-0/F-2/F-3/F-4/F-19 invariants and dependency-lock discipline.

### F-05 — no hosted CI workflow

Severity: **NONE / NOT AN M0 DEFECT**

M0 requires CI-ready commands, not hosted CI itself.

### F-06 — `pyproject.toml` is tooling config, not full package publication metadata

Severity: **NONE / NOT AN M0 DEFECT**

M0 requires package layout/importability, not PyPI publication metadata.

### F-07 — local lock-validation toolchain incompatibility discovered

Severity: **MEDIUM — REMEDIATED IN DOCUMENTATION; FINAL RERUN REQUIRED**

During local validation, `python -m pip install --upgrade pip` moved pip to `26.2.1`. With `pip-tools==7.6.0`, hashed lock compilation failed:

```text
ImportError: cannot import name 'stdlib_pkgs' from 'pip._internal.utils.compat'
```

This is a lock compiler toolchain defect, not an application defect. The project compiler pair is now pinned to `pip==26.1.2` / `pip-tools==7.6.0`.

Detailed evidence is preserved in:

- `docs/implementation/M0_LOCAL_VALIDATION_20260821.md`

---

## 11. Local Validation Evidence So Far

The 2026-08-21 local run established:

```text
Python: 3.12.10
nflreadpy dependency resolution: PASS
nflreadpy import: PASS
daily_nfl import/version: PASS (0.1.0)
pytest: 105 passed
Ruff: All checks passed!
mypy: Success, 66 source files
```

These are strong application-quality results. They are not sufficient to certify M0 because the successful dependency resolution file was generated without the required hashes, and the later hashed compile was attempted under the incompatible pip `26.2.1` compiler environment.

---

## 12. Required Final Local Validation

The previous unpinned pip-upgrade procedure is superseded. Use the pinned compiler toolchain.

From the audit branch:

```powershell
.\.venv\Scripts\Activate.ps1
python --version
python -m pip install "pip==26.1.2" "pip-tools==7.6.0"

python -m piptools compile --resolver=backtracking --generate-hashes --strip-extras --allow-unsafe --output-file=requirements-dev.txt requirements-dev.in

Select-String -Path requirements-dev.txt -Pattern "^nflreadpy==0\.1\.5"

py -3.12 -m venv local-data\m0-cert-venv
.\local-data\m0-cert-venv\Scripts\python.exe -m pip install --require-hashes -r requirements-dev.txt

.\local-data\m0-cert-venv\Scripts\python.exe -c "import daily_nfl, nflreadpy; print('daily_nfl', daily_nfl.__version__); print('nflreadpy import OK')"
.\local-data\m0-cert-venv\Scripts\python.exe -m pytest -q
.\local-data\m0-cert-venv\Scripts\python.exe -m ruff check .
.\local-data\m0-cert-venv\Scripts\python.exe -m mypy .

git status --short
git diff -- requirements-dev.txt
```

Expected certification conditions:

1. Python is 3.12.x.
2. compiler environment is `pip==26.1.2` + `pip-tools==7.6.0`.
3. hashed compile succeeds.
4. lock header records hash-generation/strip-extras/allow-unsafe invocation.
5. lock includes `nflreadpy==0.1.5` with hashes and transitive dependencies.
6. a fresh ignored venv installs the lock using `--require-hashes`.
7. `daily_nfl` and `nflreadpy` import in the fresh venv.
8. pytest, Ruff, and mypy pass in that fresh venv.
9. regenerated `requirements-dev.txt` is the intended generated change.

The fresh certification venv is created inside `local-data/`, which is already ignored by repository policy.

---

## 13. Certification Decision

Current state:

```text
M0 ARCHITECTURE-CONFORMANCE AUDIT: COMPLETE
M0 LOCAL CODE QUALITY GATE: PASS
M0 DEPENDENCY RESOLUTION: PASS
M0 HASHED LOCK REPRODUCIBILITY: BLOCKED ON FINAL PINNED-TOOLCHAIN RERUN
M0 ARCHITECTURE CERTIFICATION: WITHHELD
```

Once the final pinned-toolchain hashed lock and clean-environment gate pass, M0 may be stamped:

```text
M0 — ARCHITECTURE-CERTIFIED
```

Then:

- commit the refreshed `requirements-dev.txt` to the audit branch;
- update `PROJECT_CHECKPOINT_LOG.md` with certification evidence;
- update this document with final results and certification commit;
- merge the M0 audit branch;
- begin M1 architecture-conformance against F-1, F-3, and F-5.

Do not begin formal M1 certification before M0 is closed.
