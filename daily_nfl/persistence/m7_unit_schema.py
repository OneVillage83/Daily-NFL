"""Forward-only persistence for M7-E F-8 Unit State evidence.

Migration 11 stores append-only probabilistic unit-configuration priors and
unit-level evidence. Immutable Unit State snapshots themselves continue to use
the generic state ledger introduced by migration 8.
"""

M7_UNIT_SCHEMA_SQL = r"""
CREATE TABLE unit_configuration_observations (
    observation_id TEXT PRIMARY KEY,
    team_season_id TEXT NOT NULL REFERENCES team_seasons(team_season_id),
    game_id TEXT NOT NULL REFERENCES games(game_id),
    unit_type TEXT NOT NULL CHECK (
        unit_type IN (
            'QB_ROOM', 'OFFENSIVE_LINE', 'RECEIVING', 'BACKFIELD',
            'PASS_PROTECTION', 'RUN_BLOCKING', 'DEFENSIVE_FRONT',
            'PASS_RUSH', 'RUN_DEFENSE', 'LINEBACKER', 'COVERAGE',
            'SECONDARY', 'FIELD_GOAL', 'PUNT', 'PUNT_COVERAGE',
            'KICKOFF', 'KICK_COVERAGE', 'PUNT_RETURN', 'KICK_RETURN'
        )
    ),
    logical_key TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK (revision >= 1),
    distribution_json TEXT NOT NULL,
    distribution_sha256 TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL,
    configuration_contract TEXT NOT NULL,
    configuration_version TEXT NOT NULL,
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
    UNIQUE(team_season_id, game_id, unit_type, logical_key, revision),
    CHECK (trim(observation_id) <> ''),
    CHECK (trim(logical_key) <> ''),
    CHECK (trim(configuration_contract) <> ''),
    CHECK (trim(configuration_version) <> ''),
    CHECK (length(distribution_sha256) = 64),
    CHECK (length(payload_sha256) = 64)
);

CREATE INDEX idx_unit_configuration_lookup
    ON unit_configuration_observations(
        team_season_id, game_id, unit_type, available_at
    );
CREATE INDEX idx_unit_configuration_revision
    ON unit_configuration_observations(
        team_season_id, game_id, unit_type, logical_key, revision
    );
CREATE INDEX idx_unit_configuration_raw_observation
    ON unit_configuration_observations(evidence_observation_id);

CREATE TABLE unit_state_evidence_observations (
    observation_id TEXT PRIMARY KEY,
    team_season_id TEXT NOT NULL REFERENCES team_seasons(team_season_id),
    source_game_id TEXT REFERENCES games(game_id),
    unit_type TEXT NOT NULL CHECK (
        unit_type IN (
            'QB_ROOM', 'OFFENSIVE_LINE', 'RECEIVING', 'BACKFIELD',
            'PASS_PROTECTION', 'RUN_BLOCKING', 'DEFENSIVE_FRONT',
            'PASS_RUSH', 'RUN_DEFENSE', 'LINEBACKER', 'COVERAGE',
            'SECONDARY', 'FIELD_GOAL', 'PUNT', 'PUNT_COVERAGE',
            'KICKOFF', 'KICK_COVERAGE', 'PUNT_RETURN', 'KICK_RETURN'
        )
    ),
    logical_key TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK (revision >= 1),
    evidence_kind TEXT NOT NULL CHECK (
        evidence_kind IN (
            'CONTINUITY', 'EXPERIENCE_TOGETHER', 'ROLE_COMPATIBILITY',
            'SYNERGY', 'RECENT_PERFORMANCE'
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
    UNIQUE(team_season_id, unit_type, logical_key, revision),
    CHECK (trim(observation_id) <> ''),
    CHECK (trim(logical_key) <> ''),
    CHECK (trim(evidence_contract) <> ''),
    CHECK (trim(evidence_version) <> ''),
    CHECK (length(metrics_sha256) = 64),
    CHECK (length(payload_sha256) = 64)
);

CREATE INDEX idx_unit_state_evidence_lookup
    ON unit_state_evidence_observations(
        team_season_id, unit_type, available_at
    );
CREATE INDEX idx_unit_state_evidence_revision
    ON unit_state_evidence_observations(
        team_season_id, unit_type, logical_key, revision
    );
CREATE INDEX idx_unit_state_evidence_source_game
    ON unit_state_evidence_observations(source_game_id, unit_type);
CREATE INDEX idx_unit_state_evidence_raw_observation
    ON unit_state_evidence_observations(evidence_observation_id);

CREATE TRIGGER unit_configuration_observations_no_update
BEFORE UPDATE ON unit_configuration_observations
BEGIN
    SELECT RAISE(ABORT, 'unit_configuration_observations is append-only');
END;

CREATE TRIGGER unit_configuration_observations_no_delete
BEFORE DELETE ON unit_configuration_observations
BEGIN
    SELECT RAISE(ABORT, 'unit_configuration_observations is append-only');
END;

CREATE TRIGGER unit_state_evidence_no_update
BEFORE UPDATE ON unit_state_evidence_observations
BEGIN
    SELECT RAISE(ABORT, 'unit_state_evidence_observations is append-only');
END;

CREATE TRIGGER unit_state_evidence_no_delete
BEFORE DELETE ON unit_state_evidence_observations
BEGIN
    SELECT RAISE(ABORT, 'unit_state_evidence_observations is append-only');
END;

CREATE TRIGGER unit_configuration_require_raw_provenance
BEFORE INSERT ON unit_configuration_observations
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
    SELECT RAISE(
        ABORT,
        'unit configuration raw provenance must match evidence/provider/checksum'
    );
END;

CREATE TRIGGER unit_state_evidence_require_raw_provenance
BEFORE INSERT ON unit_state_evidence_observations
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
    SELECT RAISE(
        ABORT,
        'unit state raw provenance must match evidence/provider/checksum'
    );
END;
"""
