# M6C Gate A Remediation Decision — Historical PBP Compatibility

**Project:** The Daily Line — Daily NFL
**Checkpoint:** M6C — Controlled Historical Continuation / Full Historical Compatibility
**Status:** REMEDIATION APPROVED FOR IMPLEMENTATION / VALIDATION PENDING
**Source Gate-A executable authority:** `4a17bb0722efe37603c2856447ba02fd1005f690`
**Source failing fingerprints:** 1999 `69d402fdf4632aa9ad7e1cb5e25f4e620e362e5fe69efec6a1c8583359c9580d`; 2010 `1efce259db3a3a4c4c1bee376d4f28de01e8de36a1f4faa08fcaec1040e6260e`

This document records the evidence-backed remediation decision reached after full raw-row inspection of the two failing Gate-A sentinel seasons. It does not certify the remediation. Gate A remains blocked until executable changes pass focused tests, Ruff, strict mypy, full pytest, and a complete six-sentinel revalidation from the stored raw artifacts.

---

## 1. Proven 1999 game-opening kickoff invariant

The original Gate-A run rejected 253 provider `kickoff` rows because the pre-play possession-oriented score fields were absent.

The full raw diagnostic proves all 253 rows satisfy every one of the following conditions:

```text
candidate_count: 253
distinct_games: 253
strict_game_openers: 253
non_strict_rows: 0
```

For every affected row:

- it is the first raw row for its game;
- period is Q1;
- `quarter_seconds_remaining == 900`;
- `kickoff_attempt` is true;
- `play_type == kickoff`;
- both pre-play provider score fields are missing.

The post-score pairs were `(0,0)` for 252 rows and `(0,6)` for one row. This does not undermine the pre-play invariant: every NFL game starts 0-0, while a post-play score may legitimately differ on an opening kickoff.

### Decision

The nflverse extractor may reconstruct **pre-play 0-0 only when the caller explicitly identifies the row as the first raw row of that game and all structural opening-kickoff conditions hold**.

This is not a generic missing-score fallback. A later kickoff, non-Q1 row, non-15:00 row, non-kickoff, partial score omission, or row not proven first-in-game must continue to fail closed.

---

## 2. Proven incomplete-penalty shape

### 1999

There are 25 rows with `penalty == true` and missing structured penalty type.

The complete raw diagnostic proves:

```text
anomaly_count: 25
penalty_team missing: 0
penalty_type missing: 25
```

Action signatures include:

```text
12 rush attempts
5 pass attempts
7 no_play rows
1 non-pass/non-rush row
```

Many are genuine state-bearing scrimmage plays. Dropping the rows would therefore discard core football history.

### 2010

There are three analogous rows:

```text
anomaly_count: 3
penalty_team missing: 0
penalty_type missing: 3
```

Two are provider `no_play` rows. One is provider `run` with `rush_attempt=true`, `yards_gained=2`, defensive penalty team, penalty yards, and automatic-first-down signal. Although its description is `*** play under review ***`, its structured state/result fields are compatible with an actual state-bearing rushing play plus an incompletely typed penalty. It must not be reclassified as administrative merely from the description.

### Decision

When nflverse structurally asserts a penalty and supplies a valid penalty team but omits only `penalty_type`, preserve the play and penalty using a reserved explicit unknown-type token:

```text
UNKNOWN
```

Semantics:

> Provider asserts a penalty occurred, but the provider did not supply the foul type.

This token is not a guessed football foul. The extractor must continue to preserve all other provider-supported penalty facts, including team, yards, automatic-first-down, no-play/nullification state, disposition, player identity when present, and immutable raw provenance.

If the penalty team itself is missing, extraction remains fail-closed. M6C does not authorize free-text parsing to invent the team or foul type.

No database schema migration is required because the canonical penalty contract already stores `penalty_type` as a nonblank string. `UNKNOWN` is an explicit epistemic state within that existing contract, not a fabricated specific penalty category.

---

## 3. Validator blind spot discovered

The original M6C classifier detected excluded core plays from provider `play_type`. This was insufficient in legacy nflverse rows because 1999 frequently has `play_type == NULL` while execution flags still prove a pass or rush.

The 1999 penalty anomalies expose this directly:

- 12 rejected rows have `rush_attempt=true`;
- 5 rejected rows have `pass_attempt=true`;
- many have provider `play_type=NULL`.

Therefore a rejected core play could escape the hard-failure rule if `play_type` was null.

### Decision

The reusable nflverse validator must record an additional rejected-row **action-family** classification derived only from structured provider flags/hints, using the same priority semantics as canonical play classification where defensible.

At minimum it must recognize:

```text
KNEEL
SPIKE
PUNT
FIELD_GOAL
KICKOFF
EXTRA_POINT
TWO_POINT
SACK
SCRAMBLE
PASS
RUSH
PENALTY_ONLY
TIMEOUT
ADMINISTRATIVE
<UNKNOWN>
```

M6C classification must hard-fail when a rejected row has a core action family even if provider `play_type` is null.

The existing provider-play-type check remains useful and is not removed.

---

## 4. Validator versioning

Because rejected-row evidence and classification semantics become stricter, increment:

```text
M6C_PBP_VALIDATOR_V1 -> M6C_PBP_VALIDATOR_V2
```

Old V1 PASS summaries must not be resumable as V2 evidence. Stored raw artifacts remain reusable and must be revalidated without network reacquisition.

---

## 5. Required implementation regressions

Before any Gate-A rerun, tests must prove:

1. a normal missing pre-play score still fails closed;
2. the exact first-row/Q1/15:00/kickoff/both-scores-missing invariant reconstructs 0-0;
3. an almost-opening kickoff that violates any required condition still fails closed;
4. missing penalty type with known penalty team yields explicit `UNKNOWN` and preserves remaining structured penalty fields;
5. missing penalty team still fails closed;
6. a rejected row with `play_type=NULL` but `rush_attempt=true` is classified as excluded core RUSH and fails M6C;
7. equivalent PASS/KICKOFF action-family rejection is also hard-fail capable;
8. old resume summaries are invalidated by validator-version mismatch;
9. no current M6 normalization/persistence regressions are introduced.

---

## 6. Required post-change validation

After implementation:

```text
focused extraction/M6C/M6 tests
Ruff
strict mypy
full pytest
```

Then re-run all six sentinels from stored raw bytes with `--revalidate`:

```text
1999
2005
2010
2015
2020
2025
```

No Gate-B full-history sweep is permitted until all six are PASS or any new REVIEW_REQUIRED/FAIL result has been explicitly triaged.
