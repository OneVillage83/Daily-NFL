from pathlib import Path

import pytest

from daily_nfl.persistence import SchemaVersionError, apply_migrations, open_database


def test_newer_unknown_schema_is_refused(tmp_path: Path) -> None:
    database = tmp_path / "future.db"

    with open_database(database) as connection:
        connection.execute(
            """
            CREATE TABLE schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                applied_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "INSERT INTO schema_migrations(version, name, applied_at) VALUES (?, ?, ?)",
            (999, "future_schema", "2099-01-01T00:00:00Z"),
        )

        with pytest.raises(SchemaVersionError, match="newer than supported"):
            apply_migrations(connection)


def test_unversioned_non_empty_database_is_refused(tmp_path: Path) -> None:
    database = tmp_path / "wrong-database.db"

    with open_database(database) as connection:
        connection.execute("CREATE TABLE unrelated_data(id INTEGER PRIMARY KEY)")

        with pytest.raises(SchemaVersionError, match="unversioned or incomplete"):
            apply_migrations(connection)


def test_observation_tables_have_append_only_triggers(tmp_path: Path) -> None:
    database = tmp_path / "daily-nfl.db"

    with open_database(database) as connection:
        apply_migrations(connection)
        trigger_rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger'"
        ).fetchall()

    triggers = {str(row[0]) for row in trigger_rows}
    protected_tables = {
        "raw_evidence",
        "schedule_observations",
        "play_observations",
        "participation_observations",
        "penalty_observations",
        "game_result_observations",
        "game_results",
        "game_result_sources",
    }
    expected = {
        f"{table}_{operation}"
        for table in protected_tables
        for operation in ("no_update", "no_delete")
    }

    assert expected.issubset(triggers)
