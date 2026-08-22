import sqlite3
from pathlib import Path
from uuid import UUID

import pytest

from daily_nfl.persistence import apply_migrations, open_database
from daily_nfl.providers import NFLVERSE_DESCRIPTOR, record_provider
from daily_nfl.reconciliation import FRANCHISE_ENTITY_TYPE, IdentityRepository, new_franchise_id


def _seed_franchise(connection: sqlite3.Connection) -> str:
    record_provider(connection, NFLVERSE_DESCRIPTOR)
    franchise_id = new_franchise_id(UUID("11111111-1111-1111-1111-111111111111"))
    IdentityRepository(connection).ensure_franchise(franchise_id)
    return str(franchise_id)


def _insert_crosswalk(
    connection: sqlite3.Connection,
    *,
    franchise_id: str,
    decision_id: str | None,
) -> None:
    connection.execute(
        """
        INSERT INTO entity_crosswalk(
            canonical_entity_type,
            canonical_entity_id,
            provider_id,
            provider_entity_type,
            external_id,
            match_method,
            match_confidence,
            verified,
            decision_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "FRANCHISE",
            franchise_id,
            "nflverse",
            FRANCHISE_ENTITY_TYPE,
            "NO_DECISION",
            "MANUAL_VERIFIED",
            1.0,
            1,
            decision_id,
        ),
    )


def test_new_crosswalk_requires_decision_id(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"

    with open_database(database) as connection:
        apply_migrations(connection)
        franchise_id = _seed_franchise(connection)

        with pytest.raises(sqlite3.IntegrityError, match="requires a reconciliation decision"):
            _insert_crosswalk(connection, franchise_id=franchise_id, decision_id=None)


def test_new_crosswalk_requires_existing_decision(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"

    with open_database(database) as connection:
        apply_migrations(connection)
        franchise_id = _seed_franchise(connection)

        with pytest.raises(sqlite3.IntegrityError, match="must reference an existing decision"):
            _insert_crosswalk(
                connection,
                franchise_id=franchise_id,
                decision_id="idr_missing",
            )
