# M5 Architecture-Conformance Audit

**Project:** The Daily Line — Daily NFL  
**Milestone:** M5 — Historical PIT Engine  
**Architecture dependency:** F-4 — Historical Point-in-Time Architecture  
**Certified dependency base:** M0-M4  
**Certification status:** **NOT YET CERTIFIED — AUDIT IN PROGRESS**

## Audit rule

The existing PIT package is provisional evidence. F-4 is authoritative. If a historical reconstruction can admit information that was not defensibly knowable at the requested prediction timestamp, M5 fails regardless of apparent model quality.

## Locked M5 requirements

M5 must provide:

- defensible `available_at` derivation with method and confidence;
- separate effective/publication/observation/ingestion clocks;
- knowledge-time and real-world-validity/as-of query support;
- a hard pregame cutoff before official kickoff;
- standard horizons `T-168h`, `T-72h`, `T-24h`, `T-6h`, `T-90m`, and `T-15m`;
- no blanket exclusion of game-day information legitimately available before the cutoff;
- append-only revision history;
- fail-closed leakage validation;
- immutable feature-input snapshots with sufficient provenance for exact reconstruction;
- explicit separation of retrospective event truth from historical knowledge state.

## Initial conformance findings

| ID | Requirement | Initial status | Finding |
|---|---|---|---|
| M5-01 | Standard horizons and pre-kickoff cutoff | SATISFIED | `PredictionCutoff` enforces configured horizons and `prediction_time < kickoff`. |
| M5-02 | Game-day information allowed when available before cutoff | SATISFIED | Eligibility is timestamp-based, not weekday-based. |
| M5-03 | Four knowledge clocks represented | SATISFIED | `PITInputRef` and `KnowledgeTimestamp` retain effective/published/observed/ingested clocks. |
| M5-04 | Defensible `available_at` method/confidence | PARTIAL | Strict unknown handling exists, but inferred-report evidence is marked LOW although F-4 defines it as medium-confidence evidence, and earliest defensible public evidence is not selected across all high-confidence candidates. |
| M5-05 | Bitemporal/as-of helpers | BLOCKED | Current selector enforces knowledge time only; `effective_at` is stored but no helper performs real-world-validity + knowledge-time selection. |
| M5-06 | Later revisions hidden until known | BLOCKED | Different payloads with the same `available_at` can be ordered by later `observed_at`/`ingested_at`, allowing a retrospectively observed correction to win without a newer knowledge timestamp. |
| M5-07 | Equal-knowledge conflicting revisions fail closed | PARTIAL | Conflict exists only when the entire rank including observed/ingested clocks ties. F-4 requires conflict at the knowledge boundary when content differs and no later defensible availability exists. |
| M5-08 | Acquisition observation provenance retained | BLOCKED | Snapshot inputs keep `evidence_id` but not the M3 `evidence_observation_id`; identical raw bytes observed at different times are therefore indistinguishable in the snapshot manifest. |
| M5-09 | Provider/source versions retained in immutable snapshot | BLOCKED | Snapshot input metadata omits provider/revision/schema/parser identifiers required for exact source reconstruction where available. |
| M5-10 | Immutable feature-input snapshot contains feature contract/version/values/coverage/missingness/PIT result | BLOCKED | Current snapshot is an input manifest only and does not yet satisfy the M5 roadmap/F-4.18 feature-snapshot contract. Prediction ID remains a later M10 concern. |
| M5-11 | Strict leakage validators reject source after cutoff | SATISFIED | Generic `available_at > prediction_time` failure exists. |
| M5-12 | Current-game result/stat/play leakage rejected | SATISFIED WITH GAP | Known current-game kinds are rejected when subject identity is present; missing required subject context currently fails open. |
| M5-13 | Actual weather cannot masquerade as current-game forecast | SATISFIED WITH GAP | Current-game actual weather is rejected when subject identity is present; missing subject context currently fails open. |
| M5-14 | Later market quote / closing line rejected | SATISFIED WITH GAP | `market_quote_at > cutoff` is rejected, but missing quote timestamp currently passes. |
| M5-15 | Future game/opponent information rejected | SATISFIED WITH GAP | Future source kickoff is rejected when supplied, but missing source-game kickoff currently passes. |
| M5-16 | End-of-season aggregate rejected midseason | SATISFIED WITH GAP | Completion after cutoff is rejected when supplied, but missing completion time currently passes. |
| M5-17 | Provider corrections need defensible historical availability | PARTIAL | UNKNOWN correction availability is rejected, but correction/revision provenance is not fully preserved in generic PIT input metadata. |
| M5-18 | Schedule as-of reconstruction preserves all certified schedule fields | BLOCKED | Current helper omits M2 `actual_kickoff`, `neutral_site`, and `schedule_version` from returned state and normalized-payload hashing. |
| M5-19 | Provider disagreement is not silently overwritten | BLOCKED | Schedule observations from all providers share one logical key; the latest eligible provider can silently replace another provider rather than producing explicit conflict/reconciliation. |
| M5-20 | Official kickoff is a hard retrospective boundary | PARTIAL | `PredictionCutoff` checks the caller-provided kickoff, but persisted snapshots do not yet cross-check available retrospective `actual_kickoff` truth to prevent a stale/later scheduled kickoff from allowing an after-start pregame snapshot. |
| M5-21 | Append-only revisions/snapshots | SATISFIED | Observation history and sealed PIT snapshot tables are append-only. |
| M5-22 | Feature-availability eras remain explicit | DEFERRED BY ARCHITECTURE | Exact feature-era boundaries belong to provider capability metadata and M9 feature contracts; M5 must not fabricate missing historical coverage. |
| M5-23 | Walk-forward final evaluation | DEFERRED | Implemented/certified under later evaluation milestone M14; not an M5 exit condition. |

## Required remediation direction

M5 certification will require forward-only migration(s); prior migrations must not be rewritten. The remediation should:

1. strengthen availability derivation without inventing historical times;
2. add a true bitemporal selection helper;
3. make same-knowledge conflicting revisions fail closed regardless of later ingestion/observation ordering;
4. preserve acquisition-observation and provider/source version provenance in PIT inputs/snapshots;
5. require leakage-critical temporal/context metadata by input kind under strict policy;
6. upgrade immutable PIT snapshots to carry an explicit feature contract/version, canonical feature-value payload, coverage/missingness report, and PIT-validation result without defining M9 feature semantics prematurely;
7. include all certified schedule-observation fields in schedule as-of state;
8. fail closed on conflicting provider schedule states unless an explicit reconciliation rule exists;
9. enforce retrospective official-start boundary during persisted historical snapshot creation where `actual_kickoff` truth exists;
10. add intentional leakage/revision/provider-conflict fixtures and a small historical reconstruction validation.

## Certification gate

M5 remains **NOT CERTIFIED** until the remediated branch passes:

- full pytest;
- Ruff;
- strict mypy;
- clean tree;
- fresh schema migration/check;
- intentional leakage fixtures fail closed;
- a historical game/schedule state reconstructs correctly at multiple cutoffs;
- a later correction remains invisible to an earlier cutoff;
- a same-knowledge conflicting correction is rejected;
- immutable snapshot provenance and sealing are verified.
