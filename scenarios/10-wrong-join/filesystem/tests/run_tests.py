"""Revenue report tests. Run with: python3 tests/run_tests.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from report import build_db, get_revenue_report

report = dict(get_revenue_report(build_db()))

# Every customer must appear — including ones with no orders this period.
assert set(report) == {"Alice", "Bob", "Carol", "Dave", "Erin"}, \
    f"report is missing customers: {sorted(report)}"
# Dave placed no orders this period and must show 0, not be dropped.
assert report["Dave"] == 0, f"a customer with no orders should show 0, got {report.get('Dave')}"
# Only PAID orders count toward revenue (Alice's pending order must be excluded).
assert report["Alice"] == 100.0, report.get("Alice")
assert report["Bob"] == 200.0, report.get("Bob")
assert report["Carol"] == 100.0, report.get("Carol")
assert report["Erin"] == 40.0, report.get("Erin")

print("revenue report tests passed")
