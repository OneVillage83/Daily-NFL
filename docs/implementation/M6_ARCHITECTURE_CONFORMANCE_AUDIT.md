# M6 Architecture-Conformance Audit

**Project:** The Daily Line — Daily NFL  
**Milestone:** M6 — Canonical Play / Drive Normalization  
**Architecture dependency:** F-5 — Canonical Play / Event / Possession / Drive Architecture  
**Certified dependency base:** M0-M5  
**Validated executable SHA:** `5f1e2efe115c8f889d99eb7f6169050ee90c8ca7`  
**Certification status:** **ARCHITECTURE-CERTIFIED**

---

## 1. Scope rule

The implementation roadmap assigns M6 to **F-5**. F-6 through F-9 define team,
player, unit, and coaching state and belong to M7 State Engine V1. M6 therefore
certifies the provider-row-to-canonical football transition ledger without
prematurely claiming M7 state-model conformance.

Existing M6/M6B implementation and 2025 validation were treated as evidence to
audit, not authority to weaken F-5. Earlier M6B output remains historical
evidence, but its old next-state check is explicitly superseded because it did
not prove raw-row adjacency.

---

## 2. Locked F-5 / M6 contract

M6 provides the canonical hierarchy and transition model:

```text
GAME
  -> PERIOD
    -> POSSESSION SEGMENT
      -> DRIVE
        -> PLAY
          -> PLAY_STATE_BEFORE
          -> PLAY_EXECUTION
          -> PARTICIPATION
          -> ORDERED EVENTS
          -> PENALTIES
          -> OFFICIAL / PHYSICAL OUTCOME
          -> PLAY_STATE_AFTER
```

The certified boundary requires:

- protected causal `PLAY_STATE_BEFORE` with no outcome/analytics leakage;
- `PLAY_EXECUTION` as the object name; `PLAY_ACTION` only as a design modifier;
- the locked primary play taxonomy and modifier vocabulary;
- ordered canonical play events;
- canonical player/team participation where provider evidence exists;
- first-class penalties with disposition/enforcement semantics;
- physical outcome separate from official outcome when evidence supports both;
- deterministic `PLAY_STATE_AFTER` based only on defensible adjacent state;
- possession-segment and drive identity/transition support;
- append-only provider revisions rather than silent canonical overwrite;
- M3/M5 raw-content and acquisition-observation provenance on normalized writes;
- deterministic normalized-observation identity from exact evidence/acquisition/provider/revision facts;
- exact idempotent child membership, rejecting both missing and extra participation/penalty children;
- provider-shaped row fields/IDs excluded from the downstream canonical payload;
- fail-closed behavior when state, identity, sequence, provenance, or replay membership cannot be defended.

Derived analytics such as EPA/WPA/success remain outside canonical football truth.

---

## 3. Conformance matrix after remediation

| ID | Requirement | Status | Evidence / remediation |
|---|---|---|---|
| M6-01 | Canonical play identity independent of provider play ID | `SATISFIED` | Canonical IDs derive from canonical game + sequence; provider play IDs remain observation provenance. |
| M6-02 | Period → possession segment → drive → play hierarchy | `SATISFIED` | Certified M1/M2 contracts plus M6 canonical-row persistence retain all links. |
| M6-03 | Protected causal pre-play state | `SATISFIED` | `PrePlayState` structurally excludes realized yards, completion, TD, turnover, EPA/WPA, and success metrics. |
| M6-04 | Pre-play previous-play linkage | `SATISFIED AFTER REMEDIATION` | Canonical sequence now populates `previous_play_id` when a prior canonical play exists. |
| M6-05 | Optional pre-play charting remains unknown when unavailable | `SATISFIED AFTER REMEDIATION` | Unsupported charting flags are `None`, not fabricated `False`; explicit provider false remains false. |
| M6-06 | `PLAY_EXECUTION` naming | `SATISFIED` | `PlayExecution` remains the canonical object; no container is named PlayAction. |
| M6-07 | `PLAY_ACTION` only a modifier | `SATISFIED` | Play action contributes `PlayDesignModifier.PLAY_ACTION` and stable semantic label only. |
| M6-08 | Primary play taxonomy | `SATISFIED` | PASS/RUSH/SCRAMBLE/SACK/KNEEL/SPIKE/PUNT/FG/KICKOFF/XP/2PT/PENALTY_ONLY/TIMEOUT/ADMINISTRATIVE/OTHER retained. |
| M6-09 | Modifier vocabulary separate from play family | `SATISFIED` | RPO/screen/shotgun/under-center/motion/shift/no-huddle/designed-QB-run remain modifiers. |
| M6-10 | No description-text inference for missing charting | `SATISFIED` | nflverse extractor uses structured columns only. |
| M6-11 | Ordered event stream | `SATISFIED AFTER REMEDIATION` | Events remain sequence-addressed and attach explicit passer/target/interceptor/kicker identity where supported. |
| M6-12 | Explicit target event when structured target exists | `SATISFIED AFTER REMEDIATION` | Provider receiver ID creates canonical target participation and `TARGET` event. |
| M6-13 | Canonical participation supported | `SATISFIED AFTER REMEDIATION` | Structured passer/rusher/target/kicker/punter/returner/interceptor IDs map through canonical PlayerIds. |
| M6-14 | Provider player ID never becomes canonical identity | `SATISFIED AFTER REMEDIATION` | Normalizer requires an externally supplied M4-reconciled PlayerId mapping; unresolved IDs fail closed. |
| M6-15 | Penalty player identity reconciled or blocked | `SATISFIED AFTER REMEDIATION` | Structured penalty player IDs use the same canonical mapping; unresolved identity is rejected. |
| M6-16 | Penalties remain first-class objects/events | `SATISFIED` | Penalty identities, disposition, yards, AFD/LOD, nullification, enforcement spot, and event are retained. |
| M6-17 | No-play official outcome does not inherit physical yards | `SATISFIED` | Official no-play yards remain null/zero-safe while optional physical outcome is separate. |
| M6-18 | Physical outcome separate from official outcome | `SATISFIED` | `ObservedPhysicalOutcome` is independently serialized under the official result. |
| M6-19 | State-after uses provider state rather than arithmetic fabrication | `SATISFIED` | Next pre-state remains the source of canonical next down/distance/yardline/score when supplied. |
| M6-20 | State-after cannot cross an omitted raw row | `SATISFIED AFTER CRITICAL REMEDIATION` | Both records require raw source indexes and must be exactly adjacent. |
| M6-21 | State-after same-game boundary | `SATISFIED AFTER REMEDIATION` | Cross-game `next_record` is rejected. |
| M6-22 | Possession transition explicit | `SATISFIED` | Next possession carries canonical offense/defense identity and possession sequence. |
| M6-23 | Drive continuation explicit | `SATISFIED` | Continuation requires same canonical drive and unchanged possession. |
| M6-24 | Deterministic canonical drive object | `SATISFIED AFTER REMEDIATION` | `normalize_drive` validates one game/drive/segment/possession and builds defensible start/end/count/turnover/points fields. |
| M6-25 | Provider revisions append rather than overwrite | `SATISFIED` | Multiple play observations may reference one canonical play without replacing earlier normalized payloads. |
| M6-26 | Exact raw content retained | `SATISFIED` | New normalized writes require `evidence_id`. |
| M6-27 | Exact acquisition observation retained | `SATISFIED AFTER REMEDIATION` | New normalized writes require and persist `evidence_observation_id`. |
| M6-28 | Observation identity distinguishes repeated acquisitions | `SATISFIED AFTER REMEDIATION` | Normalized observation ID includes content, acquisition-observation, provider row, and revision identity; the writer enforces that derived ID. |
| M6-29 | Raw observation/provider mismatch fails closed | `SATISFIED AFTER REMEDIATION` | Certified writer verifies the M3 raw-observation ledger before canonical writes. |
| M6-30 | Normalization persistence atomic | `SATISFIED AFTER REMEDIATION` | Canonical identities + play/participation/penalty observations are protected by one SQLite savepoint. |
| M6-31 | Idempotent replay verifies exact child membership | `SATISFIED AFTER FINAL REMEDIATION` | Existing replay compares the complete expected participation/penalty child sets and rejects missing, mismatched, or extra children. |
| M6-32 | Provider-shaped row fields excluded downstream | `SATISFIED AFTER REMEDIATION` | Canonical JSON excludes provider IDs, provider drive/play IDs, raw description, and extraction flags. |
| M6-33 | Complete canonical pre-state/result serialization | `SATISFIED AFTER REMEDIATION` | Serializer retains optional pre-state context, previous play, events, participation, penalties, full physical outcome, and state-after. |
| M6-34 | Provisional direct persistence path cannot bypass certified writer | `SATISFIED AFTER REMEDIATION` | Historical module delegates writes to certified persistence. |
| M6-35 | No unnecessary schema migration | `SATISFIED` | M2 canonical ledgers + M5 v7 acquisition columns already satisfy M6 storage needs; migrations 1-7 remain unchanged. |
| M6-36 | Deterministic no-network M6 validator | `VALIDATED` | Final exact-head run exercises execution/events/participation/penalty/state-after/drive/provenance/atomic failure and passed. |
| M6-37 | Corrected real nflverse season validator | `VALIDATED` | Final exact-head 2025 run validated 41,975 truly adjacent transitions, skipped 2,936 nonadjacent pairs, and recorded 0 state-after errors. |
| M6-38 | Full repository quality gate | `VALIDATED` | 171 pytest PASS; Ruff PASS; strict mypy PASS on 89 source files; clean exact-head tree. |
| M6-39 | F-6 through F-9 team/player/unit/coaching state | `DEFERRED BY ROADMAP` | These are M7 architecture dependencies, not M6 exit conditions. |

---

## 4. Material findings and remediation

### F-01 — next-state validation could skip intervening raw rows

**Severity:** CRITICAL — REMEDIATED AND VALIDATED

The historical M6B validator dropped extraction failures and then paired adjacent
*surviving* rows. An omitted no-play/administrative row could therefore sit
between two rows treated as consecutive, allowing its clock/penalty/state effect
to be folded into the earlier play's `PLAY_STATE_AFTER`.

M6 now carries `source_row_index`. A supplied `next_record` must be from the same
provider game and have index exactly `current + 1`. Missing adjacency metadata or
an intervening raw row fails closed. The corrected 2025 real-season validator
confirmed:

```text
next_state_adjacent_validated: 41,975
next_state_nonadjacent_skipped: 2,936
next_state_error_count: 0
```

The old historical statement `173 validated / 0 failures` is retained as history
but is not accepted as final M6 certification evidence.

### F-02 — unavailable charting was represented as false

**Severity:** HIGH — REMEDIATED

Base nflverse PBP does not expose play-action/RPO/screen/motion/shift/designed-QB-
run fields consistently. A false default conflates "provider observed absent" with
"provider did not expose this concept." Those fields are now tri-state and remain
`None` when unavailable. No free-text inference was added.

### F-03 — normalized writes stopped at raw-content identity

**Severity:** HIGH — REMEDIATED AND VALIDATED

The provisional writer could retain `evidence_id` but not the specific M3
acquisition observation. Certified M6 persistence now requires both, validates the
exact observation/provider pair, persists it to play/participation/penalty
observations, includes acquisition identity in normalized observation identity,
and enforces the deterministic observation ID at write time. The deterministic
validator proved bad provenance fails before a canonical play can survive and rolls
back atomically.

### F-04 — play participation was always empty

**Severity:** HIGH — REMEDIATED AND VALIDATED

Structured player IDs are now extracted for explicitly supported roles. Provider
IDs must be mapped to canonical PlayerIds before normalization; unresolved actors
fail closed. The normalizer never manufactures production canonical player IDs from
provider strings. The deterministic validator produced two canonical participants,
and the real-season validator exercised structured participant extraction.

### F-05 — drive normalization was only an identity side effect

**Severity:** MEDIUM — REMEDIATED AND VALIDATED

`normalize_drive` now validates one canonical drive/possession segment and derives
only defensible start/end/count/points/turnover fields. Deterministic validation
confirmed a two-play drive with one first down.

### F-06 — canonical JSON repeated provider-row identity

**Severity:** HIGH — REMEDIATED AND VALIDATED

The downstream canonical serializer now excludes provider-shaped identity,
provider play/drive IDs, raw description, and extraction flags. Provenance remains
on the observation envelope. The deterministic validator explicitly returned
`payload_is_provider_neutral: true`.

### F-07 — direct import could bypass certified persistence

**Severity:** HIGH — REMEDIATED

The historical `normalization.persistence` module is now a compatibility boundary
that requires acquisition-observation provenance and delegates actual writes to
certified persistence; shared canonical-row helpers live in `persistence_core`.

### F-08 — idempotent replay did not prove exact child membership

**Severity:** HIGH — REMEDIATED AND VALIDATED

Final PR review found that replay proved each expected participation/penalty child
existed, but did not prove that no extra child was attached to the same normalized
revision. Certified persistence now compares complete child sets scoped to the
canonical play, exact acquisition observation, provider, and revision. Dedicated
regressions prove an extra child fails closed and that arbitrary observation IDs
cannot bypass deterministic normalized-observation identity.

---

## 5. Fail-closed behavior after remediation

M6 intentionally refuses to guess when:

- offense or defense identity is missing or inconsistent with the game;
- an explicit participant/penalty player lacks canonical reconciliation;
- a state-after candidate is not the immediately adjacent raw provider row;
- raw-row adjacency metadata is absent when state-after is requested;
- the next row belongs to another game;
- possession/drive sequences are invalid;
- drive bundles span different games, drives, possession segments, or teams;
- canonical identity collides with different stored facts;
- normalized acquisition observation does not match raw evidence/provider identity;
- supplied normalized observation identity does not match deterministic derivation;
- an existing normalized observation has missing, mismatched, or extra child membership;
- a database child/FK write fails inside the atomic savepoint.

Unknown optional charting remains unknown instead of being inferred.

---

## 6. Explicit deferrals — not M6 defects

- TeamState snapshots — F-6 / M7;
- PlayerState trajectories — F-7 / M7;
- UnitState snapshots — F-8 / M7;
- CoachingState snapshots — F-9 / M7;
- EPA/WPA/success/pressure-derived analytics — downstream feature/model milestones;
- unsupported charting concepts absent from base nflverse PBP — future provider enrichment;
- recovery of provider rows whose pre-play state cannot be defensibly reconstructed — future sequence-aware recovery, never fabricated here.

---

## 7. Executable certification evidence

Exact clean executable SHA:

```text
5f1e2efe115c8f889d99eb7f6169050ee90c8ca7
```

Quality and persistence gates:

```text
Python 3.12.10 — E:\Daily-NFL\.venv\Scripts\python.exe
targeted persistence regressions: 5 passed in 0.50s
Ruff: PASS
mypy: PASS — 89 source files
pytest: 171 passed in 3.93s
working tree: clean
fresh SQLite: 0 -> 7 PASS
SQLite check: 7 -> 7 PASS
foreign keys: true
integrity: true
```

Deterministic F-5 gate:

```text
primary_play_type: PASS
semantic_label: PLAY_ACTION_PASS
event_types: SNAP, THROW, TARGET, CATCH, PENALTY
participation_count: 2
penalty_count: 1
state_after_present: true
state_after_drive_continues: true
drive_play_count: 2
drive_first_downs: 1
raw evidence ID retained: PASS
acquisition-observation ID retained: PASS
payload SHA match: PASS
payload_is_provider_neutral: true
nonadjacent_state_after_fail_closed: true
bad_provenance_fail_closed: true
bad_provenance_atomic: true
```

Persistence regressions additionally prove:

```text
deterministic normalized observation ID enforced: PASS
extra child membership on idempotent replay rejected: PASS
```

Corrected real 2025 nflverse gate (`nflreadpy==0.1.5`):

```text
row_count: 48,771
extracted_and_normalized_count: 45,196
extraction_error_count: 3,575
normalization_error_count: 0
next_state_adjacent_validated: 41,975
next_state_nonadjacent_skipped: 2,936
next_state_error_count: 0
```

All strict extraction exclusions were confined to `<NULL>` / `no_play` rows whose
causal pre-play score, quarter clock, or yardline could not be defensibly
reconstructed. No successfully extracted state-bearing play failed canonical
normalization.

Full evidence is recorded in:

- `docs/implementation/M6_LOCAL_VALIDATION_20260823.md`

---

## 8. Certification decision

```text
M6 F-5 STATIC ARCHITECTURE AUDIT: COMPLETE
M6 RAW-ROW ADJACENCY REMEDIATION: VALIDATED
M6 UNKNOWN CHARTING SEMANTICS: VALIDATED
M6 CANONICAL PARTICIPATION: VALIDATED
M6 PENALTY PLAYER RECONCILIATION: VALIDATED
M6 DRIVE NORMALIZATION: VALIDATED
M6 M3/M5 ACQUISITION PROVENANCE: VALIDATED
M6 DETERMINISTIC OBSERVATION IDENTITY: VALIDATED
M6 EXACT IDEMPOTENT CHILD MEMBERSHIP: VALIDATED
M6 ATOMIC NORMALIZATION PERSISTENCE: VALIDATED
M6 PROVIDER-NEUTRAL DOWNSTREAM PAYLOAD: VALIDATED
M6 DIRECT PERSISTENCE BYPASS: CLOSED
M6 NO-NETWORK VALIDATOR: PASS
M6 CORRECTED REAL-PBP VALIDATOR: PASS
M6 LOCAL QUALITY GATE: PASS
M6 SQLITE GATE: PASS
M6 REAL 2025 NFLVERSE GATE: PASS
M6 ARCHITECTURE CERTIFICATION: ARCHITECTURE-CERTIFIED
```

**Final decision: M6 / F-5 is `ARCHITECTURE-CERTIFIED` on executable SHA `5f1e2efe115c8f889d99eb7f6169050ee90c8ca7`.**

Documentation-only certification commits after that SHA do not alter the executable behavior that was validated. If later evidence reveals an M6/F-5 defect, M6 must be explicitly reopened and recertified.
