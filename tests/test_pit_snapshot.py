import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest

from daily_nfl.domain import AvailabilityConfidence, AvailabilityMethod, GameId
from daily_nfl.persistence import apply_migrations, open_database
from daily_nfl.pit import (
    PITHorizon,
    PITFeatureSnapshotSpec,
    PITFeatureValue,
    PITInputKind,
    PITInputRef,
    PITSnapshotConflictError,
    PredictionCutoff,
    build_snapshot_manifest,
    record_snapshot,
)
from daily_nfl.providers import NFLVERSE_DESCRIPTOR, record_provider
from daily_nfl.reconciliation import (
    IdentityRepository,
    game_id_for_event,
    new_event_id,
    new_franchise_id,
    team_season_id_for,
)

COMPETITION_ID = "core-competition-nfl"


def _fixture_game_id() -> GameId:
    event_id = new_event_id(UUID("33333333-3333-3333-3333-333333333333"))
    return game_id_for_event(event_id)


def _feature_spec(value: float = 1.25) -> PITFeatureSnapshotSpec:
    return PITFeatureSnapshotSpec(
        feature_contract="M5_FIXTURE_V1",
        feature_version="1",
        feature_values=(PITFeatureValue("fixture_strength", value),),
        missing_features=("fixture_optional",),
    )


def _insert_game(connection: sqlite3.Connection) -> tuple[str, PredictionCutoff]:
    repository = IdentityRepository(connection)
    home = new_franchise_id(UUID("11111111-1111-1111-1111-111111111111"))
    away = new_franchise_id(UUID("22222222-2222-2222-2222-222222222222"))
    repository.ensure_franchise(home)
    repository.ensure_franchise(away)
    home_team = team_season_id_for(home, 2026)
    away_team = team_season_id_for(away, 2026)
    repository.ensure_team_season(home_team, home, 2026)
    repository.ensure_team_season(away_team, away, 2026)
    event_id = new_event_id(UUID("33333333-3333-3333-3333-333333333333"))
    game_id = game_id_for_event(event_id)
    kickoff = datetime(2026, 9, 10, 20, 20, tzinfo=UTC)
    connection.execute(
        """
        INSERT INTO games(
            game_id,
            event_id,
            season,
            season_phase,
            week,
            ruleset_version,
            home_team_season_id,
            away_team_season_id,
            scheduled_kickoff,
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
    cutoff = PredictionCutoff.from_horizon(
        game_id=game_id,
        kickoff=kickoff,
        horizon=PITHorizon.T_90M,
    )
    return str(game_id), cutoff


def _input(input_id: str, cutoff: PredictionCutoff, payload: str) -> PITInputRef:
    return PITInputRef(
        input_kind=PITInputKind.INJURY,
        input_id=input_id,
        available_at=cutoff.prediction_time - timedelta(hours=1),
        availability_method=AvailabilityMethod.SOURCE_TIMESTAMP,
        availability_confidence=AvailabilityConfidence.HIGH,
        source_table="injury_observations",
        subject_game_id=cutoff.game_id,
        observed_at=cutoff.prediction_time - timedelta(minutes=50),
        ingested_at=cutoff.prediction_time - timedelta(minutes=49),
        payload_sha256=payload * 64,
    )


def test_snapshot_identity_is_deterministic_and_input_order_independent() -> None:
    kickoff = datetime(2026, 9, 10, 20, 20, tzinfo=UTC)
    cutoff = PredictionCutoff.from_horizon(
        game_id=_fixture_game_id(),
        kickoff=kickoff,
        horizon=PITHorizon.T_90M,
    )
    first = _input("first", cutoff, "a")
    second = _input("second", cutoff, "b")

    left = build_snapshot_manifest(
        cutoff=cutoff,
        inputs=(first, second),
        feature_spec=_feature_spec(),
    )
    right = build_snapshot_manifest(
        cutoff=cutoff,
        inputs=(second, first),
        feature_spec=_feature_spec(),
    )

    assert left.snapshot_id == right.snapshot_id
    assert left.manifest_sha256 == right.manifest_sha256
    assert [input_ref.input_id for input_ref in left.inputs] == ["first", "second"]


def test_changing_input_or_feature_changes_snapshot_identity() -> None:
    kickoff = datetime(2026, 9, 10, 20, 20, tzinfo=UTC)
    cutoff = PredictionCutoff.from_horizon(
        game_id=_fixture_game_id(),
        kickoff=kickoff,
        horizon=PITHorizon.T_90M,
    )
    original = build_snapshot_manifest(
        cutoff=cutoff,
        inputs=(_input("one", cutoff, "a"),),
        feature_spec=_feature_spec(),
    )
    changed_input = build_snapshot_manifest(
        cutoff=cutoff,
        inputs=(_input("one", cutoff, "b"),),
        feature_spec=_feature_spec(),
    )
    changed_feature = build_snapshot_manifest(
        cutoff=cutoff,
        inputs=(_input("one", cutoff, "a"),),
        feature_spec=_feature_spec(2.0),
    )

    assert original.snapshot_id != changed_input.snapshot_id
    assert original.snapshot_id != changed_feature.snapshot_id


def test_snapshot_persistence_is_idempotent_sealed_and_feature_complete(tmp_path: Path) -> None:
    database = tmp_path / "pit.db"

    with open_database(database) as connection:
        apply_migrations(connection)
        _, cutoff = _insert_game(connection)
        inputs = (
            _input("first", cutoff, "a"),
            _input("second", cutoff, "b"),
        )
        manifest = build_snapshot_manifest(
            cutoff=cutoff,
            inputs=inputs,
            feature_spec=_feature_spec(),
        )
        record_snapshot(connection, manifest)
        record_snapshot(connection, manifest)

        row = connection.execute(
            """
            SELECT feature_contract, feature_version, feature_values_json,
                   coverage_report_json, missing_features_json,
                   pit_validation_result, input_count
            FROM pit_snapshots
            WHERE snapshot_id = ?
            """,
            (manifest.snapshot_id,),
        ).fetchone()
        assert row is not None
        assert row[0] == "M5_FIXTURE_V1"
        assert row[1] == "1"
        assert json.loads(str(row[2])) == {"fixture_strength": 1.25}
        assert json.loads(str(row[3])) == {
            "coverage_fraction": 0.5,
            "expected_feature_count": 2,
            "missing_feature_count": 1,
            "present_feature_count": 1,
        }
        assert json.loads(str(row[4])) == ["fixture_optional"]
        assert row[5] == "PASS"
        assert row[6] == 2
        assert connection.execute("SELECT COUNT(*) FROM pit_snapshots").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM pit_snapshot_inputs").fetchone()[0] == 2
        assert connection.execute("SELECT COUNT(*) FROM pit_snapshot_seals").fetchone()[0] == 1

        with pytest.raises(sqlite3.IntegrityError, match="membership cannot change"):
            connection.execute(
                """
                INSERT INTO pit_snapshot_inputs(
                    snapshot_id,
                    input_kind,
                    input_id,
                    source_table,
                    available_at,
                    availability_method,
                    availability_confidence
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    manifest.snapshot_id,
                    PITInputKind.OTHER.value,
                    "late-added-input",
                    "fixture_source",
                    cutoff.prediction_time.isoformat(),
                    AvailabilityMethod.SOURCE_TIMESTAMP.value,
                    AvailabilityConfidence.HIGH.value,
                ),
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE pit_snapshots SET policy_version = 'changed' WHERE snapshot_id = ?",
                (manifest.snapshot_id,),
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "DELETE FROM pit_snapshot_inputs WHERE snapshot_id = ?",
                (manifest.snapshot_id,),
            )


def test_snapshot_rejects_cutoff_that_disagrees_with_retrospective_actual_kickoff(
    tmp_path: Path,
) -> None:
    database = tmp_path / "pit.db"

    with open_database(database) as connection:
        apply_migrations(connection)
        record_provider(connection, NFLVERSE_DESCRIPTOR)
        game_id, canonical_cutoff = _insert_game(connection)
        actual_kickoff = canonical_cutoff.kickoff - timedelta(minutes=30)
        observation_time = canonical_cutoff.prediction_time - timedelta(hours=2)
        connection.execute(
            """
            INSERT INTO schedule_observations(
                observation_id, game_id, provider_id, provider_game_id, status,
                scheduled_kickoff, actual_kickoff, observed_at, ingested_at,
                available_at, availability_method, availability_confidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "schedule-final-truth",
                game_id,
                "nflverse",
                "fixture-game",
                "FINAL",
                canonical_cutoff.kickoff.isoformat(),
                actual_kickoff.isoformat(),
                observation_time.isoformat(),
                (observation_time + timedelta(seconds=1)).isoformat(),
                observation_time.isoformat(),
                AvailabilityMethod.OUR_OBSERVATION_TIME.value,
                AvailabilityConfidence.HIGH.value,
            ),
        )
        stale_cutoff = PredictionCutoff(
            game_id=canonical_cutoff.game_id,
            kickoff=canonical_cutoff.kickoff,
            prediction_time=actual_kickoff - timedelta(minutes=5),
        )
        manifest = build_snapshot_manifest(
            cutoff=stale_cutoff,
            inputs=(_input("one", stale_cutoff, "a"),),
            feature_spec=_feature_spec(),
        )

        with pytest.raises(PITSnapshotConflictError, match="must match retrospective"):
            record_snapshot(connection, manifest)
