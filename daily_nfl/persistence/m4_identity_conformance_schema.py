"""Forward-only schema additions required by the M4 F-3 identity contract.

Migration 6 leaves the provisional migration-2 identity history intact while
adding first-class source evidence for reconciliation decisions, scoped
provider identities, and a requirement that new crosswalk rows cite an
auditable reconciliation decision.
"""

M4_IDENTITY_CONFORMANCE_SCHEMA_SQL = r"""
ALTER TABLE entity_crosswalk ADD COLUMN identity_scope TEXT;
ALTER TABLE identity_reconciliation_decisions ADD COLUMN identity_scope TEXT;

DROP INDEX IF EXISTS uq_crosswalk_mapping_version;
CREATE UNIQUE INDEX uq_crosswalk_mapping_version_v2
    ON entity_crosswalk(
        provider_id,
        provider_entity_type,
        external_id,
        COALESCE(identity_scope, ''),
        COALESCE(valid_from, ''),
        COALESCE(valid_to, ''),
        canonical_entity_type,
        canonical_entity_id,
        match_method,
        match_confidence,
        verified,
        COALESCE(supersedes_crosswalk_id, 0)
    );

CREATE INDEX idx_crosswalk_external_scope
    ON entity_crosswalk(
        provider_id,
        provider_entity_type,
        external_id,
        identity_scope
    );

CREATE TABLE identity_reconciliation_evidence (
    decision_id TEXT NOT NULL
        REFERENCES identity_reconciliation_decisions(decision_id),
    evidence_sequence INTEGER NOT NULL CHECK (evidence_sequence >= 1),
    source_record_id TEXT NOT NULL,
    evidence_id TEXT NOT NULL REFERENCES raw_evidence(evidence_id),
    evidence_observation_id TEXT
        REFERENCES raw_evidence_observations(evidence_observation_id),
    evidence_kind TEXT NOT NULL,
    facts_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    PRIMARY KEY(decision_id, evidence_sequence)
);

CREATE INDEX idx_identity_reconciliation_evidence_raw
    ON identity_reconciliation_evidence(evidence_id, evidence_observation_id);
CREATE INDEX idx_identity_reconciliation_evidence_source_record
    ON identity_reconciliation_evidence(source_record_id);

CREATE TRIGGER identity_reconciliation_evidence_no_update
BEFORE UPDATE ON identity_reconciliation_evidence
BEGIN
    SELECT RAISE(ABORT, 'identity_reconciliation_evidence is append-only');
END;
CREATE TRIGGER identity_reconciliation_evidence_no_delete
BEFORE DELETE ON identity_reconciliation_evidence
BEGIN
    SELECT RAISE(ABORT, 'identity_reconciliation_evidence is append-only');
END;

CREATE TRIGGER entity_crosswalk_require_decision
BEFORE INSERT ON entity_crosswalk
WHEN NEW.decision_id IS NULL
BEGIN
    SELECT RAISE(ABORT, 'entity crosswalk requires a reconciliation decision');
END;

CREATE TRIGGER entity_crosswalk_require_existing_decision
BEFORE INSERT ON entity_crosswalk
WHEN NEW.decision_id IS NOT NULL
 AND NOT EXISTS (
    SELECT 1
    FROM identity_reconciliation_decisions decision
    WHERE decision.decision_id = NEW.decision_id
)
BEGIN
    SELECT RAISE(ABORT, 'entity crosswalk decision_id must reference an existing decision');
END;
"""
