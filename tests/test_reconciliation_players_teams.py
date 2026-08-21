import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from uuid import UUID

from daily_nfl.domain import PersonId
from daily_nfl.persistence import apply_migrations, open_database
from daily_nfl.providers import NFLVERSE_DESCRIPTOR, record_provider
from daily_nfl.reconciliation import (
    FRANCHISE_ENTITY_TYPE,
    GSIS_AUTHORITY_DESCRIPTOR,
    GSIS_AUTHORITY_PROVIDER_ID,
    CanonicalEntityType,
    ExternalIdentity,
    IdentityReconciler,
    IdentityRepository,
    MatchMethod,
    new_franchise_id,
    team_season_id_for,
)


@contextmanager
def _open_identity_database(path: Path) -> Iterator[sqlite3.Connection]:
    with open_database(path) as connection:
        apply_migrations(connection)
        record_provider(connection, NFLVERSE_DESCRIPTOR)
        record_provider(connection, GSIS_AUTHORITY_DESCRIPTOR)
        yield connection


def test_gsis_bootstraps_opaque_player_once_and_reuses_crosswalk(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"
    fixed_person = PersonId("per_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")

    with _open_identity_database(database) as connection:
        repository = IdentityRepository(connection)
        reconciler = IdentityReconciler(
            repository,
            person_id_factory=lambda: fixed_person,
        )

        first = reconciler.resolve_or_create_gsis_player(
            gsis_id="00-0033873",
            canonical_name="Fixture Player",
        )
        second = reconciler.resolve_or_create_gsis_player(gsis_id="00-0033873")

        assert first.resolved
        assert second.resolved
        assert first.external_identity.provider_id == GSIS_AUTHORITY_PROVIDER_ID
        assert first.selected_canonical_entity_id == second.selected_canonical_entity_id
        assert first.selected_canonical_entity_id != "00-0033873"
        assert first.match_method is MatchMethod.TRUSTED_EXTERNAL_ID
        assert second.match_method is MatchMethod.EXISTING_CROSSWALK
        assert connection.execute("SELECT COUNT(*) FROM persons").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM players").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM entity_crosswalk").fetchone()[0] == 1


def test_team_season_derives_from_verified_franchise_not_provider_id(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"
    franchise_id = new_franchise_id(UUID("11111111-1111-1111-1111-111111111111"))

    with _open_identity_database(database) as connection:
        repository = IdentityRepository(connection)
        reconciler = IdentityReconciler(repository)
        repository.ensure_franchise(franchise_id, "Fixture Franchise")
        reconciler.bind_verified(
            external=ExternalIdentity(
                provider_id="nflverse",
                provider_entity_type=FRANCHISE_ENTITY_TYPE,
                external_id="FX",
            ),
            canonical_entity_type=CanonicalEntityType.FRANCHISE,
            canonical_entity_id=str(franchise_id),
        )

        decision = reconciler.resolve_team_season(
            provider_id="nflverse",
            external_team_id="FX",
            season=2026,
            display_name="Fixture 2026",
        )

        expected = team_season_id_for(franchise_id, 2026)
        assert decision.resolved
        assert decision.selected_canonical_entity_id == str(expected)
        assert decision.selected_canonical_entity_id != "FX"
        row = connection.execute(
            "SELECT franchise_id, season FROM team_seasons WHERE team_season_id = ?",
            (str(expected),),
        ).fetchone()
        assert row is not None
        assert (str(row[0]), int(row[1])) == (str(franchise_id), 2026)


def test_provider_external_id_change_does_not_change_canonical_franchise(
    tmp_path: Path,
) -> None:
    database = tmp_path / "identity.db"
    franchise_id = new_franchise_id(UUID("11111111-1111-1111-1111-111111111111"))

    with _open_identity_database(database) as connection:
        repository = IdentityRepository(connection)
        reconciler = IdentityReconciler(repository)
        repository.ensure_franchise(franchise_id)

        for external_id in ("SF", "SFO"):
            reconciler.bind_verified(
                external=ExternalIdentity(
                    provider_id="nflverse",
                    provider_entity_type=FRANCHISE_ENTITY_TYPE,
                    external_id=external_id,
                ),
                canonical_entity_type=CanonicalEntityType.FRANCHISE,
                canonical_entity_id=str(franchise_id),
            )

        for external_id in ("SF", "SFO"):
            resolved = reconciler.resolve(
                ExternalIdentity("nflverse", FRANCHISE_ENTITY_TYPE, external_id),
                CanonicalEntityType.FRANCHISE,
            )
            assert resolved.selected_canonical_entity_id == str(franchise_id)
