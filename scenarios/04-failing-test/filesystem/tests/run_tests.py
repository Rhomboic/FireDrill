"""Invoice tests. Run with: python3 tests/run_tests.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from invoice import compute_total

# Quantities must be multiplied; no tax, no rounding needed in this suite.
assert compute_total([{"price": 10.0, "qty": 3}], 0.0) == 30.0, "qty should multiply"
assert compute_total(
    [{"price": 5.0, "qty": 2}, {"price": 20.0, "qty": 1}], 0.0) == 30.0, "multi-line subtotal"

print("invoice tests passed")
