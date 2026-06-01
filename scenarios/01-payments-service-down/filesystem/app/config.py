"""Configuration loading for the payments service.

Reads config/.env into the process environment and parses it into a typed
Settings object. A misconfigured .env will surface here at startup.
"""

import os
from pathlib import Path

ENV_PATH = "config/.env"


def load_env(path: str = ENV_PATH) -> None:
    """Load KEY=VALUE lines from config/.env into os.environ."""
    env_file = Path(path)
    if not env_file.exists():
        raise FileNotFoundError(f"configuration file not found: {path}")
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


class Settings:
    """Typed view over the service configuration. Raises on missing/invalid keys."""

    def __init__(self) -> None:
        # Secret key for the payments provider — required, no sane default.
        self.stripe_api_key = os.environ["STRIPE_API_KEY"]
        # Operational knobs.
        self.max_retries = int(os.environ.get("MAX_RETRIES", "3"))
        self.port = int(os.environ.get("PORT", "8080"))
        self.env = os.environ.get("ENV", "development")
