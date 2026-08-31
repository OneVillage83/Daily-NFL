"""Forward-only family-specific persistence for M7-D F-7 player state.

Migration 10 stores append-only, PIT-addressable player-state evidence. It does
not duplicate the immutable state snapshot ledger introduced by migration 8.
"""

M7_PLAYER_SCHEMA_SQL = r"""
CREATE TABLE player_state_evidence_observations (
    observation_id TEXT PRIMARY KEY,
    player_id TEXT NOT NULL REFERENCES players(player_id),
    logical_key TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK (revision >= 1),
    team_season_id TEXT REFERENCES team_seasons(team_season_id),
    source_game_id TEXT REFERENCES games(game_id),
    position TEXT NOT NULL CHECK (
        position IN (
            'QB', 'RB', 'WR', 'TE', 'OT', 'OG', 'C', 'EDGE', 'DT', 'LB',
            'CB', 'S', 'K', 'P', 'RETURNER', 'OTHER', 'UNKNOWN'
        )
    ),
    evidence_kind TEXT NOT NULL CHECK (
        evidence_kind IN (
            'POSITION', 'TALENT', 'PERFORMANCE', 'ROLE', 'WORKLOAD',
            'POSITION_SPECIFIC'
        )
    ),
    metrics_json TEXT NOT NULL,
    metrics_sha256 TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL,
    sample_weight REAL NOT NULL CHECK (sample_weight > 0.0),
    source_confidence REAL NOT NULL CHECK (
        source_confidence >= 0.0 AND source_confidence <= 1.0
    ),
    evidence_contract TEXT NOT NULL,
    evidence_version TEXT NOT NULL,
    provider_id TEXT REFERENCES providers(provider_id),
    evidence_id TEXT REFERENCES raw_evidence(evidence_id),
    evidence_observation_id TEXT
        REFERENCES raw_evidence_observations(evidence_observation_id),
    effective_at TEXT,
    published_at TEXT,
    observed_at TEXT,
    ingested_at TEXT,
    available_at TEXT NOT NULL,
    availability_method TEXT NOT NULL,
    availability_confidence TEXT NOT NULL,
    provider_revision TEXT,
    provider_schema_version TEXT,
    parser_version TEXT,
    raw_sha256 TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE(player_id, logical_key, revision),
    CHECK (trim(observation_id) <> ''),
    CHECK (trim(player_id) <> ''),
    CHECK (trim(logical_key) <> ''),
    CHECK (trim(evidence_contract) <> ''),
    CHECK (trim(evidence_version) <> ''),
    CHECK (length(metrics_sha256) = 64),
    CHECK (length(payload_sha256) = 64)
);

CREATE INDEX idx_player_state_evidence_player_available
    ON player_state_evidence_observations(player_id, available_at);
CREATE INDEX idx_player_state_evidence_logical_revision
    ON player_state_evidence_observations(player_id, logical_key, revision);
CREATE INDEX idx_player_state_evidence_team_available
    ON player_state_evidence_observations(team_season_id, available_at);
CREATE INDEX idx_player_state_evidence_source_game
    ON player_state_evidence_observations(source_game_id, player_id);
CREATE INDEX idx_player_state_evidence_kind_available
    ON player_state_evidence_observations(player_id, evidence_kind, available_at);
CREATE INDEX idx_player_state_evidence_raw_observation
    ON player_state_evidence_observations(evidence_observation_id);

CREATE TRIGGER player_state_evidence_no_update
BEFORE UPDATE ON player_state_evidence_observations
BEGIN
    SELECT RAISE(ABORT, 'player_state_evidence_observations is append-only');
END;

CREATE TRIGGER player_state_evidence_no_delete
BEFORE DELETE ON player_state_evidence_observations
BEGIN
    SELECT RAISE(ABORT, 'player_state_evidence_observations is append-only');
END;

CREATE TRIGGER player_state_evidence_require_raw_provenance
BEFORE INSERT ON player_state_evidence_observations
WHEN (
    NEW.evidence_id IS NOT NULL
    OR NEW.evidence_observation_id IS NOT NULL
    OR NEW.raw_sha256 IS NOT NULL
)
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
    SELECT RAISE(ABORT, 'player state raw provenance must match evidence/provider/checksum');
END;
"""
