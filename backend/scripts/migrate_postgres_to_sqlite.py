#!/usr/bin/env python3
"""One-time migration utility: copy data from PostgreSQL into a SQLite file."""

import argparse
import json
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TAILOR_DIR = REPO_ROOT / "backend" / "services" / "resume-tailor"
sys.path.insert(0, str(TAILOR_DIR))


def normalize_sqlite_url(value: str) -> str:
    if value.startswith("sqlite:"):
        return value
    resolved = Path(value).expanduser().resolve()
    return f"sqlite:///{resolved}"


def main() -> int:
    from core.db_sync import migrate_postgres_to_sqlite  # type: ignore[import-not-found]

    parser = argparse.ArgumentParser(
        description="Migrate data from PostgreSQL to SQLite without losing existing rows",
    )
    parser.add_argument(
        "--postgres-url",
        default=os.getenv("POSTGRES_DATABASE_URL") or os.getenv("DATABASE_URL"),
        help="PostgreSQL URL (defaults to POSTGRES_DATABASE_URL or DATABASE_URL)",
    )
    parser.add_argument(
        "--sqlite-url",
        default=os.getenv("SQLITE_DATABASE_URL", "sqlite:///./backend/services/resume-tailor/data/autocareer.db"),
        help="SQLite URL or file path",
    )

    args = parser.parse_args()

    if not args.postgres_url:
        print("Error: missing PostgreSQL URL. Set --postgres-url or POSTGRES_DATABASE_URL.")
        return 1

    sqlite_url = normalize_sqlite_url(args.sqlite_url)

    try:
        result = migrate_postgres_to_sqlite(args.postgres_url, sqlite_url)
    except Exception as exc:
        print(f"Migration failed: {exc}")
        return 1

    print(json.dumps(result, indent=2, default=str))
    if not result.get("row_counts_match"):
        print("Warning: row counts differ between PostgreSQL and SQLite after migration")
        return 2

    print("Migration succeeded and row counts match")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
