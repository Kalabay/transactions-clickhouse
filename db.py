import os

import requests


def query(sql, **settings):
    response = requests.post(
        os.getenv("CLICKHOUSE_URL", "http://localhost:8124"),
        auth=(os.getenv("CLICKHOUSE_USER", "student"), os.getenv("CLICKHOUSE_PASSWORD", "local_password")),
        params=settings,
        data=sql.encode(),
        timeout=120
    )
    response.raise_for_status()
    return response
