"""Daily revenue pipeline.

Reads the day's transactions and produces a summary (total revenue + transaction
count) for the finance report. Run with `python3 pipeline.py`.
"""

import json
from pathlib import Path

DATA = "data/transactions.json"


def load_transactions(path: str = DATA) -> list[dict]:
    return json.loads(Path(path).read_text())


def total_revenue(records: list[dict]) -> float:
    """Add up the revenue across the given transactions."""
    total = 0.0
    for r in records:
        total += r["amount"]
    return total


def summarize(records: list[dict]) -> dict:
    """Summarize the day's transactions into total revenue and a count."""
    # Index the transactions so we can look them up by customer.
    by_customer = {r["customer_id"]: r for r in records}
    deduped = list(by_customer.values())
    return {"total": total_revenue(deduped), "count": len(deduped)}


def build_report(records: list[dict]) -> dict:
    """Assemble the finance report payload from the raw transactions."""
    summary = summarize(records)
    return {
        "total": summary["total"],
        "count": summary["count"],
    }


def main() -> None:
    records = load_transactions()
    report = build_report(records)
    print(f"revenue summary: total={report['total']:.2f} count={report['count']}")


if __name__ == "__main__":
    main()
