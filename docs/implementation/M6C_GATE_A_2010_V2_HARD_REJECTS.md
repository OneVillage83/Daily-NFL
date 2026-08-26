# M6C Gate A V2 — 2010 Hard-Reject Isolation

**Project:** The Daily Line — Daily NFL  
**Checkpoint:** M6C — Controlled Historical Continuation / Full Historical Compatibility  
**Status:** TRIAGE CLOSED — REMEDIATION APPROVED  
**Executable authority under diagnosis:** `695f30f175cf70468c38b79e4150592b6ed692a9`  
**Validator:** `M6C_PBP_VALIDATOR_V2`

## 1. 2010 V2 summary

```text
status: FAIL
validation_fingerprint: 539809d9618786a111e5a8a9915a63d3ae5685e2031b61785268e583b7c20702
row_count: 46,892
normalized: 43,637
extraction_errors: 3,255
normalization_errors: 0
next_state_errors: 0
```

The only hard failure reason is:

```text
excluded core action_family 'KICKOFF'
under reason 'pre-play home/away score cannot be reconstructed'
```

## 2. Exact remaining hard-reject shape

Exactly five rows remain. All five share the same structural pattern:

- `play_id = 1`
- `play_type = NULL`
- `desc = "*** play under review ***"`
- `qtr = 1`
- `quarter_seconds_remaining = NULL`
- `yardline_100 = NULL`
- `posteam_score = NULL`
- `defteam_score = NULL`
- `kickoff_attempt = 1`
- no explicit replay/challenge result
- no structured penalty

Affected games:

```text
2010_01_DEN_JAX
2010_03_IND_DEN
2010_07_NE_SD
2010_07_PIT_MIA
2010_08_HOU_IND
```

These rows are classified as `KICKOFF` by the V2 rejected-action detector solely because `kickoff_attempt=1`, despite lacking the state fields required for an actual kickoff execution and carrying only the review-placeholder description.

## 3. Adjacency evidence

The follow-up raw-row diagnostic examined the first eight provider rows of every affected game.

In all five games:

1. the malformed review-placeholder is provider row 1 for the game;
2. it has `play_id=1`, `play_type=NULL`, missing clock/yardline/pre-scores, and description `*** play under review ***`;
3. the immediately following provider row is a real opening kickoff;
4. that real kickoff has `play_type=kickoff`, `kickoff_attempt=1`, Q1 at 15:00 (`quarter_seconds_remaining=900`), a real yardline, explicit 0-0 pre-score state, and a normal football play description;
5. subsequent rows continue normal game state from the real kickoff.

Examples:

```text
2010_01_DEN_JAX
row 1: play_id=1, review placeholder, no clock/yardline/scores
row 2: play_id=39, J.Scobee opening kickoff, Q1 15:00, yardline_100=30, scores 0-0

2010_03_IND_DEN
row 1: play_id=1, review placeholder, no clock/yardline/scores
row 2: play_id=45, M.Prater opening kickoff, Q1 15:00, yardline_100=30, scores 0-0

2010_07_NE_SD
row 1: play_id=1, review placeholder, no clock/yardline/scores
row 2: play_id=36, S.Gostkowski opening kickoff, Q1 15:00, yardline_100=30, scores 0-0

2010_07_PIT_MIA
row 1: play_id=1, review placeholder, no clock/yardline/scores
row 2: play_id=37, D.Carpenter opening kickoff, Q1 15:00, yardline_100=30, scores 0-0

2010_08_HOU_IND
row 1: play_id=1, review placeholder, no clock/yardline/scores
row 2: play_id=36, J.Kapinos opening kickoff, Q1 15:00, yardline_100=30, scores 0-0
```

The placeholder therefore does not carry a distinct football execution or state transition. The inherited `kickoff_attempt=1` flag is not sufficient to treat it as a real kickoff when the exact review-placeholder signature is present.

## 4. Approved remediation

The safest fix is validation-classification-only.

Do **not** change the certified nflverse extractor again. Do **not** broaden opening-kickoff reconstruction. Do **not** weaken the global KICKOFF hard-reject policy.

Instead, the M6C rejected-row action classifier may recognize the exact provider review-placeholder signature before inherited execution flags:

```text
desc == "*** play under review ***"
play_id == 1
play_type is absent
qtr == 1
quarter_seconds_remaining is absent
yardline_100 is absent
posteam_score is absent
defteam_score is absent
```

Rows meeting that full signature are classified as `ADMINISTRATIVE` for rejected-row coverage accounting. The actual following kickoff remains the canonical state-bearing row and continues to be validated normally.

This is not a generic review-row allowlist. A review row with real clock/yardline/score state, non-initial play identity, or a populated provider play type does not receive this classification automatically.

## 5. Versioning and validation requirement

Because rejected-row classification semantics change, bump the validator from:

```text
M6C_PBP_VALIDATOR_V2
```

to:

```text
M6C_PBP_VALIDATOR_V3
```

This prevents old V2 summaries from resuming as equivalent evidence.

Required before Gate A may close:

- focused classifier regression proving the exact placeholder becomes `ADMINISTRATIVE`;
- near-miss regression proving a real kickoff or incomplete placeholder remains `KICKOFF`/hard-rejected;
- Ruff PASS;
- strict mypy PASS;
- full pytest PASS;
- clean exact committed executable SHA;
- all six Gate-A sentinels revalidated from stored raw under V3;
- 1999/2005/2010/2015/2020/2025 all PASS;
- normalization errors remain zero;
- adjacent next-state errors remain zero.

Gate A remains **OPEN / BLOCKED pending V3 implementation and revalidation**. Gate B remains locked.
