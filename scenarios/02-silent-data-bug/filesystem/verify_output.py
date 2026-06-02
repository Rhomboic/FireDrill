"""Verifier for the revenue summary.

Finance has confirmed the correct figures for today's transactions:
the report must total $964.50 across all 10 transactions. This check fails
(exit 1) if pipeline.summarize() does not produce those figures.
"""

import sys

from pipeline import load_transactions, summarize

EXPECTED_TOTAL = 964.50
EXPECTED_COUNT = 10


def main() -> int:
    summary = summarize(load_transactions())
    ok = True
    if summary["count"] != EXPECTED_COUNT:
        print(f"FAIL count: got {summary['count']}, expected {EXPECTED_COUNT}")
        ok = False
    if abs(summary["total"] - EXPECTED_TOTAL) > 0.005:
        print(f"FAIL total: got {summary['total']:.2f}, expected {EXPECTED_TOTAL:.2f}")
        ok = False
    if ok:
        print("output verified ✓")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
