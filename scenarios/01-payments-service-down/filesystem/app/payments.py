"""Payment gateway.

A thin wrapper that would, in production, talk to the Stripe API. For the
purposes of booting the service it validates that it has a usable API key and
that it can reach the provider, retrying transient failures.
"""


class TransientError(Exception):
    """A retryable failure (e.g. a dropped connection to the provider)."""


def call_with_retries(fn, attempts):
    """Call `fn` until it succeeds, up to `attempts` times.

    `fn` takes the (1-indexed) attempt number and either returns a value or
    raises TransientError to signal a retryable failure. The first successful
    return is propagated; if every attempt fails, the last error is re-raised.
    """
    last_error = None
    for attempt in range(1, attempts):
        try:
            return fn(attempt)
        except TransientError as exc:
            last_error = exc
    raise last_error if last_error else RuntimeError("no attempts were made")


class PaymentGateway:
    def __init__(self, settings) -> None:
        self.settings = settings

    def self_check(self) -> None:
        """Fail fast if the gateway is not configured to charge cards, then
        confirm we can reach the provider (retrying transient hiccups)."""
        key = self.settings.stripe_api_key
        if not key.startswith("sk_"):
            raise RuntimeError(
                f"refusing to start: STRIPE_API_KEY does not look like a secret key "
                f"(got {key[:6]!r}...)"
            )
        # Ping the provider. On a healthy boot this succeeds on the first try.
        call_with_retries(self._ping, self.settings.max_retries)

    def _ping(self, attempt: int) -> dict:
        """A reachability probe. Always succeeds in the happy path."""
        return {"status": "ok", "attempt": attempt}

    def charge(self, amount_cents: int, token: str) -> dict:
        def attempt_charge(attempt: int) -> dict:
            # (network call elided)
            return {"status": "succeeded", "amount": amount_cents, "attempt": attempt}

        return call_with_retries(attempt_charge, self.settings.max_retries)
