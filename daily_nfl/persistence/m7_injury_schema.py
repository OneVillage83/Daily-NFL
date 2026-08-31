"""Forward-only family-specific persistence for M7-C F-10 injury state.

Migration 9 is intentionally separate from the already-applied M7-B migration 8.
"""

M7_INJURY_SCHEMA_SQL = r"""
CREATE TABLE injury_observations (
    injury_observation_id TEXT PRIMARY KEY,
    player_id TEXT NOT NULL REFERENCES players(player_id),
    team_season_id TEXT NOT NULL REFERENCES team_seasons(team_season_id),
    game_id TEXT REFERENCES games(game_id),
    provider_id TEXT NOT NULL REFERENCES providers(provider_id),
    source_id TEXT NOT NULL,
    reported_body_region TEXT,
    reported_injury_description TEXT,
    practice_status TEXT NOT NULL CHECK (
        practice_status IN ('DID_NOT_PARTICIPATE', 'LIMITED', 'FULL', 'UNKNOWN')
    ),
    game_status TEXT NOT NULL CHECK (
        game_status IN ('OUT', 'DOUBTFUL', 'QUESTIONABLE', 'NO_DESIGNATION', 'UNKNOWN')
    ),
    active_status TEXT NOT NULL CHECK (
        active_status IN ('ACTIVE', 'INACTIVE', 'UNKNOWN')
    ),
    source_text TEXT,
    source_confidence REAL CHECK (
        source_confidence IS NULL OR (source_confidence >= 0.0 AND source_confidence <= 1.0)
    ),
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
    CHECK (trim(injury_observation_id) <> ''),
    CHECK (trim(player_id) <> ''),
    CHECK (trim(team_season_id) <> ''),
    CHECK (trim(provider_id) <> ''),
    CHECK (trim(source_id) <> '')
);

CREATE INDEX idx_injury_observations_player_available
    ON injury_observations(player_id, available_at);
CREATE INDEX idx_injury_observations_team_available
    ON injury_observations(team_season_id, available_at);
CREATE INDEX idx_injury_observations_game_available
    ON injury_observations(game_id, available_at);
CREATE INDEX idx_injury_observations_evidence_observation
    ON injury_observations(evidence_observation_id);

CREATE TABLE injury_episodes (
    injury_episode_id TEXT PRIMARY KEY,
    player_id TEXT NOT NULL REFERENCES players(player_id),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    CHECK (trim(injury_episode_id) <> '')
);

CREATE INDEX idx_injury_episodes_player
    ON injury_episodes(player_id, injury_episode_id);

CREATE TABLE injury_episode_revisions (
    injury_episode_id TEXT NOT NULL REFERENCES injury_episodes(injury_episode_id),
    revision INTEGER NOT NULL CHECK (revision >= 1),
    as_of TEXT NOT NULL,
    body_region TEXT,
    laterality TEXT NOT NULL CHECK (
        laterality IN ('LEFT', 'RIGHT', 'BILATERAL', 'MIDLINE', 'UNKNOWN')
    ),
    injury_family TEXT,
    episode_start TEXT,
    episode_end TEXT,
    first_observed_at TEXT,
    source_description TEXT,
    recurrence_flag INTEGER CHECK (recurrence_flag IS NULL OR recurrence_flag IN (0, 1)),
    related_prior_episode_id TEXT REFERENCES injury_episodes(injury_episode_id),
    resolution_state TEXT NOT NULL CHECK (
        resolution_state IN ('OPEN', 'RESOLVED', 'UNKNOWN')
    ),
    confidence REAL NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    observation_count INTEGER NOT NULL CHECK (observation_count >= 0),
    created_at TEXT NOT NULL,
    PRIMARY KEY(injury_episode_id, revision),
    CHECK (
        related_prior_episode_id IS NULL
        OR related_prior_episode_id <> injury_episode_id
    )
);

CREATE INDEX idx_injury_episode_revisions_asof
    ON injury_episode_revisions(injury_episode_id, as_of, revision);

CREATE TABLE injury_episode_revision_observations (
    injury_episode_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    injury_observation_id TEXT NOT NULL
        REFERENCES injury_observations(injury_observation_id),
    PRIMARY KEY(injury_episode_id, revision, injury_observation_id),
    FOREIGN KEY(injury_episode_id, revision)
        REFERENCES injury_episode_revisions(injury_episode_id, revision)
);

CREATE INDEX idx_injury_episode_revision_observations_observation
    ON injury_episode_revision_observations(injury_observation_id);

CREATE TABLE injury_episode_revision_seals (
    injury_episode_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    sealed_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    PRIMARY KEY(injury_episode_id, revision),
    FOREIGN KEY(injury_episode_id, revision)
        REFERENCES injury_episode_revisions(injury_episode_id, revision)
);

CREATE TRIGGER injury_observations_no_update
BEFORE UPDATE ON injury_observations
BEGIN
    SELECT RAISE(ABORT, 'injury_observations is append-only');
END;
CREATE TRIGGER injury_observations_no_delete
BEFORE DELETE ON injury_observations
BEGIN
    SELECT RAISE(ABORT, 'injury_observations is append-only');
END;

CREATE TRIGGER injury_observations_require_raw_provenance
BEFORE INSERT ON injury_observations
WHEN (
    NEW.evidence_id IS NOT NULL
    OR NEW.evidence_observation_id IS NOT NULL
    OR NEW.raw_sha256 IS NOT NULL
)
 AND (
    NEW.evidence_id IS NULL
    OR NEW.evidence_observation_id IS NULL
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
    SELECT RAISE(ABORT, 'injury raw provenance must match evidence observation/provider/checksum');
END;

CREATE TRIGGER injury_episodes_no_update
BEFORE UPDATE ON injury_episodes
BEGIN
    SELECT RAISE(ABORT, 'injury_episodes is append-only');
END;
CREATE TRIGGER injury_episodes_no_delete
BEFORE DELETE ON injury_episodes
BEGIN
    SELECT RAISE(ABORT, 'injury_episodes is append-only');
END;

CREATE TRIGGER injury_episode_revisions_no_update
BEFORE UPDATE ON injury_episode_revisions
BEGIN
    SELECT RAISE(ABORT, 'injury_episode_revisions is append-only');
END;
CREATE TRIGGER injury_episode_revisions_no_delete
BEFORE DELETE ON injury_episode_revisions
BEGIN
    SELECT RAISE(ABORT, 'injury_episode_revisions is append-only');
END;

CREATE TRIGGER injury_episode_revision_observations_no_update
BEFORE UPDATE ON injury_episode_revision_observations
BEGIN
    SELECT RAISE(ABORT, 'injury_episode_revision_observations is append-only');
END;
CREATE TRIGGER injury_episode_revision_observations_no_delete
BEFORE DELETE ON injury_episode_revision_observations
BEGIN
    SELECT RAISE(ABORT, 'injury_episode_revision_observations is append-only');
END;

CREATE TRIGGER injury_episode_revision_seals_no_update
BEFORE UPDATE ON injury_episode_revision_seals
BEGIN
    SELECT RAISE(ABORT, 'injury_episode_revision_seals is append-only');
END;
CREATE TRIGGER injury_episode_revision_seals_no_delete
BEFORE DELETE ON injury_episode_revision_seals
BEGIN
    SELECT RAISE(ABORT, 'injury_episode_revision_seals is append-only');
END;

CREATE TRIGGER injury_episode_revision_observations_reject_after_seal
BEFORE INSERT ON injury_episode_revision_observations
WHEN EXISTS (
    SELECT 1
    FROM injury_episode_revision_seals seal
    WHERE seal.injury_episode_id = NEW.injury_episode_id
      AND seal.revision = NEW.revision
)
BEGIN
    SELECT RAISE(ABORT, 'cannot add injury episode observations after sealing');
END;

CREATE TRIGGER injury_episode_revision_seals_require_exact_membership
BEFORE INSERT ON injury_episode_revision_seals
WHEN NOT EXISTS (
    SELECT 1
    FROM injury_episode_revisions revision
    JOIN injury_episodes episode
      ON episode.injury_episode_id = revision.injury_episode_id
    WHERE revision.injury_episode_id = NEW.injury_episode_id
      AND revision.revision = NEW.revision
      AND revision.observation_count = (
          SELECT COUNT(*)
          FROM injury_episode_revision_observations member
          WHERE member.injury_episode_id = NEW.injury_episode_id
            AND member.revision = NEW.revision
      )
      AND NOT EXISTS (
          SELECT 1
          FROM injury_episode_revision_observations member
          JOIN injury_observations observation
            ON observation.injury_observation_id = member.injury_observation_id
          WHERE member.injury_episode_id = NEW.injury_episode_id
            AND member.revision = NEW.revision
            AND (
                observation.player_id <> episode.player_id
                OR observation.available_at > revision.as_of
            )
      )
)
BEGIN
    SELECT RAISE(
        ABORT,
        'injury episode revision cannot seal before exact PIT-safe membership is complete'
    );
END;
"""
