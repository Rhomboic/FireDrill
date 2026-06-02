# FireDrill — Project Plan & Current State

> Onboarding/roadmap doc. Point a new session here. Companion to
> [`docs/FINDINGS.md`](FINDINGS.md) (results/analysis). Last updated: 2026-06-02.

## What this is

FireDrill is an **agent gym for incident response**, built as a portfolio project
for Fleet AI (which builds RL gyms for agents). The artifact is the **environment**,
not a scorer: a reusable, resettable, sandboxed world a tool-using agent is dropped
into to diagnose and fix a broken software project. The eval sits on top of the env.

It is the companion to PuzzleChess (an eval system). FireDrill must demonstrate the
harder, Fleet-specific skill: **building environments**, plus a richer multi-dimensional
eval (resolution · blast radius · diagnosis quality), with **cost as a separate axis**.

Repo: github.com/Rhomboic/FireDrill. Dashboard target: firedrill.adamissah.com.

## Architecture (current)

```
gym/            FireDrillEnv (environment.py) + policy-agnostic protocol + tool action space
  protocol.py     Action / Observation / RewardSignal / StepResult (stdlib-only contract)
  tools.py        action space: read_file/write_file/list_directory/read_logs/run_command (+submit)
  environment.py  FireDrillEnv: reset/step/verify/snapshot/restore
agent/agent.py  ONE LLM policy that drives the env (swappable); 4-model registry
eval/
  eval.py         4-dim scoring + cost axis + results payload + aggregate
  judge.py        LLM-as-judge for diagnosis quality (1–5)
  pricing.py      sourced per-model $ rates
runner/run_job.py local-first entrypoint: env → policy → verify → judge → score → results JSON (+optional S3)
scenarios/      the broken projects (filesystem/, metadata.json) + validate.py gate
docs/           firedrill.md (this), FINDINGS.md (results)
orchestrator/   (todo) launch the scenario × model matrix
terraform/      (todo) ECS-on-EC2 + ASG, ECR, S3, secrets, dashboard
dashboard/      (todo) static results site
.github/        (todo) OIDC CI for terraform + dashboard deploy
```

The gym is **stdlib-only and policy-agnostic**: the env never imports the agent;
any policy speaking the protocol can drive it (LLM agent, scripted, RL loop).

## Models (4) — and reasoning parity

| Provider | Flagship (reasoning, high effort) | Small (baseline, no reasoning) |
|---|---|---|
| Anthropic | `claude-opus-4-8` | `claude-haiku-4-5` |
| OpenAI | `gpt-5.5` | `gpt-4.1-mini` |

- **Both flagships reason at high effort** for a fair comparison (gpt-5.5 reasons
  intrinsically, so Opus must too): Opus = adaptive thinking + `output_config.effort=high`;
  gpt-5.5 = `reasoning_effort=high`. Small models are non-reasoning baselines.
- **gpt-5.5 requires the OpenAI Responses API** — chat completions returns 400 for
  `reasoning_effort` + function tools. `gpt-4.1-mini` uses chat completions.
- gpt-5.5 API snapshot id may need confirming via `MODEL_API_ID`.

## Scoring — the deviation that matters most

**Composite is QUALITY ONLY; cost is a separate first-class axis** (decided early,
PR #9):
- `composite = 0.6·resolution + 0.2·blast_radius + 0.2·diagnosis` (each 0–1).
- **Cost** is reported separately: cache-aware token buckets → dollars (sourced
  `eval/pricing.py`: opus $5/$25, haiku $1/$5, gpt-5.5 $5/$30, gpt-4.1-mini $0.40/$1.60)
  → saturating `cost_score = k/(k+cost)`, k=$0.10 (no upper bound needed).
- Rationale: quality answers "did it do the job well", cost answers "what did it cost";
  blending them hides the cost-vs-capability tradeoff (the headline dashboard view).
- Steps/latency are reported stats, not scored.

## Scenario design strategy (evolved from findings — read these before authoring)

Findings 1–3 (see FINDINGS.md): **small, localized bugs are quality-saturated** — all
four models (even the cheap ones) solve easy + medium scenarios with clean fixes and
5/5 diagnoses. Bug *type* (silent vs. crashing) is NOT the difficulty axis. What
discriminates:

1. **Regression-check TRAPS (primary lever).** The obvious fix passes the visible
   success condition but **breaks a held-out `regression_check`** (an unstated but
   reasonable edge). A model that minimally patches resolves *with blast radius*; a
   thorough one handles the edge. Scenario 03 (off-by-one) is the template.
2. **Scale / indirection.** Multi-file projects where *localizing* the bug is the work
   (symptom in module A, cause in module C). Most convincing, more authoring effort.

Hard-won rules:
- **Symptom-only descriptions.** Tell the model the user-facing side effect only — no
  file names, commands, expected values, or edge-case specs. Let it investigate.
- **Don't signpost the trap.** If the README/description mentions the edge case, every
  model handles it and the trap dies. The held-out check must test unstated robustness.
- **Thorough prompt.** The system prompt tells the agent incidents may have *multiple
  root causes/contributors* — fix all, handle edges — while keeping blast radius low.
  (The old "make the SMALLEST change" prompt was *causing* minimal patching.)
- **Protect the grader (un-gameable, SWE-bench style).** Test/verifier files are
  declared `protected_paths`; `verify()` restores them from golden before grading
  (so resolution can't be faked by editing the test) and they're excluded from blast
  radius (so strengthening a test isn't penalized).

Net result with all of the above: scenario 03 produces a real **two-tier capability
split** — flagships fix completely (composite 1.0), small models under-fix
(resolve symptom but ship a latent regression, ~0.76).

## metadata.json schema (current)

```json
{
  "name", "stack", "difficulty",
  "description":        "symptom-only incident report shown to the model",
  "bugs": [...],                                  // ground truth, not exposed
  "success_condition":  {"cmd": "...", "exit": 0},
  "regression_check":   {"cmd": "...", "exit": 0} | null,   // held-out
  "protected_paths":    ["tests", "verify_output.py"],      // grader files; restored before scoring, excl. from blast
  "files_expected_to_change": ["src/x.js"],
  "correct_diagnosis":  "ground-truth root cause (for the judge)",
  "reference_fix":      {"description", "cmd"},   // validate: must pass success + regression, clean
  "naive_fix":          {"description", "cmd"}    // trap bait: must pass success but FAIL regression
}
```

`scenarios/validate.py` gate: each scenario must be **broken → fixable → clean**, the
reference fix must pass any regression, and if `naive_fix` is present the gate proves
the **trap fires** (naive fix passes success, fails regression).

## Scenario lineup (10, balanced polyglot)

| # | name | stack | status |
|---|---|---|---|
| 01 | payments-service-down | Python | ✅ easy (missing env var + bad value) |
| 02 | silent-data-bug | Python | ✅ medium (dedup drops records) |
| 03 | off-by-one | Node | ✅ hard (regression-check trap) |
| 04 | failing-test | Python | ⏳ design as trap |
| 05 | dead-submit-button | React + Playwright | ⏳ UI (needs Docker) |
| 06 | layout-regression | React + Playwright | ⏳ UI |
| 07 | spinner-forever | React + Playwright | ⏳ UI |
| 08 | malformed-config | config | ⏳ |
| 09 | bad-dockerfile | Docker | ⏳ |
| 10 | wrong-join | SQLite | ⏳ |

UI scenarios use headless Playwright (chromium) as the objective verifier; they need
Docker. The rest run locally with plain python3/node (no deps), keeping a fast loop.

## Infra (todo — Day 2 of original plan; mostly reuses PuzzleChess)

- **Containerize:** `Dockerfile.base` (layers /opt/firedrill: gym+agent+eval+runner) +
  per-scenario `Dockerfile` (scenario fs at /workspace). One image per scenario; `MODEL`
  is a runtime env override (one image serves all models). `runner/run_job.py` is already
  container-ready (reads SCENARIO/MODEL/S3_* from env).
- **Compute:** ECS-on-EC2 with an **Auto Scaling Group via a managed-scaling capacity
  provider** — ECS places one container per (scenario×model) job and scales the fleet
  out when at capacity, in when idle. (Not Fargate — we want a real Docker host model;
  reuses chess's ecr/iam/secrets/network terraform, swap launch type.)
- **Results → S3** (`runs/<model>/<scenario>.json` + manifest); **dashboard** at
  firedrill.adamissah.com (reuse chess CloudFront/ACM/Route53 static-site pattern;
  views: model×scenario matrix, 4-dim scores, cost-vs-capability scatter, transcript viewer).
- **GitHub Actions (OIDC, no static keys):** a `terraform` workflow + a `deploy-dashboard`
  workflow (sync to S3 + CloudFront invalidation). Mirror chess `.github/workflows`.

## Live observability

Every tool call streams a timestamped line to **stdout** during the episode
(`[HH:MM:SS] step N | read_file path -> ok`, `submit | diagnosis: ...`, `⚠ blast`
flag on unexpected-file touches), so `docker logs` / CloudWatch show the run live.
`FIREDRILL_QUIET=1` suppresses it.

## Workflow & conventions

- **PR cadence:** branch → commit a coherent change → push → open PR → **stop and wait
  for the user to merge** before the next chunk. (See memory `firedrill-pr-workflow`.)
- **Secrets:** real keys go in `.env` (gitignored), never `.env.example`. gitleaks CI
  gates every push. Scenario fixtures use only obviously-fake secrets.
- **Tests:** `tests/smoke_*.py` run with no API keys (fake clients) — gym, agent, eval,
  runner, protected-verifier. Run all before a scenario/gym PR.

## Status snapshot (2026-06-02)

Done: gym core, 4-model policy (reasoning parity, Responses API), eval+judge+cost,
local runner, live logging, scenarios 01–03, validation gate with trap proof,
protected grader, sourced pricing, findings 1–3.

Next: write Finding 3 to FINDINGS.md; author scenarios 04–10 (symptom-only, trap/scale,
protected graders); then containerize + terraform (ECS-on-EC2+ASG) + dashboard + OIDC CI;
run the full 10×4 matrix; write README with the cost-vs-capability story.

## Open questions / decisions to revisit

- Getting a *model* spread reliably needs unsignposted traps + the thorough prompt, or
  genuine scale/indirection. Small-bug scenarios will keep saturating — that's itself a
  finding (cost is the differentiator), but build ≥1 genuinely hard scale scenario.
- Optional rigor: reconcile computed cost against the provider org Cost APIs after a full
  run (actual billed $ is token-deterministic, so computed = billed given right prices).
