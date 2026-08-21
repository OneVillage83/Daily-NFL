"""Persistence bridge from stored acquisitions to the certified evidence ledger."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, datetime

from daily_nfl.providers.contracts import ProviderCapability, ProviderDescriptor
from daily_nfl.providers.service import StoredAcquisition, StoredEvidence


class ProviderMetadataConflictError(RuntimeError):
    """Raised when a canonical provider ID is reused for a different provider."""


class ProviderCapabilityConflictError(RuntimeError):
    """Raised when a capability snapshot ID conflicts with stored metadata."""


class RawEvidenceMetadataConflictError(RuntimeError):
    """Raised when an evidence ID conflicts on immutable content identity."""


class RawEvidenceObservationConflictError(RuntimeError):
    """Raised when an acquisition observation ID conflicts with stored history."""


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("persisted provenance clocks must be timezone-aware")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _license_summary(descriptor: ProviderDescriptor) -> str | None:
    values = sorted({capability.license_class for capability in descriptor.capabilities})
    return ";".join(values) if values else None


def record_provider(connection: sqlite3.Connection, descriptor: ProviderDescriptor) -> None:
    existing = connection.execute(
        """
        SELECT name, provider_type
        FROM providers
        WHERE provider_id = ?
        """,
        (descriptor.provider_id,),
    ).fetchone()
    if existing is not None and (
        str(existing[0]) != descriptor.name or str(existing[1]) != descriptor.provider_type
    ):
        raise ProviderMetadataConflictError(
            f"provider_id {descriptor.provider_id!r} already belongs to a different provider"
        )

    if existing is None:
        connection.execute(
            """
            INSERT INTO providers(
                provider_id,
                name,
                provider_type,
                provider_schema_version,
                parser_version,
                license_class
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                descriptor.provider_id,
                descriptor.name,
                descriptor.provider_type,
                descriptor.provider_schema_version,
                descriptor.parser_version,
                _license_summary(descriptor),
            ),
        )
    else:
        connection.execute(
            """
            UPDATE providers
            SET provider_schema_version = ?, parser_version = ?, license_class = ?
            WHERE provider_id = ?
            """,
            (
                descriptor.provider_schema_version,
                descriptor.parser_version,
                _license_summary(descriptor),
                descriptor.provider_id,
            ),
        )


def _capability_document(
    provider_id: str,
    capability: ProviderCapability,
    provider_schema_version: str | None,
) -> dict[str, object]:
    return {
        "provider_id": provider_id,
        "dataset": capability.dataset.value,
        "entity_coverage": list(capability.entity_coverage),
        "field_coverage": list(capability.field_coverage),
        "earliest_season": capability.earliest_season,
        "latest_season": capability.latest_season,
        "update_cadence": capability.cadence,
        "expected_latency": capability.expected_latency,
        "historical_availability": capability.historical_availability.value,
        "pit_fidelity": capability.point_in_time_fidelity.value,
        "reliability_tier": capability.reliability_tier.value,
        "reliability_note": capability.reliability_note,
        "provider_schema_version": capability.schema_version or provider_schema_version,
        "license_class": capability.license_class,
        "license_id": capability.license_id,
        "license_url": capability.license_url,
        "attribution_required": capability.attribution_required,
        "attribution_text": capability.attribution_text,
        "cost_class": capability.cost_class.value,
    }


def capability_id_for(
    provider_id: str,
    capability: ProviderCapability,
    provider_schema_version: str | None = None,
) -> str:
    """Content-address one machine-readable provider capability snapshot."""

    if not provider_id.strip():
        raise ValueError("provider_id cannot be blank")
    document = _capability_document(provider_id, capability, provider_schema_version)
    encoded = json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
    return f"pcap_{hashlib.sha256(encoded).hexdigest()}"


def _capability_values(
    descriptor: ProviderDescriptor,
    capability: ProviderCapability,
) -> tuple[object, ...]:
    capability_id = capability_id_for(
        descriptor.provider_id,
        capability,
        descriptor.provider_schema_version,
    )
    return (
        capability_id,
        descriptor.provider_id,
        capability.dataset.value,
        json.dumps(list(capability.entity_coverage), separators=(",", ":")),
        json.dumps(list(capability.field_coverage), separators=(",", ":")),
        capability.earliest_season,
        capability.latest_season,
        capability.cadence,
        capability.expected_latency,
        capability.historical_availability.value,
        capability.point_in_time_fidelity.value,
        capability.reliability_tier.value,
        capability.reliability_note,
        capability.schema_version or descriptor.provider_schema_version,
        capability.license_class,
        capability.license_id,
        capability.license_url,
        int(capability.attribution_required),
        capability.attribution_text,
        capability.cost_class.value,
    )


def record_provider_capability(
    connection: sqlite3.Connection,
    descriptor: ProviderDescriptor,
    capability: ProviderCapability,
) -> str:
    """Persist one immutable F-2.2 capability/licensing snapshot."""

    values = _capability_values(descriptor, capability)
    capability_id = str(values[0])
    existing = connection.execute(
        """
        SELECT capability_id, provider_id, dataset, entity_coverage_json,
               field_coverage_json, earliest_season, latest_season, update_cadence,
               expected_latency, historical_availability, pit_fidelity,
               reliability_tier, reliability_note, provider_schema_version,
               license_class, license_id, license_url, attribution_required,
               attribution_text, cost_class
        FROM provider_capability_snapshots
        WHERE capability_id = ?
        """,
        (capability_id,),
    ).fetchone()
    if existing is not None:
        if tuple(existing) != values:
            raise ProviderCapabilityConflictError(
                f"capability_id {capability_id!r} conflicts with stored metadata"
            )
        return capability_id

    connection.execute(
        """
        INSERT INTO provider_capability_snapshots(
            capability_id, provider_id, dataset, entity_coverage_json,
            field_coverage_json, earliest_season, latest_season, update_cadence,
            expected_latency, historical_availability, pit_fidelity,
            reliability_tier, reliability_note, provider_schema_version,
            license_class, license_id, license_url, attribution_required,
            attribution_text, cost_class
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        values,
    )
    return capability_id


def _raw_metadata_values(
    acquisition: StoredAcquisition,
    evidence: StoredEvidence,
) -> tuple[object, ...]:
    payload = evidence.payload
    artifact = evidence.artifact
    provider_schema_version = (
        payload.provider_schema_version or acquisition.descriptor.provider_schema_version
    )
    return (
        artifact.evidence_id,
        acquisition.descriptor.provider_id,
        acquisition.request.dataset.value,
        payload.source_uri,
        payload.content_type,
        artifact.sha256,
        artifact.relative_path.as_posix(),
        _iso(payload.effective_at),
        _iso(payload.published_at),
        _iso(payload.observed_at),
        _iso(evidence.ingested_at),
        _iso(payload.available_at),
        payload.availability_method.value,
        payload.availability_confidence.value,
        provider_schema_version,
        acquisition.descriptor.parser_version,
    )


def _assert_existing_raw_identity_matches(
    connection: sqlite3.Connection,
    evidence_id: str,
    expected: tuple[object, ...],
) -> None:
    row = connection.execute(
        """
        SELECT evidence_id, provider_id, endpoint_category, sha256, object_path
        FROM raw_evidence
        WHERE evidence_id = ?
        """,
        (evidence_id,),
    ).fetchone()
    if row is None:
        return

    expected_identity = (expected[0], expected[1], expected[2], expected[5], expected[6])
    actual_identity = tuple(row[index] for index in range(len(expected_identity)))
    if actual_identity != expected_identity:
        raise RawEvidenceMetadataConflictError(
            f"evidence_id {evidence_id!r} already exists with conflicting content identity"
        )


def _observation_values(
    acquisition: StoredAcquisition,
    evidence: StoredEvidence,
    capability_id: str,
    capability: ProviderCapability,
) -> tuple[object, ...]:
    payload = evidence.payload
    provider_schema_version = (
        payload.provider_schema_version
        or capability.schema_version
        or acquisition.descriptor.provider_schema_version
    )
    return (
        evidence.evidence_observation_id,
        evidence.artifact.evidence_id,
        acquisition.descriptor.provider_id,
        acquisition.request.dataset.value,
        capability_id,
        payload.source_uri,
        _iso(payload.effective_at),
        _iso(payload.published_at),
        _iso(payload.observed_at),
        _iso(evidence.ingested_at),
        _iso(payload.available_at),
        payload.availability_method.value,
        payload.availability_confidence.value,
        provider_schema_version,
        acquisition.descriptor.parser_version,
        capability.license_id,
        capability.license_url,
        int(capability.attribution_required),
        capability.attribution_text,
    )


def _record_raw_observation(
    connection: sqlite3.Connection,
    values: tuple[object, ...],
) -> None:
    observation_id = str(values[0])
    existing = connection.execute(
        """
        SELECT evidence_observation_id, evidence_id, provider_id, dataset,
               capability_id, source_uri, effective_at, published_at, observed_at,
               ingested_at, available_at, availability_method,
               availability_confidence, provider_schema_version, parser_version,
               license_id, license_url, attribution_required, attribution_text
        FROM raw_evidence_observations
        WHERE evidence_observation_id = ?
        """,
        (observation_id,),
    ).fetchone()
    if existing is not None:
        if tuple(existing) != values:
            raise RawEvidenceObservationConflictError(
                f"evidence observation {observation_id!r} conflicts with stored history"
            )
        return

    connection.execute(
        """
        INSERT INTO raw_evidence_observations(
            evidence_observation_id, evidence_id, provider_id, dataset,
            capability_id, source_uri, effective_at, published_at, observed_at,
            ingested_at, available_at, availability_method,
            availability_confidence, provider_schema_version, parser_version,
            license_id, license_url, attribution_required, attribution_text
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        values,
    )


def record_stored_acquisition(
    connection: sqlite3.Connection,
    acquisition: StoredAcquisition,
) -> None:
    """Record immutable raw content plus every distinct acquisition observation."""

    record_provider(connection, acquisition.descriptor)
    capability = acquisition.descriptor.capability_for(acquisition.request.dataset)
    if capability is None:
        raise ValueError("stored acquisition has no declared provider capability")
    capability_id = record_provider_capability(
        connection,
        acquisition.descriptor,
        capability,
    )

    for evidence in acquisition.evidence:
        values = _raw_metadata_values(acquisition, evidence)
        evidence_id = evidence.artifact.evidence_id
        existing = connection.execute(
            "SELECT 1 FROM raw_evidence WHERE evidence_id = ?",
            (evidence_id,),
        ).fetchone()
        if existing is not None:
            _assert_existing_raw_identity_matches(connection, evidence_id, values)
        else:
            connection.execute(
                """
                INSERT INTO raw_evidence(
                    evidence_id,
                    provider_id,
                    endpoint_category,
                    source_uri,
                    content_type,
                    sha256,
                    object_path,
                    effective_at,
                    published_at,
                    observed_at,
                    ingested_at,
                    available_at,
                    availability_method,
                    availability_confidence,
                    provider_schema_version,
                    parser_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )

        observation_values = _observation_values(
            acquisition,
            evidence,
            capability_id,
            capability,
        )
        _record_raw_observation(connection, observation_values)
