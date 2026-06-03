# invoice

Computes order totals (line items + tax) for the billing service. Each line
item carries a `price`, a `qty`, and an optional per-line `discount` (a fraction
off the line subtotal, applied before tax).

## Test

```
python3 tests/run_tests.py
```
