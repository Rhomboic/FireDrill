"""DEPRECATED pre-Money pricing helpers.

This module predates app.core.money and works in float dollars. It is kept only
so old import sites keep importing; do NOT use it in new code (see CONVENTIONS.md).
The functions here do not reconcile to the cent.
"""


def even_split(total_cents, n):
    """Old even-split: divide in float dollars and round each share the same way.

    Because every share is rounded independently and the remainder is dropped,
    the shares do not sum back to ``total_cents``.
    """
    dollars = total_cents / 100.0
    share = round(dollars / n, 2)
    return [int(round(share * 100))] * n
