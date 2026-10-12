CREATE TABLE IF NOT EXISTS homework.transactions_fast
(
    transaction_id UInt64 CODEC(ZSTD(1)),
    transaction_time DateTime CODEC(ZSTD(1)),
    us_state LowCardinality(String) CODEC(ZSTD(1)),
    cat_id LowCardinality(String) CODEC(ZSTD(1)),
    amount Decimal(18, 2) CODEC(ZSTD(1))
)
ENGINE = MergeTree
ORDER BY (us_state, cat_id);

CREATE MATERIALIZED VIEW IF NOT EXISTS homework.write_fast
TO homework.transactions_fast AS
SELECT transaction_id, transaction_time, us_state, cat_id, amount
FROM homework.transactions;
