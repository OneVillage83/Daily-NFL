"""SQLite connection and database-status helpers for Daily NFL."""

from dataclasses import dataclass
from pathlib import Path
import sqlite3


@dataclass(frozen=True, slots=True)
class DatabaseStatus:
    path: Path
    schema_version: int
    integrity_ok: bool
    foreign_keys_enabled: bool


def connect_database(path: str | Path) -> sqlite3.Connection:
    """Open a Daily NFL SQLite database with required safety settings."""
    database_path = Path(path)
    if str(database_path) != ":memory:":
        database_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(str(database_path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


def foreign_keys_enabled(connection: sqlite3.Connection) -> bool:
    row = connection.execute("PRAGMA foreign_keys").fetchone()
    return bool(row[0]) if row is not None else False


def integrity_ok(connection: sqlite3.Connection) -> bool:
    row = connection.execute("PRAGMA integrity_check").fetchone()
    return bool(row is not None and row[0] == "ok")
