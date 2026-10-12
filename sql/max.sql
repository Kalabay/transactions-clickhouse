CREATE TABLE IF NOT EXISTS homework.state_maximums
(
    us_state LowCardinality(String),
    best AggregateFunction(max, Tuple(Decimal(18, 2), String)) CODEC(ZSTD(1))
)
ENGINE = AggregatingMergeTree
ORDER BY us_state;

CREATE MATERIALIZED VIEW IF NOT EXISTS homework.write_max
TO homework.state_maximums AS
SELECT us_state, maxState(tuple(amount, cat_id)) AS best
FROM homework.transactions_fast
GROUP BY us_state;
