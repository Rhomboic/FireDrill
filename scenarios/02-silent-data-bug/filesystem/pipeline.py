"""Daily revenue pipeline.

Reads the day's transactions and produces a summary (total revenue + transaction
count) for the finance report. Run with `python3 pipeline.py`.
"""

import json
from pathlib import Path

DATA = "data/transactions.json"


def load_transactions(path: str = DATA) -> list[dict]:
    return json.loads(Path(path).read_text())


def summarize(records: list[dict]) -> dict:
    """Summarize the day's transactions into total revenue and a count."""
    # Index the transactions so we can look them up by customer.
    by_customer = {r["customer_id"]: r for r in records}
    total = sum(r["amount"] for r in by_customer.values())
    return {"total": round(total, 2), "count": len(by_customer)}


def main() -> None:
    records = load_transactions()
    summary = summarize(records)
    print(f"revenue summary: total={summary['total']:.2f} count={summary['count']}")


if __name__ == "__main__":
    main()
