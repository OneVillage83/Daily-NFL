# M6C Gate A V2 — 2010 Hard-Reject Isolation

**Project:** The Daily Line — Daily NFL  
**Checkpoint:** M6C — Controlled Historical Continuation / Full Historical Compatibility  
**Status:** TRIAGE OPEN — FIVE REVIEW-PLACEHOLDER ROWS REMAIN  
**Executable authority:** `695f30f175cf70468c38b79e4150592b6ed692a9`  
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

## 3. Current interpretation

The five rows are strong candidates for provider review/administrative placeholder metadata rather than true kickoff executions. However, this interpretation is not yet approved.

Before changing the classifier or opening-kickoff logic, inspect the immediately adjacent raw rows in all five games to determine:

1. whether the placeholder is the first raw row for the game;
2. whether the following row is the actual opening kickoff;
3. whether that following row carries the real Q1 15:00 clock/state/description;
4. whether the placeholder duplicates or merely annotates the opening kickoff;
5. whether an opening-kickoff repair must use the first state-bearing row rather than literally the first provider row.

## 4. Prohibited shortcut

Do not simply remove `KICKOFF` from core hard-reject accounting or allowlist these five rows. If adjacency proves they are provider metadata, classify only the exact evidence-backed placeholder shape administratively and preserve the actual opening kickoff as the canonical state-bearing row.

Gate A remains **OPEN / BLOCKED on 2010 only**. Gate B remains locked.
