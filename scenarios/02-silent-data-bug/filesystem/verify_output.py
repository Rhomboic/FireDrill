"""Verifier for the revenue summary.

Finance has confirmed the correct figures for today's transactions:
the report must total $964.60 across all 10 transactions. This check fails
(exit 1) if the pipeline does not produce those figures.
"""

import sys

from pipeline import build_report, load_transactions

EXPECTED_TOTAL = 964.60
EXPECTED_COUNT = 10


def main() -> int:
    report = build_report(load_transactions())
    ok = True
    if report["count"] != EXPECTED_COUNT:
        print(f"FAIL count: got {report['count']}, expected {EXPECTED_COUNT}")
        ok = False
    if abs(float(report["total"]) - EXPECTED_TOTAL) > 0.005:
        print(f"FAIL total: got {float(report['total']):.2f}, expected {EXPECTED_TOTAL:.2f}")
        ok = False
    if ok:
        print("output verified ✓")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
