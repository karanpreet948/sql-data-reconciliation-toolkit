"""Command line interface for the SQL Data Reconciliation Toolkit.

Example:
    python -m reconciler run \\
        --source-a data/system_a_records.csv \\
        --source-b data/system_b_records.csv \\
        --output out/reconciliation_report.csv
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from reconciler.db import SchemaValidationError, get_connection, load_csv_to_table
from reconciler.reconcile import run_reconciliation
from reconciler.report import format_summary_markdown, write_exceptions_csv

logger = logging.getLogger("reconciler")


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reconciler",
        description="Reconcile records between two financial-operations data sources.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run a full reconciliation and export an exception report.")
    run_parser.add_argument("--source-a", required=True, help="Path to the System A (source of record) CSV.")
    run_parser.add_argument("--source-b", required=True, help="Path to the System B (downstream) CSV.")
    run_parser.add_argument("--output", required=True, help="Path to write the exception report CSV.")
    run_parser.add_argument(
        "--db-path",
        default=":memory:",
        help="Optional path to persist the SQLite database to disk (default: in-memory, nothing left behind).",
    )

    return parser


def run_command(args: argparse.Namespace) -> int:
    conn = None
    try:
        conn = get_connection(args.db_path)
        load_csv_to_table(conn, args.source_a, "system_a")
        load_csv_to_table(conn, args.source_b, "system_b")

        result = run_reconciliation(conn)

        output_path = Path(args.output)
        write_exceptions_csv(result.exceptions, output_path)

        print(format_summary_markdown(result.kpis))
        print(f"\nException detail written to: {output_path}")
        return 0
    except FileNotFoundError as exc:
        logger.error("Input file error: %s", exc)
        return 1
    except SchemaValidationError as exc:
        logger.error("Schema validation error: %s", exc)
        return 1
    except Exception:  # noqa: BLE001 - top-level CLI safety net
        logger.exception("Unexpected error during reconciliation")
        return 1
    finally:
        if conn is not None:
            conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _configure_logging(args.verbose)

    if args.command == "run":
        return run_command(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
