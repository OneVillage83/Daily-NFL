"""Schema remediation for M2 architecture conformance.

This migration is intentionally additive. Existing v1-v3 rows are preserved
without fabricating newly required canonical identities or historical clocks.
New writes are constrained to use the strengthened M1/F-5 identity model.
"""

M2_CONFORMANCE_SCHEMA_SQL = r"""
ALTER TABLE games ADD COLUMN competition_id TEXT;

ALTER TABLE schedule_observations ADD COLUMN actual_kickoff TEXT;
ALTER TABLE schedule_observations ADD COLUMN neutral_site INTEGER
    CHECK (neutral_site IS NULL OR neutral_site IN (0, 1));
ALTER TABLE schedule_observations ADD COLUMN schedule_version TEXT;

CREATE TABLE possession_segments (
    possession_segment_id TEXT PRIMARY KEY,
    game_id TEXT NOT NULL REFERENCES games(game_id),
    canonical_sequence INTEGER NOT NULL CHECK (canonical_sequence >= 1),
    offense_team_season_id TEXT NOT NULL REFERENCES team_seasons(team_season_id),
    defense_team_season_id TEXT NOT NULL REFERENCES team_seasons(team_season_id),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE(game_id, canonical_sequence),
    CHECK (offense_team_season_id <> defense_team_season_id)
);

ALTER TABLE drives ADD COLUMN possession_segment_id TEXT
    REFERENCES possession_segments(possession_segment_id);
ALTER TABLE plays ADD COLUMN possession_segment_id TEXT
    REFERENCES possession_segments(possession_segment_id);

CREATE INDEX idx_possession_segments_game_sequence
    ON possession_segments(game_id, canonical_sequence);
CREATE INDEX idx_drives_possession_segment
    ON drives(possession_segment_id);
CREATE INDEX idx_plays_possession_segment
    ON plays(possession_segment_id);

CREATE TABLE play_events (
    play_event_id TEXT PRIMARY KEY,
    play_id TEXT NOT NULL REFERENCES plays(play_id),
    canonical_sequence INTEGER NOT NULL CHECK (canonical_sequence >= 1),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE(play_id, canonical_sequence)
);

CREATE TABLE participations (
    participation_id TEXT PRIMARY KEY,
    play_id TEXT NOT NULL REFERENCES plays(play_id),
    canonical_sequence INTEGER NOT NULL CHECK (canonical_sequence >= 1),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE(play_id, canonical_sequence)
);

CREATE TABLE penalties (
    penalty_id TEXT PRIMARY KEY,
    play_id TEXT NOT NULL REFERENCES plays(play_id),
    canonical_sequence INTEGER NOT NULL CHECK (canonical_sequence >= 1),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE(play_id, canonical_sequence)
);

CREATE INDEX idx_play_events_play_sequence
    ON play_events(play_id, canonical_sequence);
CREATE INDEX idx_participations_play_sequence
    ON participations(play_id, canonical_sequence);
CREATE INDEX idx_penalties_play_sequence
    ON penalties(play_id, canonical_sequence);

ALTER TABLE participation_observations ADD COLUMN participation_id TEXT
    REFERENCES participations(participation_id);
ALTER TABLE participation_observations ADD COLUMN effective_at TEXT;
ALTER TABLE participation_observations ADD COLUMN published_at TEXT;
ALTER TABLE participation_observations ADD COLUMN provider_revision TEXT;

ALTER TABLE penalty_observations ADD COLUMN penalty_id TEXT
    REFERENCES penalties(penalty_id);
ALTER TABLE penalty_observations ADD COLUMN effective_at TEXT;
ALTER TABLE penalty_observations ADD COLUMN published_at TEXT;
ALTER TABLE penalty_observations ADD COLUMN provider_revision TEXT;

CREATE INDEX idx_participation_canonical_available
    ON participation_observations(participation_id, available_at);
CREATE INDEX idx_penalty_canonical_available
    ON penalty_observations(penalty_id, available_at);

ALTER TABLE game_results ADD COLUMN final_at TEXT;

CREATE TRIGGER games_require_competition_insert
BEFORE INSERT ON games
WHEN NEW.competition_id IS NULL OR trim(NEW.competition_id) = ''
BEGIN
    SELECT RAISE(ABORT, 'games require canonical competition_id');
END;

CREATE TRIGGER participation_observations_require_identity
BEFORE INSERT ON participation_observations
WHEN NEW.participation_id IS NULL OR trim(NEW.participation_id) = ''
BEGIN
    SELECT RAISE(ABORT, 'participation observations require participation_id');
END;

CREATE TRIGGER penalty_observations_require_identity
BEFORE INSERT ON penalty_observations
WHEN NEW.penalty_id IS NULL OR trim(NEW.penalty_id) = ''
BEGIN
    SELECT RAISE(ABORT, 'penalty observations require penalty_id');
END;

CREATE TRIGGER schema_migrations_no_update
BEFORE UPDATE ON schema_migrations
BEGIN
    SELECT RAISE(ABORT, 'schema_migrations is append-only');
END;
CREATE TRIGGER schema_migrations_no_delete
BEFORE DELETE ON schema_migrations
BEGIN
    SELECT RAISE(ABORT, 'schema_migrations is append-only');
END;

CREATE TRIGGER games_no_update
BEFORE UPDATE ON games
BEGIN
    SELECT RAISE(ABORT, 'games canonical identity is append-only');
END;
CREATE TRIGGER games_no_delete
BEFORE DELETE ON games
BEGIN
    SELECT RAISE(ABORT, 'games canonical identity is append-only');
END;

CREATE TRIGGER possession_segments_no_update
BEFORE UPDATE ON possession_segments
BEGIN
    SELECT RAISE(ABORT, 'possession_segments is append-only');
END;
CREATE TRIGGER possession_segments_no_delete
BEFORE DELETE ON possession_segments
BEGIN
    SELECT RAISE(ABORT, 'possession_segments is append-only');
END;

CREATE TRIGGER drives_no_update
BEFORE UPDATE ON drives
BEGIN
    SELECT RAISE(ABORT, 'drives canonical identity is append-only');
END;
CREATE TRIGGER drives_no_delete
BEFORE DELETE ON drives
BEGIN
    SELECT RAISE(ABORT, 'drives canonical identity is append-only');
END;

CREATE TRIGGER plays_no_update
BEFORE UPDATE ON plays
BEGIN
    SELECT RAISE(ABORT, 'plays canonical identity is append-only');
END;
CREATE TRIGGER plays_no_delete
BEFORE DELETE ON plays
BEGIN
    SELECT RAISE(ABORT, 'plays canonical identity is append-only');
END;

CREATE TRIGGER play_events_no_update
BEFORE UPDATE ON play_events
BEGIN
    SELECT RAISE(ABORT, 'play_events canonical identity is append-only');
END;
CREATE TRIGGER play_events_no_delete
BEFORE DELETE ON play_events
BEGIN
    SELECT RAISE(ABORT, 'play_events canonical identity is append-only');
END;

CREATE TRIGGER participations_no_update
BEFORE UPDATE ON participations
BEGIN
    SELECT RAISE(ABORT, 'participations canonical identity is append-only');
END;
CREATE TRIGGER participations_no_delete
BEFORE DELETE ON participations
BEGIN
    SELECT RAISE(ABORT, 'participations canonical identity is append-only');
END;

CREATE TRIGGER penalties_no_update
BEFORE UPDATE ON penalties
BEGIN
    SELECT RAISE(ABORT, 'penalties canonical identity is append-only');
END;
CREATE TRIGGER penalties_no_delete
BEFORE DELETE ON penalties
BEGIN
    SELECT RAISE(ABORT, 'penalties canonical identity is append-only');
END;
"""
