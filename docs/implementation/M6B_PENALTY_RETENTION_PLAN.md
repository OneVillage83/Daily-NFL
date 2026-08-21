# M6B — Partial Penalty Event Retention Plan

**Status:** Required before M6B can close  
**Parent checkpoint:** `M6B_REAL_PBP_VALIDATION.md`  
**Architecture reference:** `../architecture/PENALTY_EVENT_AND_DISCIPLINE_ARCHITECTURE_V1.md`

## Why this work was added

The 2025 nflverse validation proved that all successfully extracted state-bearing plays normalize cleanly, but it also revealed 2,140 `play_type == "no_play"` rows whose complete pre-play score cannot be reconstructed from row-local provider fields.

Those rows cannot safely become full canonical plays under the current strict `PLAY_STATE_BEFORE` contract.

However, many `no_play` rows contain meaningful penalty facts. Therefore M6B must not treat "cannot build full causal state" as "discard the football event."

The revised M6B requirement is:

> **Retain every supportable penalty fact even when a full canonical play state cannot be constructed.**

---

# 1. Current validated baseline

2025 nflverse PBP:

```text
rows                              48,771
full extracted + normalized       45,196
full-play extraction rejects       3,575
normalization errors                   0
sample next-state errors               0
```

Current full-play rejection buckets:

```text
pre-play score unavailable
  no_play                          2,140
  NULL                               589

yardline_100 unavailable
  NULL                               844

quarter_seconds_remaining missing
  NULL                                 2
```

No PASS, RUSH, SACK, SCRAMBLE, PUNT, FIELD_GOAL, KICKOFF, EXTRA_POINT, TWO_POINT, KNEEL, or SPIKE rows appear in the rejection buckets.

This proves the full-play normalizer is healthy, but M6B is not complete until meaningful penalty facts in the rejected `no_play` population are measured and retained.

---

# 2. Required provider-row triage

Each row must be classified into one of these outcomes:

```text
A. FULL_CANONICAL_PLAY
B. PARTIAL_PENALTY_EVENT
C. PARTIAL_NON_PENALTY_EVENT
D. RAW_ONLY_ADMINISTRATIVE_OR_UNSUPPORTED
```

The classification must be deterministic and versioned.

## A. Full canonical play

Use the existing `NflversePlayRecord -> NormalizedPlayBundle` path when complete causal state is supportable.

## B. Partial penalty event

Use when full state fails but a defensible structured penalty fact exists.

Retain as much as provider evidence supports:

```text
game ID
provider play ID
drive ID if available
period / clock if available
penalty team
penalty player if available
penalty type
penalty disposition
penalty yards
automatic first down
loss of down if available
nullifies play
enforcement spot if available
provider/raw evidence lineage
```

Unknown causal fields remain unknown.

## C. Partial non-penalty event

If a meaningful football event other than a penalty exists but full state is unavailable, retain it only under an explicit partial-event contract. Do not broaden M6B scope unless the 2025 audit identifies a meaningful population requiring this path.

## D. Raw-only row

Provider rows with no supportable football fact beyond provenance remain in immutable raw evidence and are excluded from canonical feature truth.

---

# 3. Partial penalty extraction contract

Add a provider-neutral partial penalty extraction contract rather than weakening `NflversePlayRecord` fields that are intentionally required for full play state.

Recommended shape:

```text
NflversePartialPenaltyRecord

provider_game_id
provider_play_id
provider_drive_id optional
period optional
quarter_seconds_remaining optional

offense_team_code optional
defense_team_code optional
penalized_team_code
penalized_player_external_id optional

penalty_type
penalty_disposition
penalty_yards optional
automatic_first_down
loss_of_down
nullifies_play
enforcement_spot optional

description optional
```

The contract should contain only facts that can exist independently of a complete `PLAY_STATE_BEFORE`.

Do **not** make `home_score_before`, `yards_to_goal`, or other full-state fields optional inside `NflversePlayRecord` solely to accommodate this use case. Keeping separate contracts preserves semantic clarity.

---

# 4. Persistence plan

The current schema already contains `penalty_observations` and permits player identity to be null.

The first implementation should determine whether partial penalty rows can be represented without a schema migration by:

1. deriving deterministic game-relative canonical event/play identity;
2. creating a canonical play shell with nullable drive/possession where allowed;
3. retaining the provider play ID as provenance rather than canonical identity;
4. inserting one or more `penalty_observations` linked to that canonical shell;
5. preserving raw evidence ID and provider revision;
6. using an explicit partial-event observation payload/version if a `play_observation` is stored;
7. maintaining exact idempotency across repeated ingestion;
8. preserving revised provider observations append-only.

If the current play/observation tables cannot represent partial-event semantics without lying about full normalization, introduce the smallest explicit schema migration rather than overloading existing fields.

---

# 5. Multi-penalty handling

Do not assume one provider row always equals one penalty.

The audit must determine how nflverse 2025 represents:

- multiple accepted penalties on one play;
- declined plus accepted penalties;
- offsetting penalties;
- multiple fouls by the same team;
- penalties by both teams;
- special-teams enforcement.

If structured nflverse fields expose only one penalty while the raw description contains multiple known infractions, record that as a provider coverage limitation. Do not silently invent a complete multi-penalty structure from free text during M6B unless a dedicated parser is explicitly implemented and validated.

Raw evidence must remain available for later enrichment.

---

# 6. Team/player/beneficiary semantics

For every retained penalty, preserve the penalized team.

When player identity exists, retain the provider player ID for reconciliation to canonical player identity.

Future derived state must support both:

```text
cost to offending team
benefit to opponent
```

Examples:

- accepted penalty yards conceded;
- automatic first downs conceded;
- drive extensions conceded;
- opponent penalty yards received;
- automatic first downs received;
- drive extensions received.

Declined and offsetting penalties must remain distinct and must not be counted as accepted enforcement cost.

---

# 7. Validation report changes

Upgrade `validate_nflverse_pbp_normalization.py` so M6B output reports at least:

```text
row_count

full_canonical_play_count
full_play_extraction_error_count
full_play_normalization_error_count

partial_penalty_candidate_count
partial_penalty_retained_count
partial_penalty_extraction_error_count

partial_non_penalty_event_count
raw_only_row_count

meaningful_penalty_fact_loss_count

canonical_play_type_counts
penalty_disposition_counts
penalty_type_counts
penalty_team_coverage
penalty_player_id_coverage
penalty_yards_coverage
automatic_first_down_count
nullified_penalty_count
```

Also report rejection/error reasons by raw `play_type`.

The M6B target is not 100% full-play normalization. The target is:

```text
full-state plays normalized correctly
+
meaningful penalty facts retained correctly
+
unsupported state left explicitly unknown
+
meaningful penalty facts lost = 0
```

---

# 8. Tests required

Add unit/integration coverage for:

- accepted `no_play` penalty with missing pre-score;
- penalty row with missing field position;
- declined penalty;
- offsetting penalty;
- automatic first down;
- nullified official result;
- missing player identity;
- negative timeout sentinel remains unrelated to partial penalty truth;
- duplicate ingestion idempotency;
- provider revision creates a new observation without replacing old evidence;
- team identity maps correctly;
- penalty fact can persist without fabricated pre-state;
- multi-penalty provider limitation is reported explicitly.

Run the standard gate after implementation:

```powershell
python -m pytest -q
python -m ruff check .
python -m mypy .
```

Then rerun 2025 real-data validation.

---

# 9. M6B exit gate — revised

M6B is complete only when all of the following are true:

- full 2025 state-bearing play validation remains at zero normalization errors;
- representative next-state transitions remain at zero errors;
- FTN-only design fields remain optional enrichment rather than inferred text features;
- every 2025 rejected `no_play` row is audited for supportable penalty facts;
- all supportable partial penalty facts are retained through a canonical/provenance-backed path;
- accepted / declined / offsetting semantics remain distinct;
- penalty yards and automatic-first-down information are retained where provider evidence supports them;
- penalized-team identity is retained;
- player identity is retained when supportable and left unknown otherwise;
- physical outcome is not fabricated for nullified plays;
- partial-event persistence is idempotent and revision-safe;
- validator reports `meaningful_penalty_fact_loss_count = 0` or explicitly documents any provider fact that cannot yet be represented;
- dependency lock includes `nflreadpy==0.1.5` for the local validation tooling;
- pytest, Ruff, and mypy are clean.

Only after this gate passes may M6B be marked complete.

M6C/full historical nflverse backfill remains explicitly out of scope until the project resumes after the planned pivot.

---

# 10. Future modeling plan carried forward

M6B only guarantees truth retention. It does not prematurely decide which penalty variables are predictive.

Later milestones will evaluate:

```text
penalties/game
accepted penalties/game
penalty yards/game
penalties/snap
penalties/drive

offense/defense/special-teams penalty rates
penalty-type rates
player/unit penalty rates

automatic first downs conceded/received
drive extensions conceded/received
drive-killing offensive penalties
nullified successful/explosive/scoring plays

red-zone penalties
third/fourth-down penalties
two-minute penalties
late-game / one-score penalties

penalty EPA/WPA conceded/received
leverage-weighted penalty rate
expected points lost/gained via penalties
```

These future features must be PIT-safe, versioned, opponent/context aware, and empirically validated out of sample.
