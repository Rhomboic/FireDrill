# payments-service

Charges customer cards via Stripe. Boots with `python main.py`, which loads
`config/.env`, validates configuration, and runs a startup self-check.

## Run

```
python main.py
```

A healthy boot prints `payments service ready`. Startup logs are written to
`logs/`.
