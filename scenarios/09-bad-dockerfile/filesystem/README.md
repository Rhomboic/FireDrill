# status-service

A tiny HTTP service, shipped as a container. It exposes:

```
GET /health   ->  200 {"status":"ok"}
GET /version  ->  200 {"service":"status-service","version":"1.4.2"}
```

`/version` is not hardcoded — the app reads its payload at request time from the
packaged `templates/version.json` asset.

Build and run it the way the `Dockerfile` describes, then check that it serves.
Right now a freshly built container does not stay up long enough to answer.
`verify_serves.py` reproduces the build-and-run and probes `/health`.
