# ledger-billing

A small billing service. It stores invoices and works out how a bill is divided
among the people paying it (and, on the refund side, how money is divided back).

## Layout

```
app/
  api/           thin request handlers (validate + delegate)
  services/      business logic: billing, refunds
  repositories/  data access (invoices)
  core/          shared primitives: money, config
  legacy/        deprecated pre-Money helpers — do not use in new code
tests/           acceptance checks (run_tests.py)
data/            seed invoices
logs/            service logs
```

## Running the checks

```
python3 tests/run_tests.py
```

## Conventions

See [CONVENTIONS.md](CONVENTIONS.md). The important one for this service: money is
integer cents via `app.core.money.Money`, and amounts are divided with
`Money.allocate`, never by hand.
