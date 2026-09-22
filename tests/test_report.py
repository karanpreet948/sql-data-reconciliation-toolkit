"""Tests for reconciler.report: CSV export and Markdown summary
formatting."""
from __future__ import annotations

import csv

from reconciler.reconcile import run_reconciliation
from reconciler.report import format_summary_markdown, write_exceptions_csv


def test_write_exceptions_csv(loaded_conn, tmp_path):
    result = run_reconciliation(loaded_conn)
    output_path = tmp_path / "out" / "report.csv"

    written_path = write_exceptions_csv(result.exceptions, output_path)
    assert written_path == output_path
    assert output_path.exists()

    with output_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 4
    ids = {row["record_id"] for row in rows}
    assert ids == {"R2", "R3", "R4", "R6"}


def test_format_summary_markdown_contains_kpi_values(loaded_conn):
    result = run_reconciliation(loaded_conn)
    markdown = format_summary_markdown(result.kpis)

    assert "Reconciliation Summary" in markdown
    assert "| Total records compared | 6 |" in markdown
    assert "| Matched records | 2 |" in markdown
    assert "| Exceptions | 4 |" in markdown
    assert "$50.00" in markdown
