import sqlite3
from pathlib import Path
from uuid import UUID

import pytest

from daily_nfl.persistence import SCHEMA_VERSION, apply_migrations, open_database
from daily_nfl.persistence.migrations import MIGRATIONS
from daily_nfl.reconciliation import (
    IdentityRepository,
    game_id_for_event,
    new_event_id,
    new_franchise_id,
    team_season_id_for,
)

COMPETITION_ID = "core-competition-nfl"


def _apply_through_v6(connection: sqlite3.Connection) -> None:
    for migration in MIGRATIONS:
        if migration.version > 6:
            break
        escaped_name = migration.name.replace("'", "''")
        connection.executescript(
            "BEGIN IMMEDIATE;\n"
            f"{migration.sql}\n"
            "INSERT INTO schema_migrations(version, name) "
            f"VALUES ({migration.version}, '{escaped_name}');\n"
            "COMMIT;"
        )


def _seed_game(connection: sqlite3.Connection) -> str:
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
            "2026-09-10T20:20:00+00:00",
            COMPETITION_ID,
        ),
    )
    return str(game_id)


def _insert_m5_snapshot_row(
    connection: sqlite3.Connection,
    *,
    snapshot_id: str,
    game_id: str,
    input_count: int,
) -> None:
    coverage = (
        '{"coverage_fraction":1.0,"expected_feature_count":0,'
        '"missing_feature_count":0,"present_feature_count":0}'
    )
    connection.execute(
        """
        INSERT INTO pit_snapshots(
            snapshot_id, game_id, prediction_time, kickoff, horizon,
            policy_version, manifest_sha256, feature_contract, feature_version,
            feature_values_json, coverage_report_json, missing_features_json,
            pit_validation_result, input_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            snapshot_id,
            game_id,
            "2026-09-10T18:50:00Z",
            "2026-09-10T20:20:00Z",
            "T-90m",
            "NFL_PIT_POLICY_V1",
            "a" * 64,
            "M5_FIXTURE_V1",
            "1",
            "{}",
            coverage,
            "[]",
            "PASS",
            input_count,
        ),
    )


def test_v7_migration_preserves_legacy_v6_pit_snapshot(tmp_path: Path) -> None:
    database = tmp_path / "m4-to-m5.db"

    with open_database(database) as connection:
        _apply_through_v6(connection)
        game_id = _seed_game(connection)
        connection.execute(
            """
            INSERT INTO pit_snapshots(
                snapshot_id, game_id, prediction_time, kickoff, horizon,
                policy_version, manifest_sha256
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "pit_legacy",
                game_id,
                "2026-09-10T18:50:00Z",
                "2026-09-10T20:20:00Z",
                "T-90m",
                "NFL_PIT_POLICY_V1",
                "b" * 64,
            ),
        )
        connection.execute(
            "INSERT INTO pit_snapshot_seals(snapshot_id) VALUES ('pit_legacy')"
        )
        connection.commit()

        assert apply_migrations(connection) == SCHEMA_VERSION
        legacy = connection.execute(
            """
            SELECT snapshot_id, feature_contract, pit_validation_result, input_count
            FROM pit_snapshots
            WHERE snapshot_id = 'pit_legacy'
            """,
        ).fetchone()

    assert legacy is not None
    assert tuple(legacy) == ("pit_legacy", None, None, None)


def test_m5_snapshot_cannot_seal_until_declared_membership_is_complete(
    tmp_path: Path,
) -> None:
    database = tmp_path / "pit.db"

    with open_database(database) as connection:
        apply_migrations(connection)
        game_id = _seed_game(connection)
        _insert_m5_snapshot_row(
            connection,
            snapshot_id="pit_incomplete",
            game_id=game_id,
            input_count=1,
        )

        with pytest.raises(sqlite3.IntegrityError, match="membership is complete"):
            connection.execute(
                "INSERT INTO pit_snapshot_seals(snapshot_id) VALUES ('pit_incomplete')"
            )


def test_m5_snapshot_rejects_incomplete_raw_provenance(tmp_path: Path) -> None:
    database = tmp_path / "pit.db"

    with open_database(database) as connection:
        apply_migrations(connection)
        game_id = _seed_game(connection)
        _insert_m5_snapshot_row(
            connection,
            snapshot_id="pit_evidence",
            game_id=game_id,
            input_count=1,
        )

        with pytest.raises(sqlite3.IntegrityError, match="raw provenance must match"):
            connection.execute(
                """
                INSERT INTO pit_snapshot_inputs(
                    snapshot_id, input_kind, input_id, source_table,
                    available_at, availability_method, availability_confidence,
                    evidence_observation_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "pit_evidence",
                    "INJURY",
                    "fixture-input",
                    "fixture_source",
                    "2026-09-10T18:00:00Z",
                    "SOURCE_TIMESTAMP",
                    "HIGH",
                    "reo_missing",
                ),
            )
