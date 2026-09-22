"""Tests for reconciler.db: CSV loading, schema validation, error paths."""
from __future__ import annotations

from pathlib import Path

import pytest

from reconciler.db import SchemaValidationError, get_connection, load_csv_to_table

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_load_csv_to_table_returns_row_count():
    conn = get_connection(":memory:")
    rows_loaded = load_csv_to_table(conn, str(FIXTURES_DIR / "fixture_a.csv"), "system_a")
    assert rows_loaded == 5

    count = conn.execute("SELECT COUNT(*) FROM system_a").fetchone()[0]
    assert count == 5
    conn.close()


def test_load_csv_to_table_missing_file_raises():
    conn = get_connection(":memory:")
    with pytest.raises(FileNotFoundError):
        load_csv_to_table(conn, str(FIXTURES_DIR / "does_not_exist.csv"), "system_a")
    conn.close()


def test_load_csv_to_table_missing_column_raises(tmp_path):
    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_text("record_id,amount,status\nR1,100.00,SETTLED\n", encoding="utf-8")

    conn = get_connection(":memory:")
    with pytest.raises(SchemaValidationError, match="missing required column"):
        load_csv_to_table(conn, str(bad_csv), "system_a")
    conn.close()


def test_load_csv_to_table_malformed_amount_raises(tmp_path):
    bad_csv = tmp_path / "bad_amount.csv"
    bad_csv.write_text(
        "record_id,account_id,amount,status,last_updated_date\n"
        "R1,ACC-1,not_a_number,SETTLED,2026-01-01\n",
        encoding="utf-8",
    )

    conn = get_connection(":memory:")
    with pytest.raises(SchemaValidationError, match="malformed row"):
        load_csv_to_table(conn, str(bad_csv), "system_a")
    conn.close()


def test_load_csv_to_table_empty_file_raises(tmp_path):
    empty_csv = tmp_path / "empty.csv"
    empty_csv.write_text("", encoding="utf-8")

    conn = get_connection(":memory:")
    with pytest.raises(SchemaValidationError, match="empty"):
        load_csv_to_table(conn, str(empty_csv), "system_a")
    conn.close()


def test_reload_drops_previous_table_contents():
    conn = get_connection(":memory:")
    load_csv_to_table(conn, str(FIXTURES_DIR / "fixture_a.csv"), "system_a")
    load_csv_to_table(conn, str(FIXTURES_DIR / "fixture_a.csv"), "system_a")
    count = conn.execute("SELECT COUNT(*) FROM system_a").fetchone()[0]
    assert count == 5  # not doubled
    conn.close()
