# M0 Local Validation Evidence — 2026-08-21

**Project:** The Daily Line — Daily NFL  
**Milestone:** M0 — Repository Bootstrap & Engineering Constitution  
**Branch:** `audit/m0-architecture-conformance`  
**Purpose:** Preserve the local validation evidence used by the M0 architecture-conformance audit.

---

## 1. Environment

Observed local interpreter:

```text
Python 3.12.10
```

Initial project compiler/dependency inputs expected:

```text
pip==26.1.2
pip-tools==7.6.0
nflreadpy==0.1.5
```

---

## 2. Preliminary dependency resolution

Before switching to the audit branch, `requirements-dev.txt` was regenerated without the M0-required hash-generation flags:

```powershell
python -m piptools compile `
  --resolver=backtracking `
  --output-file=requirements-dev.txt `
  requirements-dev.in
```

This successfully resolved:

```text
nflreadpy==0.1.5
polars==1.43.2
polars-runtime-32==1.43.2
pydantic-settings==2.15.0
requests==2.34.2
...
```

`Select-String` confirmed `nflreadpy==0.1.5` was present in the generated file.

This proved that the dependency input itself resolves successfully, but the resulting file is **not an acceptable M0 production lock** because it was generated without `--generate-hashes`, `--strip-extras`, and `--allow-unsafe`.

---

## 3. Preliminary code quality gate

Using that resolved environment, the local quality gate passed:

```text
pytest: 105 passed
Ruff: All checks passed!
mypy: Success: no issues found in 66 source files
```

This is positive code-quality evidence, but it does not by itself close the M0 reproducibility gate because the environment was not rebuilt from a valid hashed lock.

---

## 4. Audit-branch lock regeneration attempt

After switching to:

```text
audit/m0-architecture-conformance
```

the interpreter was confirmed as:

```text
Python 3.12.10
```

The command sequence then performed an unpinned pip upgrade:

```powershell
python -m pip install --upgrade pip
```

which changed pip from:

```text
26.1.2
```

to:

```text
26.2.1
```

`pip-tools==7.6.0` remained installed.

The required hashed compile then failed before dependency resolution with:

```text
ImportError: cannot import name 'stdlib_pkgs' from 'pip._internal.utils.compat'
```

This failure is a compiler-toolchain compatibility problem, not a Daily NFL application/test failure.

`pip-tools==7.6.0` imports pip internal APIs and is not compatible with the upgraded `pip==26.2.1` environment used in this attempt.

---

## 5. Important audit finding

The local validation exposed a second reproducibility issue in the previous README bootstrap instructions:

```text
python -m pip install --upgrade pip
```

was unsafe because it allowed the lock compiler's pip dependency to float beyond the tested/pinned compiler pair.

The M0 audit branch therefore changed the bootstrap policy to use the explicit compiler toolchain:

```text
pip==26.1.2
pip-tools==7.6.0
```

and forbids an unpinned pip upgrade before lock compilation.

---

## 6. Evidence that application dependencies are otherwise healthy

Even after the failed hashed compile, the already generated non-hashed dependency set was installed/available and the following checks succeeded:

```text
daily_nfl 0.1.0
nflreadpy import OK
pytest: 105 passed
Ruff: All checks passed!
mypy: Success: no issues found in 66 source files
```

Again, this validates the application code/dependency resolution but does **not** substitute for a clean install from the final hashed lock.

---

## 7. Current certification state

```text
M0 LOCAL CODE QUALITY GATE: PASS
M0 DEPENDENCY RESOLUTION: PASS
M0 HASHED LOCK REPRODUCIBILITY: NOT YET CLOSED
M0 ARCHITECTURE CERTIFICATION: WITHHELD
```

Remaining certification work:

1. restore/install `pip==26.1.2` with `pip-tools==7.6.0` under Python 3.12;
2. regenerate `requirements-dev.txt` with `--generate-hashes --strip-extras --allow-unsafe`;
3. confirm `nflreadpy==0.1.5` is present in the hashed lock;
4. create a fresh ignored Python 3.12 virtual environment;
5. install the hashed lock into that clean environment with `--require-hashes`;
6. run package/nflreadpy import checks in that clean environment;
7. run pytest, Ruff, and mypy using that clean environment;
8. commit the refreshed lock to the audit branch;
9. update the M0 conformance audit and project checkpoint with final certification evidence.
