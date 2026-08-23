"""Forward-only schema additions required by the M5 F-4 PIT contract.

Migration 7 preserves the provisional migration-3 PIT history while adding
source-observation provenance and the metadata needed for certified immutable
feature-input snapshots.
"""

M5_PIT_CONFORMANCE_SCHEMA_SQL = r"""
ALTER TABLE schedule_observations ADD COLUMN evidence_observation_id TEXT
    REFERENCES raw_evidence_observations(evidence_observation_id);
ALTER TABLE play_observations ADD COLUMN evidence_observation_id TEXT
    REFERENCES raw_evidence_observations(evidence_observation_id);
ALTER TABLE participation_observations ADD COLUMN evidence_observation_id TEXT
    REFERENCES raw_evidence_observations(evidence_observation_id);
ALTER TABLE penalty_observations ADD COLUMN evidence_observation_id TEXT
    REFERENCES raw_evidence_observations(evidence_observation_id);
ALTER TABLE game_result_observations ADD COLUMN evidence_observation_id TEXT
    REFERENCES raw_evidence_observations(evidence_observation_id);

ALTER TABLE pit_snapshots ADD COLUMN feature_contract TEXT;
ALTER TABLE pit_snapshots ADD COLUMN feature_version TEXT;
ALTER TABLE pit_snapshots ADD COLUMN feature_values_json TEXT;
ALTER TABLE pit_snapshots ADD COLUMN coverage_report_json TEXT;
ALTER TABLE pit_snapshots ADD COLUMN missing_features_json TEXT;
ALTER TABLE pit_snapshots ADD COLUMN pit_validation_result TEXT;
ALTER TABLE pit_snapshots ADD COLUMN input_count INTEGER;

ALTER TABLE pit_snapshot_inputs ADD COLUMN evidence_observation_id TEXT
    REFERENCES raw_evidence_observations(evidence_observation_id);
ALTER TABLE pit_snapshot_inputs ADD COLUMN provider_id TEXT
    REFERENCES providers(provider_id);
ALTER TABLE pit_snapshot_inputs ADD COLUMN provider_revision TEXT;
ALTER TABLE pit_snapshot_inputs ADD COLUMN provider_schema_version TEXT;
ALTER TABLE pit_snapshot_inputs ADD COLUMN parser_version TEXT;
ALTER TABLE pit_snapshot_inputs ADD COLUMN raw_sha256 TEXT;

CREATE INDEX idx_schedule_obs_evidence_observation
    ON schedule_observations(evidence_observation_id);
CREATE INDEX idx_play_obs_evidence_observation
    ON play_observations(evidence_observation_id);
CREATE INDEX idx_participation_obs_evidence_observation
    ON participation_observations(evidence_observation_id);
CREATE INDEX idx_penalty_obs_evidence_observation
    ON penalty_observations(evidence_observation_id);
CREATE INDEX idx_result_obs_evidence_observation
    ON game_result_observations(evidence_observation_id);
CREATE INDEX idx_pit_snapshot_inputs_evidence_observation
    ON pit_snapshot_inputs(evidence_observation_id);

CREATE TRIGGER pit_snapshots_require_m5_metadata
BEFORE INSERT ON pit_snapshots
WHEN NEW.feature_contract IS NULL
  OR trim(NEW.feature_contract) = ''
  OR NEW.feature_version IS NULL
  OR trim(NEW.feature_version) = ''
  OR NEW.feature_values_json IS NULL
  OR NEW.coverage_report_json IS NULL
  OR NEW.missing_features_json IS NULL
  OR NEW.pit_validation_result <> 'PASS'
  OR NEW.input_count IS NULL
  OR NEW.input_count < 0
BEGIN
    SELECT RAISE(ABORT, 'M5 PIT snapshots require certified feature metadata');
END;

CREATE TRIGGER pit_snapshot_inputs_require_evidence_pair
BEFORE INSERT ON pit_snapshot_inputs
WHEN (NEW.evidence_id IS NOT NULL OR NEW.evidence_observation_id IS NOT NULL)
 AND (
    NEW.evidence_id IS NULL
    OR NEW.evidence_observation_id IS NULL
    OR NEW.provider_id IS NULL
    OR NEW.raw_sha256 IS NULL
    OR NOT EXISTS (
        SELECT 1
        FROM raw_evidence_observations observation
        JOIN raw_evidence raw
          ON raw.evidence_id = observation.evidence_id
        WHERE observation.evidence_observation_id = NEW.evidence_observation_id
          AND observation.evidence_id = NEW.evidence_id
          AND observation.provider_id = NEW.provider_id
          AND raw.sha256 = NEW.raw_sha256
    )
)
BEGIN
    SELECT RAISE(ABORT, 'PIT raw provenance must match evidence observation/provider/checksum');
END;

CREATE TRIGGER pit_snapshot_seals_require_validated_manifest
BEFORE INSERT ON pit_snapshot_seals
WHEN NOT EXISTS (
        SELECT 1
        FROM pit_snapshots snapshot
        WHERE snapshot.snapshot_id = NEW.snapshot_id
          AND snapshot.pit_validation_result = 'PASS'
          AND snapshot.input_count = (
              SELECT COUNT(*)
              FROM pit_snapshot_inputs input
              WHERE input.snapshot_id = NEW.snapshot_id
          )
    )
BEGIN
    SELECT RAISE(ABORT, 'PIT snapshot cannot seal before validated input membership is complete');
END;
"""
