"""Web service entrypoint. Loads config/settings.json and starts the server."""

import json
import sys
from pathlib import Path

CONFIG = "config/settings.json"


def load_config(path: str = CONFIG) -> dict:
    return json.loads(Path(path).read_text())


def main() -> int:
    cfg = load_config()
    port = int(cfg["port"])
    workers = int(cfg["workers"])
    if workers < 1:
        raise ValueError(f"workers must be >= 1, got {workers}")
    print(f"server ready on port {port} with {workers} workers ({cfg['log_level']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
