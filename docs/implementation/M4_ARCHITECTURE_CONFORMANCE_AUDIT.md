# M4 Architecture-Conformance Audit

**Project:** The Daily Line — Daily NFL  
**Milestone:** M4 — Identity & Reconciliation Engine  
**Audit date:** 2026-08-21  
**Audit branch:** `audit/m4-architecture-conformance`  
**Certified base:** M3 merge `a4804645dd43a708197af625c8fb2a0fca220c09`  
**Architecture dependency:** F-3 — Canonical Identity & Reconciliation  
**Validated executable code head:** `c15ef10df3e0f2eae393e0dc0c3c586b0d9f0505`  
**Certification status:** **ARCHITECTURE-CERTIFIED**

---

## 1. Audit purpose

M4 certifies how external NFL/provider identities are reconciled to stable Daily NFL canonical identity. F-3 requires provider IDs to remain replaceable crosswalk attributes, ambiguous matches to remain unresolved, reconciliation decisions to be auditable, historical mapping changes to remain traceable, and provider identity changes not to create new canonical people/games/drives/plays merely because an upstream identifier changed.

The existing reconciliation package was treated as provisional evidence. F-3 is authoritative.

---

## 2. Governing F-3 contract

The locked identity contract requires:

- opaque canonical identity independent of provider IDs;
- generic provider/external-ID crosswalks with validity intervals, match method, confidence, and verification state;
- no silent fuzzy matching;
- explicit unresolved / ambiguous / conflict outcomes;
- unresolved records that retain candidate matches, matching evidence, confidence, provider, and source row/raw evidence;
- provider game IDs treated as crosswalks rather than canonical Game IDs;
- provider drive/play IDs and sequence/context treated as reconciliation evidence rather than canonical identity;
- corrections and changes represented as versioned/superseding mappings rather than destructive mutation;
- football-specific reconciliation rules in Daily NFL for GSIS player identity, franchise/team history, game identity, and drive/play identity.

Provider-local identifiers must also remain scoped to the namespace where the upstream provider makes them unique. In particular, a drive/play ID that is only unique inside a game cannot be treated as globally unique merely because its text matches another game's provider ID.

M4 consumes the certified M1 canonical ID vocabulary, certified M2 persistence/append-only rules, and certified M3 raw-evidence provenance.

---

## 3. Roadmap M4 contract

Deliverables:

- canonical ID generation;
- provider crosswalk persistence;
- GSIS external-ID mapping support;
- team/franchise reconciliation rules;
- game reconciliation rules;
- player reconciliation rules;
- unresolved-identity representation;
- match confidence and method;
- no silent fuzzy matching.

Exit conditions:

- ambiguous matches remain unresolved;
- provider IDs can change without changing canonical identity;
- reconciliation decisions are auditable.

Local validation requires a small provider sample. Historical as-of availability selection remains M5 and is not pulled into M4.

---

## 4. Conformance matrix

| ID | Requirement | Status | Evidence / remediation |
|---|---|---|---|
| M4-01 | Canonical root IDs do not embed provider IDs | `SATISFIED` | Existing opaque UUID-root / canonical-parent derivation retained. |
| M4-02 | F-3 NFL identity vocabulary is represented | `SATISFIED AFTER REMEDIATION` | Reconciliation vocabulary expanded to franchise, team-season, person/player, roster-stint, coach-role, event/game, possession/segment, drive/play/event, injury/depth observations, participation, penalty. |
| M4-03 | Missing opaque identity generators do not rely on provider IDs | `SATISFIED AFTER REMEDIATION` | Added roster-stint, coach-role, injury-observation, and depth-chart-snapshot root generators. |
| M4-04 | External IDs remain crosswalk attributes | `SATISFIED` | Crosswalk stores provider/entity/external ID separately from canonical target. |
| M4-05 | Crosswalk validity intervals are enforceable | `SATISFIED AFTER REMEDIATION` | Team-season mappings now receive non-overlapping NFL league-year validity windows. |
| M4-06 | Same provider team code can represent different team-seasons | `SATISFIED AFTER REMEDIATION` | 2025/2026 mappings for the same external code resolve to distinct canonical TeamSeason IDs. |
| M4-07 | Legacy timeless team-season mapping cannot leak into another season | `SATISFIED AFTER REMEDIATION` | Wrong-season reuse returns explicit `CONFLICT` rather than silently selecting the old TeamSeason. |
| M4-08 | GSIS can bootstrap opaque canonical player identity | `SATISFIED` | Trusted GSIS authority creates Person/Player once and persists a crosswalk. |
| M4-09 | Provider player ID is not canonical player ID | `SATISFIED` | Player identity derives from opaque Person identity, not GSIS/provider text. |
| M4-10 | Franchise identity persists across provider ID changes | `SATISFIED` | Multiple provider external IDs can map to one canonical franchise. |
| M4-11 | Game provider ID reconciles by canonical context | `SATISFIED` | Composite team/season/phase/week or kickoff-tolerance matching retained. |
| M4-12 | Existing game crosswalk is checked against supplied canonical context | `SATISFIED AFTER REMEDIATION` | Context mismatch now returns `CONFLICT`; stale crosswalk is not trusted blindly. |
| M4-13 | Drive provider ID reconciles to canonical drive | `SATISFIED AFTER REMEDIATION` | Added canonical game + drive sequence + optional possession-segment matching. |
| M4-14 | Play provider ID reconciles to canonical play | `SATISFIED AFTER REMEDIATION` | Added canonical game + play sequence + optional drive matching. |
| M4-15 | Provider drive/play IDs can change without canonical identity changing | `SATISFIED AFTER REMEDIATION` | Separate old/new external IDs can map to the same canonical drive/play. |
| M4-16 | Provider-local drive/play IDs cannot collide across games | `SATISFIED AFTER REMEDIATION` | Added explicit provider identity scope; drive/play IDs are scoped by canonical game while raw external ID text is preserved. |
| M4-17 | Fuzzy matching never silently resolves | `SATISFIED` | Review-only fuzzy candidates remain non-selecting; DB fuzzy crosswalk trigger retained. |
| M4-18 | Ambiguous candidate sets remain unresolved | `SATISFIED` | Multiple game/drive/play candidates produce `AMBIGUOUS` with no selected identity. |
| M4-19 | Unresolved decisions retain candidates and confidence | `SATISFIED` | Existing decision/candidate contract retained. |
| M4-20 | Unresolved decisions retain source row/raw evidence | `SATISFIED AFTER REMEDIATION` | Added typed `ReconciliationEvidence` and append-only relational evidence ledger linked to M3 raw content/acquisition observations. |
| M4-21 | Matching facts used by reconciliation are auditable | `SATISFIED AFTER REMEDIATION` | Evidence rows persist structured `facts_json` rather than prose-only rationale. |
| M4-22 | New crosswalks cite a reconciliation decision | `SATISFIED AFTER REMEDIATION` | Migration v6 requires non-null decision ID and an existing decision row for new crosswalk inserts. |
| M4-23 | Resolved decision + crosswalk write is atomic | `SATISFIED AFTER REMEDIATION` | Repository savepoint records decision/evidence and binding as one unit; failed binding removes provisional decision rows. |
| M4-24 | Crosswalk history is append-only | `SATISFIED` | Existing update/delete triggers retained. |
| M4-25 | Reconciliation decision history is append-only | `SATISFIED` | Existing decision update/delete triggers retained. |
| M4-26 | Reconciliation evidence history is append-only | `SATISFIED AFTER REMEDIATION` | Migration v6 adds update/delete rejection triggers. |
| M4-27 | Verification/confidence/method change cannot be silently collapsed | `SATISFIED AFTER REMEDIATION` | Same target/interval with changed resolution metadata requires explicit supersession. |
| M4-28 | Supersession preserves earlier historical mapping | `SATISFIED` | Existing supersedes relationship retained and index widened for explicit metadata revisions. |
| M4-29 | Forward migration preserves M3/M4 provisional history | `VALIDATED` | v5→v6 migration coverage passes inside the 141-test exact-head suite; fresh 0→6 and 6→6 CLI gates also pass. |
| M4-30 | M1/M2/M3 certified contracts remain intact | `VALIDATED` | Final exact-head quality gate passes: 141 pytest, Ruff, strict mypy; migration remains additive/forward-only with migrations 1–5 unchanged. |
| M4-31 | Real small provider sample reaches canonical reconciliation | `VALIDATED` | Real nflverse record `2025_01_DAL_PHI` reaches opaque franchise and season-scoped TeamSeason reconciliation with raw/evidence-observation lineage. |
| M4-32 | Full repository quality gate | `VALIDATED` | Python 3.12.10: 141 passed in 2.65s; Ruff PASS; strict mypy PASS on 76 source files; clean tree. |

---

## 5. Findings and remediations

### F-01 — unresolved identity lacked raw/source-row evidence

**Severity:** HIGH — REMEDIATED

The provisional decision ledger captured provider/external identity, candidates, confidence, and prose explanation, but could not point to the M3 raw content, acquisition observation, and exact source row that justified a decision. F-3 explicitly requires unresolved records to retain matching evidence and source row/raw evidence.

M4 adds `ReconciliationEvidence` and append-only `identity_reconciliation_evidence`, including source-record identity, raw evidence ID, optional M3 evidence-observation ID, evidence kind, and structured matching facts.

### F-02 — team-season crosswalks were effectively timeless

**Severity:** HIGH — REMEDIATED

A provider team code such as `SF` could be mapped to a canonical TeamSeason without `valid_from` / `valid_to`. A later request for the same provider code in a different season could therefore reuse the wrong canonical TeamSeason.

M4 now assigns a non-overlapping NFL season identity interval from March 1 of the named season through the instant before March 1 of the next year. This keeps January/February postseason games in the season that began the prior fall while preventing adjacent TeamSeason mappings from overlapping.

Legacy timeless mappings are not silently rewritten. If one points at a different season than requested, reconciliation fails closed with `EXISTING_MAPPING_CONTEXT_MISMATCH`.

### F-03 — drive/play reconciliation was absent

**Severity:** HIGH — REMEDIATED

F-3 treats provider drive/play identifiers, sequence, and context as reconciliation evidence rather than canonical identity. The provisional engine had game reconciliation but no first-class drive/play reconciliation methods.

M4 adds conservative drive and play reconciliation using canonical game + sequence + optional parent context. No provider drive/play ID participates in canonical ID construction.

### F-04 — provider-local play/drive IDs could collide across games

**Severity:** HIGH — REMEDIATED

Provider play and drive identifiers are not guaranteed to be globally unique. Treating `(provider, provider_entity_type, external_id)` as the entire identity key would allow a value such as provider play `1` in one game to collide with provider play `1` in another game.

M4 adds optional `identity_scope` to the crosswalk and decision ledgers. Drive/play reconciliation scopes the provider identity by canonical game ID while retaining the provider's raw external ID unchanged. Unit coverage verifies that the same provider play ID can independently map inside two different canonical games.

### F-05 — reconciliation evidence was not atomically coupled to binding

**Severity:** HIGH — REMEDIATED

A resolved decision and its crosswalk were previously separate calls. M4 introduces an atomic repository operation that records the decision/evidence and creates the binding inside a savepoint. If the binding conflicts, the new decision/evidence rows are rolled back rather than leaving a misleading resolved decision without a binding.

### F-06 — crosswalk metadata changes could be silently collapsed

**Severity:** HIGH — REMEDIATED

If the canonical target and interval matched an existing crosswalk, provisional persistence returned the old row even when verification state, match method, or confidence had changed. That lost the fact that reconciliation quality changed later.

M4 now treats that as a new mapping version requiring explicit supersession. Migration v6 widens the unique version key so a superseding metadata revision can coexist append-only with the prior row.

### F-07 — database did not require crosswalk decision provenance

**Severity:** MEDIUM — REMEDIATED

The provisional `decision_id` column was nullable. Migration v6 leaves legacy history untouched but requires every newly inserted crosswalk to carry a decision ID that already exists in the decision ledger.

### F-08 — reconciliation identity vocabulary lagged the certified domain vocabulary

**Severity:** MEDIUM — REMEDIATED

M1 already defined the broader F-3 NFL identity vocabulary, but the reconciliation enum only exposed a subset. M4 brings the reconciliation vocabulary in line with F-3 and adds opaque generators for missing root identity classes.

This does **not** fabricate richer roster-stint, coaching, injury, or depth-chart state/storage. Crosswalk binding validates only canonical identity ledgers that are actually materialized. Later data/state milestones remain responsible for richer records.

---

## 6. Fail-closed rules after remediation

M4 intentionally refuses to guess in the following cases:

- fuzzy candidates cannot become crosswalks;
- multiple canonical candidates remain `AMBIGUOUS`;
- an existing crosswalk whose canonical context disagrees with a game/drive/play hint returns `CONFLICT`;
- a timeless legacy TeamSeason mapping for the wrong season returns `CONFLICT`;
- overlapping active mappings to different canonical identities fail within the same provider identity scope;
- provider-local drive/play IDs in different games remain separate scopes rather than colliding;
- a resolution-metadata change without explicit supersession fails;
- a new crosswalk without a recorded decision fails at the database boundary;
- a crosswalk target whose canonical ledger does not exist fails;
- canonical identity classes whose richer ledger is not materialized are not accepted as phantom crosswalk targets.

---

## 7. Explicit deferrals — not M4 defects

- historical `available_at` derivation / as-of selection — M5;
- feature leakage controls — M5 and later feature milestones;
- complete provider roster/injury/depth acquisition mappings — future provider expansion;
- roster-stint / coaching-role / injury / depth-chart richer persistence and state population — later data/state milestones;
- full play/drive normalization semantics — M6;
- entity-specific fuzzy-search algorithms or automated fuzzy acceptance — deliberately not introduced;
- cross-sport identity infrastructure ownership — Daily-Data-Core conceptually, with Daily NFL retaining football-specific reconciliation rules.

---

## 8. Certification evidence

Final exact-head local evidence:

```text
validated executable head: c15ef10df3e0f2eae393e0dc0c3c586b0d9f0505
Python 3.12.10
pytest: 141 passed in 2.65s
Ruff: All checks passed!
mypy: Success: no issues found in 76 source files
git status --short: clean
```

SQLite evidence:

```text
fresh DB: schema 0 -> 6
foreign_keys_enabled: true
integrity_ok: true
mode: migrate

check DB: schema 6 -> 6
foreign_keys_enabled: true
integrity_ok: true
mode: check
```

Real nflverse reconciliation evidence:

```text
provider_id: nflverse
season: 2025
source_record_id: 2025_01_DAL_PHI
schema_version: 6
sha256 == stored_sha256: PASS
franchise_status: RESOLVED
team_season_status: RESOLVED
team_season_match_method: CANONICAL_COMPOSITE
reconciliation_evidence_rows: 2
team_crosswalk_valid_from: 2025-03-01T00:00:00+00:00
team_crosswalk_valid_to: 2026-02-28T23:59:59.999999+00:00
```

Detailed evidence is preserved in `docs/implementation/M4_LOCAL_VALIDATION_20260821.md`.

---

## 9. Certification decision

```text
M4 F-3 STATIC ARCHITECTURE AUDIT: COMPLETE
M4 IDENTITY VOCABULARY REMEDIATION: VALIDATED
M4 RECONCILIATION EVIDENCE REMEDIATION: VALIDATED
M4 TEAM-SEASON VALIDITY REMEDIATION: VALIDATED
M4 PROVIDER-LOCAL ID SCOPING: VALIDATED
M4 DRIVE / PLAY RECONCILIATION: VALIDATED
M4 CROSSWALK VERSIONING / ATOMICITY: VALIDATED
M4 MIGRATION v6: VALIDATED
M4 LOCAL QUALITY GATE: PASS
M4 SQLITE v6 GATE: PASS
M4 REAL NFLVERSE RECONCILIATION GATE: PASS
M4 ARCHITECTURE CERTIFICATION: PASS

M4 — ARCHITECTURE-CERTIFIED
```

Documentation commits after `c15ef10df3e0f2eae393e0dc0c3c586b0d9f0505` record evidence/status only and do not change the executable behavior that was validated.
