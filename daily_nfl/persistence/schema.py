"""SQLite schema for the Daily NFL canonical persistence layer."""

SCHEMA_VERSION = 1

INITIAL_SCHEMA_SQL = r"""
CREATE TABLE schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE providers (
    provider_id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    provider_type TEXT NOT NULL,
    provider_schema_version TEXT,
    parser_version TEXT,
    license_class TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE raw_evidence (
    evidence_id TEXT PRIMARY KEY,
    provider_id TEXT NOT NULL REFERENCES providers(provider_id),
    endpoint_category TEXT NOT NULL,
    source_uri TEXT,
    content_type TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    object_path TEXT NOT NULL,
    effective_at TEXT,
    published_at TEXT,
    observed_at TEXT,
    ingested_at TEXT NOT NULL,
    available_at TEXT NOT NULL,
    availability_method TEXT NOT NULL,
    availability_confidence TEXT NOT NULL,
    provider_schema_version TEXT,
    parser_version TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE(provider_id, endpoint_category, sha256)
);

CREATE INDEX idx_raw_evidence_available_at
    ON raw_evidence(available_at);
CREATE INDEX idx_raw_evidence_provider
    ON raw_evidence(provider_id, endpoint_category);

CREATE TABLE franchises (
    franchise_id TEXT PRIMARY KEY,
    canonical_name TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE team_seasons (
    team_season_id TEXT PRIMARY KEY,
    franchise_id TEXT NOT NULL REFERENCES franchises(franchise_id),
    season INTEGER NOT NULL CHECK (season >= 1920),
    display_name TEXT,
    UNIQUE(franchise_id, season)
);

CREATE TABLE persons (
    person_id TEXT PRIMARY KEY,
    canonical_name TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE players (
    player_id TEXT PRIMARY KEY,
    person_id TEXT NOT NULL REFERENCES persons(person_id),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE(person_id)
);

CREATE TABLE entity_crosswalk (
    crosswalk_id INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_entity_type TEXT NOT NULL,
    canonical_entity_id TEXT NOT NULL,
    provider_id TEXT NOT NULL REFERENCES providers(provider_id),
    provider_entity_type TEXT NOT NULL,
    external_id TEXT NOT NULL,
    valid_from TEXT,
    valid_to TEXT,
    match_method TEXT NOT NULL,
    match_confidence REAL NOT NULL CHECK (match_confidence >= 0.0 AND match_confidence <= 1.0),
    verified INTEGER NOT NULL DEFAULT 0 CHECK (verified IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE UNIQUE INDEX uq_crosswalk_external_valid_from
    ON entity_crosswalk(
        provider_id,
        provider_entity_type,
        external_id,
        COALESCE(valid_from, '')
    );
CREATE INDEX idx_crosswalk_canonical
    ON entity_crosswalk(canonical_entity_type, canonical_entity_id);
CREATE INDEX idx_crosswalk_external
    ON entity_crosswalk(provider_id, provider_entity_type, external_id);

CREATE TABLE games (
    game_id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL UNIQUE,
    season INTEGER NOT NULL CHECK (season >= 1920),
    season_phase TEXT NOT NULL,
    week INTEGER,
    ruleset_version TEXT NOT NULL,
    home_team_season_id TEXT NOT NULL REFERENCES team_seasons(team_season_id),
    away_team_season_id TEXT NOT NULL REFERENCES team_seasons(team_season_id),
    venue_id TEXT,
    scheduled_kickoff TEXT NOT NULL,
    neutral_site INTEGER NOT NULL DEFAULT 0 CHECK (neutral_site IN (0, 1)),
    CHECK (home_team_season_id <> away_team_season_id)
);

CREATE INDEX idx_games_kickoff ON games(scheduled_kickoff);
CREATE INDEX idx_games_season_week ON games(season, season_phase, week);

CREATE TABLE schedule_observations (
    observation_id TEXT PRIMARY KEY,
    game_id TEXT NOT NULL REFERENCES games(game_id),
    evidence_id TEXT REFERENCES raw_evidence(evidence_id),
    provider_id TEXT NOT NULL REFERENCES providers(provider_id),
    provider_game_id TEXT,
    status TEXT NOT NULL,
    scheduled_kickoff TEXT NOT NULL,
    venue_id TEXT,
    effective_at TEXT,
    published_at TEXT,
    observed_at TEXT,
    ingested_at TEXT NOT NULL,
    available_at TEXT NOT NULL,
    availability_method TEXT NOT NULL,
    availability_confidence TEXT NOT NULL,
    provider_revision TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX idx_schedule_obs_game_available
    ON schedule_observations(game_id, available_at);

CREATE TABLE possessions (
    possession_id TEXT PRIMARY KEY,
    game_id TEXT NOT NULL REFERENCES games(game_id),
    offense_team_season_id TEXT NOT NULL REFERENCES team_seasons(team_season_id),
    defense_team_season_id TEXT NOT NULL REFERENCES team_seasons(team_season_id),
    CHECK (offense_team_season_id <> defense_team_season_id)
);

CREATE TABLE drives (
    drive_id TEXT PRIMARY KEY,
    game_id TEXT NOT NULL REFERENCES games(game_id),
    possession_id TEXT REFERENCES possessions(possession_id),
    canonical_sequence INTEGER,
    UNIQUE(game_id, canonical_sequence)
);

CREATE TABLE plays (
    play_id TEXT PRIMARY KEY,
    game_id TEXT NOT NULL REFERENCES games(game_id),
    drive_id TEXT REFERENCES drives(drive_id),
    possession_id TEXT REFERENCES possessions(possession_id),
    canonical_sequence INTEGER,
    UNIQUE(game_id, canonical_sequence)
);

CREATE INDEX idx_plays_game_sequence ON plays(game_id, canonical_sequence);

CREATE TABLE play_observations (
    observation_id TEXT PRIMARY KEY,
    play_id TEXT NOT NULL REFERENCES plays(play_id),
    evidence_id TEXT REFERENCES raw_evidence(evidence_id),
    provider_id TEXT NOT NULL REFERENCES providers(provider_id),
    provider_play_id TEXT,
    provider_revision TEXT,
    normalized_payload_json TEXT NOT NULL,
    normalized_sha256 TEXT NOT NULL,
    effective_at TEXT,
    published_at TEXT,
    observed_at TEXT,
    ingested_at TEXT NOT NULL,
    available_at TEXT NOT NULL,
    availability_method TEXT NOT NULL,
    availability_confidence TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX idx_play_obs_play_available
    ON play_observations(play_id, available_at);

CREATE TABLE participation_observations (
    observation_id TEXT PRIMARY KEY,
    play_id TEXT NOT NULL REFERENCES plays(play_id),
    player_id TEXT NOT NULL REFERENCES players(player_id),
    team_season_id TEXT NOT NULL REFERENCES team_seasons(team_season_id),
    evidence_id TEXT REFERENCES raw_evidence(evidence_id),
    provider_id TEXT NOT NULL REFERENCES providers(provider_id),
    side TEXT NOT NULL,
    role TEXT NOT NULL,
    on_field INTEGER NOT NULL DEFAULT 1 CHECK (on_field IN (0, 1)),
    observed_at TEXT,
    ingested_at TEXT NOT NULL,
    available_at TEXT NOT NULL,
    availability_method TEXT NOT NULL,
    availability_confidence TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX idx_participation_play
    ON participation_observations(play_id);
CREATE INDEX idx_participation_player
    ON participation_observations(player_id, available_at);

CREATE TABLE penalty_observations (
    observation_id TEXT PRIMARY KEY,
    play_id TEXT NOT NULL REFERENCES plays(play_id),
    team_season_id TEXT NOT NULL REFERENCES team_seasons(team_season_id),
    player_id TEXT REFERENCES players(player_id),
    evidence_id TEXT REFERENCES raw_evidence(evidence_id),
    provider_id TEXT NOT NULL REFERENCES providers(provider_id),
    penalty_type TEXT NOT NULL,
    disposition TEXT NOT NULL,
    yards INTEGER,
    automatic_first_down INTEGER NOT NULL DEFAULT 0 CHECK (automatic_first_down IN (0, 1)),
    loss_of_down INTEGER NOT NULL DEFAULT 0 CHECK (loss_of_down IN (0, 1)),
    nullifies_play INTEGER NOT NULL DEFAULT 0 CHECK (nullifies_play IN (0, 1)),
    enforcement_spot TEXT,
    observed_at TEXT,
    ingested_at TEXT NOT NULL,
    available_at TEXT NOT NULL,
    availability_method TEXT NOT NULL,
    availability_confidence TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    CHECK (yards IS NULL OR yards >= 0)
);

CREATE INDEX idx_penalty_play ON penalty_observations(play_id);

CREATE TABLE game_result_observations (
    result_observation_id TEXT PRIMARY KEY,
    game_id TEXT NOT NULL REFERENCES games(game_id),
    evidence_id TEXT REFERENCES raw_evidence(evidence_id),
    provider_id TEXT NOT NULL REFERENCES providers(provider_id),
    provider_revision TEXT,
    home_points_final INTEGER NOT NULL CHECK (home_points_final >= 0),
    away_points_final INTEGER NOT NULL CHECK (away_points_final >= 0),
    overtime INTEGER NOT NULL DEFAULT 0 CHECK (overtime IN (0, 1)),
    finalized INTEGER NOT NULL DEFAULT 1 CHECK (finalized IN (0, 1)),
    effective_at TEXT,
    published_at TEXT,
    observed_at TEXT,
    ingested_at TEXT NOT NULL,
    available_at TEXT NOT NULL,
    availability_method TEXT NOT NULL,
    availability_confidence TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX idx_result_obs_game_provider
    ON game_result_observations(game_id, provider_id, available_at);

CREATE TABLE game_results (
    result_id TEXT PRIMARY KEY,
    game_id TEXT NOT NULL REFERENCES games(game_id),
    revision INTEGER NOT NULL CHECK (revision >= 1),
    home_points_final INTEGER NOT NULL CHECK (home_points_final >= 0),
    away_points_final INTEGER NOT NULL CHECK (away_points_final >= 0),
    overtime INTEGER NOT NULL DEFAULT 0 CHECK (overtime IN (0, 1)),
    finalized INTEGER NOT NULL DEFAULT 1 CHECK (finalized IN (0, 1)),
    reconciliation_method TEXT NOT NULL,
    reconciliation_confidence REAL NOT NULL
        CHECK (reconciliation_confidence >= 0.0 AND reconciliation_confidence <= 1.0),
    derived_at TEXT NOT NULL,
    available_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE(game_id, revision)
);

CREATE TABLE game_result_sources (
    result_id TEXT NOT NULL REFERENCES game_results(result_id),
    result_observation_id TEXT NOT NULL
        REFERENCES game_result_observations(result_observation_id),
    PRIMARY KEY(result_id, result_observation_id)
);

CREATE INDEX idx_game_results_game_revision
    ON game_results(game_id, revision);
CREATE INDEX idx_game_result_sources_observation
    ON game_result_sources(result_observation_id);

CREATE VIEW current_game_results AS
SELECT gr.*
FROM game_results gr
JOIN (
    SELECT game_id, MAX(revision) AS revision
    FROM game_results
    WHERE finalized = 1
    GROUP BY game_id
) latest
  ON latest.game_id = gr.game_id
 AND latest.revision = gr.revision
WHERE gr.finalized = 1;

CREATE TRIGGER raw_evidence_no_update
BEFORE UPDATE ON raw_evidence
BEGIN
    SELECT RAISE(ABORT, 'raw_evidence is append-only');
END;
CREATE TRIGGER raw_evidence_no_delete
BEFORE DELETE ON raw_evidence
BEGIN
    SELECT RAISE(ABORT, 'raw_evidence is append-only');
END;

CREATE TRIGGER schedule_observations_no_update
BEFORE UPDATE ON schedule_observations
BEGIN
    SELECT RAISE(ABORT, 'schedule_observations is append-only');
END;
CREATE TRIGGER schedule_observations_no_delete
BEFORE DELETE ON schedule_observations
BEGIN
    SELECT RAISE(ABORT, 'schedule_observations is append-only');
END;

CREATE TRIGGER play_observations_no_update
BEFORE UPDATE ON play_observations
BEGIN
    SELECT RAISE(ABORT, 'play_observations is append-only');
END;
CREATE TRIGGER play_observations_no_delete
BEFORE DELETE ON play_observations
BEGIN
    SELECT RAISE(ABORT, 'play_observations is append-only');
END;

CREATE TRIGGER participation_observations_no_update
BEFORE UPDATE ON participation_observations
BEGIN
    SELECT RAISE(ABORT, 'participation_observations is append-only');
END;
CREATE TRIGGER participation_observations_no_delete
BEFORE DELETE ON participation_observations
BEGIN
    SELECT RAISE(ABORT, 'participation_observations is append-only');
END;

CREATE TRIGGER penalty_observations_no_update
BEFORE UPDATE ON penalty_observations
BEGIN
    SELECT RAISE(ABORT, 'penalty_observations is append-only');
END;
CREATE TRIGGER penalty_observations_no_delete
BEFORE DELETE ON penalty_observations
BEGIN
    SELECT RAISE(ABORT, 'penalty_observations is append-only');
END;

CREATE TRIGGER game_result_observations_no_update
BEFORE UPDATE ON game_result_observations
BEGIN
    SELECT RAISE(ABORT, 'game_result_observations is append-only');
END;
CREATE TRIGGER game_result_observations_no_delete
BEFORE DELETE ON game_result_observations
BEGIN
    SELECT RAISE(ABORT, 'game_result_observations is append-only');
END;

CREATE TRIGGER game_results_no_update
BEFORE UPDATE ON game_results
BEGIN
    SELECT RAISE(ABORT, 'game_results is append-only');
END;
CREATE TRIGGER game_results_no_delete
BEFORE DELETE ON game_results
BEGIN
    SELECT RAISE(ABORT, 'game_results is append-only');
END;

CREATE TRIGGER game_result_sources_no_update
BEFORE UPDATE ON game_result_sources
BEGIN
    SELECT RAISE(ABORT, 'game_result_sources is append-only');
END;
CREATE TRIGGER game_result_sources_no_delete
BEFORE DELETE ON game_result_sources
BEGIN
    SELECT RAISE(ABORT, 'game_result_sources is append-only');
END;
"""
