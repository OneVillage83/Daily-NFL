# M3 Architecture-Conformance Audit

**Project:** The Daily Line — Daily NFL  
**Milestone:** M3 — Raw Evidence & Provider Abstraction  
**Audit date:** 2026-08-21  
**Audit branch:** `audit/m3-architecture-conformance`  
**Certified base:** M2 merge `a0e20f89951946f53b51db94a428669022294bd2`  
**Validated executable code head:** `3276d5f77027bf2894294a1d66c99c0958ca3286`  
**Architecture dependency:** F-2 — Data Source & Acquisition Architecture  
**Certification status:** **M3 — ARCHITECTURE-CERTIFIED**

---

## 1. Audit purpose

M3 certifies the boundary between external NFL data and the rest of Daily NFL. F-2 requires provider substitution, raw-first evidence retention, machine-readable capability and licensing metadata, defensible observation clocks, immutable history, and normalized-record lineage that can answer where a value came from and which exact observed bytes supported it.

The existing provider package was treated as provisional evidence. F-2 remained authoritative throughout certification.

---

## 2. Governing F-2 contract

Production acquisition must remain behind provider interfaces. Provider-shaped payloads must pass through immutable raw evidence before normalization, canonical state, features, or models.

The provider capability registry must be able to represent, where applicable: provider, dataset, entity coverage, field coverage, season coverage, cadence, expected latency, historical availability, point-in-time fidelity, reliability tier, schema version, license, attribution requirements, and cost class.

Normalized observations must remain traceable to provider/dataset/source-record identity, source publication and observation time, ingestion time, raw checksum/artifact, schema/parser version, and licensing context. Provider conflicts must survive acquisition so later reconciliation can reason about them explicitly.

---

## 3. Roadmap M3 contract

Deliverables:

- provider protocol/interfaces;
- provider capability registry;
- immutable raw evidence store contract;
- SHA-256 checksum generation;
- normalized acquisition result envelope;
- parser/provider schema version fields;
- licensing metadata fields;
- provider observation timestamps.

Initial provider is the nflverse / nflreadpy ecosystem behind an adapter. Production NFL domain code must not directly depend on provider-specific loaders. Local Lane-B validation may invoke nflreadpy to inspect schemas and small historical slices.

Exit conditions are one tiny dataset acquired through the abstraction, immutable checksummed raw evidence, and normalized records that retain provenance.

---

## 4. Conformance matrix

| ID | Requirement | Status | Evidence / remediation |
|---|---|---|---|
| M3-01 | Provider protocol isolates external acquisition | `SATISFIED` | `ProviderAdapter` exposes descriptor + raw acquisition contract. |
| M3-02 | Provider loaders stay out of domain/model ownership | `SATISFIED` | Production nflverse loader remains inside `daily_nfl.providers`; nflreadpy is validation-only. |
| M3-03 | Machine-readable provider capability registry | `SATISFIED AFTER REMEDIATION` | Existing registry retained; capability contract expanded materially. |
| M3-04 | Entity and field coverage represented | `SATISFIED AFTER REMEDIATION` | Added validated coverage tuples. |
| M3-05 | Season coverage, cadence, latency, historical availability represented | `SATISFIED AFTER REMEDIATION` | Added missing latency/history metadata while retaining season/cadence. |
| M3-06 | PIT fidelity and reliability tier represented | `SATISFIED AFTER REMEDIATION` | PIT enum retained; reliability tier added. |
| M3-07 | Schema/parser version represented | `SATISFIED AFTER REMEDIATION` | Descriptor/payload fields retained; capability-level schema metadata added where known. |
| M3-08 | License and attribution are dataset attributes | `SATISFIED AFTER REMEDIATION` | Added license ID/URL and explicit attribution requirement/text. |
| M3-09 | Cost class represented | `SATISFIED` | Existing `CostClass` retained. |
| M3-10 | Capability declaration matches implemented exact-raw adapter | `SATISFIED AFTER REMEDIATION` | Certified nflverse descriptor now declares only schedule + PBP mappings currently implemented. |
| M3-11 | Raw response is retained before parsing | `SATISFIED` | HTTP loader returns exact bytes; acquisition service stores them before downstream parsing. |
| M3-12 | SHA-256/content-addressed evidence identity | `SATISFIED` | Raw store contract plus live checksum parity gate. |
| M3-13 | Raw store is immutable and tamper-fail-closed | `SATISFIED` | Exclusive-create storage refuses overwrite when stored bytes disagree. |
| M3-14 | Raw content and acquisition observation are distinct | `SATISFIED AFTER REMEDIATION` | Migration v5 adds `raw_evidence_observations` while preserving M2 content ledger. |
| M3-15 | Re-observing unchanged bytes preserves history | `SATISFIED AFTER REMEDIATION` | Same content artifact can have multiple immutable acquisition observations. |
| M3-16 | Independent ingestion events get distinct observation identity | `SATISFIED AFTER REMEDIATION` | Identity includes evidence, source URI, observed time, and ingested time. |
| M3-17 | Full provenance clocks are retainable | `SATISFIED` | Effective/published/observed/ingested/available clocks retained where available. |
| M3-18 | Upstream publication timestamp captured when exposed | `SATISFIED AFTER REMEDIATION` | HTTP `Last-Modified` is parsed best-effort; live gate retained `2026-08-21T19:16:24+00:00`. |
| M3-19 | Capability/licensing metadata is historically snapshotable | `SATISFIED AFTER REMEDIATION` | Migration v5 adds append-only `provider_capability_snapshots`. |
| M3-20 | Raw observation snapshots license/attribution context | `SATISFIED AFTER REMEDIATION` | Live gate persisted CC-BY-4.0 + required nflverse attribution. |
| M3-21 | Generic acquisition service enforces capability | `SATISFIED AFTER REMEDIATION` | Undeclared datasets fail before provider loader invocation. |
| M3-22 | Stored artifact/request/provider invariants checked | `SATISFIED AFTER REMEDIATION` | Provider, dataset, checksum, size, type, and temporal ordering are validated. |
| M3-23 | Normalized acquisition has record-level raw lineage | `SATISFIED AFTER REMEDIATION` | `NormalizedRecordProvenance` adds source record, evidence, and evidence-observation identity. |
| M3-24 | Every normalized record requires lineage | `SATISFIED AFTER REMEDIATION` | Envelope rejects cardinality mismatch and unrelated evidence IDs. |
| M3-25 | Provider disagreements can survive acquisition | `SATISFIED` | Provider/evidence observations remain independent; canonical reconciliation is deferred. |
| M3-26 | M2 history remains forward-only | `SATISFIED AFTER REMEDIATION` | New schema is migration 5; migrations 1-4 are unchanged. |
| M3-27 | v4 raw evidence survives v5 | `PASS` | Full local suite passed, including migration-conformance coverage. |
| M3-28 | New M3 ledgers are append-only | `PASS` | Full local suite passed, including update/delete rejection expectations. |
| M3-29 | Tiny real dataset acquired through abstraction | `PASS` | Real nflverse schedule acquisition completed under schema v5. |
| M3-30 | nflreadpy schema/small historical validation | `PASS` | nflreadpy 0.1.5 returned 285 schedule rows for 2025 with required schema. |
| M3-31 | Full repository quality gate | `PASS` | 130 pytest PASS; Ruff PASS; strict mypy PASS across 71 source files; clean tree. |

---

## 5. Findings and remediations

### F-01 — capability metadata was materially incomplete

**Severity:** HIGH — REMEDIATED

The provisional capability object could not encode entity/field coverage, expected latency, historical availability, reliability tier, explicit license identity/URL, attribution, or dataset-level schema metadata. Those are now first-class validated fields.

### F-02 — the nflverse descriptor overclaimed executable capability

**Severity:** HIGH — REMEDIATED

The descriptor declared several datasets while the exact-byte HTTP mapping only implemented schedule and PBP. M3 now declares only the exact-raw capabilities that can actually execute. Additional datasets require their own raw mapping, coverage, latency, PIT, schema, and licensing review before being declared.

### F-03 — unchanged raw bytes erased later observations

**Severity:** HIGH — REMEDIATED

M2 correctly deduplicated immutable content by provider/dataset/SHA, but provisional M3 persistence also treated that content identity as acquisition identity. A later observation of unchanged bytes disappeared. Migration v5 preserves M2 content deduplication and adds separate append-only acquisition-observation history.

### F-04 — licensing was too provider-wide

**Severity:** HIGH — REMEDIATED

Current nflverse documentation shows that not every dataset necessarily shares the same terms or attribution. M3 therefore stores licensing and attribution per capability and snapshots them onto raw acquisition observations.

### F-05 — normalized provenance was batch-level only

**Severity:** HIGH — REMEDIATED

The prior normalized envelope listed contributing evidence IDs for a batch but could not say which source record/raw observation supported each normalized record. Record-level provenance is now mandatory.

### F-06 — HTTP publication time was ignored

**Severity:** MEDIUM — REMEDIATED

When the upstream HTTP response exposes `Last-Modified`, M3 records it as `published_at`. Missing or invalid headers remain unknown rather than guessed. `available_at` remains anchored to Daily NFL observation until M5 certifies stronger historical availability semantics.

### F-07 — orchestration trusted only adapter-level capability checks

**Severity:** MEDIUM — REMEDIATED

The generic acquisition service now fails before calling a provider adapter if the requested dataset was not declared.

---

## 6. Upstream / licensing boundary

The currently certified exact-raw nflverse capabilities are schedule and play-by-play. The nflverse-data release repository identifies its broad release-data license as CC BY 4.0, so those two capability records carry CC-BY-4.0 plus attribution metadata.

This does not authorize Daily NFL to assign that same metadata to every future nflverse dataset. Current nflreadpy documentation describes separate terms for some FTN-backed data. Future capabilities are reviewed dataset-by-dataset.

---

## 7. Explicit deferrals — not M3 defects

- additional exact-raw nflverse datasets beyond schedule/PBP;
- entity reconciliation and provider conflict resolution — M4;
- defensible historical `available_at` derivation and as-of selection — M5;
- full play/drive normalization semantics — M6;
- feature/state/model layers;
- Daily-Data-Core shared weather/odds/travel acquisition;
- commercial/live provider integrations.

---

## 8. Certification evidence

Validated executable code head:

```text
3276d5f77027bf2894294a1d66c99c0958ca3286
```

Full repository gate:

```text
pytest: 130 passed in 2.48s
Ruff: All checks passed!
mypy: Success: no issues found in 71 source files
git status --short: clean
```

Real nflverse raw gate:

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
sha256 == stored_sha256: PASS
```

nflreadpy Lane-B gate:

```text
nflreadpy_version: 0.1.5
season: 2025
row_count: 285
column_count: 46
required columns/schema: PASS
```

Detailed evidence is preserved in `docs/implementation/M3_LOCAL_VALIDATION_20260821.md`.

---

## 9. Final decision

```text
M3 F-2 STATIC ARCHITECTURE AUDIT: PASS
M3 CAPABILITY / LICENSING REMEDIATION: PASS
M3 RAW OBSERVATION HISTORY REMEDIATION: PASS
M3 NORMALIZED PROVENANCE CONTRACT: PASS
M3 MIGRATION v5: PASS
M3 LOCAL QUALITY GATE: PASS
M3 REAL NFLVERSE RAW GATE: PASS
M3 NFLREADPY LANE-B GATE: PASS
M3 — ARCHITECTURE-CERTIFIED
```

M4 — Identity & Reconciliation Engine is the next architecture-certification target.
