# Engineering conventions

A few rules this codebase holds itself to. New code is expected to follow them;
reviewers will push back if it doesn't.

## Money

- **Money is integer cents.** Every amount is a whole number of cents, wrapped in
  `app.core.money.Money`. Do not represent money as a float anywhere. Float
  arithmetic loses fractions of a cent and makes totals stop reconciling.
- **Do money math through `app.core.money`.** Don't reimplement money handling
  with floats or ad-hoc rounding. Use the shared money primitive so amounts stay
  exact.

## Layering

- `app/api` is a thin layer: validate input, call a service, return. No business
  logic in handlers.
- `app/services` holds business logic and calls `app/repositories` for data.
- `app/core` holds shared primitives (money, config). It depends on nothing else.

## Deprecated code

- `app/legacy/` predates the conventions above (it works in float dollars). It is
  kept only so existing import sites keep working. **Do not call it from new or
  fixed code.** Moving a caller off `app.legacy` is the preferred fix, not a
  reason to keep using it.

## Stable interfaces

- Public service functions (e.g. `app.services.billing.split_bill`) are called
  from multiple places. Keep their signatures stable when fixing them.
