import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest

from daily_nfl.domain import AvailabilityConfidence, AvailabilityMethod, GameId
from daily_nfl.persistence import SCHEMA_VERSION, apply_migrations, open_database
from daily_nfl.persistence.identity_schema import IDENTITY_RECONCILIATION_SCHEMA_SQL
from daily_nfl.persistence.schema import INITIAL_SCHEMA_SQL
from daily_nfl.pit import PITSelectionConflictError, PredictionCutoff, schedule_state_as_of
from daily_nfl.providers import (
    NFLVERSE_DESCRIPTOR,
    ProviderDescriptor,
    record_provider,
)
from daily_nfl.reconciliation import (
    IdentityRepository,
    game_id_for_event,
    new_event_id,
    new_franchise_id,
    team_season_id_for,
)

COMPETITION_ID = "core-competition-nfl"
ALT_PROVIDER = ProviderDescriptor(
    provider_id="fixture-alt",
    name="Fixture Alternate Schedule Provider",
    provider_type="TEST",
    parser_version="fixture-v1",
)


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
    provider_id: str = "nflverse",
    actual_kickoff: datetime | None = None,
    neutral_site: bool | None = None,
    schedule_version: str | None = None,
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
            actual_kickoff,
            neutral_site,
            schedule_version,
            observed_at,
            ingested_at,
            available_at,
            availability_method,
            availability_confidence,
            provider_revision
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            observation_id,
            str(game_id),
            provider_id,
            "fixture-game",
            status,
            kickoff.isoformat(),
            actual_kickoff.isoformat() if actual_kickoff is not None else None,
            int(neutral_site) if neutral_site is not None else None,
            schedule_version,
            available_at.isoformat(),
            (available_at + timedelta(seconds=1)).isoformat(),
            available_at.isoformat(),
            AvailabilityMethod.SOURCE_TIMESTAMP.value,
            AvailabilityConfidence.HIGH.value,
            provider_revision,
        ),
    )


def test_version_two_database_migrates_to_current_pit_schema(tmp_path: Path) -> None:
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
        snapshot_columns = {
            str(row[1])
            for row in connection.execute("PRAGMA table_info(pit_snapshots)").fetchall()
        }
        input_columns = {
            str(row[1])
            for row in connection.execute("PRAGMA table_info(pit_snapshot_inputs)").fetchall()
        }

    assert {
        "pit_snapshots",
        "pit_snapshot_inputs",
        "pit_snapshot_seals",
        "possession_segments",
    }.issubset(tables)
    assert {
        "feature_contract",
        "feature_version",
        "feature_values_json",
        "coverage_report_json",
        "missing_features_json",
        "pit_validation_result",
        "input_count",
    }.issubset(snapshot_columns)
    assert {
        "evidence_observation_id",
        "provider_id",
        "provider_revision",
        "provider_schema_version",
        "parser_version",
        "raw_sha256",
    }.issubset(input_columns)


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
            neutral_site=False,
            schedule_version="schedule-1",
        )
        _insert_schedule_observation(
            connection,
            observation_id="schedule-v2",
            game_id=game_id,
            status="POSTPONED",
            kickoff=kickoff,
            available_at=correction_available,
            provider_revision="v2",
            neutral_site=False,
            schedule_version="schedule-2",
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
    assert early.schedule_version == "schedule-1"
    assert early.neutral_site is False
    assert later.observation_id == "schedule-v2"
    assert later.status == "POSTPONED"
    assert later.schedule_version == "schedule-2"
    assert later.provider_revision == "v2"


def test_schedule_as_of_preserves_actual_kickoff_and_all_supporting_sources(
    tmp_path: Path,
) -> None:
    database = tmp_path / "pit.db"

    with open_database(database) as connection:
        apply_migrations(connection)
        record_provider(connection, NFLVERSE_DESCRIPTOR)
        record_provider(connection, ALT_PROVIDER)
        game_id, kickoff = _insert_game(connection)
        cutoff = PredictionCutoff(
            game_id=game_id,
            kickoff=kickoff,
            prediction_time=kickoff - timedelta(minutes=30),
        )
        available = kickoff - timedelta(hours=2)
        for provider_id, suffix in (("nflverse", "a"), ("fixture-alt", "b")):
            _insert_schedule_observation(
                connection,
                observation_id=f"schedule-{suffix}",
                game_id=game_id,
                status="SCHEDULED",
                kickoff=kickoff,
                actual_kickoff=kickoff,
                available_at=available,
                provider_revision="r1",
                provider_id=provider_id,
                neutral_site=True,
                schedule_version="schedule-v1",
            )

        state = schedule_state_as_of(connection, game_id=game_id, cutoff=cutoff)

    assert state is not None
    assert state.actual_kickoff == kickoff
    assert state.neutral_site is True
    assert state.schedule_version == "schedule-v1"
    assert len(state.supporting_inputs) == 2
    assert {item.provider_id for item in state.supporting_inputs} == {
        "nflverse",
        "fixture-alt",
    }


def test_schedule_as_of_fails_closed_when_providers_disagree(tmp_path: Path) -> None:
    database = tmp_path / "pit.db"

    with open_database(database) as connection:
        apply_migrations(connection)
        record_provider(connection, NFLVERSE_DESCRIPTOR)
        record_provider(connection, ALT_PROVIDER)
        game_id, kickoff = _insert_game(connection)
        cutoff = PredictionCutoff(
            game_id=game_id,
            kickoff=kickoff,
            prediction_time=kickoff - timedelta(hours=1),
        )
        available = kickoff - timedelta(hours=2)
        _insert_schedule_observation(
            connection,
            observation_id="schedule-a",
            game_id=game_id,
            status="SCHEDULED",
            kickoff=kickoff,
            available_at=available,
            provider_revision="r1",
            provider_id="nflverse",
        )
        _insert_schedule_observation(
            connection,
            observation_id="schedule-b",
            game_id=game_id,
            status="POSTPONED",
            kickoff=kickoff,
            available_at=available,
            provider_revision="r1",
            provider_id="fixture-alt",
        )

        with pytest.raises(PITSelectionConflictError, match="conflicting provider schedule"):
            schedule_state_as_of(connection, game_id=game_id, cutoff=cutoff)


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
