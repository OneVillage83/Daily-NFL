"""Forward-only schema additions required by the M3 F-2 provider contract.

Migration 5 keeps M2's content-addressed ``raw_evidence`` ledger intact while
adding immutable acquisition-observation history and versioned provider
capability/licensing snapshots. Identical bytes may therefore be deduplicated
without discarding when and how those bytes were observed.
"""

M3_PROVIDER_SCHEMA_SQL = r"""
CREATE TABLE provider_capability_snapshots (
    capability_id TEXT PRIMARY KEY,
    provider_id TEXT NOT NULL REFERENCES providers(provider_id),
    dataset TEXT NOT NULL,
    entity_coverage_json TEXT NOT NULL,
    field_coverage_json TEXT NOT NULL,
    earliest_season INTEGER CHECK (earliest_season IS NULL OR earliest_season >= 1920),
    latest_season INTEGER CHECK (latest_season IS NULL OR latest_season >= 1920),
    update_cadence TEXT NOT NULL,
    expected_latency TEXT,
    historical_availability TEXT NOT NULL,
    pit_fidelity TEXT NOT NULL,
    reliability_tier TEXT NOT NULL,
    reliability_note TEXT,
    provider_schema_version TEXT,
    license_class TEXT NOT NULL,
    license_id TEXT,
    license_url TEXT,
    attribution_required INTEGER NOT NULL CHECK (attribution_required IN (0, 1)),
    attribution_text TEXT,
    cost_class TEXT NOT NULL,
    recorded_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    CHECK (latest_season IS NULL OR earliest_season IS NULL OR latest_season >= earliest_season),
    CHECK (attribution_required = 0 OR attribution_text IS NOT NULL)
);

CREATE INDEX idx_provider_capabilities_provider_dataset
    ON provider_capability_snapshots(provider_id, dataset);

CREATE TABLE raw_evidence_observations (
    evidence_observation_id TEXT PRIMARY KEY,
    evidence_id TEXT NOT NULL REFERENCES raw_evidence(evidence_id),
    provider_id TEXT NOT NULL REFERENCES providers(provider_id),
    dataset TEXT NOT NULL,
    capability_id TEXT NOT NULL REFERENCES provider_capability_snapshots(capability_id),
    source_uri TEXT,
    effective_at TEXT,
    published_at TEXT,
    observed_at TEXT NOT NULL,
    ingested_at TEXT NOT NULL,
    available_at TEXT NOT NULL,
    availability_method TEXT NOT NULL,
    availability_confidence TEXT NOT NULL,
    provider_schema_version TEXT,
    parser_version TEXT NOT NULL,
    license_id TEXT,
    license_url TEXT,
    attribution_required INTEGER NOT NULL CHECK (attribution_required IN (0, 1)),
    attribution_text TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    CHECK (attribution_required = 0 OR attribution_text IS NOT NULL)
);

CREATE INDEX idx_raw_evidence_observations_evidence
    ON raw_evidence_observations(evidence_id, observed_at);
CREATE INDEX idx_raw_evidence_observations_provider_dataset
    ON raw_evidence_observations(provider_id, dataset, available_at);

CREATE TRIGGER provider_capability_snapshots_no_update
BEFORE UPDATE ON provider_capability_snapshots
BEGIN
    SELECT RAISE(ABORT, 'provider capability snapshots are append-only');
END;
CREATE TRIGGER provider_capability_snapshots_no_delete
BEFORE DELETE ON provider_capability_snapshots
BEGIN
    SELECT RAISE(ABORT, 'provider capability snapshots are append-only');
END;

CREATE TRIGGER raw_evidence_observations_no_update
BEFORE UPDATE ON raw_evidence_observations
BEGIN
    SELECT RAISE(ABORT, 'raw evidence observations are append-only');
END;
CREATE TRIGGER raw_evidence_observations_no_delete
BEFORE DELETE ON raw_evidence_observations
BEGIN
    SELECT RAISE(ABORT, 'raw evidence observations are append-only');
END;
"""
