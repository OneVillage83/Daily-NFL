"""Validate exact-byte nflverse acquisition, storage, and provenance persistence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from daily_nfl.persistence import apply_migrations, open_database  # noqa: E402
from daily_nfl.providers import (  # noqa: E402
    AcquisitionRequest,
    AcquisitionService,
    DatasetKind,
    FileSystemRawEvidenceStore,
    NflverseAdapter,
    NflverseHttpLoader,
    record_stored_acquisition,
    sha256_bytes,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("local-data/m3-validation.db"),
        help="SQLite validation database",
    )
    parser.add_argument(
        "--raw-root",
        type=Path,
        default=Path("local-data/m3-raw"),
        help="Root directory for immutable raw evidence",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="HTTP timeout in seconds",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    database: Path = args.database
    raw_root: Path = args.raw_root

    adapter = NflverseAdapter(
        loader=NflverseHttpLoader(
            user_agent="Daily-NFL/0.1 M3-validation",
            timeout_seconds=args.timeout,
        )
    )
    service = AcquisitionService(FileSystemRawEvidenceStore(raw_root))
    acquisition = service.acquire(adapter, AcquisitionRequest(dataset=DatasetKind.SCHEDULE))

    with open_database(database) as connection:
        schema_version = apply_migrations(connection)
        record_stored_acquisition(connection, acquisition)
        connection.commit()
        counts = connection.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM raw_evidence WHERE provider_id = ?),
                (SELECT COUNT(*) FROM raw_evidence_observations WHERE provider_id = ?),
                (SELECT COUNT(*) FROM provider_capability_snapshots WHERE provider_id = ?)
            """,
            (
                adapter.descriptor.provider_id,
                adapter.descriptor.provider_id,
                adapter.descriptor.provider_id,
            ),
        ).fetchone()
        persisted_observation = connection.execute(
            """
            SELECT capability_id, license_id, attribution_required, attribution_text
            FROM raw_evidence_observations
            WHERE evidence_observation_id = ?
            """,
            (acquisition.evidence[0].evidence_observation_id,),
        ).fetchone()

    evidence = acquisition.evidence[0]
    stored_path = raw_root / evidence.artifact.relative_path
    stored_bytes = stored_path.read_bytes()
    stored_sha256 = sha256_bytes(stored_bytes)
    if stored_sha256 != evidence.artifact.sha256:
        raise RuntimeError("stored raw evidence checksum does not match acquisition artifact")
    if stored_bytes != evidence.payload.content:
        raise RuntimeError("stored raw evidence bytes do not match provider payload")
    if counts is None or persisted_observation is None:
        raise RuntimeError("M3 validation metadata was not persisted")

    result = {
        "database": str(database),
        "raw_root": str(raw_root),
        "schema_version": schema_version,
        "provider_id": acquisition.descriptor.provider_id,
        "dataset": acquisition.request.dataset.value,
        "evidence_id": evidence.artifact.evidence_id,
        "evidence_observation_id": evidence.evidence_observation_id,
        "sha256": evidence.artifact.sha256,
        "stored_sha256": stored_sha256,
        "size_bytes": evidence.artifact.size_bytes,
        "relative_path": evidence.artifact.relative_path.as_posix(),
        "source_uri": evidence.payload.source_uri,
        "published_at": (
            evidence.payload.published_at.isoformat()
            if evidence.payload.published_at is not None
            else None
        ),
        "observed_at": evidence.payload.observed_at.isoformat(),
        "available_at": evidence.payload.available_at.isoformat(),
        "ingested_at": evidence.ingested_at.isoformat(),
        "raw_evidence_count": int(counts[0]),
        "raw_observation_count": int(counts[1]),
        "capability_snapshot_count": int(counts[2]),
        "capability_id": str(persisted_observation[0]),
        "license_id": persisted_observation[1],
        "attribution_required": bool(persisted_observation[2]),
        "attribution_text": persisted_observation[3],
    }
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
