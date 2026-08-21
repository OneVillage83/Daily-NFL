import sqlite3
from pathlib import Path
from uuid import UUID

import pytest

from daily_nfl.persistence import (
    SCHEMA_VERSION,
    apply_migrations,
    current_schema_version,
    open_database,
)
from daily_nfl.persistence.schema import INITIAL_SCHEMA_SQL
from daily_nfl.providers import NFLVERSE_DESCRIPTOR, record_provider
from daily_nfl.reconciliation import (
    FRANCHISE_ENTITY_TYPE,
    CanonicalEntityType,
    ExternalIdentity,
    IdentityReconciler,
    IdentityRepository,
    new_franchise_id,
)


def test_version_one_database_migrates_to_identity_schema(tmp_path: Path) -> None:
    database = tmp_path / "v1.db"

    with open_database(database) as connection:
        connection.executescript(INITIAL_SCHEMA_SQL)
        connection.execute(
            "INSERT INTO schema_migrations(version, name) VALUES (?, ?)",
            (1, "initial_persistence_foundation"),
        )
        connection.commit()

        assert current_schema_version(connection) == 1
        assert apply_migrations(connection) == SCHEMA_VERSION

        tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        assert "identity_reconciliation_decisions" in tables

        crosswalk_columns = {
            str(row[1])
            for row in connection.execute("PRAGMA table_info(entity_crosswalk)").fetchall()
        }
        assert {"decision_id", "supersedes_crosswalk_id"}.issubset(crosswalk_columns)


def test_crosswalk_and_decision_ledgers_are_append_only(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"
    franchise_id = new_franchise_id(UUID("11111111-1111-1111-1111-111111111111"))

    with open_database(database) as connection:
        apply_migrations(connection)
        record_provider(connection, NFLVERSE_DESCRIPTOR)
        repository = IdentityRepository(connection)
        reconciler = IdentityReconciler(repository)
        repository.ensure_franchise(franchise_id)
        decision = reconciler.bind_verified(
            external=ExternalIdentity(
                "nflverse",
                FRANCHISE_ENTITY_TYPE,
                "IMMUTABLE",
            ),
            canonical_entity_type=CanonicalEntityType.FRANCHISE,
            canonical_entity_id=str(franchise_id),
        )
        crosswalk_id = repository.active_crosswalks(
            ExternalIdentity("nflverse", FRANCHISE_ENTITY_TYPE, "IMMUTABLE")
        )[0].crosswalk_id

        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE entity_crosswalk SET verified = 0 WHERE crosswalk_id = ?",
                (crosswalk_id,),
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "DELETE FROM identity_reconciliation_decisions WHERE decision_id = ?",
                (decision.decision_id,),
            )


def test_database_rejects_fuzzy_crosswalk_insert(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"
    franchise_id = new_franchise_id(UUID("11111111-1111-1111-1111-111111111111"))

    with open_database(database) as connection:
        apply_migrations(connection)
        record_provider(connection, NFLVERSE_DESCRIPTOR)
        IdentityRepository(connection).ensure_franchise(franchise_id)
        connection.execute(
            """
            INSERT INTO identity_reconciliation_decisions(
                decision_id,
                provider_id,
                provider_entity_type,
                external_id,
                expected_canonical_entity_type,
                status,
                candidate_count,
                reason_code,
                details_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "idr_fuzzy_direct_test",
                "nflverse",
                FRANCHISE_ENTITY_TYPE,
                "FUZZY",
                "FRANCHISE",
                "AMBIGUOUS",
                1,
                "FUZZY_REQUIRES_REVIEW",
                '{"candidates":[]}',
            ),
        )

        with pytest.raises(sqlite3.IntegrityError, match="fuzzy candidates"):
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
                    str(franchise_id),
                    "nflverse",
                    FRANCHISE_ENTITY_TYPE,
                    "FUZZY",
                    "FUZZY_CANDIDATE_ONLY",
                    0.95,
                    0,
                    "idr_fuzzy_direct_test",
                ),
            )
