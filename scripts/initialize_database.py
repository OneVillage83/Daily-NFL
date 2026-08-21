"""Initialize or validate the Daily NFL SQLite database."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from daily_nfl.persistence import (  # noqa: E402
    SCHEMA_VERSION,
    apply_migrations,
    foreign_keys_enabled,
    integrity_ok,
    open_database,
    validate_schema_history,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("local-data/daily-nfl.db"),
        help="SQLite database path",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate an existing database without applying migrations",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    database: Path = args.database

    with open_database(database) as connection:
        before = validate_schema_history(connection)
        if args.check:
            after = before
        else:
            after = apply_migrations(connection)

        integrity = integrity_ok(connection)
        foreign_keys = foreign_keys_enabled(connection)

    status = {
        "database": str(database),
        "schema_version_before": before,
        "schema_version_after": after,
        "supported_schema_version": SCHEMA_VERSION,
        "integrity_ok": integrity,
        "foreign_keys_enabled": foreign_keys,
        "mode": "check" if args.check else "migrate",
    }
    print(json.dumps(status, sort_keys=True))

    if args.check and after != SCHEMA_VERSION:
        return 2
    if not integrity or not foreign_keys:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
