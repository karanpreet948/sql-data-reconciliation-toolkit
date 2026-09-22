"""Report generation.

Writes the exception detail to a CSV file and renders a Markdown summary
of the reconciliation KPIs for terminal/README-style output.
"""
from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Any

from reconciler.reconcile import ExceptionRecord

logger = logging.getLogger(__name__)

REPORT_FIELDS = [
    "record_id",
    "exception_type",
    "account_id",
    "amount_a",
    "amount_b",
    "status_a",
    "status_b",
    "last_updated_a",
    "last_updated_b",
    "variance",
]


def write_exceptions_csv(exceptions: list[ExceptionRecord], output_path: str | Path) -> Path:
    """Write every exception row to a CSV report, sorted by exception
    type then record_id for readability."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    ordered = sorted(exceptions, key=lambda e: (e.exception_type, e.record_id))

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=REPORT_FIELDS)
        writer.writeheader()
        for exc in ordered:
            writer.writerow(exc.as_dict())

    logger.info("Wrote %d exception rows to %s", len(ordered), path)
    return path


def format_summary_markdown(kpis: dict[str, Any]) -> str:
    """Render the KPI dictionary as a Markdown table for console/README
    display."""
    lines = [
        "## Reconciliation Summary",
        "",
        "| KPI | Value |",
        "|---|---|",
        f"| Total records compared | {kpis['total_records_compared']} |",
        f"| Matched records | {kpis['matched_records']} |",
        f"| Exceptions | {kpis['exception_count']} |",
        f"| Missing in System B | {kpis['missing_in_b']} |",
        f"| Missing in System A | {kpis['missing_in_a']} |",
        f"| Amount mismatches | {kpis['amount_mismatches']} |",
        f"| Status mismatches | {kpis['status_mismatches']} |",
        f"| Total $ variance | ${kpis['total_amount_variance']:,.2f} |",
    ]
    return "\n".join(lines)
