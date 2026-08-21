from pathlib import Path
from uuid import UUID

from daily_nfl.persistence import apply_migrations, open_database
from daily_nfl.providers import NFLVERSE_DESCRIPTOR, record_provider
from daily_nfl.reconciliation import (
    PLAY_ENTITY_TYPE,
    ExternalIdentity,
    IdentityReconciler,
    IdentityRepository,
    PlayIdentityHint,
    game_id_for_event,
    new_event_id,
    new_franchise_id,
    play_id_for,
    possession_id_for,
    possession_segment_id_for,
    team_season_id_for,
)

COMPETITION_ID = "core-competition-nfl"


def _seed_game_with_first_play(
    repository: IdentityRepository,
    *,
    event_uuid: UUID,
    week: int,
) -> tuple[str, str]:
    connection = repository.connection
    home = new_franchise_id(UUID("11111111-1111-1111-1111-111111111111"))
    away = new_franchise_id(UUID("22222222-2222-2222-2222-222222222222"))
    repository.ensure_franchise(home)
    repository.ensure_franchise(away)
    home_team = team_season_id_for(home, 2026)
    away_team = team_season_id_for(away, 2026)
    repository.ensure_team_season(home_team, home, 2026)
    repository.ensure_team_season(away_team, away, 2026)

    event_id = new_event_id(event_uuid)
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
            week,
            "NFL_2026",
            str(home_team),
            str(away_team),
            f"2026-09-{9 + week:02d}T17:20:00Z",
            COMPETITION_ID,
        ),
    )
    possession_id = possession_id_for(game_id, 1)
    segment_id = possession_segment_id_for(game_id, 1)
    play_id = play_id_for(game_id, 1)
    connection.execute(
        """
        INSERT INTO possessions(
            possession_id, game_id, offense_team_season_id, defense_team_season_id
        ) VALUES (?, ?, ?, ?)
        """,
        (str(possession_id), str(game_id), str(home_team), str(away_team)),
    )
    connection.execute(
        """
        INSERT INTO possession_segments(
            possession_segment_id, game_id, canonical_sequence,
            offense_team_season_id, defense_team_season_id
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (str(segment_id), str(game_id), 1, str(home_team), str(away_team)),
    )
    connection.execute(
        """
        INSERT INTO plays(
            play_id, game_id, possession_id, canonical_sequence, possession_segment_id
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (str(play_id), str(game_id), str(possession_id), 1, str(segment_id)),
    )
    return str(game_id), str(play_id)


def test_same_provider_play_id_can_exist_in_two_games(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"

    with open_database(database) as connection:
        apply_migrations(connection)
        record_provider(connection, NFLVERSE_DESCRIPTOR)
        repository = IdentityRepository(connection)
        reconciler = IdentityReconciler(repository)
        first_game, first_play = _seed_game_with_first_play(
            repository,
            event_uuid=UUID("33333333-3333-3333-3333-333333333333"),
            week=1,
        )
        second_game, second_play = _seed_game_with_first_play(
            repository,
            event_uuid=UUID("44444444-4444-4444-4444-444444444444"),
            week=2,
        )

        first = reconciler.reconcile_play(
            provider_id="nflverse",
            external_play_id="1",
            hint=PlayIdentityHint(game_id=first_game, canonical_sequence=1),
        )
        second = reconciler.reconcile_play(
            provider_id="nflverse",
            external_play_id="1",
            hint=PlayIdentityHint(game_id=second_game, canonical_sequence=1),
        )

        assert first.selected_canonical_entity_id == first_play
        assert second.selected_canonical_entity_id == second_play
        assert first_play != second_play

        first_bindings = repository.active_crosswalks(
            ExternalIdentity("nflverse", PLAY_ENTITY_TYPE, "1", scope=first_game)
        )
        second_bindings = repository.active_crosswalks(
            ExternalIdentity("nflverse", PLAY_ENTITY_TYPE, "1", scope=second_game)
        )
        assert len(first_bindings) == len(second_bindings) == 1
        assert first_bindings[0].canonical_entity_id == first_play
        assert second_bindings[0].canonical_entity_id == second_play
