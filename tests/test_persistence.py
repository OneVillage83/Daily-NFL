import sqlite3
from pathlib import Path

import pytest

from daily_nfl.persistence import (
    SCHEMA_VERSION,
    apply_migrations,
    current_schema_version,
    foreign_keys_enabled,
    integrity_ok,
    open_database,
)


def test_clean_database_initializes_to_current_schema(tmp_path: Path) -> None:
    database = tmp_path / "daily-nfl.db"

    with open_database(database) as connection:
        apply_migrations(connection)
        assert current_schema_version(connection) == SCHEMA_VERSION
        assert foreign_keys_enabled(connection)
        assert integrity_ok(connection)

        tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert {
            "schema_migrations",
            "providers",
            "raw_evidence",
            "entity_crosswalk",
            "franchises",
            "team_seasons",
            "persons",
            "players",
            "games",
            "schedule_observations",
            "possessions",
            "drives",
            "plays",
            "play_observations",
            "participation_observations",
            "penalty_observations",
            "game_result_observations",
            "game_results",
            "game_result_sources",
        }.issubset(tables)


def test_migrations_are_idempotent(tmp_path: Path) -> None:
    database = tmp_path / "daily-nfl.db"

    with open_database(database) as connection:
        first = apply_migrations(connection)
        second = apply_migrations(connection)

        assert first == SCHEMA_VERSION
        assert second == SCHEMA_VERSION
        row = connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()
        assert row is not None
        assert row[0] == SCHEMA_VERSION


def test_foreign_keys_are_enforced(tmp_path: Path) -> None:
    database = tmp_path / "daily-nfl.db"

    with open_database(database) as connection:
        apply_migrations(connection)
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO team_seasons(team_season_id, franchise_id, season) "
                "VALUES (?, ?, ?)",
                ("team-2026", "missing-franchise", 2026),
            )


def test_raw_evidence_is_append_only(tmp_path: Path) -> None:
    database = tmp_path / "daily-nfl.db"

    with open_database(database) as connection:
        apply_migrations(connection)
        connection.execute(
            "INSERT INTO providers(provider_id, name, provider_type) VALUES (?, ?, ?)",
            ("provider-1", "Fixture Provider", "TEST"),
        )
        connection.execute(
            """
            INSERT INTO raw_evidence(
                evidence_id,
                provider_id,
                endpoint_category,
                content_type,
                sha256,
                object_path,
                ingested_at,
                available_at,
                availability_method,
                availability_confidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "evidence-1",
                "provider-1",
                "schedule",
                "application/json",
                "abc123",
                "raw/provider-1/schedule/abc123.json",
                "2026-08-20T20:00:00Z",
                "2026-08-20T20:00:00Z",
                "OUR_OBSERVATION_TIME",
                "HIGH",
            ),
        )

        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE raw_evidence SET object_path = ? WHERE evidence_id = ?",
                ("changed.json", "evidence-1"),
            )

        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "DELETE FROM raw_evidence WHERE evidence_id = ?",
                ("evidence-1",),
            )


def test_game_results_preserve_observations_canonical_revisions_and_sources(
    tmp_path: Path,
) -> None:
    database = tmp_path / "daily-nfl.db"

    with open_database(database) as connection:
        apply_migrations(connection)
        connection.execute(
            "INSERT INTO providers(provider_id, name, provider_type) VALUES (?, ?, ?)",
            ("provider-1", "Fixture Provider", "TEST"),
        )
        connection.execute(
            "INSERT INTO franchises(franchise_id, canonical_name) VALUES (?, ?)",
            ("home-franchise", "Home"),
        )
        connection.execute(
            "INSERT INTO franchises(franchise_id, canonical_name) VALUES (?, ?)",
            ("away-franchise", "Away"),
        )
        connection.execute(
            "INSERT INTO team_seasons(team_season_id, franchise_id, season) VALUES (?, ?, ?)",
            ("home-2026", "home-franchise", 2026),
        )
        connection.execute(
            "INSERT INTO team_seasons(team_season_id, franchise_id, season) VALUES (?, ?, ?)",
            ("away-2026", "away-franchise", 2026),
        )
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
                scheduled_kickoff
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "game-1",
                "event-1",
                2026,
                "REGULAR",
                1,
                "NFL_2026",
                "home-2026",
                "away-2026",
                "2026-09-10T17:20:00Z",
            ),
        )

        for revision, home_points in ((1, 27), (2, 28)):
            observation_id = f"provider-result-{revision}"
            result_id = f"canonical-result-{revision}"
            connection.execute(
                """
                INSERT INTO game_result_observations(
                    result_observation_id,
                    game_id,
                    provider_id,
                    provider_revision,
                    home_points_final,
                    away_points_final,
                    ingested_at,
                    available_at,
                    availability_method,
                    availability_confidence
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    observation_id,
                    "game-1",
                    "provider-1",
                    str(revision),
                    home_points,
                    24,
                    "2026-09-11T00:00:00Z",
                    "2026-09-11T00:00:00Z",
                    "OUR_OBSERVATION_TIME",
                    "HIGH",
                ),
            )
            connection.execute(
                """
                INSERT INTO game_results(
                    result_id,
                    game_id,
                    revision,
                    home_points_final,
                    away_points_final,
                    reconciliation_method,
                    reconciliation_confidence,
                    derived_at,
                    available_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result_id,
                    "game-1",
                    revision,
                    home_points,
                    24,
                    "SINGLE_SOURCE",
                    1.0,
                    "2026-09-11T00:00:00Z",
                    "2026-09-11T00:00:00Z",
                ),
            )
            connection.execute(
                "INSERT INTO game_result_sources(result_id, result_observation_id) VALUES (?, ?)",
                (result_id, observation_id),
            )

        canonical_rows = connection.execute(
            "SELECT revision, home_points_final FROM game_results ORDER BY revision"
        ).fetchall()
        observation_count = connection.execute(
            "SELECT COUNT(*) FROM game_result_observations"
        ).fetchone()
        source_count = connection.execute("SELECT COUNT(*) FROM game_result_sources").fetchone()
        current = connection.execute(
            "SELECT revision, home_points_final FROM current_game_results WHERE game_id = ?",
            ("game-1",),
        ).fetchone()

        assert [(row[0], row[1]) for row in canonical_rows] == [(1, 27), (2, 28)]
        assert observation_count is not None and observation_count[0] == 2
        assert source_count is not None and source_count[0] == 2
        assert current is not None
        assert (current[0], current[1]) == (2, 28)

        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE game_results SET home_points_final = 30 WHERE result_id = ?",
                ("canonical-result-1",),
            )
