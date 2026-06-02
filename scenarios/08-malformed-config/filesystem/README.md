# web-service

A small web service with layered configuration.

Config is merged from two files (and an optional env override):

- `config/defaults.json` — baseline values shipped with the service.
- `config/settings.json` — the operator's per-deployment overrides, which are
  meant to take precedence over the defaults.
- `REQUEST_TIMEOUT` — optional env var that overrides everything.

## Run

```
python3 app.py
```

A healthy start prints `server ready ...` with the effective config. Startup
logs are in `logs/`.
