"""SQLite database utilities for the reconciliation toolkit.

Responsible for opening a SQLite connection (in-memory by default, so the
whole pipeline runs with zero external setup) and loading CSV extracts
from each source system into normalized tables that the SQL queries in
``sql/`` can then reconcile.
"""
from __future__ import annotations

import csv
import logging
import sqlite3
from pathlib import Path
from typing import Iterable

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = ["record_id", "account_id", "amount", "status", "last_updated_date"]

_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS {table_name} (
    record_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    amount REAL NOT NULL,
    status TEXT NOT NULL,
    last_updated_date TEXT NOT NULL
);
"""


class SchemaValidationError(Exception):
    """Raised when a source CSV does not match the expected schema."""


def get_connection(db_path: str = ":memory:") -> sqlite3.Connection:
    """Open a SQLite connection.

    Defaults to an in-memory database so the toolkit needs no external
    database server and leaves nothing behind on disk unless a
    ``db_path`` is explicitly supplied.
    """
    logger.debug("Opening SQLite connection at %s", db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _validate_header(header: Iterable[str], source_path: Path) -> None:
    header_list = list(header)
    missing = [c for c in REQUIRED_COLUMNS if c not in header_list]
    if missing:
        raise SchemaValidationError(
            f"{source_path} is missing required column(s): {', '.join(missing)}. "
            f"Expected columns: {', '.join(REQUIRED_COLUMNS)}."
        )


def load_csv_to_table(conn: sqlite3.Connection, csv_path: str, table_name: str) -> int:
    """Load a CSV file into a SQLite table, validating its schema first.

    Args:
        conn: An open SQLite connection.
        csv_path: Path to the source CSV file.
        table_name: Name of the table to (re)create and load into.

    Returns:
        The number of rows loaded.

    Raises:
        FileNotFoundError: If ``csv_path`` does not exist.
        SchemaValidationError: If required columns are missing, the file
            is empty, or a row cannot be parsed against the schema.
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Source file not found: {csv_path}")

    conn.execute(f"DROP TABLE IF EXISTS {table_name}")
    conn.execute(_TABLE_SCHEMA.format(table_name=table_name))

    rows_loaded = 0
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise SchemaValidationError(f"{csv_path} appears to be empty or has no header row.")
        _validate_header(reader.fieldnames, path)

        insert_sql = f"""
            INSERT INTO {table_name} (record_id, account_id, amount, status, last_updated_date)
            VALUES (?, ?, ?, ?, ?)
        """
        for line_num, row in enumerate(reader, start=2):
            try:
                conn.execute(
                    insert_sql,
                    (
                        row["record_id"],
                        row["account_id"],
                        float(row["amount"]),
                        row["status"],
                        row["last_updated_date"],
                    ),
                )
                rows_loaded += 1
            except (ValueError, KeyError) as exc:
                raise SchemaValidationError(
                    f"{csv_path}: malformed row at line {line_num}: {exc}"
                ) from exc

    conn.commit()
    logger.info("Loaded %d rows from %s into table '%s'", rows_loaded, csv_path, table_name)
    return rows_loaded
