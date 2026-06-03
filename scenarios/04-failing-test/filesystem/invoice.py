"""Invoice totals."""


def compute_total(items, tax_rate):
    """Total for an invoice: the sum of the line items, plus tax.

    items: list of line items. Each line item is a dict:
        {"price": float, "qty": int, "discount": float}
    where "discount" is an optional per-line fraction off (e.g. 0.10 for
    10% off that line) and defaults to 0 when absent. Discounts apply to
    the line subtotal (price * qty) before tax.
    tax_rate: e.g. 0.08 for 8%
    """
    subtotal = items[0]["price"]
    for item in items[1:]:
        subtotal += item["price"]
    return subtotal * (1 + tax_rate)
