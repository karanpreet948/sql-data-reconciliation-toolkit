"""Tests for reconciler.reconcile: the SQL-driven reconciliation logic.

Uses the fixture_a.csv / fixture_b.csv pair, which is hand-crafted so
every exception type appears exactly once with known values:

    R1  -> matches in both systems
    R2  -> amount mismatch (200.00 vs 250.00, variance 50.00)
    R3  -> status mismatch (SETTLED vs REVERSED)
    R4  -> present only in System A (missing in B)
    R5  -> matches in both systems
    R6  -> present only in System B (missing in A)
"""
from __future__ import annotations

from reconciler.reconcile import get_summary_kpis, run_reconciliation


def test_summary_kpis(loaded_conn):
    kpis = get_summary_kpis(loaded_conn)

    assert kpis["total_records_compared"] == 6
    assert kpis["matched_records"] == 2
    assert kpis["exception_count"] == 4
    assert kpis["missing_in_b"] == 1
    assert kpis["missing_in_a"] == 1
    assert kpis["amount_mismatches"] == 1
    assert kpis["status_mismatches"] == 1
    assert kpis["total_amount_variance"] == 50.0


def test_run_reconciliation_exception_count(loaded_conn):
    result = run_reconciliation(loaded_conn)
    assert len(result.exceptions) == 4

    by_id = {exc.record_id: exc for exc in result.exceptions}
    assert set(by_id.keys()) == {"R2", "R3", "R4", "R6"}


def test_missing_in_b_detected(loaded_conn):
    result = run_reconciliation(loaded_conn)
    exc = next(e for e in result.exceptions if e.record_id == "R4")
    assert exc.exception_type == "MISSING_IN_B"
    assert exc.amount_a == 400.0
    assert exc.amount_b is None
    assert exc.variance == 400.0


def test_missing_in_a_detected(loaded_conn):
    result = run_reconciliation(loaded_conn)
    exc = next(e for e in result.exceptions if e.record_id == "R6")
    assert exc.exception_type == "MISSING_IN_A"
    assert exc.amount_b == 600.0
    assert exc.amount_a is None
    assert exc.variance == 600.0


def test_amount_mismatch_detected(loaded_conn):
    result = run_reconciliation(loaded_conn)
    exc = next(e for e in result.exceptions if e.record_id == "R2")
    assert exc.exception_type == "AMOUNT_MISMATCH"
    assert exc.amount_a == 200.0
    assert exc.amount_b == 250.0
    assert exc.variance == 50.0


def test_status_mismatch_detected(loaded_conn):
    result = run_reconciliation(loaded_conn)
    exc = next(e for e in result.exceptions if e.record_id == "R3")
    assert exc.exception_type == "STATUS_MISMATCH"
    assert exc.status_a == "SETTLED"
    assert exc.status_b == "REVERSED"
    assert exc.variance == 0.0


def test_matched_records_produce_no_exceptions(loaded_conn):
    result = run_reconciliation(loaded_conn)
    ids_with_exceptions = {e.record_id for e in result.exceptions}
    assert "R1" not in ids_with_exceptions
    assert "R5" not in ids_with_exceptions
