-- Aggregate KPI query: computes headline reconciliation metrics in a
-- single pass, using the same join logic as the detail queries above.
-- This is the query the CLI's summary report is built from.
SELECT
    (SELECT COUNT(*) FROM (
        SELECT record_id FROM system_a
        UNION
        SELECT record_id FROM system_b
    )) AS total_records_compared,

    (SELECT COUNT(*)
     FROM system_a a
     INNER JOIN system_b b ON a.record_id = b.record_id
     WHERE a.status = b.status AND ABS(a.amount - b.amount) <= 0.01
    ) AS matched_records,

    (SELECT COUNT(*)
     FROM system_a a
     LEFT JOIN system_b b ON a.record_id = b.record_id
     WHERE b.record_id IS NULL
    ) AS missing_in_b,

    (SELECT COUNT(*)
     FROM system_b b
     LEFT JOIN system_a a ON b.record_id = a.record_id
     WHERE a.record_id IS NULL
    ) AS missing_in_a,

    (SELECT COUNT(*)
     FROM system_a a
     INNER JOIN system_b b ON a.record_id = b.record_id
     WHERE ABS(a.amount - b.amount) > 0.01
    ) AS amount_mismatches,

    (SELECT COUNT(*)
     FROM system_a a
     INNER JOIN system_b b ON a.record_id = b.record_id
     WHERE a.status <> b.status
    ) AS status_mismatches,

    (SELECT COALESCE(SUM(ABS(a.amount - b.amount)), 0)
     FROM system_a a
     INNER JOIN system_b b ON a.record_id = b.record_id
     WHERE ABS(a.amount - b.amount) > 0.01
    ) AS total_amount_variance;
