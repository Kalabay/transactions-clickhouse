import argparse
import csv
import json
from datetime import datetime
from decimal import Decimal

from confluent_kafka import Producer
import os

from db import query


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file", nargs="?", default="data/test.csv")
    args = parser.parse_args()
    if int(query("SELECT count() FROM homework.transactions").text):
        raise RuntimeError("table is not empty. use a fresh database")
    producer = Producer({"bootstrap.servers": os.getenv("KAFKA_BROKERS", "kafka:9092"), "linger.ms": 20})
    errors = []

    def delivered(error, message):
        if error:
            errors.append(str(error))

    count = 0
    with open(args.file, encoding="utf-8-sig", newline="") as file:
        for count, row in enumerate(csv.DictReader(file), 1):
            amount = Decimal(row["amount"])
            if not amount.is_finite() or amount != amount.quantize(Decimal("0.01")) or abs(amount) >= 10 ** 16:
                raise ValueError(f"invalid amount at row {count}")
            if not row["us_state"] or not row["cat_id"]:
                raise ValueError(f"missing state or category at row {count}")
            data = {
                "transaction_id": count,
                "transaction_time": datetime.fromisoformat(row["transaction_time"]).strftime("%Y-%m-%d %H:%M:%S"),
                "us_state": row["us_state"],
                "cat_id": row["cat_id"],
                "amount": str(amount)
            }
            while True:
                try:
                    producer.produce("transactions", json.dumps(data).encode(), on_delivery=delivered)
                    break
                except BufferError:
                    producer.poll(0.1)
            producer.poll(0)
            if errors:
                raise RuntimeError(errors[0])
    if producer.flush(120) or errors:
        raise RuntimeError(f"send failed: {errors[:1]}")
    print(f"sent: {count}")


if __name__ == "__main__":
    main()
