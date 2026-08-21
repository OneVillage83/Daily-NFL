"""Schema additions for immutable M5 point-in-time snapshots."""

PIT_SNAPSHOT_SCHEMA_SQL = r"""
CREATE TABLE pit_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    game_id TEXT NOT NULL REFERENCES games(game_id),
    prediction_time TEXT NOT NULL,
    kickoff TEXT NOT NULL,
    horizon TEXT,
    policy_version TEXT NOT NULL,
    manifest_sha256 TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX idx_pit_snapshots_game_cutoff
    ON pit_snapshots(game_id, prediction_time);

CREATE TABLE pit_snapshot_inputs (
    snapshot_id TEXT NOT NULL REFERENCES pit_snapshots(snapshot_id),
    input_kind TEXT NOT NULL,
    input_id TEXT NOT NULL,
    source_table TEXT NOT NULL,
    evidence_id TEXT REFERENCES raw_evidence(evidence_id),
    subject_game_id TEXT REFERENCES games(game_id),
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
    PRIMARY KEY(snapshot_id, input_kind, input_id)
);

CREATE TABLE pit_snapshot_seals (
    snapshot_id TEXT PRIMARY KEY REFERENCES pit_snapshots(snapshot_id),
    sealed_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX idx_pit_snapshot_inputs_available
    ON pit_snapshot_inputs(snapshot_id, available_at);
CREATE INDEX idx_pit_snapshot_inputs_evidence
    ON pit_snapshot_inputs(evidence_id);

CREATE TRIGGER pit_snapshot_inputs_require_unsealed
BEFORE INSERT ON pit_snapshot_inputs
WHEN EXISTS (
    SELECT 1 FROM pit_snapshot_seals seal
    WHERE seal.snapshot_id = NEW.snapshot_id
)
BEGIN
    SELECT RAISE(ABORT, 'sealed PIT snapshot membership cannot change');
END;

CREATE TRIGGER pit_snapshots_no_update
BEFORE UPDATE ON pit_snapshots
BEGIN
    SELECT RAISE(ABORT, 'pit_snapshots is append-only');
END;
CREATE TRIGGER pit_snapshots_no_delete
BEFORE DELETE ON pit_snapshots
BEGIN
    SELECT RAISE(ABORT, 'pit_snapshots is append-only');
END;

CREATE TRIGGER pit_snapshot_inputs_no_update
BEFORE UPDATE ON pit_snapshot_inputs
BEGIN
    SELECT RAISE(ABORT, 'pit_snapshot_inputs is append-only');
END;
CREATE TRIGGER pit_snapshot_inputs_no_delete
BEFORE DELETE ON pit_snapshot_inputs
BEGIN
    SELECT RAISE(ABORT, 'pit_snapshot_inputs is append-only');
END;

CREATE TRIGGER pit_snapshot_seals_no_update
BEFORE UPDATE ON pit_snapshot_seals
BEGIN
    SELECT RAISE(ABORT, 'pit_snapshot_seals is append-only');
END;
CREATE TRIGGER pit_snapshot_seals_no_delete
BEFORE DELETE ON pit_snapshot_seals
BEGIN
    SELECT RAISE(ABORT, 'pit_snapshot_seals is append-only');
END;
"""
