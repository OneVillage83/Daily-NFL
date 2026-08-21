import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest

from daily_nfl.domain import AvailabilityConfidence, AvailabilityMethod, GameId
from daily_nfl.persistence import SCHEMA_VERSION, apply_migrations, open_database
from daily_nfl.persistence.identity_schema import IDENTITY_RECONCILIATION_SCHEMA_SQL
from daily_nfl.persistence.schema import INITIAL_SCHEMA_SQL
from daily_nfl.pit import PredictionCutoff, schedule_state_as_of
from daily_nfl.providers import NFLVERSE_DESCRIPTOR, record_provider
from daily_nfl.reconciliation import (
    IdentityRepository,
    game_id_for_event,
    new_event_id,
    new_franchise_id,
    team_season_id_for,
)

COMPETITION_ID = "core-competition-nfl"


def _insert_game(connection: sqlite3.Connection) -> tuple[GameId, datetime]:
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
    return game_id, kickoff


def _insert_schedule_observation(
    connection: sqlite3.Connection,
    *,
    observation_id: str,
    game_id: GameId,
    status: str,
    kickoff: datetime,
    available_at: datetime,
    provider_revision: str,
) -> None:
    connection.execute(
        """
        INSERT INTO schedule_observations(
            observation_id,
            game_id,
            provider_id,
            provider_game_id,
            status,
            scheduled_kickoff,
            observed_at,
            ingested_at,
            available_at,
            availability_method,
            availability_confidence,
            provider_revision
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            observation_id,
            str(game_id),
            "nflverse",
            "fixture-game",
            status,
            kickoff.isoformat(),
            available_at.isoformat(),
            (available_at + timedelta(seconds=1)).isoformat(),
            available_at.isoformat(),
            AvailabilityMethod.SOURCE_TIMESTAMP.value,
            AvailabilityConfidence.HIGH.value,
            provider_revision,
        ),
    )


def test_version_two_database_migrates_to_pit_schema(tmp_path: Path) -> None:
    database = tmp_path / "v2.db"

    with open_database(database) as connection:
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
        connection.commit()

        assert apply_migrations(connection) == SCHEMA_VERSION
        tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

    assert {
        "pit_snapshots",
        "pit_snapshot_inputs",
        "pit_snapshot_seals",
        "possession_segments",
    }.issubset(tables)


def test_schedule_as_of_switches_only_after_revision_available_at(tmp_path: Path) -> None:
    database = tmp_path / "pit.db"

    with open_database(database) as connection:
        apply_migrations(connection)
        record_provider(connection, NFLVERSE_DESCRIPTOR)
        game_id, kickoff = _insert_game(connection)
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
        first_available = kickoff - timedelta(hours=5)
        correction_available = kickoff - timedelta(hours=2)
        _insert_schedule_observation(
            connection,
            observation_id="schedule-v1",
            game_id=game_id,
            status="SCHEDULED",
            kickoff=kickoff,
            available_at=first_available,
            provider_revision="v1",
        )
        _insert_schedule_observation(
            connection,
            observation_id="schedule-v2",
            game_id=game_id,
            status="POSTPONED",
            kickoff=kickoff,
            available_at=correction_available,
            provider_revision="v2",
        )

        early = schedule_state_as_of(
            connection,
            game_id=game_id,
            cutoff=early_cutoff,
        )
        later = schedule_state_as_of(
            connection,
            game_id=game_id,
            cutoff=later_cutoff,
        )

    assert early is not None
    assert later is not None
    assert early.observation_id == "schedule-v1"
    assert early.status == "SCHEDULED"
    assert later.observation_id == "schedule-v2"
    assert later.status == "POSTPONED"


def test_schedule_query_rejects_mismatched_cutoff_game(tmp_path: Path) -> None:
    database = tmp_path / "pit.db"

    with open_database(database) as connection:
        apply_migrations(connection)
        record_provider(connection, NFLVERSE_DESCRIPTOR)
        game_id, kickoff = _insert_game(connection)
        cutoff = PredictionCutoff(
            game_id=GameId("gam_other"),
            kickoff=kickoff,
            prediction_time=kickoff - timedelta(hours=2),
        )

        with pytest.raises(ValueError, match="must match"):
            schedule_state_as_of(connection, game_id=game_id, cutoff=cutoff)
