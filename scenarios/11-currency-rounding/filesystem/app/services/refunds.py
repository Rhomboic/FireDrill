"""Refund service.

Splitting a refund across the original payers reuses the billing split so the
math stays consistent between what we charged and what we give back.
"""

from app.services.billing import split_bill


def split_refund(total_cents: int, n: int) -> list[int]:
    return split_bill(total_cents, n)
