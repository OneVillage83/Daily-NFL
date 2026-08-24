# M6 Local Validation — 2026-08-23

**Project:** The Daily Line — Daily NFL  
**Milestone:** M6 — Canonical Play / Drive Normalization  
**Architecture:** F-5 — Canonical Play / Event / Possession / Drive Architecture  
**Validated executable SHA:** `5f1e2efe115c8f889d99eb7f6169050ee90c8ca7`  
**Interpreter:** Python 3.12.10 — `E:\Daily-NFL\.venv\Scripts\python.exe`  
**Result:** **PASS**

---

## 1. Exact-head / clean-tree check

```text
git rev-parse HEAD
5f1e2efe115c8f889d99eb7f6169050ee90c8ca7

git status --short
<clean>
```

No executable or test changes occurred after this SHA during validation. Documentation-only certification commits may follow and must not replace this executable proof point.

---

## 2. Targeted persistence regression gate

```text
python -m pytest -q tests/test_play_normalization_persistence.py
5 passed in 0.50s
```

This targeted gate includes the final PR-review remediations:

- deterministic normalized observation identity is enforced by the writer;
- exact idempotent child membership is checked;
- extra participation/penalty children are rejected;
- bad acquisition provenance fails closed;
- failed persistence remains atomic;
- provider revisions append rather than replacing canonical identity.

---

## 3. Project quality gate

```text
python -m ruff check .
All checks passed!

python -m mypy .
Success: no issues found in 89 source files

python -m pytest -q
171 passed in 3.93s
```

---

## 4. SQLite schema/integrity gate

M6 required no schema v8. Existing M2 canonical child ledgers plus M5 schema-v7 acquisition-observation columns already satisfy the F-5 persistence requirements.

Fresh database:

```json
{"foreign_keys_enabled":true,"integrity_ok":true,"mode":"migrate","schema_version_after":7,"schema_version_before":0,"supported_schema_version":7}
```

Current-schema check:

```json
{"foreign_keys_enabled":true,"integrity_ok":true,"mode":"check","schema_version_after":7,"schema_version_before":7,"supported_schema_version":7}
```

Result:

```text
schema 0 -> 7: PASS
schema 7 -> 7: PASS
foreign keys: PASS
integrity: PASS
```

---

## 5. Deterministic no-network F-5 validator

Command:

```powershell
python scripts/validate_m6_normalization.py --database $db
```

Observed evidence:

```text
schema_version: 7
primary_play_type: PASS
semantic_label: PLAY_ACTION_PASS
event_types: SNAP, THROW, TARGET, CATCH, PENALTY
participation_count: 2
penalty_count: 1
state_after_present: true
state_after_drive_continues: true
drive_play_count: 2
drive_first_downs: 1
provider_id: nflverse
evidence_id: m6-fixture-evidence
evidence_observation_id: reo_m6_fixture_observation
normalized_sha256: 5d6443c92367c6ee134d257deecc7a58d55e46bdcafa1f0a1a19bee76e5c3f2a
payload_sha256:    5d6443c92367c6ee134d257deecc7a58d55e46bdcafa1f0a1a19bee76e5c3f2a
payload_is_provider_neutral: true
nonadjacent_state_after_fail_closed: true
bad_provenance_fail_closed: true
bad_provenance_atomic: true
```

This proves the certified persistence boundary retains both immutable raw-content identity and the exact acquisition-observation identity, rejects mismatched provenance before canonical data can survive, and excludes provider-shaped IDs/free text from the downstream canonical payload.

The targeted persistence gate additionally proves that a write cannot supply an arbitrary observation ID and that idempotent replay rejects extra child membership instead of merely confirming expected children exist.

---

## 6. Real nflverse dependency gate

```text
nflreadpy version: 0.1.5
```

`requirements-dev.in` pins `nflreadpy==0.1.5`, and the generated hashed `requirements-dev.txt` contains the same exact version.

---

## 7. Corrected real 2025 nflverse full-season PBP gate

Command:

```powershell
python scripts/validate_nflverse_pbp_normalization.py `
    --season 2025 `
    --output "local-data/m6b/pbp-normalization-validation-2025-cert.json"
```

Provider dataset:

```text
season: 2025
row_count: 48,771
extracted_and_normalized_count: 45,196
extraction_error_count: 3,575
normalization_error_count: 0
```

Canonical play taxonomy:

```text
ADMINISTRATIVE       10
EXTRA_POINT        1,330
FIELD_GOAL         1,140
KICKOFF            2,927
KNEEL                453
OTHER                 60
PASS              18,288
PENALTY_ONLY       2,447
PUNT               2,042
RUSH              13,714
SACK               1,352
SCRAMBLE           1,221
SPIKE                 82
TWO_POINT            130
```

Strict extraction exclusions:

```text
pre-play home/away score cannot be reconstructed
  <NULL>:    589
  no_play: 2,140

required nflverse field 'quarter_seconds_remaining' is missing
  <NULL>:      2

required nflverse field 'yardline_100' is missing
  <NULL>:    844
```

All 3,575 rejects remain confined to `<NULL>` / `no_play` provider rows. No successfully extracted state-bearing play failed canonical normalization.

### Corrected state-after evidence

```text
next_state_adjacent_validated: 41,975
next_state_nonadjacent_skipped: 2,936
next_state_error_count: 0
```

This supersedes the historical M6B `173 validated / 0 failures` next-state check for certification purposes. The old validator paired adjacent *surviving* extracted rows and did not prove that no rejected raw row sat between them. The corrected validator carries the original raw-row index and validates `PLAY_STATE_AFTER` only when the next successfully extracted row is literally the next provider row.

The 2,936 skipped pairs are expected positive evidence: the validator detected a raw-row gap and refused to bridge it.

---

## 8. Certification conclusion

All required M6/F-5 executable gates passed on the exact clean executable SHA:

```text
Python 3.12.10 project venv                   PASS
targeted persistence regressions — 5 passed  PASS
Ruff                                          PASS
strict mypy                                   PASS
pytest — 171 passed                           PASS
SQLite 0 -> 7                                 PASS
SQLite 7 -> 7                                 PASS
no-network F-5 validator                      PASS
canonical PLAY_EXECUTION / modifiers          PASS
ordered event stream                          PASS
canonical participation                       PASS
first-class penalty handling                  PASS
physical vs official outcome separation       PASS
adjacent PLAY_STATE_AFTER                      PASS
nonadjacent transition fail-closed             PASS
deterministic drive normalization              PASS
raw evidence provenance                        PASS
acquisition-observation provenance              PASS
deterministic observation identity              PASS
exact idempotent child membership               PASS
atomic failed-provenance rollback               PASS
provider-neutral canonical payload              PASS
real 2025 PBP normalization — 45,196 rows      PASS
real normalization errors — 0                   PASS
adjacent state transitions — 41,975             PASS
adjacent state errors — 0                       PASS
nonadjacent transitions explicitly skipped      PASS
git working tree clean                          PASS
```

**M6 executable validation decision: PASS.**
