"""Forward-only persistence for M7-F F-9 Coaching & Scheme State evidence.

Migration 12 stores canonical coaching-stint identity plus append-only staff,
empirical scheme, and public-label observations. Immutable Coaching State
snapshots themselves continue to use the generic state ledger from migration 8.
"""

M7_COACHING_SCHEMA_SQL = r"""
CREATE TABLE coaching_stints (
    coaching_stint_id TEXT PRIMARY KEY,
    person_id TEXT NOT NULL REFERENCES persons(person_id),
    team_season_id TEXT NOT NULL REFERENCES team_seasons(team_season_id),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    CHECK (trim(coaching_stint_id) <> '')
);

CREATE INDEX idx_coaching_stints_person_team
    ON coaching_stints(person_id, team_season_id);

CREATE TABLE coaching_assignment_observations (
    observation_id TEXT PRIMARY KEY,
    coaching_stint_id TEXT NOT NULL REFERENCES coaching_stints(coaching_stint_id),
    person_id TEXT NOT NULL REFERENCES persons(person_id),
    team_season_id TEXT NOT NULL REFERENCES team_seasons(team_season_id),
    logical_key TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK (revision >= 1),
    role_type TEXT NOT NULL CHECK (
        role_type IN (
            'HEAD_COACH', 'OFFENSIVE_COORDINATOR', 'DEFENSIVE_COORDINATOR',
            'SPECIAL_TEAMS_COORDINATOR', 'QB_COACH', 'OL_COACH', 'RB_COACH',
            'WR_COACH', 'TE_COACH', 'DL_COACH', 'LB_COACH', 'DB_COACH',
            'OTHER'
        )
    ),
    responsibilities_json TEXT NOT NULL,
    responsibilities_sha256 TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL,
    effective_from TEXT,
    effective_to TEXT,
    assignment_contract TEXT NOT NULL,
    assignment_version TEXT NOT NULL,
    provider_id TEXT REFERENCES providers(provider_id),
    evidence_id TEXT REFERENCES raw_evidence(evidence_id),
    evidence_observation_id TEXT
        REFERENCES raw_evidence_observations(evidence_observation_id),
    knowledge_effective_at TEXT,
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
    UNIQUE(team_season_id, logical_key, revision),
    CHECK (trim(observation_id) <> ''),
    CHECK (trim(logical_key) <> ''),
    CHECK (trim(assignment_contract) <> ''),
    CHECK (trim(assignment_version) <> ''),
    CHECK (length(responsibilities_sha256) = 64),
    CHECK (length(payload_sha256) = 64),
    CHECK (
        effective_from IS NULL
        OR effective_to IS NULL
        OR effective_to >= effective_from
    )
);

CREATE INDEX idx_coaching_assignment_lookup
    ON coaching_assignment_observations(
        team_season_id, logical_key, available_at, revision
    );
CREATE INDEX idx_coaching_assignment_stint
    ON coaching_assignment_observations(coaching_stint_id, available_at);
CREATE INDEX idx_coaching_assignment_raw_observation
    ON coaching_assignment_observations(evidence_observation_id);

CREATE TABLE coaching_scheme_evidence_observations (
    observation_id TEXT PRIMARY KEY,
    team_season_id TEXT NOT NULL REFERENCES team_seasons(team_season_id),
    source_game_id TEXT REFERENCES games(game_id),
    applies_to_game_id TEXT REFERENCES games(game_id),
    logical_key TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK (revision >= 1),
    component TEXT NOT NULL CHECK (
        component IN (
            'OFFENSIVE_SCHEME', 'DEFENSIVE_SCHEME', 'SPECIAL_TEAMS_SCHEME',
            'DECISION_POLICY', 'ADAPTATION', 'COACHING_EFFECTIVENESS'
        )
    ),
    evidence_scope TEXT NOT NULL CHECK (
        evidence_scope IN ('BASE', 'GAME_SPECIFIC_DEVIATION')
    ),
    game_state_conditioned INTEGER NOT NULL
        CHECK (game_state_conditioned IN (0, 1)),
    conditioning_json TEXT NOT NULL,
    conditioning_sha256 TEXT NOT NULL,
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
    UNIQUE(team_season_id, logical_key, revision),
    CHECK (trim(observation_id) <> ''),
    CHECK (trim(logical_key) <> ''),
    CHECK (trim(evidence_contract) <> ''),
    CHECK (trim(evidence_version) <> ''),
    CHECK (length(conditioning_sha256) = 64),
    CHECK (length(metrics_sha256) = 64),
    CHECK (length(payload_sha256) = 64),
    CHECK (
        evidence_scope <> 'GAME_SPECIFIC_DEVIATION'
        OR (
            applies_to_game_id IS NOT NULL
            AND component IN (
                'OFFENSIVE_SCHEME', 'DEFENSIVE_SCHEME',
                'SPECIAL_TEAMS_SCHEME', 'DECISION_POLICY'
            )
        )
    ),
    CHECK (
        evidence_scope <> 'BASE'
        OR applies_to_game_id IS NULL
    ),
    CHECK (
        component NOT IN (
            'OFFENSIVE_SCHEME', 'DEFENSIVE_SCHEME',
            'SPECIAL_TEAMS_SCHEME', 'DECISION_POLICY'
        )
        OR game_state_conditioned = 1
    )
);

CREATE INDEX idx_coaching_scheme_lookup
    ON coaching_scheme_evidence_observations(
        team_season_id, component, evidence_scope, available_at
    );
CREATE INDEX idx_coaching_scheme_revision
    ON coaching_scheme_evidence_observations(
        team_season_id, logical_key, revision
    );
CREATE INDEX idx_coaching_scheme_source_game
    ON coaching_scheme_evidence_observations(source_game_id, component);
CREATE INDEX idx_coaching_scheme_applies_game
    ON coaching_scheme_evidence_observations(applies_to_game_id, component);
CREATE INDEX idx_coaching_scheme_raw_observation
    ON coaching_scheme_evidence_observations(evidence_observation_id);

CREATE TABLE public_scheme_label_observations (
    observation_id TEXT PRIMARY KEY,
    team_season_id TEXT NOT NULL REFERENCES team_seasons(team_season_id),
    side TEXT NOT NULL CHECK (side IN ('OFFENSE', 'DEFENSE', 'SPECIAL_TEAMS')),
    logical_key TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK (revision >= 1),
    label TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL,
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
    UNIQUE(team_season_id, logical_key, revision),
    CHECK (trim(observation_id) <> ''),
    CHECK (trim(logical_key) <> ''),
    CHECK (trim(label) <> ''),
    CHECK (length(payload_sha256) = 64)
);

CREATE INDEX idx_public_scheme_label_lookup
    ON public_scheme_label_observations(
        team_season_id, side, available_at
    );
CREATE INDEX idx_public_scheme_label_revision
    ON public_scheme_label_observations(
        team_season_id, logical_key, revision
    );
CREATE INDEX idx_public_scheme_label_raw_observation
    ON public_scheme_label_observations(evidence_observation_id);

CREATE TRIGGER coaching_stints_no_update
BEFORE UPDATE ON coaching_stints
BEGIN
    SELECT RAISE(ABORT, 'coaching_stints is append-only');
END;
CREATE TRIGGER coaching_stints_no_delete
BEFORE DELETE ON coaching_stints
BEGIN
    SELECT RAISE(ABORT, 'coaching_stints is append-only');
END;

CREATE TRIGGER coaching_assignment_observations_no_update
BEFORE UPDATE ON coaching_assignment_observations
BEGIN
    SELECT RAISE(ABORT, 'coaching_assignment_observations is append-only');
END;
CREATE TRIGGER coaching_assignment_observations_no_delete
BEFORE DELETE ON coaching_assignment_observations
BEGIN
    SELECT RAISE(ABORT, 'coaching_assignment_observations is append-only');
END;

CREATE TRIGGER coaching_scheme_evidence_no_update
BEFORE UPDATE ON coaching_scheme_evidence_observations
BEGIN
    SELECT RAISE(ABORT, 'coaching_scheme_evidence_observations is append-only');
END;
CREATE TRIGGER coaching_scheme_evidence_no_delete
BEFORE DELETE ON coaching_scheme_evidence_observations
BEGIN
    SELECT RAISE(ABORT, 'coaching_scheme_evidence_observations is append-only');
END;

CREATE TRIGGER public_scheme_label_observations_no_update
BEFORE UPDATE ON public_scheme_label_observations
BEGIN
    SELECT RAISE(ABORT, 'public_scheme_label_observations is append-only');
END;
CREATE TRIGGER public_scheme_label_observations_no_delete
BEFORE DELETE ON public_scheme_label_observations
BEGIN
    SELECT RAISE(ABORT, 'public_scheme_label_observations is append-only');
END;

CREATE TRIGGER coaching_assignment_require_stint_identity
BEFORE INSERT ON coaching_assignment_observations
WHEN NOT EXISTS (
    SELECT 1
    FROM coaching_stints stint
    WHERE stint.coaching_stint_id = NEW.coaching_stint_id
      AND stint.person_id = NEW.person_id
      AND stint.team_season_id = NEW.team_season_id
)
BEGIN
    SELECT RAISE(
        ABORT,
        'coaching assignment stint/person/team identity must match canonical stint'
    );
END;

CREATE TRIGGER coaching_assignment_require_raw_provenance
BEFORE INSERT ON coaching_assignment_observations
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
        'coaching assignment raw provenance must match evidence/provider/checksum'
    );
END;

CREATE TRIGGER coaching_scheme_require_raw_provenance
BEFORE INSERT ON coaching_scheme_evidence_observations
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
        'coaching scheme raw provenance must match evidence/provider/checksum'
    );
END;

CREATE TRIGGER public_scheme_label_require_raw_provenance
BEFORE INSERT ON public_scheme_label_observations
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
        'public scheme label raw provenance must match evidence/provider/checksum'
    );
END;
"""
