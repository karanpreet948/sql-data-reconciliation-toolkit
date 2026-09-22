-- Records present in System A (source of record) with no matching
-- record_id in System B (downstream / reporting system).
-- Business meaning: the source transaction has not yet propagated
-- downstream, or the downstream feed dropped it.
SELECT
    a.record_id,
    a.account_id,
    a.amount,
    a.status,
    a.last_updated_date
FROM system_a a
LEFT JOIN system_b b ON a.record_id = b.record_id
WHERE b.record_id IS NULL;
