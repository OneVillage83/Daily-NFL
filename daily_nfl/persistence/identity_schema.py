"""Schema additions for M4 identity reconciliation and crosswalk auditability."""

IDENTITY_RECONCILIATION_SCHEMA_SQL = r"""
DROP INDEX IF EXISTS uq_crosswalk_external_valid_from;

ALTER TABLE entity_crosswalk ADD COLUMN decision_id TEXT;
ALTER TABLE entity_crosswalk ADD COLUMN supersedes_crosswalk_id INTEGER
    REFERENCES entity_crosswalk(crosswalk_id);

CREATE UNIQUE INDEX uq_crosswalk_mapping_version
    ON entity_crosswalk(
        provider_id,
        provider_entity_type,
        external_id,
        COALESCE(valid_from, ''),
        canonical_entity_type,
        canonical_entity_id
    );

CREATE INDEX idx_crosswalk_supersedes
    ON entity_crosswalk(supersedes_crosswalk_id);

CREATE TABLE identity_reconciliation_decisions (
    decision_id TEXT PRIMARY KEY,
    provider_id TEXT NOT NULL REFERENCES providers(provider_id),
    provider_entity_type TEXT NOT NULL,
    external_id TEXT NOT NULL,
    expected_canonical_entity_type TEXT NOT NULL,
    status TEXT NOT NULL,
    selected_canonical_entity_id TEXT,
    match_method TEXT,
    match_confidence REAL
        CHECK (match_confidence IS NULL OR (match_confidence >= 0.0 AND match_confidence <= 1.0)),
    candidate_count INTEGER NOT NULL CHECK (candidate_count >= 0),
    valid_at TEXT,
    reason_code TEXT NOT NULL,
    details_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    CHECK (
        (
            status = 'RESOLVED'
            AND selected_canonical_entity_id IS NOT NULL
            AND match_method IS NOT NULL
            AND match_confidence IS NOT NULL
            AND match_method <> 'FUZZY_CANDIDATE_ONLY'
        )
        OR
        (
            status IN ('UNRESOLVED', 'AMBIGUOUS', 'CONFLICT')
            AND selected_canonical_entity_id IS NULL
        )
    )
);

CREATE INDEX idx_identity_decision_external
    ON identity_reconciliation_decisions(
        provider_id,
        provider_entity_type,
        external_id,
        created_at
    );
CREATE INDEX idx_identity_decision_selected
    ON identity_reconciliation_decisions(
        expected_canonical_entity_type,
        selected_canonical_entity_id
    );

CREATE TRIGGER entity_crosswalk_reject_fuzzy_insert
BEFORE INSERT ON entity_crosswalk
WHEN NEW.match_method = 'FUZZY_CANDIDATE_ONLY'
BEGIN
    SELECT RAISE(ABORT, 'fuzzy candidates cannot become canonical crosswalks');
END;

CREATE TRIGGER entity_crosswalk_no_update
BEFORE UPDATE ON entity_crosswalk
BEGIN
    SELECT RAISE(ABORT, 'entity_crosswalk is append-only');
END;
CREATE TRIGGER entity_crosswalk_no_delete
BEFORE DELETE ON entity_crosswalk
BEGIN
    SELECT RAISE(ABORT, 'entity_crosswalk is append-only');
END;

CREATE TRIGGER identity_reconciliation_decisions_no_update
BEFORE UPDATE ON identity_reconciliation_decisions
BEGIN
    SELECT RAISE(ABORT, 'identity_reconciliation_decisions is append-only');
END;
CREATE TRIGGER identity_reconciliation_decisions_no_delete
BEFORE DELETE ON identity_reconciliation_decisions
BEGIN
    SELECT RAISE(ABORT, 'identity_reconciliation_decisions is append-only');
END;
"""
