# M6B — Real nflverse PBP Validation

Status: **Full-play validation passed; partial penalty-event retention required before checkpoint close**

Related references:

- [`M6B_PENALTY_RETENTION_PLAN.md`](./M6B_PENALTY_RETENTION_PLAN.md)
- [`../architecture/PENALTY_EVENT_AND_DISCIPLINE_ARCHITECTURE_V1.md`](../architecture/PENALTY_EVENT_AND_DISCIPLINE_ARCHITECTURE_V1.md)

## Scope

M6B validates the M6 canonical play/drive normalization contracts against one real, completed nflverse play-by-play season before any full historical backfill.

This checkpoint deliberately does **not** start M6C or acquire the full 1999-current nflverse history.

M6B now has two separate success conditions:

1. full state-bearing football plays must normalize correctly; and
2. meaningful penalty facts must be retained even when a complete `PLAY_STATE_BEFORE` cannot be reconstructed.

The governing distinction is:

> **A row that cannot become a full canonical play is not automatically a row that contains no usable football truth.**

---

## Real-data fixture

- Season: 2025
- Loader used only for local inspection/validation: `nflreadpy==0.1.5`
- Rows: 48,771
- Columns: 372
- Candidate M6 fields present: 51
- Candidate fields absent from base PBP: `no_play`, `play_action`, `rpo`, `screen`, `motion`, `shift`, `designed_qb_run`

Base PBP therefore remains the source for core football state/result fields. FTN-style charting concepts such as play action, RPO, screen, motion, shift, and designed-QB-run remain optional enrichment inputs and must not be inferred from description text.

`no_play` is derived from nflverse `play_type == "no_play"` rather than from a direct `no_play` column.

---

## Full-season full-play normalization result

Final 2025 full-play validation:

- `extracted_and_normalized_count`: 45,196
- `extraction_error_count`: 3,575
- `normalization_error_count`: 0
- `next_state_validated`: 173
- `next_state_error_count`: 0

Canonical taxonomy among successfully normalized rows:

- ADMINISTRATIVE: 10
- EXTRA_POINT: 1,330
- FIELD_GOAL: 1,140
- KICKOFF: 2,927
- KNEEL: 453
- OTHER: 60
- PASS: 18,288
- PENALTY_ONLY: 2,447
- PUNT: 2,042
- RUSH: 13,714
- SACK: 1,352
- SCRAMBLE: 1,221
- SPIKE: 82
- TWO_POINT: 130

No successfully extracted state-bearing row failed canonical normalization.

---

## Full-play extraction rejects

All 3,575 full-play extraction rejects are confined to raw rows whose nflverse `play_type` is either `NULL` or `no_play`:

- pre-play home/away score cannot be reconstructed
  - `<NULL>`: 589
  - `no_play`: 2,140
- `quarter_seconds_remaining` missing
  - `<NULL>`: 2
- `yardline_100` missing
  - `<NULL>`: 844

No pass, run, sack, scramble, punt, field goal, kickoff, extra point, two-point attempt, kneel, or spike row appears in these rejection buckets.

This proves that the strict full-play path is not losing ordinary state-bearing play families.

However, these 3,575 rows are **not all classified as disposable data**.

### Revised interpretation of `no_play`

The 2,140 rejected `no_play` rows require a second audit path.

A `no_play` designation can represent an official result nullified by penalty. Therefore:

> **`no_play` does not mean `no information`.**

If a rejected row contains a defensible penalty fact, that fact must be retained even though row-local provider evidence cannot support a complete `PLAY_STATE_BEFORE`.

The system must preserve supportable information such as:

```text
penalized team
penalized player if available
penalty type
accepted / declined / offsetting
penalty yards
automatic first down
loss of down if available
nullifies play
enforcement spot if available
game / provider play / drive identity
raw evidence and provider revision
period / clock if available
```

while leaving unsupported pre-state fields explicitly unknown.

The complete implementation plan is in `M6B_PENALTY_RETENTION_PLAN.md`.

---

## Why full state is not fabricated for rejected rows

The row-local provider fields used for full-play state are intentionally strict.

`posteam_score` / `defteam_score` are start-of-play score fields, while cumulative home/away score fields represent a different point in the state transition. They must not be substituted blindly just to force a row through normalization.

Likewise, missing `yardline_100`, down/distance, possession, or physical yards must remain unknown when provider evidence cannot defend them.

The new retention policy therefore separates:

```text
FULL CANONICAL PLAY
```

from:

```text
PARTIAL CANONICAL PENALTY / EVENT
```

rather than weakening the full-play causal contract.

---

## Physical outcome vs official outcome

Penalty-nullified plays may contain two analytically distinct facts:

```text
PHYSICAL EXECUTION
```

and

```text
OFFICIAL OUTCOME
```

For example, a runner may physically gain substantial yardage before an offensive holding penalty nullifies the official gain.

The architecture should preserve both when evidence supports both.

Base nflverse PBP does not always provide the physical yardage of a nullified play, so M6B must not invent `physical_yards_gained`. Future enrichment may add it through a defensible, provenance-backed source or validated parser.

---

## Penalty information carried forward to modeling

Retained penalty truth will later support team, player, unit, coaching, feature, and simulation layers.

Planned feature families include:

```text
penalties per game
accepted penalties per game
penalty yards per game
penalties per snap / drive

offensive / defensive / special-teams penalty rates
penalty-type rates
player and unit penalty rates

automatic first downs conceded / received
drive extensions conceded / received
drive-killing offensive penalties
nullified successful / explosive / scoring plays

red-zone penalties
third- and fourth-down penalties
two-minute and late-game penalties
one-score-game penalties

penalty EPA / WPA conceded and received
leverage-weighted penalty rate
expected points lost or gained through penalties
```

These features are future M7/M9+ work. M6B only guarantees that the underlying event truth is retained correctly.

See `PENALTY_EVENT_AND_DISCIPLINE_ARCHITECTURE_V1.md` for the complete modeling plan and PIT requirements.

---

## Provider data-quality handling

At least one real 2025 nflverse row reported a negative timeout counter. Canonical NFL timeout state cannot be negative, so the provider extractor treats negative timeout values as `None` (unknown) rather than zero or a valid count.

After this correction, normalization errors fell from 1 to 0.

---

## Current conclusions

The following M6B findings are now locked:

1. The small `NflversePlayRecord` boundary is compatible with real 2025 nflverse state-bearing PBP.
2. Provider IDs remain provenance only; canonical play identity remains provider-neutral.
3. Core state-bearing football play families normalize cleanly across the season.
4. `PLAY_STATE_AFTER` reconstruction from the next state-bearing row validated on 173 adjacent transitions with zero failures in the sample game.
5. Optional FTN/charting modifiers remain explicit enrichments rather than text-derived guesses.
6. Full-play extraction failures are measured and categorized rather than hidden.
7. A full-play extraction failure must not erase a valid penalty fact.
8. `no_play` penalty rows require a partial-event retention path before M6B closes.
9. Physical and official outcomes remain distinct when evidence supports both.
10. No full historical backfill should begin until the project explicitly resumes at M6C after the planned pivot.

---

## Revised M6B exit gate

M6B is complete only when:

- 2025 state-bearing full-play normalization remains at zero normalization errors;
- representative next-state transitions remain at zero errors;
- all rejected `no_play` rows are audited for supportable penalty truth;
- every supportable partial penalty fact is retained through a canonical, provenance-backed path;
- accepted / declined / offsetting semantics remain distinct;
- penalized-team identity is preserved;
- player identity is preserved when supportable and unknown otherwise;
- penalty yards, automatic first down, loss of down, nullification, and enforcement information are preserved where provider evidence supports them;
- unsupported pre-state and physical-outcome values remain unknown rather than fabricated;
- partial penalty persistence is idempotent and revision-safe;
- validation reports the number of full plays, partial penalty events, raw-only rows, and meaningful penalty facts lost;
- the target `meaningful_penalty_fact_loss_count = 0` is met or any provider limitation is explicitly documented;
- `requirements-dev.txt` is refreshed to include `nflreadpy==0.1.5` and resolved hashes;
- pytest, Ruff, and mypy pass.

M6C/full historical nflverse acquisition remains out of scope until the project resumes after the planned pivot.
