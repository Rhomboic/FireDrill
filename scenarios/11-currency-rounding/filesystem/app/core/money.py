"""The money primitive for the whole service.

Every amount in this codebase is an integer number of cents wrapped in `Money`.
We never represent money as a float: float arithmetic silently loses fractions
of a cent and makes totals fail to reconcile. See CONVENTIONS.md.

When you need to divide an amount (split a bill, prorate a charge, distribute a
refund), use `Money.allocate` rather than dividing by hand. It guarantees two
things that naive division does not:

  * the parts sum back to EXACTLY the original amount (no cent is created or
    lost), and
  * the split is fair — the parts differ by at most one cent beyond what their
    weights already imply.
"""

from __future__ import annotations

from decimal import Decimal


class Money:
    __slots__ = ("cents",)

    def __init__(self, cents: int):
        if not isinstance(cents, int) or isinstance(cents, bool):
            raise TypeError(f"Money is integer cents, got {type(cents).__name__}")
        self.cents = cents

    @classmethod
    def from_dollars(cls, dollars) -> "Money":
        """Build Money from a dollar amount given as a string or Decimal.

        Floats are intentionally not accepted: passing 0.1 + 0.2 here should be a
        loud error, not a silent 0.30000000000000004.
        """
        if isinstance(dollars, float):
            raise TypeError("pass dollars as a string or Decimal, never a float")
        d = Decimal(str(dollars))
        return cls(int((d * 100).to_integral_value()))

    def allocate(self, weights: list[int]) -> list["Money"]:
        """Split this amount across `weights` using the largest-remainder method.

        Returns one Money per weight. The cents sum exactly to ``self.cents`` and
        the leftover cents (the part that does not divide evenly) are handed to
        the entries with the largest fractional remainder, so the split is as
        even as it can be.
        """
        total = sum(weights)
        if total <= 0:
            raise ValueError("weights must sum to a positive amount")

        shares = [self.cents * w // total for w in weights]
        leftover = self.cents - sum(shares)

        # Distribute the leftover cents to the largest remainders first.
        order = sorted(
            range(len(weights)),
            key=lambda i: (self.cents * weights[i]) % total,
            reverse=True,
        )
        for i in range(leftover):
            shares[order[i]] += 1

        return [Money(s) for s in shares]

    def __eq__(self, other) -> bool:
        return isinstance(other, Money) and other.cents == self.cents

    def __hash__(self) -> int:
        return hash(self.cents)

    def __repr__(self) -> str:
        return f"Money({self.cents})"
