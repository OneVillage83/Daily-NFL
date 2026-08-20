"""Versioned SQLite migrations for Daily NFL."""

import sqlite3
from dataclasses import dataclass

from daily_nfl.persistence.schema import INITIAL_SCHEMA_SQL, SCHEMA_VERSION


@dataclass(frozen=True, slots=True)
class Migration:
    version: int
    name: str
    sql: str


MIGRATIONS: tuple[Migration, ...] = (
    Migration(version=1, name="initial_persistence_foundation", sql=INITIAL_SCHEMA_SQL),
)


class SchemaVersionError(RuntimeError):
    """Raised when a database schema cannot be safely migrated."""


def current_schema_version(connection: sqlite3.Connection) -> int:
    table_exists = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
    ).fetchone()
    if table_exists is None:
        return 0

    row = connection.execute("SELECT COALESCE(MAX(version), 0) FROM schema_migrations").fetchone()
    if row is None:
        return 0
    return int(row[0])


def apply_migrations(connection: sqlite3.Connection) -> int:
    """Apply all pending migrations and return the resulting schema version."""
    current = current_schema_version(connection)
    latest = max(migration.version for migration in MIGRATIONS)

    if current > latest or current > SCHEMA_VERSION:
        raise SchemaVersionError(
            f"database schema version {current} is newer than supported version {SCHEMA_VERSION}"
        )

    expected_next = current + 1
    for migration in MIGRATIONS:
        if migration.version <= current:
            continue
        if migration.version != expected_next:
            raise SchemaVersionError(
                f"migration sequence gap: expected version {expected_next}, found {migration.version}"
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

    return current
