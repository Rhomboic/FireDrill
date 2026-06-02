"""Web service entrypoint.

Configuration is layered. From lowest to highest precedence it should be:

    1. config/defaults.json   baseline shipped with the service
    2. config/settings.json   the operator's per-deployment overrides
    3. REQUEST_TIMEOUT env var an optional last-minute override

`effective_config()` merges the layers and the server runs on the result.
`python3 app.py` boots the service and prints the effective config.
"""

import json
import os
import sys
from pathlib import Path

DEFAULTS = "config/defaults.json"
SETTINGS = "config/settings.json"


def _load(path: str) -> dict:
    return json.loads(Path(path).read_text())


def effective_config() -> dict:
    """Merge the config layers into the effective runtime config.

    Operator settings are meant to win over the shipped defaults, and an
    optional REQUEST_TIMEOUT env var wins over everything.
    """
    defaults = _load(DEFAULTS)
    settings = _load(SETTINGS)

    cfg = dict(settings)
    cfg.update(defaults)  # layer the two config files

    env_timeout = os.environ.get("REQUEST_TIMEOUT")
    if env_timeout is not None:
        cfg["request_timeout"] = int(env_timeout)
    return cfg


def main() -> int:
    cfg = effective_config()
    port = int(cfg["port"])
    workers = int(cfg["workers"])
    timeout = int(cfg["request_timeout"])
    if workers < 1:
        raise ValueError(f"workers must be >= 1, got {workers}")
    print(
        f"server ready on port {port} with {workers} workers, "
        f"request_timeout={timeout}s ({cfg['log_level']})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
