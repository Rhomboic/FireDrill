# status-service

A tiny HTTP service with a `/health` endpoint, shipped as a container.

Build and run it the way the `Dockerfile` describes, then check that it serves:

```
GET /health  ->  200 {"status":"ok"}
```

Right now a freshly built container does not stay up long enough to answer.
`verify_serves.py` reproduces the build-and-run and probes `/health`.
