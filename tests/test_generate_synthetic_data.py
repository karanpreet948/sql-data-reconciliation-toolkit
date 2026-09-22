"""Tests for the synthetic data generator: reproducibility and injected
discrepancy invariants."""
from __future__ import annotations

import random

from scripts.generate_synthetic_data import build_system_b, generate_base_records


def test_generation_is_reproducible_with_fixed_seed():
    rng1 = random.Random(42)
    records1 = generate_base_records(50, rng1)

    rng2 = random.Random(42)
    records2 = generate_base_records(50, rng2)

    assert [r.__dict__ for r in records1] == [r.__dict__ for r in records2]


def test_system_b_has_missing_and_extra_records():
    rng = random.Random(7)
    system_a = generate_base_records(100, rng)
    system_b = build_system_b(system_a, rng)

    a_ids = {r.record_id for r in system_a}
    b_ids = {r.record_id for r in system_b}

    # Some System A records should not have made it to System B.
    assert len(a_ids - b_ids) > 0
    # Some System B records should not exist in System A.
    assert len(b_ids - a_ids) > 0
    # But the two sets should still mostly overlap.
    assert len(a_ids & b_ids) > 0


def test_system_b_contains_amount_or_status_discrepancies():
    rng = random.Random(7)
    system_a = generate_base_records(100, rng)
    system_b = build_system_b(system_a, rng)

    a_by_id = {r.record_id: r for r in system_a}
    discrepancies = 0
    for rec_b in system_b:
        rec_a = a_by_id.get(rec_b.record_id)
        if rec_a is None:
            continue
        if abs(rec_a.amount - rec_b.amount) > 0.01 or rec_a.status != rec_b.status:
            discrepancies += 1

    assert discrepancies > 0
