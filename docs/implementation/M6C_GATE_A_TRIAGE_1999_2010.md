# M6C Gate A Triage — 1999 and 2010

**Project:** The Daily Line — Daily NFL
**Checkpoint:** M6C — Controlled Historical Continuation / Full Historical Compatibility
**Status:** TRIAGE OPEN
**Source Gate-A executable authority:** `4a17bb0722efe37603c2856447ba02fd1005f690`

This document preserves the exact failure shape for the two Gate-A sentinel seasons that did not pass. It exists separately from final certification evidence so later work can reconstruct why remediation was required without relying on chat history.

---

## 1. Cross-season result

Neither failing season has a canonical normalization failure or adjacent-state failure.

```text
1999 normalization_error_count: 0
1999 next_state_error_count: 0

2010 normalization_error_count: 0
2010 next_state_error_count: 0
```

The failures occur at the provider-row extraction/classification boundary before canonical normalization.

---

## 2. 1999

```text
status: FAIL
validation_fingerprint: 69d402fdf4632aa9ad7e1cb5e25f4e620e362e5fe69efec6a1c8583359c9580d
row_count: 46,136
extracted_and_normalized_count: 45,250
extraction_error_count: 886
normalization_error_count: 0
next_state_adjacent_validated: 44,663
next_state_nonadjacent_skipped: 329
next_state_error_count: 0
```

### Hard/review reasons

```text
excluded core/unreviewed play_type 'kickoff'
  under reason 'pre-play home/away score cannot be reconstructed'

new extraction reason:
  penalty flag is set but structured penalty team/type is missing
```

### Extraction buckets

```text
penalty flag set but structured penalty team/type missing: 25
  <NULL>: 18
  no_play: 7

pre-play home/away score cannot be reconstructed: 825
  <NULL>: 570
  kickoff: 253
  no_play: 2

quarter_seconds_remaining missing: 8
  <NULL>: 8

yardline_100 missing: 28
  <NULL>: 28
```

### Representative 1999 kickoff evidence

Examples show a first-quarter 15:00 kickoff with `posteam_score` and `defteam_score` absent, e.g.:

```text
game_id: 1999_01_ARI_PHI
play_id: 35
play_type: kickoff
qtr: 1
quarter_seconds_remaining: 900
desc: C.Jacke kicks 68 yards from ARI 30 to PHI 2. A.Rossum to PHI 23 for 21 yards (P.Sapp).
posteam_score: NULL
defteam_score: NULL
```

and:

```text
game_id: 1999_01_BUF_IND
play_id: 35
play_type: kickoff
qtr: 1
quarter_seconds_remaining: 900
desc: M.Vanderjagt kicks 60 yards from IND 30 to BUF 10. K.Williams to BUF 32 for 22 yards (K.Elias).
posteam_score: NULL
defteam_score: NULL
```

This strongly suggests a legacy-era provider omission on game-opening kickoff pre-score state, but remediation is **not approved yet**. Before deriving 0-0, the full set of 253 rows must prove that every affected kickoff is a true game-opening state under explicit structural conditions.

### Representative 1999 penalty evidence

The missing structured penalty rows are not all ignorable administrative rows. Examples include real scrimmage plays:

```text
(8:49) E.James left tackle to BUF 45 for 40 yards (T.Smith). PENALTY on BUF-H.Jones, 5 yards, enforced at BUF 45.
```

and:

```text
(8:08) B.Hobert pass to E.Kennison pushed ob at CAR 11 for 5 yards (E.Davis). PENALTY on CAR-E.Davis, 5 yards, enforced at CAR 11.
```

The certified provider penalty contract requires a nonblank team code and penalty type. Therefore M6C must not silently drop these penalties, invent a penalty type, or approve the extraction failure as harmless without further evidence.

---

## 3. 2010

```text
status: FAIL
validation_fingerprint: 1efce259db3a3a4c4c1bee376d4f28de01e8de36a1f4faa08fcaec1040e6260e
row_count: 46,892
extracted_and_normalized_count: 43,634
extraction_error_count: 3,258
normalization_error_count: 0
next_state_adjacent_validated: 40,729
next_state_nonadjacent_skipped: 2,638
next_state_error_count: 0
```

### Hard/review reasons

```text
excluded core/unreviewed play_type 'run'
  under reason 'penalty flag is set but structured penalty team/type is missing'

new extraction reason:
  penalty flag is set but structured penalty team/type is missing
```

### Extraction buckets

```text
penalty flag set but structured penalty team/type missing: 3
  no_play: 2
  run: 1

pre-play home/away score cannot be reconstructed: 2,404
  <NULL>: 554
  no_play: 1,850

quarter_seconds_remaining missing: 54
  <NULL>: 54

yardline_100 missing: 797
  <NULL>: 795
  no_play: 2
```

### Representative 2010 penalty evidence

All three missing-structured-penalty samples have description:

```text
*** play under review ***
```

Two are provider `no_play` rows. The hard-failing third row is:

```text
game_id: 2010_11_DET_DAL
play_id: 3306
play_type: run
qtr: 4
quarter_seconds_remaining: 783
posteam: DAL
defteam: DET
posteam_score: 21
defteam_score: 19
yardline_100: 13
desc: *** play under review ***
```

This may be a provider review-placeholder row whose inherited `play_type=run` does not describe a distinct football execution. That interpretation is **not approved yet**. The full raw structured replay/challenge fields and adjacent rows must be inspected before classifying it as administrative or safely excludable.

---

## 4. Architecture constraints for remediation

1. Do not add `kickoff` or `run` to the generic M6C exclusion allowlist merely to make Gate A green.
2. Do not infer penalty team/type from free text unless an explicit architecture decision later authorizes and tests a deterministic legacy parser.
3. Do not drop a known penalty flag and emit a canonical play as if no penalty occurred.
4. A 0-0 pre-score repair is potentially defensible only for a structurally proven game-opening state; it must not be a generic missing-score fallback.
5. Review placeholders may be excluded/administratively normalized only when explicit provider structure and adjacency prove they are metadata rows rather than distinct execution.
6. Any executable remediation requires focused regression tests, exact-head Ruff/mypy/full pytest, and a full Gate-A rerun from stored raw bytes before Gate B.

---

## 5. Next diagnostic

Before code changes, inspect:

### 1999 kickoff set

For all 253 rejected kickoff rows, prove or disprove:

- distinct game count;
- row is the first raw row for its game (or first state-bearing row under a documented rule);
- period is 1;
- clock is 900;
- kickoff_attempt is true;
- pre-score fields are null;
- post-score fields are 0-0 or otherwise consistent with a non-scoring opening kickoff;
- no affected row is a later kickoff, overtime kickoff, or post-score kickoff.

### 1999/2010 missing-penalty set

For every affected row, inspect:

- penalty / penalty_team / penalty_type / penalty_yards;
- pass_attempt / rush_attempt / sack / scramble / kickoff and other execution flags;
- replay_or_challenge and replay result fields when available;
- no_play/provider play type;
- participant IDs;
- previous and next raw rows in the same game;
- whether the row duplicates, annotates, or changes a neighboring football execution.

No remediation decision is final until this raw evidence is reviewed.
