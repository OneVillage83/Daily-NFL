import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest

from daily_nfl.domain import AvailabilityConfidence, AvailabilityMethod, GameId
from daily_nfl.persistence import apply_migrations, open_database
from daily_nfl.pit import (
    PITHorizon,
    PITInputKind,
    PITInputRef,
    PredictionCutoff,
    build_snapshot_manifest,
    record_snapshot,
)
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

    left = build_snapshot_manifest(cutoff=cutoff, inputs=(first, second))
    right = build_snapshot_manifest(cutoff=cutoff, inputs=(second, first))

    assert left.snapshot_id == right.snapshot_id
    assert left.manifest_sha256 == right.manifest_sha256
    assert [input_ref.input_id for input_ref in left.inputs] == ["first", "second"]


def test_changing_one_input_changes_snapshot_identity() -> None:
    kickoff = datetime(2026, 9, 10, 20, 20, tzinfo=UTC)
    cutoff = PredictionCutoff.from_horizon(
        game_id=_fixture_game_id(),
        kickoff=kickoff,
        horizon=PITHorizon.T_90M,
    )
    original = build_snapshot_manifest(cutoff=cutoff, inputs=(_input("one", cutoff, "a"),))
    changed = build_snapshot_manifest(cutoff=cutoff, inputs=(_input("one", cutoff, "b"),))

    assert original.snapshot_id != changed.snapshot_id


def test_snapshot_persistence_is_idempotent_sealed_and_append_only(tmp_path: Path) -> None:
    database = tmp_path / "pit.db"

    with open_database(database) as connection:
        apply_migrations(connection)
        _, cutoff = _insert_game(connection)
        inputs = (
            _input("first", cutoff, "a"),
            _input("second", cutoff, "b"),
        )
        manifest = build_snapshot_manifest(cutoff=cutoff, inputs=inputs)
        record_snapshot(connection, manifest)
        record_snapshot(connection, manifest)

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
