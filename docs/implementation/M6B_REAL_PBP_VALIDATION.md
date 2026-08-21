# M6B — Real nflverse PBP Validation

Status: **Complete pending dependency-lock refresh**

## Scope

M6B validates the M6 canonical play/drive normalization contracts against one real, completed nflverse play-by-play season before any full historical backfill.

This checkpoint deliberately does **not** start M6C or acquire the full 1999-current nflverse history.

## Real-data fixture

- Season: 2025
- Loader used only for local inspection/validation: `nflreadpy==0.1.5`
- Rows: 48,771
- Columns: 372
- Candidate M6 fields present: 51
- Candidate fields absent from base PBP: `no_play`, `play_action`, `rpo`, `screen`, `motion`, `shift`, `designed_qb_run`

Base PBP therefore remains the source for core football state/result fields. FTN-style charting concepts such as play action, RPO, screen, motion, shift, and designed-QB-run remain optional enrichment inputs and must not be inferred from description text.

`no_play` is derived from nflverse `play_type == "no_play"` rather than from a direct `no_play` column.

## Full-season normalization result

Final 2025 validation:

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

## Expected strict exclusions

All 3,575 extraction rejects are confined to raw rows whose nflverse `play_type` is either `NULL` or `no_play`:

- pre-play home/away score cannot be reconstructed
  - `<NULL>`: 589
  - `no_play`: 2,140
- `quarter_seconds_remaining` missing
  - `<NULL>`: 2
- `yardline_100` missing
  - `<NULL>`: 844

No pass, run, sack, scramble, punt, field goal, kickoff, extra point, two-point attempt, kneel, or spike row is present in these rejection buckets.

These rows remain excluded in Canonical Play V1 because the row-local provider evidence does not contain enough start-of-play state to construct `PLAY_STATE_BEFORE` without guessing. M6B intentionally fails closed rather than filling pre-state from incompatible post-play/cumulative fields.

A later sequence-aware recovery layer may revisit excluded `no_play`/administrative rows by using adjacent canonical state plus explicit provenance. That work is **not** required for M6B and must not silently reinterpret post-play values as pre-play state.

## Provider data-quality handling

At least one real 2025 nflverse row reported a negative timeout counter. Canonical NFL timeout state cannot be negative, so the provider extractor treats negative timeout values as `None` (unknown) rather than zero or a valid count. After this correction, normalization errors fell from 1 to 0.

## M6B conclusions

1. The small `NflversePlayRecord` boundary is compatible with the real 2025 nflverse PBP schema.
2. Provider IDs remain provenance only; canonical play identity remains provider-neutral.
3. Core state-bearing football play families normalize cleanly across the season.
4. `PLAY_STATE_AFTER` reconstruction from the next state-bearing row validated on 173 adjacent transitions with zero failures in the sample game.
5. Optional FTN/charting modifiers must remain explicit enrichments rather than text-derived guesses.
6. Strict exclusions are now measured and categorized rather than hidden.
7. No full historical backfill should begin until the project explicitly resumes at M6C.

## Remaining housekeeping before checkpoint close

Regenerate and commit `requirements-dev.txt` from `requirements-dev.in` so the development lock contains `nflreadpy==0.1.5` and its resolved dependencies/hashes.
