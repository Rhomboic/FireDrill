# FireDrill dashboard

A Vite + React app that renders the gym's results — a model × scenario matrix
(composite score + cost per cell), a per-model summary, and a per-job drawer with
the diagnosis, blast radius, the unified diff of the agent's fix, the full tool
transcript, and the objective verification output.

It reads the result JSONs straight from S3 (`runs/manifest.json` then
`runs/<model>/<scenario>.json`). Override the source with `?base=<url>`.

## Develop

```bash
npm install
npm run dev        # http://localhost:5173 — reads /results/ (put a manifest.json
                   # + <model>/<scenario>.json under public/results for local data)
npm run build      # -> dist/  (deployed to S3/CloudFront)
```

The live site at firedrill.adamissah.com is the built `dist/` synced to S3,
fronted by CloudFront, and reads results from the public `runs/*` prefix.
