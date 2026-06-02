# revenue-report

Generates the per-customer revenue report for the period from the SQLite
database seeded in `data/seed.sql`. The schema has `customers`, `orders`
(one row per order, with the order `amount`) and `line_items` (one row per
item, many per order).

## Run

```
python3 report.py          # prints the report
python3 tests/run_tests.py # checks it
```
