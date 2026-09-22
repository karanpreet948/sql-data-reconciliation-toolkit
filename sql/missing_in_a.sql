-- Records present in System B (downstream / reporting system) with no
-- matching record_id in System A (source of record).
-- Business meaning: a record exists downstream that the source system
-- no longer has -- e.g. it was voided/purged upstream but the
-- downstream copy was never cleaned up.
SELECT
    b.record_id,
    b.account_id,
    b.amount,
    b.status,
    b.last_updated_date
FROM system_b b
LEFT JOIN system_a a ON b.record_id = a.record_id
WHERE a.record_id IS NULL;
