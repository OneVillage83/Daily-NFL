import sqlite3
from pathlib import Path

import pytest

from daily_nfl.persistence import SCHEMA_VERSION, apply_migrations, open_database
from daily_nfl.persistence.identity_schema import IDENTITY_RECONCILIATION_SCHEMA_SQL
from daily_nfl.persistence.pit_schema import PIT_SNAPSHOT_SCHEMA_SQL
from daily_nfl.persistence.schema import INITIAL_SCHEMA_SQL

COMPETITION_ID = "core-competition-nfl"


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {
        str(row[1])
        for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
    }


def _apply_legacy_v3(connection: sqlite3.Connection) -> None:
    connection.executescript(INITIAL_SCHEMA_SQL)
    connection.execute(
        "INSERT INTO schema_migrations(version, name) VALUES (?, ?)",
        (1, "initial_persistence_foundation"),
    )
    connection.executescript(IDENTITY_RECONCILIATION_SCHEMA_SQL)
    connection.execute(
        "INSERT INTO schema_migrations(version, name) VALUES (?, ?)",
        (2, "identity_reconciliation_foundation"),
    )
    connection.executescript(PIT_SNAPSHOT_SCHEMA_SQL)
    connection.execute(
        "INSERT INTO schema_migrations(version, name) VALUES (?, ?)",
        (3, "historical_pit_snapshot_foundation"),
    )
    connection.commit()


def _insert_legacy_identity_rows(connection: sqlite3.Connection) -> None:
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
            "game-legacy",
            "event-legacy",
            2026,
            "REGULAR",
            1,
            "NFL_2026",
            "home-2026",
            "away-2026",
            "2026-09-13T20:20:00Z",
        ),
    )
    connection.execute(
        """
        INSERT INTO possessions(
            possession_id,
            game_id,
            offense_team_season_id,
            defense_team_season_id
        ) VALUES (?, ?, ?, ?)
        """,
        ("pos-legacy", "game-legacy", "home-2026", "away-2026"),
    )
    connection.execute(
        """
        INSERT INTO drives(drive_id, game_id, possession_id, canonical_sequence)
        VALUES (?, ?, ?, ?)
        """,
        ("drive-legacy", "game-legacy", "pos-legacy", 1),
    )
    connection.execute(
        """
        INSERT INTO plays(play_id, game_id, drive_id, possession_id, canonical_sequence)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("play-legacy", "game-legacy", "drive-legacy", "pos-legacy", 1),
    )


def test_m2_schema_represents_certified_m1_and_f4_contracts(tmp_path: Path) -> None:
    database = tmp_path / "m2.db"

    with open_database(database) as connection:
        assert apply_migrations(connection) == SCHEMA_VERSION

        assert "competition_id" in _columns(connection, "games")
        assert {
            "actual_kickoff",
            "neutral_site",
            "schedule_version",
        }.issubset(_columns(connection, "schedule_observations"))
        assert "possession_segment_id" in _columns(connection, "drives")
        assert "possession_segment_id" in _columns(connection, "plays")
        assert {
            "participation_id",
            "effective_at",
            "published_at",
            "provider_revision",
        }.issubset(_columns(connection, "participation_observations"))
        assert {
            "penalty_id",
            "effective_at",
            "published_at",
            "provider_revision",
        }.issubset(_columns(connection, "penalty_observations"))
        assert "final_at" in _columns(connection, "game_results")

        tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert {
            "possession_segments",
            "play_events",
            "participations",
            "penalties",
        }.issubset(tables)


def test_new_game_write_requires_canonical_competition_id(tmp_path: Path) -> None:
    database = tmp_path / "new-write.db"

    with open_database(database) as connection:
        apply_migrations(connection)
        connection.execute(
            "INSERT INTO franchises(franchise_id) VALUES ('home-franchise')"
        )
        connection.execute(
            "INSERT INTO franchises(franchise_id) VALUES ('away-franchise')"
        )
        connection.execute(
            "INSERT INTO team_seasons(team_season_id, franchise_id, season) "
            "VALUES ('home-2026', 'home-franchise', 2026)"
        )
        connection.execute(
            "INSERT INTO team_seasons(team_season_id, franchise_id, season) "
            "VALUES ('away-2026', 'away-franchise', 2026)"
        )

        with pytest.raises(sqlite3.IntegrityError, match="competition_id"):
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
                    "game-no-competition",
                    "event-no-competition",
                    2026,
                    "REGULAR",
                    1,
                    "NFL_2026",
                    "home-2026",
                    "away-2026",
                    "2026-09-13T20:20:00Z",
                ),
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
                scheduled_kickoff,
                competition_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "game-valid",
                "event-valid",
                2026,
                "REGULAR",
                1,
                "NFL_2026",
                "home-2026",
                "away-2026",
                "2026-09-13T20:20:00Z",
                COMPETITION_ID,
            ),
        )

        stored = connection.execute(
            "SELECT competition_id FROM games WHERE game_id='game-valid'"
        ).fetchone()
        assert stored is not None and stored[0] == COMPETITION_ID


def test_v3_migration_preserves_legacy_rows_without_fabricating_new_identity(
    tmp_path: Path,
) -> None:
    database = tmp_path / "legacy-v3.db"

    with open_database(database) as connection:
        _apply_legacy_v3(connection)
        _insert_legacy_identity_rows(connection)
        connection.commit()

        assert apply_migrations(connection) == SCHEMA_VERSION

        game = connection.execute(
            "SELECT competition_id FROM games WHERE game_id='game-legacy'"
        ).fetchone()
        drive = connection.execute(
            "SELECT possession_segment_id FROM drives WHERE drive_id='drive-legacy'"
        ).fetchone()
        play = connection.execute(
            "SELECT possession_segment_id FROM plays WHERE play_id='play-legacy'"
        ).fetchone()

        assert game is not None and game[0] is None
        assert drive is not None and drive[0] is None
        assert play is not None and play[0] is None

        connection.execute(
            "UPDATE games SET competition_id=? WHERE game_id='game-legacy'",
            (COMPETITION_ID,),
        )
        connection.execute(
            """
            INSERT INTO possession_segments(
                possession_segment_id,
                game_id,
                canonical_sequence,
                offense_team_season_id,
                defense_team_season_id
            ) VALUES (?, ?, ?, ?, ?)
            """,
            ("segment-1", "game-legacy", 1, "home-2026", "away-2026"),
        )
        connection.execute(
            "UPDATE drives SET possession_segment_id='segment-1' WHERE drive_id='drive-legacy'"
        )
        connection.execute(
            "UPDATE plays SET possession_segment_id='segment-1' WHERE play_id='play-legacy'"
        )

        upgraded = connection.execute(
            """
            SELECT g.competition_id, d.possession_segment_id, p.possession_segment_id
            FROM games g
            JOIN drives d ON d.game_id = g.game_id
            JOIN plays p ON p.drive_id = d.drive_id
            WHERE g.game_id='game-legacy'
            """
        ).fetchone()
        assert upgraded is not None
        assert tuple(upgraded) == (COMPETITION_ID, "segment-1", "segment-1")

        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE games SET competition_id='different' WHERE game_id='game-legacy'"
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE drives SET possession_segment_id=NULL WHERE drive_id='drive-legacy'"
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE plays SET canonical_sequence=2 WHERE play_id='play-legacy'"
            )


def test_new_participation_and_penalty_observations_require_canonical_identity(
    tmp_path: Path,
) -> None:
    database = tmp_path / "child-identity.db"

    with open_database(database) as connection:
        apply_migrations(connection)
        connection.execute(
            "INSERT INTO providers(provider_id, name, provider_type) VALUES ('p', 'P', 'TEST')"
        )
        connection.execute(
            "INSERT INTO franchises(franchise_id) VALUES ('home-franchise')"
        )
        connection.execute(
            "INSERT INTO franchises(franchise_id) VALUES ('away-franchise')"
        )
        connection.execute(
            "INSERT INTO team_seasons(team_season_id, franchise_id, season) "
            "VALUES ('home-2026', 'home-franchise', 2026)"
        )
        connection.execute(
            "INSERT INTO team_seasons(team_season_id, franchise_id, season) "
            "VALUES ('away-2026', 'away-franchise', 2026)"
        )
        connection.execute(
            "INSERT INTO persons(person_id) VALUES ('person-1')"
        )
        connection.execute(
            "INSERT INTO players(player_id, person_id) VALUES ('player-1', 'person-1')"
        )
        connection.execute(
            """
            INSERT INTO games(
                game_id, event_id, season, season_phase, week, ruleset_version,
                home_team_season_id, away_team_season_id, scheduled_kickoff,
                competition_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                "2026-09-13T20:20:00Z",
                COMPETITION_ID,
            ),
        )
        connection.execute(
            """
            INSERT INTO possession_segments(
                possession_segment_id, game_id, canonical_sequence,
                offense_team_season_id, defense_team_season_id
            ) VALUES ('segment-1', 'game-1', 1, 'home-2026', 'away-2026')
            """
        )
        connection.execute(
            """
            INSERT INTO plays(
                play_id, game_id, canonical_sequence, possession_segment_id
            ) VALUES ('play-1', 'game-1', 1, 'segment-1')
            """
        )

        with pytest.raises(sqlite3.IntegrityError, match="participation_id"):
            connection.execute(
                """
                INSERT INTO participation_observations(
                    observation_id, play_id, player_id, team_season_id, provider_id,
                    side, role, ingested_at, available_at,
                    availability_method, availability_confidence
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "participation-observation-missing-id",
                    "play-1",
                    "player-1",
                    "home-2026",
                    "p",
                    "OFFENSE",
                    "PASSER",
                    "2026-09-13T20:00:01Z",
                    "2026-09-13T20:00:00Z",
                    "SOURCE_TIMESTAMP",
                    "HIGH",
                ),
            )

        with pytest.raises(sqlite3.IntegrityError, match="penalty_id"):
            connection.execute(
                """
                INSERT INTO penalty_observations(
                    observation_id, play_id, team_season_id, provider_id,
                    penalty_type, disposition, ingested_at, available_at,
                    availability_method, availability_confidence
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "penalty-observation-missing-id",
                    "play-1",
                    "away-2026",
                    "p",
                    "Offside",
                    "ACCEPTED",
                    "2026-09-13T20:00:01Z",
                    "2026-09-13T20:00:00Z",
                    "SOURCE_TIMESTAMP",
                    "HIGH",
                ),
            )
