# revenue-report

Generates the per-customer revenue report for the period from the SQLite
database seeded in `data/seed.sql`. The schema has `customers` and `orders`
(one row per order, with the order `amount` and a `status` of `paid`,
`pending`, or `refunded`).

Revenue counts **paid** orders only. Every customer must appear on the report,
including customers with no paid revenue this period (shown as `0.00`).

## Run

```
python3 report.py          # prints the report
python3 tests/run_tests.py # checks it
```
