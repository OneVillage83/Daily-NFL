# M0 Local Validation Evidence — 2026-08-21

**Project:** The Daily Line — Daily NFL  
**Milestone:** M0 — Repository Bootstrap & Engineering Constitution  
**Branch:** `audit/m0-architecture-conformance`  
**Final result:** **PASS — used for M0 architecture certification**

---

## 1. Environment

Final certification interpreter:

```text
Python 3.12.10
```

Validated lock-compiler toolchain:

```text
pip==26.1.2
pip-tools==7.6.0
```

Required M6B development dependency:

```text
nflreadpy==0.1.5
```

---

## 2. Preliminary discovery and failed compiler attempt

An initial dependency-resolution run without hash-generation flags successfully resolved `nflreadpy==0.1.5` and its transitive dependencies. That established that the dependency input itself was valid, but the generated file was not acceptable as the project lock because hashes were omitted.

A subsequent attempt upgraded pip without a version pin:

```text
pip 26.1.2 -> 26.2.1
```

With `pip-tools==7.6.0`, lock compilation then failed with:

```text
ImportError: cannot import name 'stdlib_pkgs' from 'pip._internal.utils.compat'
```

This was diagnosed as a lock-compiler toolchain incompatibility rather than a Daily NFL application failure.

M0 remediation:

- remove the unsafe unpinned pip-upgrade instruction;
- explicitly use the validated pair `pip==26.1.2` / `pip-tools==7.6.0` for lock compilation;
- document the lock-toolchain rule in README and `AGENTS.md`.

---

## 3. Final hashed dependency lock

`requirements-dev.txt` was regenerated with the required reproducibility flags under Python 3.12:

```text
--generate-hashes
--strip-extras
--allow-unsafe
```

The resulting lock preserves the prior dependency set and adds the missing nflreadpy graph.

Observed diff summary:

```text
requirements-dev.txt | 229 +++++++++++++++++++++++++++++++++++++++++++++++++++
1 file changed, 229 insertions(+)
```

No existing lock entries were deleted.

The committed lock now includes:

```text
nflreadpy==0.1.5
```

with generated SHA-256 hashes, plus required dependencies including the resolved Polars, requests, pydantic-settings, platformdirs, and related packages.

Committed as:

```text
173f5a117325bb248a5ecc174ec27b6e3859447f
build: refresh hashed dev dependency lock
```

---

## 4. Fresh-environment certification run

A new ignored Python 3.12 virtual environment was used:

```text
local-data/m0-cert-venv
```

The fresh environment successfully imported both the project package and the provider dependency:

```text
daily_nfl 0.1.0
nflreadpy import OK
```

### pytest

```text
105 passed in 1.14s
```

### Ruff

```text
All checks passed!
```

### mypy

```text
Success: no issues found in 66 source files
```

The working-tree state after regeneration showed only the intended generated lock change before commit:

```text
M requirements-dev.txt
```

---

## 5. Certification conclusion

All M0 environment/reproducibility gates are satisfied:

```text
Python 3.12 baseline: PASS
pinned compiler toolchain: PASS
hashed dev lock generation: PASS
nflreadpy==0.1.5 captured in lock: PASS
fresh isolated environment: PASS
Daily NFL import/version: PASS
nflreadpy import: PASS
pytest: PASS — 105 tests
Ruff: PASS
strict mypy: PASS — 66 source files
```

Final result:

```text
M0 HASHED LOCK REPRODUCIBILITY: PASS
M0 CLEAN-ENVIRONMENT QUALITY GATE: PASS
M0 ARCHITECTURE CERTIFICATION: PASS
```

This evidence is incorporated into `M0_ARCHITECTURE_CONFORMANCE_AUDIT.md` and supports the formal status:

```text
M0 — ARCHITECTURE-CERTIFIED
```
