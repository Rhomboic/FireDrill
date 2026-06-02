"""Invoice totals."""


def compute_total(items, tax_rate):
    """Total for an invoice: the sum of the line items, plus tax.

    items: list of {"price": float, "qty": int}
    tax_rate: e.g. 0.08 for 8%
    """
    subtotal = items[0]["price"]
    for item in items[1:]:
        subtotal += item["price"]
    return subtotal * (1 + tax_rate)
