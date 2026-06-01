"""Payments service entrypoint.

Boots the service: loads configuration, constructs the payment gateway, runs a
startup self-check, and reports ready. Exits non-zero if anything fails to boot.
"""

import sys

from app.config import load_env, Settings
from app.payments import PaymentGateway


def main() -> int:
    load_env()                      # read config/.env into the environment
    settings = Settings()           # validate + parse configuration
    gateway = PaymentGateway(settings)
    gateway.self_check()            # verify the gateway is wired correctly
    print(f"payments service ready (env={settings.env}, port={settings.port})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
