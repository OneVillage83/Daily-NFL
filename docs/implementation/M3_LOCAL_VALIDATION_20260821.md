# M3 Local Validation — 2026-08-21

**Project:** The Daily Line — Daily NFL  
**Milestone:** M3 — Raw Evidence & Provider Abstraction  
**Architecture dependency:** F-2  
**Validated code head:** `3276d5f77027bf2894294a1d66c99c0958ca3286`  
**Validation environment:** Windows PowerShell, repository `E:\Daily-NFL`, active `.venv`

## Full repository quality gate

The M3 branch was pulled locally and validated from a clean working tree.

```text
pytest: 130 passed in 2.48s
Ruff: All checks passed!
mypy: Success: no issues found in 71 source files
git status --short: clean
```

## Real nflverse exact-byte acquisition gate

A fresh disposable SQLite database and raw-evidence directory were used to acquire the nflverse schedule through the certified provider adapter, raw evidence store, and metadata persistence path.

Key observed result:

```text
schema_version: 5
provider_id: nflverse
dataset: SCHEDULE
raw_evidence_count: 1
raw_observation_count: 1
capability_snapshot_count: 1
license_id: CC-BY-4.0
attribution_required: true
attribution_text: nflverse
size_bytes: 518008
```

The downloaded content was stored at a content-addressed raw path and independently re-read from disk. The acquired and stored SHA-256 values were identical:

```text
sha256:
b8e679b3fb05b8ccbebd296533f24b575ced0fc298fc5b262a8a560d6f1955e1

stored_sha256:
b8e679b3fb05b8ccbebd296533f24b575ced0fc298fc5b262a8a560d6f1955e1
```

The acquisition persisted distinct raw-content and observation identity:

```text
evidence_id:
4784fa4b03c00d7b01ddcde49188d8c36392900d4111e77704da5fece5e3da8a

evidence_observation_id:
reo_3b76520b82a3c90be5abf791eb92db49e1495cbd931e04dbc50f6360159fa9b4

capability_id:
pcap_819019fa646f18613f38cd155563ee0159844fb2936e279ef048c43d71a14bda
```

The upstream response also exposed a valid publication timestamp through HTTP metadata, and M3 retained it rather than fabricating one:

```text
published_at: 2026-08-21T19:16:24+00:00
observed_at: 2026-08-21T19:22:52.857692+00:00
ingested_at: 2026-08-21T19:22:52.857692+00:00
available_at: 2026-08-21T19:22:52.857692+00:00
```

This gate proves that the certified M3 path can acquire exact upstream bytes, persist immutable content plus an independent acquisition observation, retain capability/licensing context, and verify stored checksum parity under schema version 5.

## nflreadpy Lane-B historical schema gate

The validation-only nflreadpy path was exercised for the 2025 schedule slice.

```text
nflreadpy_version: 0.1.5
season: 2025
row_count: 285
column_count: 46
required_columns: season, game_id, home_team, away_team
```

Required schema:

```text
season: Int32
game_id: String
home_team: String
away_team: String
```

First returned row:

```text
game_id: 2025_01_DAL_PHI
home_team: PHI
away_team: DAL
season: 2025
```

This validates the small historical Lane-B requirement without making nflreadpy the production owner of raw evidence.

## Certification conclusion

All M3 certification conditions are satisfied at validated executable code head `3276d5f77027bf2894294a1d66c99c0958ca3286`:

```text
M3 LOCAL QUALITY GATE: PASS
M3 REAL NFLVERSE RAW GATE: PASS
M3 STORED CHECKSUM / PROVENANCE GATE: PASS
M3 NFLREADPY LANE-B GATE: PASS
M3 ARCHITECTURE CERTIFICATION: PASS
```

Documentation commits created after the validated code head record this evidence and status only; they do not change the provider, persistence, schema, or acquisition behavior that was executed locally.
