# revenue-pipeline

Produces the daily revenue summary (total + transaction count) for finance.

## Run

```
python3 pipeline.py        # prints the summary
python3 verify_output.py   # checks the summary against the known-correct figures
```

The summary must cover **every** transaction in `data/transactions.json`. Recent
reports have come in low — see `logs/`.
