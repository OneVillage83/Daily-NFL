"""Daily NFL SQLite persistence foundation."""

from daily_nfl.persistence.database import (
    DatabaseStatus,
    connect_database,
    foreign_keys_enabled,
    integrity_ok,
    open_database,
)
from daily_nfl.persistence.migrations import (
    SCHEMA_VERSION,
    SchemaVersionError,
    apply_migrations,
    current_schema_version,
    validate_schema_history,
)

__all__ = [
    "DatabaseStatus",
    "SCHEMA_VERSION",
    "SchemaVersionError",
    "apply_migrations",
    "connect_database",
    "current_schema_version",
    "foreign_keys_enabled",
    "integrity_ok",
    "open_database",
    "validate_schema_history",
]
