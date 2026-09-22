"""End-to-end test of the CLI's ``run`` command against the fixture
data, exercising the full load -> reconcile -> export pipeline."""
from __future__ import annotations

import csv
from pathlib import Path

from reconciler.cli import main

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_cli_run_end_to_end(tmp_path, capsys):
    output_path = tmp_path / "report.csv"

    exit_code = main(
        [
            "run",
            "--source-a",
            str(FIXTURES_DIR / "fixture_a.csv"),
            "--source-b",
            str(FIXTURES_DIR / "fixture_b.csv"),
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert output_path.exists()

    with output_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 4

    captured = capsys.readouterr()
    assert "Reconciliation Summary" in captured.out
    assert "Exceptions | 4" in captured.out


def test_cli_run_missing_source_file_returns_error_code(tmp_path):
    exit_code = main(
        [
            "run",
            "--source-a",
            str(FIXTURES_DIR / "does_not_exist.csv"),
            "--source-b",
            str(FIXTURES_DIR / "fixture_b.csv"),
            "--output",
            str(tmp_path / "report.csv"),
        ]
    )
    assert exit_code == 1
