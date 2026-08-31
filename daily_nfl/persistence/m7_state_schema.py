"""Forward-only schema additions for the M7 immutable state ledger.

Migration 8 adds the shared persistence substrate used by F-6 through F-10.
Migrations 1-7 remain immutable historical authority.
"""

M7_STATE_SCHEMA_SQL = r"""
CREATE TABLE state_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    state_type TEXT NOT NULL,
    subject_type TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    team_season_id TEXT REFERENCES team_seasons(team_season_id),
    game_id TEXT REFERENCES games(game_id),
    as_of TEXT NOT NULL,
    calculation_contract TEXT NOT NULL,
    model_version TEXT NOT NULL,
    state_payload_json TEXT NOT NULL,
    uncertainty_json TEXT NOT NULL,
    coverage_json TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL,
    pit_validation TEXT NOT NULL CHECK (pit_validation = 'PASS'),
    input_count INTEGER NOT NULL CHECK (input_count >= 0),
    dependency_count INTEGER NOT NULL CHECK (dependency_count >= 0),
    created_at TEXT NOT NULL,
    CHECK (trim(snapshot_id) <> ''),
    CHECK (trim(state_type) <> ''),
    CHECK (trim(subject_type) <> ''),
    CHECK (trim(subject_id) <> ''),
    CHECK (trim(calculation_contract) <> ''),
    CHECK (trim(model_version) <> ''),
    CHECK (length(payload_sha256) = 64)
);

CREATE INDEX idx_state_snapshots_subject_asof
    ON state_snapshots(state_type, subject_type, subject_id, as_of);
CREATE INDEX idx_state_snapshots_team_asof
    ON state_snapshots(team_season_id, as_of);
CREATE INDEX idx_state_snapshots_game_asof
    ON state_snapshots(game_id, as_of);

CREATE TABLE state_snapshot_inputs (
    snapshot_id TEXT NOT NULL REFERENCES state_snapshots(snapshot_id),
    input_kind TEXT NOT NULL,
    input_id TEXT NOT NULL,
    source_table TEXT NOT NULL,
    evidence_id TEXT REFERENCES raw_evidence(evidence_id),
    evidence_observation_id TEXT
        REFERENCES raw_evidence_observations(evidence_observation_id),
    provider_id TEXT REFERENCES providers(provider_id),
    provider_revision TEXT,
    provider_schema_version TEXT,
    parser_version TEXT,
    subject_game_id TEXT,
    available_at TEXT NOT NULL,
    availability_method TEXT NOT NULL,
    availability_confidence TEXT NOT NULL,
    effective_at TEXT,
    published_at TEXT,
    observed_at TEXT,
    ingested_at TEXT,
    source_game_kickoff TEXT,
    market_quote_at TEXT,
    season_complete_at TEXT,
    payload_sha256 TEXT,
    raw_sha256 TEXT,
    PRIMARY KEY(snapshot_id, input_kind, input_id),
    CHECK (trim(input_kind) <> ''),
    CHECK (trim(input_id) <> ''),
    CHECK (trim(source_table) <> '')
);

CREATE INDEX idx_state_snapshot_inputs_source
    ON state_snapshot_inputs(source_table, input_kind, input_id);
CREATE INDEX idx_state_snapshot_inputs_available
    ON state_snapshot_inputs(snapshot_id, available_at);
CREATE INDEX idx_state_snapshot_inputs_evidence_observation
    ON state_snapshot_inputs(evidence_observation_id);

CREATE TABLE state_snapshot_dependencies (
    snapshot_id TEXT NOT NULL REFERENCES state_snapshots(snapshot_id),
    parent_snapshot_id TEXT NOT NULL REFERENCES state_snapshots(snapshot_id),
    PRIMARY KEY(snapshot_id, parent_snapshot_id),
    CHECK (snapshot_id <> parent_snapshot_id)
);

CREATE INDEX idx_state_snapshot_dependencies_parent
    ON state_snapshot_dependencies(parent_snapshot_id, snapshot_id);

CREATE TABLE state_snapshot_seals (
    snapshot_id TEXT PRIMARY KEY REFERENCES state_snapshots(snapshot_id),
    sealed_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TRIGGER state_snapshots_no_update
BEFORE UPDATE ON state_snapshots
BEGIN
    SELECT RAISE(ABORT, 'state_snapshots is append-only');
END;
CREATE TRIGGER state_snapshots_no_delete
BEFORE DELETE ON state_snapshots
BEGIN
    SELECT RAISE(ABORT, 'state_snapshots is append-only');
END;

CREATE TRIGGER state_snapshot_inputs_no_update
BEFORE UPDATE ON state_snapshot_inputs
BEGIN
    SELECT RAISE(ABORT, 'state_snapshot_inputs is append-only');
END;
CREATE TRIGGER state_snapshot_inputs_no_delete
BEFORE DELETE ON state_snapshot_inputs
BEGIN
    SELECT RAISE(ABORT, 'state_snapshot_inputs is append-only');
END;

CREATE TRIGGER state_snapshot_dependencies_no_update
BEFORE UPDATE ON state_snapshot_dependencies
BEGIN
    SELECT RAISE(ABORT, 'state_snapshot_dependencies is append-only');
END;
CREATE TRIGGER state_snapshot_dependencies_no_delete
BEFORE DELETE ON state_snapshot_dependencies
BEGIN
    SELECT RAISE(ABORT, 'state_snapshot_dependencies is append-only');
END;

CREATE TRIGGER state_snapshot_seals_no_update
BEFORE UPDATE ON state_snapshot_seals
BEGIN
    SELECT RAISE(ABORT, 'state_snapshot_seals is append-only');
END;
CREATE TRIGGER state_snapshot_seals_no_delete
BEFORE DELETE ON state_snapshot_seals
BEGIN
    SELECT RAISE(ABORT, 'state_snapshot_seals is append-only');
END;

CREATE TRIGGER state_snapshot_inputs_reject_after_seal
BEFORE INSERT ON state_snapshot_inputs
WHEN EXISTS (
    SELECT 1 FROM state_snapshot_seals seal
    WHERE seal.snapshot_id = NEW.snapshot_id
)
BEGIN
    SELECT RAISE(ABORT, 'cannot add state snapshot inputs after sealing');
END;

CREATE TRIGGER state_snapshot_dependencies_reject_after_seal
BEFORE INSERT ON state_snapshot_dependencies
WHEN EXISTS (
    SELECT 1 FROM state_snapshot_seals seal
    WHERE seal.snapshot_id = NEW.snapshot_id
)
BEGIN
    SELECT RAISE(ABORT, 'cannot add state snapshot dependencies after sealing');
END;

CREATE TRIGGER state_snapshot_inputs_reject_late_input
BEFORE INSERT ON state_snapshot_inputs
WHEN EXISTS (
    SELECT 1
    FROM state_snapshots snapshot
    WHERE snapshot.snapshot_id = NEW.snapshot_id
      AND NEW.available_at > snapshot.as_of
)
BEGIN
    SELECT RAISE(ABORT, 'state snapshot input cannot be available after snapshot as_of');
END;

CREATE TRIGGER state_snapshot_inputs_require_raw_provenance
BEFORE INSERT ON state_snapshot_inputs
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
    SELECT RAISE(ABORT, 'state raw provenance must match evidence observation/provider/checksum');
END;

CREATE TRIGGER state_snapshot_dependencies_require_parent
BEFORE INSERT ON state_snapshot_dependencies
WHEN NOT EXISTS (
        SELECT 1
        FROM state_snapshots parent
        JOIN state_snapshot_seals seal
          ON seal.snapshot_id = parent.snapshot_id
        JOIN state_snapshots child
          ON child.snapshot_id = NEW.snapshot_id
        WHERE parent.snapshot_id = NEW.parent_snapshot_id
          AND parent.as_of <= child.as_of
    )
BEGIN
    SELECT RAISE(ABORT, 'state dependency parent must be sealed and not later than child as_of');
END;

CREATE TRIGGER state_snapshot_dependencies_reject_cycle
BEFORE INSERT ON state_snapshot_dependencies
WHEN NEW.snapshot_id = NEW.parent_snapshot_id
 OR EXISTS (
    WITH RECURSIVE ancestors(snapshot_id) AS (
        SELECT parent_snapshot_id
        FROM state_snapshot_dependencies
        WHERE snapshot_id = NEW.parent_snapshot_id
        UNION
        SELECT dependency.parent_snapshot_id
        FROM state_snapshot_dependencies dependency
        JOIN ancestors
          ON dependency.snapshot_id = ancestors.snapshot_id
    )
    SELECT 1
    FROM ancestors
    WHERE snapshot_id = NEW.snapshot_id
)
BEGIN
    SELECT RAISE(ABORT, 'state snapshot dependency cycle is forbidden');
END;

CREATE TRIGGER state_snapshot_seals_require_complete_membership
BEFORE INSERT ON state_snapshot_seals
WHEN NOT EXISTS (
    SELECT 1
    FROM state_snapshots snapshot
    WHERE snapshot.snapshot_id = NEW.snapshot_id
      AND snapshot.pit_validation = 'PASS'
      AND snapshot.input_count = (
          SELECT COUNT(*)
          FROM state_snapshot_inputs input
          WHERE input.snapshot_id = NEW.snapshot_id
      )
      AND snapshot.dependency_count = (
          SELECT COUNT(*)
          FROM state_snapshot_dependencies dependency
          WHERE dependency.snapshot_id = NEW.snapshot_id
      )
      AND NOT EXISTS (
          SELECT 1
          FROM state_snapshot_inputs input
          WHERE input.snapshot_id = NEW.snapshot_id
            AND input.available_at > snapshot.as_of
      )
      AND NOT EXISTS (
          SELECT 1
          FROM state_snapshot_dependencies dependency
          LEFT JOIN state_snapshot_seals parent_seal
            ON parent_seal.snapshot_id = dependency.parent_snapshot_id
          LEFT JOIN state_snapshots parent
            ON parent.snapshot_id = dependency.parent_snapshot_id
          WHERE dependency.snapshot_id = NEW.snapshot_id
            AND (
                parent_seal.snapshot_id IS NULL
                OR parent.as_of > snapshot.as_of
            )
      )
)
BEGIN
    SELECT RAISE(ABORT, 'state snapshot cannot seal before exact validated membership is complete');
END;
"""
