# M4 Local Validation — 2026-08-21

**Project:** The Daily Line — Daily NFL  
**Milestone:** M4 — Identity & Reconciliation Engine  
**Architecture dependency:** F-3 — Canonical Identity & Reconciliation  
**Validated executable code head:** `c15ef10df3e0f2eae393e0dc0c3c586b0d9f0505`  
**Validation environment:** Windows PowerShell, repository `E:\Daily-NFL`, active Python 3.12.10 `.venv`

## Exact interpreter gate

The final certification run used the project virtual environment rather than the host Python installation.

```text
Python 3.12.10
E:\Daily-NFL\.venv\Scripts\python.exe
```

The validated branch head was explicitly confirmed before the final gate:

```text
c15ef10df3e0f2eae393e0dc0c3c586b0d9f0505
```

## Full repository quality gate

The working tree was clean before and after validation.

```text
pytest: 141 passed in 2.65s
Ruff: All checks passed!
mypy: Success: no issues found in 76 source files
git status --short: clean
```

An earlier Ruff-only import-order failure in `daily_nfl/reconciliation/__init__.py` was corrected without changing behavior. The final exact executable head above is the head on which all three quality gates passed.

## Fresh SQLite migration gate

A disposable database was initialized from zero through the repository migration CLI.

```json
{"database":"C:\\Users\\OneVi\\AppData\\Local\\Temp\\daily-nfl-m4-cert.db","foreign_keys_enabled":true,"integrity_ok":true,"mode":"migrate","schema_version_after":6,"schema_version_before":0,"supported_schema_version":6}
```

This proves the complete migration chain initializes a clean database from schema 0 to the M4-supported schema version 6 with foreign keys enabled and SQLite integrity checks passing.

## SQLite check-mode gate

The same database was then validated without migration.

```json
{"database":"C:\\Users\\OneVi\\AppData\\Local\\Temp\\daily-nfl-m4-cert.db","foreign_keys_enabled":true,"integrity_ok":true,"mode":"check","schema_version_after":6,"schema_version_before":6,"supported_schema_version":6}
```

This proves the persisted migration ledger is accepted as complete/current and schema version 6 remains stable under check mode.

## Real nflverse reconciliation gate

The dedicated M4 validator acquired the real nflverse schedule asset through the certified M3 raw-evidence path, selected a 2025 schedule record, and carried its provenance into F-3 reconciliation.

```json
{"away_team_external_id":"DAL","canonical_franchise_id":"frn_ba67580448c44caeb4556c73fa20c80d","canonical_team_season_id":"tms_d8af3a2a168457139a53ef7899903335","evidence_id":"30f21cb79f6dcbacc606b4188bea1386c86f0ac0603ea908f335ab9c2c34763c","evidence_observation_id":"reo_82de6291cba590896226d07889904f245ca4d62143efce5cab6516b2be020cd6","franchise_status":"RESOLVED","home_team_external_id":"PHI","provider_id":"nflverse","reconciliation_evidence_rows":2,"schema_version":6,"season":2025,"sha256":"cef1b66dc08ab3d88e6bb4c0a33a368b3bb344a58536b86b81a3064b07ed2be7","source_record_id":"2025_01_DAL_PHI","stored_sha256":"cef1b66dc08ab3d88e6bb4c0a33a368b3bb344a58536b86b81a3064b07ed2be7","team_crosswalk_valid_from":"2025-03-01T00:00:00+00:00","team_crosswalk_valid_to":"2026-02-28T23:59:59.999999+00:00","team_season_match_method":"CANONICAL_COMPOSITE","team_season_status":"RESOLVED"}
```

The real-provider run establishes all of the following at once:

- the database is on schema version 6;
- exact acquired bytes are retained (`sha256 == stored_sha256`);
- the source record is explicit (`2025_01_DAL_PHI`);
- immutable raw content identity is retained (`evidence_id`);
- the particular acquisition observation is retained (`evidence_observation_id`);
- reconciliation evidence rows are persisted (`2`);
- the provider team identity resolves to an opaque canonical franchise ID rather than the provider abbreviation;
- TeamSeason identity is separately opaque and season-scoped;
- TeamSeason derivation uses `CANONICAL_COMPOSITE` rather than treating the provider ID as canonical;
- the crosswalk validity interval is explicitly bounded to the 2025 NFL season identity window.

## F-3 failure-state evidence covered by the M4 test suite

The final 141-test suite includes architecture-locking behavior for:

- ambiguous/fuzzy candidate handling without silent auto-resolution;
- provider-ID changes preserving canonical identity;
- same provider-local drive/play ID text being safely reused in different games through explicit identity scope;
- conflicting active crosswalks failing closed;
- wrong-season legacy TeamSeason mappings failing closed;
- canonical game context mismatch detection;
- explicit supersession when verification/method/confidence changes;
- append-only crosswalk, decision, and reconciliation-evidence ledgers;
- decision-required crosswalk creation;
- raw/source evidence retention on unresolved decisions;
- drive and play reconciliation using canonical game/sequence context.

## Certification conclusion

All M4 certification conditions are satisfied at validated executable head `c15ef10df3e0f2eae393e0dc0c3c586b0d9f0505`:

```text
M4 LOCAL QUALITY GATE: PASS
M4 SQLITE 0→6 MIGRATION GATE: PASS
M4 SQLITE 6→6 CHECK GATE: PASS
M4 REAL NFLVERSE RECONCILIATION GATE: PASS
M4 F-3 ARCHITECTURE CERTIFICATION: PASS
```

Documentation commits created after the validated executable head record certification evidence/status only; they do not alter the code/schema behavior that was executed locally.
