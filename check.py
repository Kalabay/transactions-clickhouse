import argparse
import csv
import io
import json
import hashlib
from datetime import datetime
import time
from decimal import Decimal
from pathlib import Path
from statistics import median

from db import query


def rows(text):
    return [(row["us_state"], row["cat_id"], Decimal(row["amount"])) for row in csv.DictReader(io.StringIO(text))]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file", nargs="?", default="data/test.csv")
    args = parser.parse_args()
    best = {}
    count = 0
    source_hash = hashlib.sha256()
    with open(args.file, encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            count += 1
            value = (Decimal(row["amount"]), row["cat_id"])
            fields = [str(count), datetime.fromisoformat(row["transaction_time"]).strftime("%Y-%m-%d %H:%M:%S"), row["us_state"], row["cat_id"], format(value[0], ".2f")]
            source_hash.update((json.dumps(fields) + "\n").encode())
            state = row["us_state"]
            if state not in best or value > best[state]:
                best[state] = value
    if not count:
        raise ValueError("csv is empty")
    expected = [(state, best[state][1], best[state][0]) for state in sorted(best)]
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        loaded = int(query("SELECT count() FROM homework.transactions").text)
        if loaded > count:
            raise RuntimeError("extra rows in database. use a fresh database")
        if loaded == count and int(query("SELECT count() FROM homework.transactions_fast").text) == count:
            break
        time.sleep(2)
    else:
        raise RuntimeError(f"load timeout: {loaded}/{count}")
    for table in ["transactions", "transactions_fast"]:
        stored = query(f"SELECT transaction_id, transaction_time, us_state, cat_id, amount FROM homework.{table} ORDER BY transaction_id FORMAT CSVWithNames")
        stored_hash = hashlib.sha256()
        for row in csv.DictReader(io.StringIO(stored.text)):
            fields = [row["transaction_id"], row["transaction_time"], row["us_state"], row["cat_id"], format(Decimal(row["amount"]), ".2f")]
            stored_hash.update((json.dumps(fields) + "\n").encode())
        if stored_hash.digest() != source_hash.digest():
            raise AssertionError(f"stored data does not match csv: {table}")
    queries = {
        "before": Path("sql/query_old.sql").read_text(),
        "after": Path("sql/query.sql").read_text(),
        "max": Path("sql/query_max.sql").read_text()
    }
    for name, sql in queries.items():
        response = query(sql + " FORMAT CSVWithNames", use_query_cache=0, max_threads=2)
        if rows(response.text) != expected:
            raise AssertionError(f"wrong result: {name}")
        if name == "max":
            Path("results").mkdir(exist_ok=True)
            Path("results/answer.csv").write_text(response.text, encoding="utf-8")
    ids = query("SELECT uniqExact(transaction_id) FROM homework.transactions").text.strip()
    if int(ids) != count:
        raise AssertionError("duplicate transaction ids")
    measurements = []
    runs = {}
    prefix = str(time.time_ns())
    for repeat in range(12):
        order = list(queries)
        shift = repeat % len(order)
        order = order[shift:] + order[:shift]
        for name in order:
            query_id = f"check_{prefix}_{name}_{repeat}"
            query(queries[name] + " FORMAT CSVWithNames", query_id=query_id, use_query_cache=0, max_threads=2, log_queries=1, log_queries_probability=1, log_queries_min_query_duration_ms=0)
            if repeat >= 2:
                runs[query_id] = (name, repeat - 1)
    query("SYSTEM FLUSH LOGS")
    logs = query(f"SELECT query_id, query_duration_ms, read_rows, read_bytes, memory_usage FROM system.query_log WHERE type = 'QueryFinish' AND startsWith(query_id, 'check_{prefix}_') FORMAT JSON").json()["data"]
    for log in logs:
        if log["query_id"] in runs:
            name, repeat = runs[log["query_id"]]
            measurements.append({
                "variant": name,
                "run": repeat,
                "seconds": int(log["query_duration_ms"]) / 1000,
                "read_rows": int(log["read_rows"]),
                "read_bytes": int(log["read_bytes"]),
                "peak_memory_bytes": int(log["memory_usage"])
            })
    if len(measurements) != 10 * len(queries):
        raise AssertionError("missing query measurements")
    measurements.sort(key=lambda row: (row["run"], row["variant"]))
    with open("results/times.csv", "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(measurements[0]))
        writer.writeheader()
        writer.writerows(measurements)
    report = {
        "file": args.file,
        "rows": count,
        "states": len(expected),
        "clickhouse": query("SELECT version()").text.strip(),
        "threads": 2,
        "timing_source": "system.query_log.query_duration_ms",
        "runs": 10,
        "cache": "query cache disabled; two warm-up runs per variant",
        "result_matches_csv": True,
        "all_stored_rows_match_csv": True,
        "source_sha256": hashlib.sha256(Path(args.file).read_bytes()).hexdigest()
    }
    for name in queries:
        report[name + "_seconds"] = median(x["seconds"] for x in measurements if x["variant"] == name)
    report["peak_memory_bytes"] = {name: median(x["peak_memory_bytes"] for x in measurements if x["variant"] == name) for name in queries}
    report["speedup"] = report["before_seconds"] / report["after_seconds"] if report["after_seconds"] else None
    report["max_speedup"] = report["before_seconds"] / report["max_seconds"] if report["max_seconds"] else None
    report["extra_speedup"] = report["after_seconds"] / report["max_seconds"] if report["max_seconds"] else None
    report["storage"] = query("SELECT table, sum(rows) AS rows, sum(bytes_on_disk) AS bytes FROM system.parts WHERE database = 'homework' AND active AND table IN ('transactions', 'transactions_fast', 'state_maximums') GROUP BY table ORDER BY table FORMAT JSON").json()["data"]
    Path("results/check.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
