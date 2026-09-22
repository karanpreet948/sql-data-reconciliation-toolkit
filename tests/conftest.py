"""Shared pytest fixtures for the reconciler test suite."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from reconciler.db import get_connection, load_csv_to_table

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def loaded_conn() -> sqlite3.Connection:
    """An in-memory SQLite connection pre-loaded with the small,
    hand-crafted fixture_a.csv / fixture_b.csv datasets used to exercise
    every exception type deterministically."""
    conn = get_connection(":memory:")
    load_csv_to_table(conn, str(FIXTURES_DIR / "fixture_a.csv"), "system_a")
    load_csv_to_table(conn, str(FIXTURES_DIR / "fixture_b.csv"), "system_b")
    yield conn
    conn.close()
