# M6C Gate B — Full Historical Compatibility Result

**Project:** The Daily Line — Daily NFL  
**Checkpoint:** M6C — Controlled Historical Continuation / Full Historical Compatibility  
**Gate:** B — Full completed-history sweep  
**Status:** CLOSED / PASS  
**Historical range:** 1999–2025 inclusive (27 completed seasons)  
**Contract:** `M6C_HISTORICAL_CHECKPOINT_V1`  
**Validator:** `M6C_PBP_VALIDATOR_V3`  
**Validator-semantics authority:** `d4c3e14c2a3cd9c40dd33a9a2acc9c75d7b4dfd0`  
**Runner/provenance authority:** `98aba116a80c51c6dc9f05d602f5bc41e68188e6`

## Command

```text
python scripts/run_m6c_historical_checkpoint.py \
    --gate full \
    --database local-data/m6c/m6c-history.db \
    --raw-root local-data/m6c/raw \
    --output-root local-data/m6c/validation
```

The run intentionally omitted `--revalidate`. Gate C had already proven that an integrity/version/raw-bound PASS summary can safely resume, so certified sentinel summaries were resumed while the previously unvalidated seasons were acquired and validated normally.

## Aggregate result

```text
contract_version: M6C_HISTORICAL_CHECKPOINT_V1
validator_version: M6C_PBP_VALIDATOR_V3
overall_status: PASS
schema_version: 7
season_count: 27
requested_seasons: 1999 through 2025 inclusive
manifest_sha256: e28c45a371c2c85926444c92808385f993595c9cdb8fecc5973338393c450634

row_count: 1,279,628
extracted_and_normalized_count: 1,195,503
extraction_error_count: 84,125
normalization_error_count: 0
next_state_adjacent_validated: 1,120,141
next_state_nonadjacent_skipped: 68,089
next_state_error_count: 0
raw_size_bytes: 488,034,547
```

Exact accounting holds:

```text
1,195,503 normalized + 84,125 extraction exclusions + 0 normalization errors
= 1,279,628 provider rows
```

No successfully extracted row failed canonical normalization. No literally adjacent provider-row state transition failed `PLAY_STATE_AFTER` validation.

## Per-season result

Every completed season passed. `non_pass_count = 0`.

```text
1999 PASS  449ea036dec6b782335c518125e8aa8f88dc5ab7800958789c967c07222bcd9b
2000 PASS  3d572cf1de956ba582110e65607909dc87a0de9f6b96a3595a4a2905e9c1604a
2001 PASS  2e7a02e2a9d086382ba5a8e88c52913f206ceed5238b6b00a341a0950723dc7d
2002 PASS  eb0357e139d55458f34c359836185922b7bf57befaf0b10f20e26502b14412d1
2003 PASS  0763741cbe50d913340c572fb7b799f047e5fe70824a6268fa3e82a5f342d710
2004 PASS  cb6713ea829993f093e88027f410b3bb6857f7b8c522baeece36025d2fcb163d
2005 PASS  d5a2f357b97bdec17d9dbd1df52d2e47fef1f7e38cdf5ad124f7378a24cfb796
2006 PASS  dad9bed9bb17d3912220296c55fc1278a8c8e2fdc2de6766a4d83fee526e8af0
2007 PASS  c5b990a8c702fef3db888d5ced197a87957859b5d168d568862c3f61e09eb3a8
2008 PASS  897b813fbdb59adb4a7dcc88a9c2313072ece902f4eefab61617291cf327842c
2009 PASS  062c5dd91101dea54a42304954e104ac62609b80cfc058a4c8d9c4adb7ba9665
2010 PASS  ea4e95b083c48b22f42b35180f2b7a9cab4c9b7b0c41be88e25fc294e316e898
2011 PASS  e3806feea76ea4df239ee6874566034d39b813ca99c6b02b6f4e28d83b7876f1
2012 PASS  7714a0e82e0932c82b2c022ec8ede3b7c2e156870f601e6fe8eb701d9b809090
2013 PASS  b5f5e9ec015865567edd5ed608a02cc01b68d1b6b5204066d1824ccefc90b314
2014 PASS  2316bf92e9c1ff6a1c18bc1f76dfe3c9394b4ea8a7a7cb1848b6d4a281fb6387
2015 PASS  e38576c5954367147796b68263e4530ba7c31e6a74f0250bcf8b7af942cb5917
2016 PASS  cefa26d76b64f29bf1f80e4224c2c86e111529827543113503308aceda08cdf5
2017 PASS  ed2da163b399d604224cf31ce085a9034d3942b9f580bda6e7355a1d1d8da4c8
2018 PASS  ce75d13616d86a807a5e96a1c3df7a7462bcbc8ebd45e16f4f4fd6ab7af8a881
2019 PASS  07199e2621633a0596efd4a323c5d22ee5c0caaf57e18d31fcc5fc2114e3a85f
2020 PASS  55fc4ef101df4f2167e92b0ae548aafe513bc92255d2a4e87323d068299d71ac
2021 PASS  1c62dcf3c7f0667d29464eee1f52dfb0f2ebd50f5ed946a899097b6e999586e6
2022 PASS  aad703e850044948d8993b8ee0b9b25082a02e88aeceb7ff7d5b207a58064478
2023 PASS  e8b4c43a30cae18287e43ad5b34c391984f6136d540a2854ce393b63e24252c0
2024 PASS  077778479365059a0e4772ec40bdb57143dcef8e9e1c048d9cec93e383687e42
2025 PASS  d66f08ec2dbd884ba611af590b51c83251fb3cbda1964cfee6f72b9f6b6b8f8e
```

## Acquisition / resume behavior

Previously certified sentinels resumed from stored raw evidence. The other historical seasons were acquired and validated. 2025 retained the forced-reacquisition provenance established during Gate C while the Gate-B invocation itself reused its immutable raw object and resumed validation.

This is expected behavior under the locked M6C provenance model:

- `validation_acquisition_mode` describes how the raw object used by the persisted validation summary was originally obtained;
- `raw_resolution_mode` describes what the current invocation did with raw evidence;
- `execution_mode` describes what the current invocation did with validation.

## Interpretation

Gate B demonstrates that the certified M6 extraction/normalization semantics are compatible with the complete nflverse completed-season PBP range from 1999 through 2025 under the reviewed fail-closed exclusion policy.

This does **not** certify a production canonical historical-player backfill. M6C still uses validation-only opaque PlayerIds in memory where required to exercise normalization because the repository does not yet contain the certified historical identity inputs necessary to reconcile every historical actor to production canonical PlayerIds.

M6C also does **not** certify F-6 through F-9 state-engine semantics. TeamState, PlayerState, UnitState, CoachingState, injury/availability state, and related state engines remain M7 work.

## Gate B disposition

```text
27 / 27 seasons PASS
non_pass_count: 0
normalization_error_count: 0
next_state_error_count: 0
Gate B: CLOSED / PASS
```

M6C certification is still withheld pending the final architecture-conformance audit, legacy M6 regression, SQLite migration/integrity check, exact-head quality gate, certification evidence/status updates, complete PR scope review, and pinned merge.
