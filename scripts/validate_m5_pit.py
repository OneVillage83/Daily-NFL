"""Validate M5 historical PIT reconstruction and fail-closed leakage behavior."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from daily_nfl.domain import (  # noqa: E402
    AvailabilityConfidence,
    AvailabilityMethod,
    GameId,
)
from daily_nfl.persistence import apply_migrations, open_database  # noqa: E402
from daily_nfl.pit import (  # noqa: E402
    PITFeatureSnapshotSpec,
    PITFeatureValue,
    PITInputKind,
    PITInputRef,
    PITLeakageError,
    PredictionCutoff,
    build_snapshot_manifest,
    record_snapshot,
    schedule_state_as_of,
)
from daily_nfl.providers import (  # noqa: E402
    AcquisitionRequest,
    AcquisitionService,
    DatasetKind,
    FileSystemRawEvidenceStore,
    NflverseAdapter,
    ProviderPayload,
    record_stored_acquisition,
)
from daily_nfl.reconciliation import (  # noqa: E402
    IdentityRepository,
    game_id_for_event,
    new_event_id,
    new_franchise_id,
    team_season_id_for,
)

COMPETITION_ID = "core-competition-nfl"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("local-data/m5-validation.db"),
        help="SQLite validation database",
    )
    parser.add_argument(
        "--raw-root",
        type=Path,
        default=Path("local-data/m5-raw"),
        help="Root directory for immutable fixture raw evidence",
    )
    return parser.parse_args()


def _seed_game(connection: sqlite3.Connection, kickoff: datetime) -> GameId:
    repository = IdentityRepository(connection)
    home = new_franchise_id(UUID("11111111-1111-1111-1111-111111111111"))
    away = new_franchise_id(UUID("22222222-2222-2222-2222-222222222222"))
    repository.ensure_franchise(home, "M5 Fixture Home")
    repository.ensure_franchise(away, "M5 Fixture Away")
    home_team = team_season_id_for(home, 2026)
    away_team = team_season_id_for(away, 2026)
    repository.ensure_team_season(home_team, home, 2026)
    repository.ensure_team_season(away_team, away, 2026)
    event_id = new_event_id(UUID("33333333-3333-3333-3333-333333333333"))
    game_id = game_id_for_event(event_id)
    connection.execute(
        """
        INSERT INTO games(
            game_id, event_id, season, season_phase, week, ruleset_version,
            home_team_season_id, away_team_season_id, scheduled_kickoff,
            competition_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(game_id),
            str(event_id),
            2026,
            "REGULAR",
            1,
            "NFL_2026",
            str(home_team),
            str(away_team),
            kickoff.isoformat(),
            COMPETITION_ID,
        ),
    )
    return game_id


def main() -> int:
    args = parse_args()
    database: Path = args.database
    raw_root: Path = args.raw_root
    kickoff = datetime(2026, 9, 10, 20, 20, tzinfo=UTC)
    first_available = kickoff - timedelta(hours=5)
    correction_available = kickoff - timedelta(hours=2)

    payloads = (
        ProviderPayload(
            content=b"m5-fixture-schedule-v1",
            content_type="application/octet-stream",
            source_uri="fixture://m5/schedule/v1",
            observed_at=first_available,
            available_at=first_available,
            availability_method=AvailabilityMethod.OUR_OBSERVATION_TIME,
            availability_confidence=AvailabilityConfidence.HIGH,
            provider_schema_version="M5_FIXTURE_V1",
        ),
        ProviderPayload(
            content=b"m5-fixture-schedule-v2",
            content_type="application/octet-stream",
            source_uri="fixture://m5/schedule/v2",
            observed_at=correction_available,
            available_at=correction_available,
            availability_method=AvailabilityMethod.OUR_OBSERVATION_TIME,
            availability_confidence=AvailabilityConfidence.HIGH,
            provider_schema_version="M5_FIXTURE_V2",
        ),
    )
    adapter = NflverseAdapter(loader=lambda _: payloads)
    acquisition = AcquisitionService(FileSystemRawEvidenceStore(raw_root)).acquire(
        adapter,
        AcquisitionRequest(dataset=DatasetKind.SCHEDULE),
    )
    if len(acquisition.evidence) != 2:
        raise RuntimeError("M5 fixture acquisition did not produce two immutable revisions")
    first_evidence, correction_evidence = acquisition.evidence

    with open_database(database) as connection:
        schema_version = apply_migrations(connection)
        record_stored_acquisition(connection, acquisition)
        game_id = _seed_game(connection, kickoff)

        for observation_id, status, available_at, stored, revision in (
            (
                "m5-schedule-v1",
                "SCHEDULED",
                first_available,
                first_evidence,
                "v1",
            ),
            (
                "m5-schedule-v2",
                "POSTPONED",
                correction_available,
                correction_evidence,
                "v2",
            ),
        ):
            connection.execute(
                """
                INSERT INTO schedule_observations(
                    observation_id, game_id, evidence_id, evidence_observation_id,
                    provider_id, provider_game_id, status, scheduled_kickoff,
                    neutral_site, schedule_version, observed_at, ingested_at,
                    available_at, availability_method, availability_confidence,
                    provider_revision
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    observation_id,
                    str(game_id),
                    stored.artifact.evidence_id,
                    stored.evidence_observation_id,
                    "nflverse",
                    "2026_01_FIXTURE",
                    status,
                    kickoff.isoformat(),
                    0,
                    revision,
                    available_at.isoformat(),
                    (available_at + timedelta(seconds=1)).isoformat(),
                    available_at.isoformat(),
                    AvailabilityMethod.OUR_OBSERVATION_TIME.value,
                    AvailabilityConfidence.HIGH.value,
                    revision,
                ),
            )

        early_cutoff = PredictionCutoff(
            game_id=game_id,
            kickoff=kickoff,
            prediction_time=kickoff - timedelta(hours=3),
        )
        later_cutoff = PredictionCutoff(
            game_id=game_id,
            kickoff=kickoff,
            prediction_time=kickoff - timedelta(hours=1),
        )
        early_state = schedule_state_as_of(
            connection,
            game_id=game_id,
            cutoff=early_cutoff,
        )
        later_state = schedule_state_as_of(
            connection,
            game_id=game_id,
            cutoff=later_cutoff,
        )
        if early_state is None or later_state is None:
            raise RuntimeError("M5 schedule reconstruction unexpectedly returned no state")
        if early_state.observation_id != "m5-schedule-v1":
            raise RuntimeError("later schedule correction leaked into earlier PIT cutoff")
        if later_state.observation_id != "m5-schedule-v2":
            raise RuntimeError("later cutoff failed to adopt known schedule correction")
        if early_state.input_ref.evidence_observation_id is None:
            raise RuntimeError("M5 schedule state lost acquisition-observation provenance")

        feature_spec = PITFeatureSnapshotSpec(
            feature_contract="M5_VALIDATION_FEATURE_CONTRACT_V1",
            feature_version="1",
            feature_values=(PITFeatureValue("schedule_known", True),),
            missing_features=("optional_fixture_feature",),
        )
        manifest = build_snapshot_manifest(
            cutoff=early_cutoff,
            inputs=early_state.supporting_inputs,
            feature_spec=feature_spec,
        )
        record_snapshot(connection, manifest)

        seal_row = connection.execute(
            "SELECT 1 FROM pit_snapshot_seals WHERE snapshot_id = ?",
            (manifest.snapshot_id,),
        ).fetchone()
        stored_input = connection.execute(
            """
            SELECT evidence_id, evidence_observation_id, provider_id,
                   provider_revision, raw_sha256
            FROM pit_snapshot_inputs
            WHERE snapshot_id = ?
            """,
            (manifest.snapshot_id,),
        ).fetchone()
        if seal_row is None or stored_input is None:
            raise RuntimeError("M5 immutable snapshot did not persist/seal")
        if stored_input[1] != early_state.input_ref.evidence_observation_id:
            raise RuntimeError("M5 snapshot lost acquisition-observation provenance")

        leaked = PITInputRef(
            input_kind=PITInputKind.CURRENT_GAME_RESULT,
            input_id="deliberate-current-game-result",
            available_at=early_cutoff.prediction_time - timedelta(minutes=1),
            availability_method=AvailabilityMethod.SOURCE_TIMESTAMP,
            availability_confidence=AvailabilityConfidence.HIGH,
            source_table="deliberate_leak_fixture",
            subject_game_id=game_id,
            payload_sha256="f" * 64,
        )
        leakage_fail_closed = False
        try:
            build_snapshot_manifest(
                cutoff=early_cutoff,
                inputs=(leaked,),
                feature_spec=feature_spec,
            )
        except PITLeakageError:
            leakage_fail_closed = True
        if not leakage_fail_closed:
            raise RuntimeError("M5 deliberate leakage fixture was not rejected")
        connection.commit()

    result = {
        "schema_version": schema_version,
        "game_id": str(game_id),
        "early_cutoff": early_cutoff.prediction_time.isoformat(),
        "later_cutoff": later_cutoff.prediction_time.isoformat(),
        "early_observation_id": early_state.observation_id,
        "later_observation_id": later_state.observation_id,
        "early_status": early_state.status,
        "later_status": later_state.status,
        "later_correction_hidden_at_early_cutoff": (
            early_state.observation_id == "m5-schedule-v1"
        ),
        "later_correction_visible_at_late_cutoff": (
            later_state.observation_id == "m5-schedule-v2"
        ),
        "snapshot_id": manifest.snapshot_id,
        "snapshot_sealed": seal_row is not None,
        "snapshot_input_count": len(manifest.inputs),
        "evidence_id": stored_input[0],
        "evidence_observation_id": stored_input[1],
        "provider_id": stored_input[2],
        "provider_revision": stored_input[3],
        "raw_sha256": stored_input[4],
        "leakage_fail_closed": leakage_fail_closed,
    }
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
