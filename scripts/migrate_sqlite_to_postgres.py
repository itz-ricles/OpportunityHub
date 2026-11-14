"""Copy an existing SQLite database into PostgreSQL (for example Amazon RDS).

    python scripts/migrate_sqlite_to_postgres.py --sqlite database/opportunityhub.db \
        --postgres "postgresql://USER:PASSWORD@HOST:5432/DBNAME"

Creates the tables if needed, refuses to run if the target already contains data, keeps every id (so
saved items and tracker entries stay linked), and fixes the id counters so new rows continue after the last id.
"""
import argparse
import sqlite3
import sys
from pathlib import Path

import psycopg
from psycopg import sql

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from db import postgres_schema  # noqa: E402

# Parents before children, so foreign keys are satisfied.
TABLES = {
    "users": ["id", "full_name", "email", "password_hash", "role", "created_at"],
    "opportunities": ["id", "title", "category", "organisation", "location", "geographical_scope", "description",
                      "eligibility", "funding_information", "application_url", "deadline", "status",
                      "created_at", "updated_at"],
    "saved_opportunities": ["id", "user_id", "opportunity_id", "created_at"],
    "applications": ["id", "user_id", "opportunity_id", "application_status", "notes", "created_at", "updated_at"],
}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sqlite", required=True, help="path to the SQLite file")
    parser.add_argument("--postgres", required=True, help="PostgreSQL connection URL")
    args = parser.parse_args()

    if not Path(args.sqlite).is_file():
        sys.exit(f"SQLite file not found: {args.sqlite}")
    source = sqlite3.connect(f"file:{args.sqlite}?mode=ro", uri=True)

    with psycopg.connect(args.postgres, connect_timeout=10) as target:
        target.execute(postgres_schema())
        for table in TABLES:
            count = target.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table))).fetchone()[0]
            if count:
                sys.exit(f"Target table '{table}' already has {count} rows. Use an empty database.")

        for table, columns in TABLES.items():
            rows = source.execute(f"SELECT {', '.join(columns)} FROM {table} ORDER BY id").fetchall()  # nosec B608
            insert = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
                sql.Identifier(table),
                sql.SQL(", ").join(map(sql.Identifier, columns)),
                sql.SQL(", ").join(sql.Placeholder() * len(columns)))
            with target.cursor() as cur:
                cur.executemany(insert, rows)
            # Make the auto-number counter continue after the highest copied id.
            target.execute(sql.SQL(
                "SELECT setval(pg_get_serial_sequence({}, 'id'), COALESCE((SELECT MAX(id) FROM {}), 1), "
                "(SELECT MAX(id) IS NOT NULL FROM {}))").format(
                sql.Literal(table), sql.Identifier(table), sql.Identifier(table)))
            print(f"{table}: copied {len(rows)} rows")

        for table in TABLES:  # verify before committing (leaving the 'with' block commits)
            expected = source.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]  # nosec B608
            got = target.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table))).fetchone()[0]
            if expected != got:
                target.rollback()
                sys.exit(f"Row count mismatch in {table}: {expected} vs {got}. Nothing was saved.")
    print("Migration complete and verified.")


if __name__ == "__main__":
    main()
