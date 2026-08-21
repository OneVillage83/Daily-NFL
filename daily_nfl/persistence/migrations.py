"""Versioned SQLite migrations for Daily NFL."""

import sqlite3
from dataclasses import dataclass

from daily_nfl.persistence.identity_schema import IDENTITY_RECONCILIATION_SCHEMA_SQL
from daily_nfl.persistence.m2_conformance_schema import M2_CONFORMANCE_SCHEMA_SQL
from daily_nfl.persistence.pit_schema import PIT_SNAPSHOT_SCHEMA_SQL
from daily_nfl.persistence.schema import INITIAL_SCHEMA_SQL

SCHEMA_VERSION = 4


@dataclass(frozen=True, slots=True)
class Migration:
    version: int
    name: str
    sql: str


MIGRATIONS: tuple[Migration, ...] = (
    Migration(version=1, name="initial_persistence_foundation", sql=INITIAL_SCHEMA_SQL),
    Migration(
        version=2,
        name="identity_reconciliation_foundation",
        sql=IDENTITY_RECONCILIATION_SCHEMA_SQL,
    ),
    Migration(
        version=3,
        name="historical_pit_snapshot_foundation",
        sql=PIT_SNAPSHOT_SCHEMA_SQL,
    ),
    Migration(
        version=4,
        name="m2_architecture_conformance",
        sql=M2_CONFORMANCE_SCHEMA_SQL,
    ),
)


class SchemaVersionError(RuntimeError):
    """Raised when a database schema cannot be safely migrated or trusted."""


def _user_tables(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        """
    ).fetchall()
    return {str(row[0]) for row in rows}


def _migration_table_exists(connection: sqlite3.Connection) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
    ).fetchone()
    return row is not None


def current_schema_version(connection: sqlite3.Connection) -> int:
    if not _migration_table_exists(connection):
        return 0

    row = connection.execute("SELECT COALESCE(MAX(version), 0) FROM schema_migrations").fetchone()
    if row is None:
        return 0
    return int(row[0])


def _validate_migration_history(connection: sqlite3.Connection, current: int) -> None:
    """Fail closed if the recorded migration ledger is incomplete or altered."""
    if current == 0:
        return

    rows = connection.execute(
        "SELECT version, name FROM schema_migrations ORDER BY version"
    ).fetchall()
    expected = {migration.version: migration.name for migration in MIGRATIONS}

    if len(rows) != current:
        raise SchemaVersionError(
            "migration history is incomplete: "
            f"highest version is {current} but ledger contains {len(rows)} row(s)"
        )

    for expected_version in range(1, current + 1):
        row = rows[expected_version - 1]
        version = int(row[0])
        name = str(row[1])
        if version != expected_version:
            raise SchemaVersionError(
                "migration history contains a sequence gap: "
                f"expected version {expected_version}, found {version}"
            )
        expected_name = expected.get(version)
        if expected_name is None:
            raise SchemaVersionError(f"migration version {version} is not supported by this code")
        if name != expected_name:
            raise SchemaVersionError(
                "migration history name mismatch: "
                f"version {version} expected {expected_name!r}, found {name!r}"
            )


def validate_schema_history(connection: sqlite3.Connection) -> int:
    """Validate the version ledger without applying migrations.

    Returns the highest valid recorded schema version. The caller may compare
    that value with ``SCHEMA_VERSION`` when an exact current-schema check is
    required. A non-empty unversioned database, future schema, sequence gap, or
    renamed migration fails closed.
    """
    current = current_schema_version(connection)
    latest = max(migration.version for migration in MIGRATIONS)

    if current == 0 and _user_tables(connection):
        raise SchemaVersionError(
            "refusing to trust an unversioned or incomplete non-empty database"
        )
    if current > latest or current > SCHEMA_VERSION:
        raise SchemaVersionError(
            f"database schema version {current} is newer than supported version {SCHEMA_VERSION}"
        )
    _validate_migration_history(connection, current)
    return current


def apply_migrations(connection: sqlite3.Connection) -> int:
    """Apply all pending migrations and return the resulting schema version."""
    current = current_schema_version(connection)
    latest = max(migration.version for migration in MIGRATIONS)

    if current == 0 and _user_tables(connection):
        raise SchemaVersionError(
            "refusing to migrate an unversioned or incomplete non-empty database"
        )
    if current > latest or current > SCHEMA_VERSION:
        raise SchemaVersionError(
            f"database schema version {current} is newer than supported version {SCHEMA_VERSION}"
        )
    _validate_migration_history(connection, current)

    expected_next = current + 1
    for migration in MIGRATIONS:
        if migration.version <= current:
            continue
        if migration.version != expected_next:
            raise SchemaVersionError(
                "migration sequence gap: "
                f"expected version {expected_next}, found {migration.version}"
            )

        escaped_name = migration.name.replace("'", "''")
        script = (
            "BEGIN IMMEDIATE;\n"
            f"{migration.sql}\n"
            "INSERT INTO schema_migrations(version, name) "
            f"VALUES ({migration.version}, '{escaped_name}');\n"
            "COMMIT;"
        )
        try:
            connection.executescript(script)
        except sqlite3.Error:
            if connection.in_transaction:
                connection.rollback()
            raise

        current = migration.version
        expected_next = current + 1

    _validate_migration_history(connection, current)
    return current
