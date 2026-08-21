"""Validate M4 reconciliation against one real nflverse schedule row.

This Lane-B certification utility keeps production acquisition raw-first: it
acquires the exact nflverse schedule artifact through the M3 adapter/store,
reads one historical row from the stored bytes, and proves that the M4 identity
engine records source evidence while mapping provider identity to opaque
canonical franchise and season-scoped team identity.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import polars as pl

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
from daily_nfl.reconciliation import (  # noqa: E402
    FRANCHISE_ENTITY_TYPE,
    TEAM_SEASON_ENTITY_TYPE,
    CanonicalEntityType,
    ExternalIdentity,
    IdentityReconciler,
    IdentityRepository,
    ReconciliationEvidence,
    new_franchise_id,
)

REQUIRED_COLUMNS = ("season", "game_id", "home_team", "away_team")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("local-data/m4-validation.db"),
        help="SQLite validation database",
    )
    parser.add_argument(
        "--raw-root",
        type=Path,
        default=Path("local-data/m4-raw"),
        help="Root directory for immutable raw evidence",
    )
    parser.add_argument("--season", type=int, default=2025)
    parser.add_argument("--timeout", type=float, default=60.0)
    return parser.parse_args()


def _one_schedule_row(path: Path, season: int) -> dict[str, object]:
    frame = pl.read_parquet(path)
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise RuntimeError(f"nflverse schedule schema missing required columns: {missing}")
    rows = (
        frame.filter(pl.col("season") == season)
        .select(REQUIRED_COLUMNS)
        .head(1)
        .to_dicts()
    )
    if not rows:
        raise RuntimeError(f"nflverse schedule contains no row for season {season}")
    return rows[0]


def main() -> int:
    args = parse_args()
    database: Path = args.database
    raw_root: Path = args.raw_root
    season: int = args.season

    adapter = NflverseAdapter(
        loader=NflverseHttpLoader(
            user_agent="Daily-NFL/0.1 M4-validation",
            timeout_seconds=args.timeout,
        )
    )
    service = AcquisitionService(FileSystemRawEvidenceStore(raw_root))
    acquisition = service.acquire(
        adapter,
        AcquisitionRequest(dataset=DatasetKind.SCHEDULE),
    )
    stored = acquisition.evidence[0]
    stored_path = raw_root / stored.artifact.relative_path
    stored_bytes = stored_path.read_bytes()
    stored_sha256 = sha256_bytes(stored_bytes)
    if stored_sha256 != stored.artifact.sha256:
        raise RuntimeError("stored raw evidence checksum does not match acquisition artifact")

    row = _one_schedule_row(stored_path, season)
    source_record_id = str(row["game_id"])
    home_team = str(row["home_team"])
    away_team = str(row["away_team"])
    evidence = ReconciliationEvidence(
        source_record_id=source_record_id,
        evidence_id=stored.artifact.evidence_id,
        evidence_observation_id=stored.evidence_observation_id,
        evidence_kind="NFLVERSE_SCHEDULE_ROW",
        facts=(
            ("season", str(season)),
            ("home_team", home_team),
            ("away_team", away_team),
        ),
    )

    with open_database(database) as connection:
        schema_version = apply_migrations(connection)
        record_stored_acquisition(connection, acquisition)
        repository = IdentityRepository(connection)
        reconciler = IdentityReconciler(repository)

        franchise_id = new_franchise_id()
        repository.ensure_franchise(franchise_id, f"M4 validation {home_team}")
        franchise_decision = reconciler.bind_verified(
            external=ExternalIdentity(
                provider_id="nflverse",
                provider_entity_type=FRANCHISE_ENTITY_TYPE,
                external_id=home_team,
            ),
            canonical_entity_type=CanonicalEntityType.FRANCHISE,
            canonical_entity_id=str(franchise_id),
            evidence=(evidence,),
        )
        team_decision = reconciler.resolve_team_season(
            provider_id="nflverse",
            external_team_id=home_team,
            season=season,
            display_name=f"{home_team} {season}",
            evidence=(evidence,),
        )
        if not franchise_decision.resolved or not team_decision.resolved:
            raise RuntimeError("M4 validation identity decisions did not resolve")
        if team_decision.selected_canonical_entity_id is None:
            raise RuntimeError("M4 validation team-season identity is missing")
        if team_decision.selected_canonical_entity_id == home_team:
            raise RuntimeError("provider team ID leaked into canonical team-season identity")

        team_crosswalk = repository.active_crosswalks(
            ExternalIdentity(
                provider_id="nflverse",
                provider_entity_type=TEAM_SEASON_ENTITY_TYPE,
                external_id=home_team,
                valid_at=team_decision.external_identity.valid_at,
            )
        )
        if len(team_crosswalk) != 1:
            raise RuntimeError("M4 validation expected exactly one active team-season crosswalk")
        binding = team_crosswalk[0]
        evidence_count_row = connection.execute(
            """
            SELECT COUNT(*)
            FROM identity_reconciliation_evidence
            WHERE decision_id IN (?, ?)
            """,
            (franchise_decision.decision_id, team_decision.decision_id),
        ).fetchone()
        evidence_count = int(evidence_count_row[0]) if evidence_count_row else 0
        if evidence_count < 2:
            raise RuntimeError("M4 validation reconciliation evidence was not persisted")
        connection.commit()

    result = {
        "schema_version": schema_version,
        "provider_id": acquisition.descriptor.provider_id,
        "season": season,
        "source_record_id": source_record_id,
        "home_team_external_id": home_team,
        "away_team_external_id": away_team,
        "evidence_id": stored.artifact.evidence_id,
        "evidence_observation_id": stored.evidence_observation_id,
        "sha256": stored.artifact.sha256,
        "stored_sha256": stored_sha256,
        "canonical_franchise_id": str(franchise_id),
        "canonical_team_season_id": team_decision.selected_canonical_entity_id,
        "franchise_status": franchise_decision.status.value,
        "team_season_status": team_decision.status.value,
        "team_season_match_method": (
            team_decision.match_method.value if team_decision.match_method is not None else None
        ),
        "team_crosswalk_valid_from": (
            binding.valid_from.isoformat() if binding.valid_from is not None else None
        ),
        "team_crosswalk_valid_to": (
            binding.valid_to.isoformat() if binding.valid_to is not None else None
        ),
        "reconciliation_evidence_rows": evidence_count,
    }
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
