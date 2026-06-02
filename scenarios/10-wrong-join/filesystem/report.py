"""Revenue report: total revenue per customer for the period."""

import sqlite3
from pathlib import Path

QUERY = """
SELECT c.name, COALESCE(SUM(o.amount), 0) AS revenue
FROM customers c
JOIN orders o ON o.customer_id = c.id
GROUP BY c.id
ORDER BY c.name
"""


def build_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.executescript(Path("data/seed.sql").read_text())
    return conn


def get_revenue_report(conn: sqlite3.Connection):
    return [(name, round(revenue, 2)) for name, revenue in conn.execute(QUERY)]


def main() -> None:
    for name, revenue in get_revenue_report(build_db()):
        print(f"{name}: {revenue:.2f}")


if __name__ == "__main__":
    main()
