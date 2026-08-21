import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

from daily_nfl.domain import FranchiseId
from daily_nfl.persistence import apply_migrations, open_database
from daily_nfl.providers import NFLVERSE_DESCRIPTOR, record_provider
from daily_nfl.reconciliation import (
    GAME_ENTITY_TYPE,
    GameIdentityHint,
    IdentityReconciler,
    IdentityRepository,
    MatchMethod,
    ReconciliationStatus,
    game_id_for_event,
    new_event_id,
    new_franchise_id,
    team_season_id_for,
)


@contextmanager
def _open_identity_database(path: Path) -> Iterator[sqlite3.Connection]:
    with open_database(path) as connection:
        apply_migrations(connection)
        record_provider(connection, NFLVERSE_DESCRIPTOR)
        yield connection


def _insert_fixture_game(
    connection: sqlite3.Connection,
    *,
    home: FranchiseId,
    away: FranchiseId,
    season: int,
    week: int,
    kickoff: datetime,
    token: str,
) -> str:
    repository = IdentityRepository(connection)
    repository.ensure_franchise(home)
    repository.ensure_franchise(away)
    home_team = team_season_id_for(home, season)
    away_team = team_season_id_for(away, season)
    repository.ensure_team_season(home_team, home, season)
    repository.ensure_team_season(away_team, away, season)
    event_id = new_event_id(UUID(token))
    game_id = game_id_for_event(event_id)
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
            str(game_id),
            str(event_id),
            season,
            "REGULAR",
            week,
            "NFL_2026",
            str(home_team),
            str(away_team),
            kickoff.isoformat(),
        ),
    )
    return str(game_id)


def test_game_reconciliation_uses_composite_then_existing_crosswalk(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"
    home = new_franchise_id(UUID("11111111-1111-1111-1111-111111111111"))
    away = new_franchise_id(UUID("22222222-2222-2222-2222-222222222222"))
    kickoff = datetime(2026, 9, 10, 17, 20, tzinfo=UTC)

    with _open_identity_database(database) as connection:
        game_id = _insert_fixture_game(
            connection,
            home=home,
            away=away,
            season=2026,
            week=1,
            kickoff=kickoff,
            token="33333333-3333-3333-3333-333333333333",
        )
        reconciler = IdentityReconciler(IdentityRepository(connection))
        hint = GameIdentityHint(
            season=2026,
            season_phase="REGULAR",
            week=1,
            home_team_season_id=team_season_id_for(home, 2026),
            away_team_season_id=team_season_id_for(away, 2026),
            scheduled_kickoff=kickoff,
        )

        first = reconciler.reconcile_game(
            provider_id="nflverse",
            external_game_id="2026_01_AWAY_HOME",
            hint=hint,
        )
        second = reconciler.reconcile_game(
            provider_id="nflverse",
            external_game_id="2026_01_AWAY_HOME",
            hint=hint,
        )

        assert first.selected_canonical_entity_id == game_id
        assert first.match_method is MatchMethod.CANONICAL_COMPOSITE
        assert second.selected_canonical_entity_id == game_id
        assert second.match_method is MatchMethod.EXISTING_CROSSWALK


def test_game_reconciliation_refuses_ambiguous_candidates(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"
    home = new_franchise_id(UUID("11111111-1111-1111-1111-111111111111"))
    away = new_franchise_id(UUID("22222222-2222-2222-2222-222222222222"))
    kickoff = datetime(2026, 9, 10, 17, 20, tzinfo=UTC)

    with _open_identity_database(database) as connection:
        _insert_fixture_game(
            connection,
            home=home,
            away=away,
            season=2026,
            week=1,
            kickoff=kickoff,
            token="33333333-3333-3333-3333-333333333333",
        )
        _insert_fixture_game(
            connection,
            home=home,
            away=away,
            season=2026,
            week=1,
            kickoff=kickoff + timedelta(hours=1),
            token="44444444-4444-4444-4444-444444444444",
        )
        reconciler = IdentityReconciler(IdentityRepository(connection))
        decision = reconciler.reconcile_game(
            provider_id="nflverse",
            external_game_id="ambiguous-game",
            hint=GameIdentityHint(
                season=2026,
                season_phase="REGULAR",
                week=1,
                home_team_season_id=team_season_id_for(home, 2026),
                away_team_season_id=team_season_id_for(away, 2026),
                scheduled_kickoff=kickoff,
            ),
        )

        assert decision.status is ReconciliationStatus.AMBIGUOUS
        assert decision.selected_canonical_entity_id is None
        assert len(decision.candidates) == 2
        count = connection.execute(
            "SELECT COUNT(*) FROM entity_crosswalk WHERE provider_entity_type = ?",
            (GAME_ENTITY_TYPE,),
        ).fetchone()[0]
        assert count == 0


def test_game_reconciliation_without_week_uses_kickoff_tolerance(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"
    home = new_franchise_id(UUID("11111111-1111-1111-1111-111111111111"))
    away = new_franchise_id(UUID("22222222-2222-2222-2222-222222222222"))
    kickoff = datetime(2026, 9, 10, 17, 20, tzinfo=UTC)

    with _open_identity_database(database) as connection:
        _insert_fixture_game(
            connection,
            home=home,
            away=away,
            season=2026,
            week=1,
            kickoff=kickoff,
            token="33333333-3333-3333-3333-333333333333",
        )
        decision = IdentityReconciler(IdentityRepository(connection)).reconcile_game(
            provider_id="nflverse",
            external_game_id="outside-window",
            hint=GameIdentityHint(
                season=2026,
                season_phase="REGULAR",
                week=None,
                home_team_season_id=team_season_id_for(home, 2026),
                away_team_season_id=team_season_id_for(away, 2026),
                scheduled_kickoff=kickoff + timedelta(days=30),
            ),
            max_kickoff_delta=timedelta(days=7),
        )

        assert decision.status is ReconciliationStatus.UNRESOLVED
        assert decision.selected_canonical_entity_id is None
