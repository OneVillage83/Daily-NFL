# M2 Local Validation — 2026-08-21

**Project:** The Daily Line — Daily NFL  
**Milestone:** M2 — Persistence & Migration Foundation  
**Architecture dependencies:** F-2, F-3, F-4, F-5  
**Validated code head:** `d6246696f29e263049f3bb07dd5eb5538e589c22`  
**Validation environment:** Windows PowerShell, repository `E:\Daily-NFL`, active `.venv`

## Full repository quality gate

The final M2 branch head was pulled locally with a clean working tree before validation.

```text
pytest: 124 passed in 2.30s
Ruff: All checks passed!
mypy: Success: no issues found in 68 source files
git status --short: clean
```

## Real SQLite initialization gate

A fresh disposable SQLite database was created through the repository migration CLI.

```json
{"database": "C:\\Users\\OneVi\\AppData\\Local\\Temp\\daily-nfl-m2-cert.db", "foreign_keys_enabled": true, "integrity_ok": true, "mode": "migrate", "schema_version_after": 4, "schema_version_before": 0, "supported_schema_version": 4}
```

This proves a clean database initializes from schema version 0 to the current supported schema version 4 with foreign keys enabled and SQLite integrity checks passing.

## Real SQLite check-mode gate

The same database was then validated in non-migrating check mode.

```json
{"database": "C:\\Users\\OneVi\\AppData\\Local\\Temp\\daily-nfl-m2-cert.db", "foreign_keys_enabled": true, "integrity_ok": true, "mode": "check", "schema_version_after": 4, "schema_version_before": 4, "supported_schema_version": 4}
```

This proves the persisted migration ledger is accepted as complete and current, schema version 4 remains unchanged in check mode, foreign keys remain enabled, and database integrity remains valid.

## Failure-state evidence encountered during certification

The local gate also exercised the strengthened migration and event-ledger contracts. Two stale test expectations were discovered and corrected without weakening implementation behavior:

1. a completed pass with a penalty correctly persists four canonical play events (`SNAP`, `THROW`, `CATCH`, `PENALTY`), not three;
2. legacy v3 rows accept one explicit identity-link backfill and then reject subsequent mutation with entity-specific immutability errors for game, drive, and play identity.

These were test-contract corrections, not architecture rollbacks.

## Certification conclusion

All M2 certification conditions are satisfied at validated code head `d6246696f29e263049f3bb07dd5eb5538e589c22`:

```text
M2 LOCAL QUALITY GATE: PASS
M2 REAL SQLITE INITIALIZE/CHECK GATE: PASS
M2 ARCHITECTURE CERTIFICATION: PASS
```

Documentation commits created after the validated code head record this evidence only; they do not alter the code/schema behavior that was executed locally.
