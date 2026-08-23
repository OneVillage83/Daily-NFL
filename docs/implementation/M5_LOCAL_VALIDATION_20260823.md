# M5 Local Validation — 2026-08-23

**Project:** The Daily Line — Daily NFL  
**Milestone:** M5 — Historical PIT Engine  
**Architecture dependency:** F-4 — Historical Point-in-Time Architecture  
**Validated executable code head:** `d553c3a46b36478b069eae97b7b52f283c97b47a`  
**Validation environment:** Windows PowerShell, repository `E:\Daily-NFL`, active Python 3.12.10 `.venv`

## Exact interpreter and repository gate

The final certification run explicitly confirmed the project interpreter, exact executable branch head, and a clean working tree before and after execution.

```text
Python 3.12.10
E:\Daily-NFL\.venv\Scripts\python.exe
HEAD: d553c3a46b36478b069eae97b7b52f283c97b47a
git status --short: clean
```

## Cross-provider schedule-state regression

The final pre-certification architecture review identified that provider-specific `schedule_version` values must remain provenance rather than participate in canonical cross-provider state agreement. The executable head removes `schedule_version` only from the cross-provider canonical-state signature while retaining schedule/provider revision metadata on the selected state and snapshot provenance.

The dedicated repository regression passed:

```text
python -m pytest -q tests/test_pit_schema_repository.py
5 passed in 0.57s
```

This test now verifies that two providers may agree on canonical schedule state while carrying different provider-specific schedule-version/revision labels, and that both supporting source inputs remain retained.

## Full repository quality gate

```text
Ruff: All checks passed!
mypy: Success: no issues found in 82 source files
pytest: 161 passed in 3.64s
git status --short: clean
```

## Fresh SQLite migration gate

A disposable certification database was initialized through the complete forward-only migration chain.

```json
{"database":"C:\\Users\\OneVi\\AppData\\Local\\Temp\\daily-nfl-m5-cert.db","foreign_keys_enabled":true,"integrity_ok":true,"mode":"migrate","schema_version_after":7,"schema_version_before":0,"supported_schema_version":7}
```

Result:

```text
schema 0 -> 7: PASS
foreign keys enabled: PASS
integrity: PASS
```

## SQLite check-mode gate

The same database was then checked without applying another migration.

```json
{"database":"C:\\Users\\OneVi\\AppData\\Local\\Temp\\daily-nfl-m5-cert.db","foreign_keys_enabled":true,"integrity_ok":true,"mode":"check","schema_version_after":7,"schema_version_before":7,"supported_schema_version":7}
```

Result:

```text
schema 7 -> 7: PASS
foreign keys enabled: PASS
integrity: PASS
```

## Deterministic historical PIT reconstruction gate

The deterministic M5 validator used two immutable historical schedule revisions for a 2025 fixture and reconstructed different information states around the correction's knowledge time.

```json
{"early_cutoff":"2025-09-11T17:20:00+00:00","early_observation_id":"m5-schedule-v1","early_status":"SCHEDULED","evidence_id":"0c1a6905fa2f853b71a2bde51c568da9501889b35959e047e8cefb1c5c6fcc49","evidence_observation_id":"reo_e5713113fdfc22acf68691cb33f181f0b88077fa00df89ec623af3121bb81404","fixture_season":2025,"game_id":"nflg_7f78c0d79df95548ae6f0e4522fd5609","later_correction_hidden_at_early_cutoff":true,"later_correction_visible_at_late_cutoff":true,"later_cutoff":"2025-09-11T19:20:00+00:00","later_observation_id":"m5-schedule-v2","later_status":"POSTPONED","leakage_fail_closed":true,"provider_id":"nflverse","provider_revision":"v1","raw_sha256":"59701c963b52d71347b1631498c9a4761e86d4f4f265abb39ff584ae518ff3dd","schema_version":7,"snapshot_id":"pit_525e1e538578b4f523c1a58f2926ec0d5f03c371daef9187ac4d07a82c0b4f6e","snapshot_input_count":1,"snapshot_sealed":true}
```

This establishes:

- early historical cutoff resolves `m5-schedule-v1` / `SCHEDULED`;
- later historical cutoff resolves `m5-schedule-v2` / `POSTPONED`;
- the later correction is invisible before its defensible knowledge time;
- the correction becomes visible after its knowledge time;
- the immutable snapshot seals successfully;
- raw evidence identity is retained;
- acquisition-observation identity is retained;
- provider/revision/checksum provenance is retained;
- deliberate current-game leakage is rejected fail-closed.

## F-4 negative/failure-state evidence

The final 161-test suite includes architecture-locking coverage for:

- all six standard PIT horizons;
- legitimate game-day information before cutoff;
- earliest defensible availability derivation;
- inferred timing confidence and explicit opt-in;
- same-knowledge conflicting revisions failing closed;
- deterministic same-content duplicates;
- bitemporal effective-state selection;
- missing `effective_at` failure;
- late correction to an older effective state not displacing newer real-world state;
- current-game result/stat/play leakage rejection;
- actual current-game weather rejection;
- later market quote rejection;
- future-game and future season/week label rejection;
- pre-completion season-final aggregate rejection;
- provider-correction context requirements;
- raw acquisition provenance requirements;
- deterministic feature-snapshot identity;
- sealed snapshot membership;
- raw evidence/provider/checksum database enforcement;
- retrospective actual-kickoff boundary enforcement;
- provider schedule disagreement failure;
- provider agreement with distinct provider-specific version labels;
- v6 -> v7 legacy PIT snapshot preservation;
- M3/M4 forward-migration preservation.

## Certification conclusion

All executable M5 / F-4 certification conditions passed at exact executable head `d553c3a46b36478b069eae97b7b52f283c97b47a`:

```text
M5 LOCAL QUALITY GATE: PASS
M5 TARGETED CROSS-PROVIDER REGRESSION: PASS
M5 SQLITE 0→7 MIGRATION GATE: PASS
M5 SQLITE 7→7 CHECK GATE: PASS
M5 HISTORICAL PIT RECONSTRUCTION GATE: PASS
M5 LEAKAGE FAIL-CLOSED GATE: PASS
M5 F-4 ARCHITECTURE CERTIFICATION: PASS
```

Documentation/status commits made after the validated executable head record certification evidence only. The executable certification authority remains `d553c3a46b36478b069eae97b7b52f283c97b47a` unless a later executable change explicitly reopens M5.