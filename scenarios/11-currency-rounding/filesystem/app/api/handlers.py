"""Thin API layer.

Handlers validate input and delegate to services. They contain no business
logic of their own (CONVENTIONS.md).
"""

from app.services.billing import split_bill


def handle_split_bill(payload: dict) -> dict:
    total_cents = int(payload["total_cents"])
    payers = int(payload["payers"])
    shares = split_bill(total_cents, payers)
    return {"shares": shares, "total": sum(shares)}
