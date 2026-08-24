# M6 Architecture-Conformance Audit

**Project:** The Daily Line — Daily NFL  
**Milestone:** M6 — Canonical Play / Drive Normalization  
**Architecture dependency:** F-5 — Canonical Play / Event / Possession / Drive Architecture  
**Certified dependency base:** M0-M5  
**Certification status:** **NOT YET CERTIFIED — STATIC AUDIT / REMEDIATION IMPLEMENTED; EXECUTABLE GATES PENDING**

---

## 1. Scope rule

The implementation roadmap assigns M6 to **F-5**. F-6 through F-9 define team,
player, unit, and coaching state and belong to M7 State Engine V1. M6 therefore
certifies the provider-row-to-canonical football transition ledger without
prematurely claiming M7 state-model conformance.

Existing M6/M6B implementation and 2025 validation are evidence to audit, not
authority to weaken F-5. Earlier M6B output remains historical evidence but its
old next-state check is explicitly superseded where this audit found a sequence
assumption that did not prove raw-row adjacency.

---

## 2. Locked F-5 / M6 contract

M6 must provide a canonical hierarchy and transition model:

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

The certification boundary requires:

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
- provider-shaped row fields/IDs excluded from the downstream canonical payload;
- fail-closed behavior when state, identity, sequence, or provenance cannot be defended.

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
| M6-11 | Ordered event stream | `SATISFIED AFTER REMEDIATION` | Events remain sequence-addressed and now attach explicit passer/target/interceptor/kicker identity where supported. |
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
| M6-28 | Observation identity distinguishes repeated acquisitions | `SATISFIED AFTER REMEDIATION` | Normalized observation ID includes both content and acquisition-observation identity. |
| M6-29 | Raw observation/provider mismatch fails closed | `SATISFIED AFTER REMEDIATION` | Certified writer verifies the M3 raw-observation ledger before canonical writes. |
| M6-30 | Normalization persistence atomic | `SATISFIED AFTER REMEDIATION` | Canonical identities + play/participation/penalty observations are protected by one SQLite savepoint. |
| M6-31 | Idempotent replay verifies child membership | `SATISFIED AFTER REMEDIATION` | Existing observation replay verifies expected participation/penalty observation identity/provenance. |
| M6-32 | Provider-shaped row fields excluded downstream | `SATISFIED AFTER REMEDIATION` | Canonical JSON excludes provider IDs, provider drive/play IDs, raw description, and extraction flags. |
| M6-33 | Complete canonical pre-state/result serialization | `SATISFIED AFTER REMEDIATION` | Serializer retains optional pre-state context, previous play, events, participation, penalties, full physical outcome, and state-after. |
| M6-34 | Provisional direct persistence path cannot bypass certified writer | `SATISFIED AFTER REMEDIATION` | Historical module is now a compatibility boundary delegating writes to certified persistence. |
| M6-35 | No unnecessary schema migration | `SATISFIED` | M2 canonical ledgers + M5 v7 acquisition columns already satisfy M6 storage needs; migrations 1-7 remain unchanged. |
| M6-36 | Deterministic no-network M6 validator | `IMPLEMENTED; LOCAL GATE PENDING` | `scripts/validate_m6_normalization.py` exercises execution/events/participation/penalty/state-after/drive/provenance/atomic failure. |
| M6-37 | Corrected real nflverse season validator | `IMPLEMENTED; REAL GATE PENDING` | Validator records raw row index, validates only truly adjacent transitions, and reports skipped nonadjacent pairs. |
| M6-38 | Full repository quality gate | `LOCAL VALIDATION PENDING` | pytest / Ruff / strict mypy / clean tree required. |
| M6-39 | F-6 through F-9 team/player/unit/coaching state | `DEFERRED BY ROADMAP` | These are M7 architecture dependencies, not M6 exit conditions. |

---

## 4. Material findings and remediation

### F-01 — next-state validation could skip intervening raw rows

**Severity:** CRITICAL — REMEDIATED

The historical M6B validator dropped extraction failures and then paired adjacent
*surviving* rows. An omitted no-play/administrative row could therefore sit
between two rows treated as consecutive, allowing its clock/penalty/state effect
to be folded into the earlier play's `PLAY_STATE_AFTER`.

M6 now carries `source_row_index`. A supplied `next_record` must be from the same
provider game and have index exactly `current + 1`. Missing adjacency metadata or
an intervening raw row fails closed. The real-season validator now skips, rather
than bridges, nonadjacent surviving rows.

The old historical statement `173 validated / 0 failures` is retained as history
but is not accepted as final M6 certification evidence. A corrected 2025 rerun is
required.

### F-02 — unavailable charting was represented as false

**Severity:** HIGH — REMEDIATED

Base nflverse PBP does not expose play-action/RPO/screen/motion/shift/designed-QB-
run fields consistently. A false default conflates "provider observed absent" with
"provider did not expose this concept." Those fields are now tri-state and remain
`None` when unavailable. No free-text inference was added.

### F-03 — normalized writes stopped at raw-content identity

**Severity:** HIGH — REMEDIATED

The provisional writer could retain `evidence_id` but not the specific M3
acquisition observation. M5 already proved why those identities must remain
separate. Certified M6 persistence now requires both, validates the exact
observation/provider pair, persists it to play/participation/penalty observations,
and includes acquisition identity in normalized observation identity.

### F-04 — play participation was always empty

**Severity:** HIGH — REMEDIATED

The F-5 participation object existed but nflverse normalization never populated it.
Structured player IDs are now extracted for explicitly supported roles. Provider
IDs must be mapped to canonical PlayerIds before normalization; unresolved actors
fail closed. The normalizer never manufactures canonical player IDs from provider
strings.

### F-05 — drive normalization was only an identity side effect

**Severity:** MEDIUM — REMEDIATED

Persistence created drive identity, but no deterministic F-5 drive summary was
constructed. `normalize_drive` now validates one canonical drive/possession segment
and derives only defensible start/end/count/points/turnover fields.

### F-06 — canonical JSON repeated provider-row identity

**Severity:** HIGH — REMEDIATED

Provider IDs/play IDs/drive IDs and provider free text were repeated inside the
normalized payload even though the observation record already carries lineage.
The downstream canonical serializer now excludes provider-shaped identity and
extraction flags. Provenance remains available on the observation envelope.

### F-07 — direct import could bypass certified persistence

**Severity:** HIGH — REMEDIATED

The package export was switched to the certified writer, but the historical
`normalization.persistence` module still contained the old write implementation.
It is now a compatibility boundary that requires acquisition-observation
provenance and delegates actual writes to certified persistence; shared canonical
row helpers live separately in `persistence_core`.

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
- an existing normalized observation or child membership disagrees with replayed data;
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

## 7. Required executable certification evidence

Before M6 certification, the branch must produce:

```text
Python 3.12.10 project .venv
full pytest PASS
Ruff PASS
strict mypy PASS
clean working tree
schema version 7 remains valid
fresh SQLite 0 -> 7 migrate PASS
SQLite 7 -> 7 check PASS
M6 deterministic validator PASS
canonical PASS / PLAY_ACTION execution PASS
ordered SNAP/THROW/TARGET/CATCH/... event evidence PASS
canonical participation PASS
penalty identity/event PASS
adjacent PLAY_STATE_AFTER PASS
nonadjacent state-after rejection PASS
canonical drive construction PASS
raw evidence ID retained
acquisition-observation ID retained
bad acquisition provenance rejection + atomic rollback PASS
provider-neutral canonical payload PASS
corrected real 2025 nflverse full-season normalization run
real-season normalization_error_count = 0 for successfully extracted rows
real-season next_state_error_count = 0 for truly adjacent validated transitions
nonadjacent surviving transitions explicitly counted/skipped
```

---

## 8. Current decision

```text
M6 F-5 STATIC ARCHITECTURE AUDIT: COMPLETE
M6 RAW-ROW ADJACENCY REMEDIATION: IMPLEMENTED
M6 UNKNOWN CHARTING SEMANTICS: IMPLEMENTED
M6 CANONICAL PARTICIPATION: IMPLEMENTED
M6 PENALTY PLAYER RECONCILIATION: IMPLEMENTED
M6 DRIVE NORMALIZATION: IMPLEMENTED
M6 M3/M5 ACQUISITION PROVENANCE: IMPLEMENTED
M6 ATOMIC NORMALIZATION PERSISTENCE: IMPLEMENTED
M6 PROVIDER-NEUTRAL DOWNSTREAM PAYLOAD: IMPLEMENTED
M6 DIRECT PERSISTENCE BYPASS: CLOSED
M6 NO-NETWORK VALIDATOR: IMPLEMENTED
M6 CORRECTED REAL-PBP VALIDATOR: IMPLEMENTED
M6 LOCAL QUALITY GATE: PENDING
M6 SQLITE GATE: PENDING
M6 DETERMINISTIC VALIDATOR GATE: PENDING
M6 REAL 2025 NFLVERSE GATE: PENDING
M6 ARCHITECTURE CERTIFICATION: WITHHELD UNTIL ALL EXECUTABLE GATES PASS
```
