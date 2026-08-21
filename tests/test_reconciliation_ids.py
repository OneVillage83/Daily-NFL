from uuid import UUID

from daily_nfl.reconciliation import (
    game_id_for_event,
    new_event_id,
    new_franchise_id,
    new_person_id,
    player_id_for_person,
    team_season_id_for,
)


def test_root_ids_are_opaque_and_provider_independent() -> None:
    franchise_id = new_franchise_id(UUID("11111111-1111-1111-1111-111111111111"))
    person_id = new_person_id(UUID("22222222-2222-2222-2222-222222222222"))
    event_id = new_event_id(UUID("33333333-3333-3333-3333-333333333333"))

    assert str(franchise_id).startswith("frn_")
    assert str(person_id).startswith("per_")
    assert str(event_id).startswith("evt_")
    assert "GSIS" not in str(person_id)
    assert "nflverse" not in str(franchise_id)


def test_dependent_ids_derive_only_from_canonical_parents() -> None:
    franchise_id = new_franchise_id(UUID("11111111-1111-1111-1111-111111111111"))
    person_id = new_person_id(UUID("22222222-2222-2222-2222-222222222222"))
    event_id = new_event_id(UUID("33333333-3333-3333-3333-333333333333"))

    assert team_season_id_for(franchise_id, 2026) == team_season_id_for(franchise_id, 2026)
    assert player_id_for_person(person_id) == player_id_for_person(person_id)
    assert game_id_for_event(event_id) == game_id_for_event(event_id)
    assert team_season_id_for(franchise_id, 2026) != team_season_id_for(franchise_id, 2025)
