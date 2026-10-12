CREATE DATABASE IF NOT EXISTS homework;

CREATE TABLE IF NOT EXISTS homework.transactions
(
    transaction_id UInt64,
    transaction_time DateTime,
    us_state String,
    cat_id String,
    amount Decimal(18, 2)
)
ENGINE = MergeTree
ORDER BY transaction_id;

CREATE TABLE IF NOT EXISTS homework.kafka_transactions
(
    transaction_id UInt64,
    transaction_time DateTime,
    us_state String,
    cat_id String,
    amount Decimal(18, 2)
)
ENGINE = Kafka
SETTINGS kafka_broker_list = 'kafka:9092',
    kafka_topic_list = 'transactions',
    kafka_group_name = 'clickhouse-homework',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1,
    kafka_flush_interval_ms = 1000;

CREATE MATERIALIZED VIEW IF NOT EXISTS homework.read_kafka
TO homework.transactions AS
SELECT transaction_id, transaction_time, us_state, cat_id, amount
FROM homework.kafka_transactions;
