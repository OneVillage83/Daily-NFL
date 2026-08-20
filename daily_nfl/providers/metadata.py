"""Persistence bridge from stored acquisitions to the M2 evidence ledger."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

from daily_nfl.providers.contracts import ProviderDescriptor
from daily_nfl.providers.service import StoredAcquisition, StoredEvidence


class ProviderMetadataConflictError(RuntimeError):
    """Raised when a canonical provider ID is reused for a different provider."""


class RawEvidenceMetadataConflictError(RuntimeError):
    """Raised when an evidence ID conflicts on immutable content identity."""


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


def record_stored_acquisition(
    connection: sqlite3.Connection,
    acquisition: StoredAcquisition,
) -> None:
    """Record provider metadata and every immutable raw evidence object."""
    record_provider(connection, acquisition.descriptor)
    for evidence in acquisition.evidence:
        values = _raw_metadata_values(acquisition, evidence)
        evidence_id = evidence.artifact.evidence_id
        existing = connection.execute(
            "SELECT 1 FROM raw_evidence WHERE evidence_id = ?",
            (evidence_id,),
        ).fetchone()
        if existing is not None:
            _assert_existing_raw_identity_matches(connection, evidence_id, values)
            continue

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
