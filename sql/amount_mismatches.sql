-- Records present in both systems where the reported amount differs by
-- more than one cent (a small tolerance absorbs floating point noise).
SELECT
    a.record_id,
    a.account_id AS account_id_a,
    a.amount AS amount_a,
    b.amount AS amount_b,
    a.status AS status_a,
    b.status AS status_b,
    a.last_updated_date AS last_updated_a,
    b.last_updated_date AS last_updated_b
FROM system_a a
INNER JOIN system_b b ON a.record_id = b.record_id
WHERE ABS(a.amount - b.amount) > 0.01;
