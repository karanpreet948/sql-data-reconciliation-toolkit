"""Core reconciliation logic.

Runs the hand-written SQL queries in ``sql/`` against the two loaded
SQLite tables (``system_a`` and ``system_b``), assembles a per-record
list of exceptions for the detail report, and computes the headline KPIs
via a dedicated SQL aggregate query.
"""
from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"


def _load_sql(filename: str) -> str:
    sql_path = SQL_DIR / filename
    if not sql_path.exists():
        raise FileNotFoundError(f"SQL file not found: {sql_path}")
    return sql_path.read_text(encoding="utf-8")


@dataclass
class ExceptionRecord:
    """A single reconciliation exception, ready to be written to the
    exception report."""

    record_id: str
    exception_type: str
    account_id: Optional[str] = None
    amount_a: Optional[float] = None
    amount_b: Optional[float] = None
    status_a: Optional[str] = None
    status_b: Optional[str] = None
    last_updated_a: Optional[str] = None
    last_updated_b: Optional[str] = None
    variance: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "exception_type": self.exception_type,
            "account_id": self.account_id,
            "amount_a": self.amount_a,
            "amount_b": self.amount_b,
            "status_a": self.status_a,
            "status_b": self.status_b,
            "last_updated_a": self.last_updated_a,
            "last_updated_b": self.last_updated_b,
            "variance": round(self.variance, 2),
        }


@dataclass
class ReconciliationResult:
    """The full output of a reconciliation run: exception detail rows
    plus the aggregate KPI dictionary."""

    exceptions: list[ExceptionRecord] = field(default_factory=list)
    kpis: dict[str, Any] = field(default_factory=dict)


def get_summary_kpis(conn: sqlite3.Connection) -> dict[str, Any]:
    """Compute headline reconciliation KPIs via ``sql/summary_kpis.sql``.

    This is a genuine SQL aggregate query (not a Python/pandas
    calculation) executed directly against SQLite.
    """
    sql = _load_sql("summary_kpis.sql")
    row = conn.execute(sql).fetchone()
    total_compared = row["total_records_compared"]
    matched = row["matched_records"]
    return {
        "total_records_compared": total_compared,
        "matched_records": matched,
        "exception_count": total_compared - matched,
        "missing_in_b": row["missing_in_b"],
        "missing_in_a": row["missing_in_a"],
        "amount_mismatches": row["amount_mismatches"],
        "status_mismatches": row["status_mismatches"],
        "total_amount_variance": round(row["total_amount_variance"] or 0.0, 2),
    }


def run_reconciliation(conn: sqlite3.Connection) -> ReconciliationResult:
    """Execute the full SQL-based reconciliation and return exception
    detail rows plus summary KPIs.

    Assumes ``system_a`` and ``system_b`` tables already exist in
    ``conn`` (see :func:`reconciler.db.load_csv_to_table`).
    """
    exceptions: list[ExceptionRecord] = []

    for row in conn.execute(_load_sql("missing_in_b.sql")):
        exceptions.append(
            ExceptionRecord(
                record_id=row["record_id"],
                exception_type="MISSING_IN_B",
                account_id=row["account_id"],
                amount_a=row["amount"],
                status_a=row["status"],
                last_updated_a=row["last_updated_date"],
                variance=row["amount"] or 0.0,
            )
        )

    for row in conn.execute(_load_sql("missing_in_a.sql")):
        exceptions.append(
            ExceptionRecord(
                record_id=row["record_id"],
                exception_type="MISSING_IN_A",
                account_id=row["account_id"],
                amount_b=row["amount"],
                status_b=row["status"],
                last_updated_b=row["last_updated_date"],
                variance=row["amount"] or 0.0,
            )
        )

    amount_mismatch_ids: set[str] = set()
    for row in conn.execute(_load_sql("amount_mismatches.sql")):
        amount_mismatch_ids.add(row["record_id"])
        exceptions.append(
            ExceptionRecord(
                record_id=row["record_id"],
                exception_type="AMOUNT_MISMATCH",
                account_id=row["account_id_a"],
                amount_a=row["amount_a"],
                amount_b=row["amount_b"],
                status_a=row["status_a"],
                status_b=row["status_b"],
                last_updated_a=row["last_updated_a"],
                last_updated_b=row["last_updated_b"],
                variance=abs(row["amount_a"] - row["amount_b"]),
            )
        )

    for row in conn.execute(_load_sql("status_mismatches.sql")):
        if row["record_id"] in amount_mismatch_ids:
            # This record already has an AMOUNT_MISMATCH row -- fold the
            # status detail into it instead of double-reporting the same
            # record_id as two separate exception rows.
            for exc in exceptions:
                if exc.record_id == row["record_id"] and exc.exception_type == "AMOUNT_MISMATCH":
                    exc.status_a = row["status_a"]
                    exc.status_b = row["status_b"]
            continue
        exceptions.append(
            ExceptionRecord(
                record_id=row["record_id"],
                exception_type="STATUS_MISMATCH",
                account_id=row["account_id_a"],
                amount_a=row["amount_a"],
                amount_b=row["amount_b"],
                status_a=row["status_a"],
                status_b=row["status_b"],
                last_updated_a=row["last_updated_a"],
                last_updated_b=row["last_updated_b"],
                variance=0.0,
            )
        )

    kpis = get_summary_kpis(conn)

    logger.info(
        "Reconciliation complete: %d compared, %d matched, %d exceptions, $%.2f total variance",
        kpis["total_records_compared"],
        kpis["matched_records"],
        kpis["exception_count"],
        kpis["total_amount_variance"],
    )

    return ReconciliationResult(exceptions=exceptions, kpis=kpis)
