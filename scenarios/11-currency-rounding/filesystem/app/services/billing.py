"""Billing service: how a bill is divided among payers.

NOTE: this still calls the deprecated float splitter in app.legacy.pricing.
See logs/billing.log for the support tickets about splits that don't add up.
Per CONVENTIONS.md this should move onto app.core.money.Money, whose `allocate`
reconciles to the cent and splits fairly.
"""

from app.legacy.pricing import even_split


def split_bill(total_cents: int, n: int) -> list[int]:
    """Split a bill of ``total_cents`` evenly across ``n`` payers.

    Returns a list of ``n`` integer-cent shares. This is a public service
    function: app.api.handlers and app.services.refunds call it, so keep the
    signature stable.
    """
    return even_split(total_cents, n)
