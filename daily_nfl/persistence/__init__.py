"""Daily NFL SQLite persistence foundation."""

from daily_nfl.persistence.database import (
    DatabaseStatus,
    connect_database,
    foreign_keys_enabled,
    integrity_ok,
)
from daily_nfl.persistence.migrations import (
    SchemaVersionError,
    apply_migrations,
    current_schema_version,
)
from daily_nfl.persistence.schema import SCHEMA_VERSION

__all__ = [
    "DatabaseStatus",
    "SCHEMA_VERSION",
    "SchemaVersionError",
    "apply_migrations",
    "connect_database",
    "current_schema_version",
    "foreign_keys_enabled",
    "integrity_ok",
]
