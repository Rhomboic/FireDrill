"""Payment gateway.

A thin wrapper that would, in production, talk to the Stripe API. For the
purposes of booting the service it validates that it has a usable API key.
"""


class PaymentGateway:
    def __init__(self, settings) -> None:
        self.settings = settings

    def self_check(self) -> None:
        """Fail fast if the gateway is not configured to charge cards."""
        key = self.settings.stripe_api_key
        if not key.startswith("sk_"):
            raise RuntimeError(
                f"refusing to start: STRIPE_API_KEY does not look like a secret key "
                f"(got {key[:6]!r}...)"
            )

    def charge(self, amount_cents: int, token: str) -> dict:
        for attempt in range(self.settings.max_retries):
            # (network call elided)
            return {"status": "succeeded", "amount": amount_cents, "attempt": attempt}
        raise RuntimeError("charge failed after retries")
