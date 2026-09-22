"""Synthetic data generator for the SQL Data Reconciliation Toolkit.

Generates two related CSV extracts that simulate a "source of record"
system (System A) and a "downstream / reporting" system (System B) in a
generic financial-operations context (for example: a transaction ledger
vs. a billing / reporting data mart copy). System B is derived from
System A with deliberately injected discrepancies so the reconciliation
logic in the ``reconciler`` package has real exceptions to detect:

* Records missing from System B (not yet propagated downstream).
* Records present only in System B (e.g. a record System A later voided
  or purged, but the downstream copy was never cleaned up).
* Amount mismatches (rounding drift, a re-stated fee, a partial capture).
* Status mismatches (the downstream status has not caught up yet).
* Stale ``last_updated_date`` values on a handful of downstream rows.

All randomness is drawn from a seeded ``random.Random`` instance, so
re-running this script with the same ``--seed`` produces byte-for-byte
identical CSV output. This is what makes the whole pipeline reproducible
end to end with zero external dependencies.

Usage:
    python scripts/generate_synthetic_data.py \\
        --num-records 300 --seed 42 --output-dir data
"""
from __future__ import annotations

import argparse
import csv
import random
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

STATUSES = ["SETTLED", "PENDING", "FAILED", "REVERSED"]

DEFAULT_NUM_RECORDS = 300
DEFAULT_SEED = 42
BASE_DATE = date(2026, 6, 1)


@dataclass
class Record:
    """A single reconcilable record shared by both source systems."""

    record_id: str
    account_id: str
    amount: float
    status: str
    last_updated_date: str


def _random_date(rng: random.Random, start: date, days_span: int) -> date:
    return start + timedelta(days=rng.randint(0, days_span))


def generate_base_records(num_records: int, rng: random.Random) -> list[Record]:
    """Generate the System A (source of record) population."""
    records = []
    for i in range(1, num_records + 1):
        record_id = f"TXN-{i:05d}"
        account_id = f"ACC-{rng.randint(1000, 1999)}"
        amount = round(rng.uniform(15.0, 4800.0), 2)
        status = rng.choices(STATUSES, weights=[70, 15, 10, 5])[0]
        updated = _random_date(rng, BASE_DATE, 90)
        records.append(Record(record_id, account_id, amount, status, updated.isoformat()))
    return records


def _random_extra_record(rng: random.Random, next_id: int) -> Record:
    record_id = f"TXN-{next_id:05d}"
    account_id = f"ACC-{rng.randint(1000, 1999)}"
    amount = round(rng.uniform(15.0, 4800.0), 2)
    status = rng.choices(STATUSES, weights=[70, 15, 10, 5])[0]
    updated = _random_date(rng, BASE_DATE, 90)
    return Record(record_id, account_id, amount, status, updated.isoformat())


def build_system_b(records: list[Record], rng: random.Random) -> list[Record]:
    """Derive System B (downstream) records from System A, injecting
    realistic reconciliation discrepancies.

    Returns a new list of :class:`Record` -- the input list is not
    mutated.
    """
    system_b = [Record(r.record_id, r.account_id, r.amount, r.status, r.last_updated_date) for r in records]

    n = len(system_b)
    all_indices = list(range(n))
    rng.shuffle(all_indices)

    missing_count = max(1, int(n * 0.05))
    amount_mismatch_count = max(1, int(n * 0.08))
    status_mismatch_count = max(1, int(n * 0.06))
    stale_date_count = max(1, int(n * 0.04))

    remaining = all_indices
    missing_idx = set(remaining[:missing_count])
    remaining = remaining[missing_count:]

    amount_mismatch_idx = set(remaining[:amount_mismatch_count])
    remaining = remaining[amount_mismatch_count:]

    status_mismatch_idx = set(remaining[:status_mismatch_count])
    remaining = remaining[status_mismatch_count:]

    stale_date_idx = set(remaining[:stale_date_count])

    for idx in amount_mismatch_idx:
        rec = system_b[idx]
        # Simulate rounding drift, a partial payment, or a re-stated fee.
        delta = round(rng.uniform(1.0, 75.0) * rng.choice([-1, 1]), 2)
        rec.amount = round(rec.amount + delta, 2)

    for idx in status_mismatch_idx:
        rec = system_b[idx]
        alt_statuses = [s for s in STATUSES if s != rec.status]
        rec.status = rng.choice(alt_statuses)

    for idx in stale_date_idx:
        rec = system_b[idx]
        updated = date.fromisoformat(rec.last_updated_date) - timedelta(days=rng.randint(1, 10))
        rec.last_updated_date = updated.isoformat()

    system_b = [rec for i, rec in enumerate(system_b) if i not in missing_idx]

    # Add a handful of records that exist only downstream (e.g. a record
    # System A subsequently voided/purged but System B has not caught up).
    extra_count = max(1, int(n * 0.03))
    for i in range(extra_count):
        system_b.append(_random_extra_record(rng, n + i + 1))

    rng.shuffle(system_b)
    return system_b


def write_csv(records: list[Record], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["record_id", "account_id", "amount", "status", "last_updated_date"])
        for r in records:
            writer.writerow([r.record_id, r.account_id, f"{r.amount:.2f}", r.status, r.last_updated_date])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate synthetic reconciliation source data.")
    parser.add_argument("--num-records", type=int, default=DEFAULT_NUM_RECORDS, help="Number of System A records to generate.")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Random seed for reproducible output.")
    parser.add_argument("--output-dir", default="data", help="Directory to write the two CSV files into.")
    args = parser.parse_args(argv)

    rng = random.Random(args.seed)
    system_a = generate_base_records(args.num_records, rng)
    system_b = build_system_b(system_a, rng)

    output_dir = Path(args.output_dir)
    write_csv(system_a, output_dir / "system_a_records.csv")
    write_csv(system_b, output_dir / "system_b_records.csv")

    print(f"Generated {len(system_a)} System A records and {len(system_b)} System B records in {output_dir}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
