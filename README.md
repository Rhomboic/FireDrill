# FireDrill

**An RL-compatible agent gym with a Gymnasium-style `reset`/`step`/`verify` interface.** FireDrill is a reusable, reproducible, resettable environment that **any** policy — an LLM agent, a human, or an RL training loop — can be dropped into and stepped through. The artifact is the *environment*, not the scorer.

The task domain makes it concrete: it's 11pm, a startup's service is down, and the on-call engineer is an AI agent. Each environment is a stateful, broken software project with a real filesystem, logs, and side effects; the policy acts through tools and the world responds, with **reward queryable at any step** (the precondition for RL use). The agent must diagnose and fix the incident — and it's scored not just on *whether* it fixed things, but *how* it reasoned, how efficiently it worked, and whether it broke anything else along the way. Scoring is one consumer of the environment, not the point of it.

## The environment interface

The core primitive is a Gymnasium-style `FireDrillEnv`, fully decoupled from any agent:

```python
env.reset()                    # restore /workspace to a pristine golden state; return the task + first observation
env.step(action)               # action = a tool call; returns (observation, reward_signal, done, info)
env.verify()                   # run the objective checks at ANY point (resolution / blast radius / regression)
env.snapshot() / env.restore() # reproducible rollouts — one container, many episodes
```

- **Action space** — five tools: `read_file`, `write_file`, `list_directory`, `read_logs`, `run_command`.
- **Observation space** — file contents, directory listings, logs, and command stdout/stderr/exit codes.
- **Reward** — quality dimensions (queryable mid-episode), kept separate so a consumer can reweight them; the **composite is quality only**:
  - **Resolution** — does the previously-broken thing work now? (objective verifier)
  - **Blast radius** — did it touch/break anything outside the expected fix?
  - **Diagnosis quality** — an LLM-as-judge scores the agent's root-cause explanation 1–5.
- **Cost** — a separate first-class axis, *not* folded into the composite: cache-aware token usage priced to **dollars**, plus a saturating `k/(k+cost)` score (no upper bound needed). Quality answers "did it do the job well"; cost answers "what did that cost" — the cost-vs-capability tradeoff is the thing you actually compare. Steps and latency are reported as stats.

## Scenarios

Ten hand-authored **local projects** (not real repos — file trees baked into containers), a balanced polyglot set, each targeting one failure mode with an objective verifier that fails before the fix and passes after:

| # | Scenario | Stack | Failure mode |
|---|---|---|---|
| 1 | payments-service-down | Python | missing env var + dependency |
| 2 | silent-data-bug | Python | pipeline drops/corrupts records |
| 3 | off-by-one | Node | wrong result, no crash |
| 4 | failing-test | Python | recent change broke a green test |
| 5 | dead-submit-button | React + Playwright | broken submit handler |
| 6 | layout-regression | React + Playwright | nav overlaps content |
| 7 | spinner-forever | React + Playwright | wrong API base URL / CORS |
| 8 | malformed-config | config | broken YAML/JSON/.env |
| 9 | bad-dockerfile | Docker | wrong port / missing COPY |
| 10 | wrong-join | SQL | JOIN/filter returns wrong aggregate |

Each scenario also plants a **regression trap**: a second, subtler, production-shaped bug where the obvious *symptomatic* fix passes the visible success condition but fails a **held-out `regression_check`**. That trap is the lever that separates a careful reasoner from a hasty one — see Results.

## Results — does the gym discriminate?

A gym is only useful if it separates policies. The story arrived in three acts:

1. **Saturated.** The first matrix (one well-signposted bug per scenario) had every model resolving 8/10 — composite spread across the four models was just **0.024**. No signal.
2. **Traps.** A held-out regression trap on every scenario (the symptomatic fix passes the visible check but fails a hidden one) lifted the spread to **0.100**.
3. **Averaged.** A *single* run turned out to be too noisy to trust — an untouched scenario swung from 0.28 spread to 0.00 between two runs on model non-determinism alone. So each cell is now the **mean of 6 runs**. With the variance averaged out, the spread is **0.152** — the largest yet, and a stable ordering.

### Methodology

Each `(scenario × model)` cell runs **N = 6 episodes** and the scores are averaged (`run_matrix.sh` defaults to `REPEAT=3`; this run used 6). Resolution becomes a pass-*rate*; cost is reported two ways — **mean cost per run** (the per-cell value you compare models on) and **actual spend** across all runs (the real bill). Reasoning flagships run at high effort.

### Most recent run — 10 scenarios × 4 models, 6 runs/cell averaged

| Model | Composite | Resolution | Blast radius | Diagnosis | Cost / run | Actual spend |
|---|---|---|---|---|---|---|
| **Claude Opus 4.8** | **0.99** | 100% | 0.98 | 0.97 | $0.107 | $1.07 |
| **GPT-5.5** | **0.99** | 100% | 0.95 | 1.00 | $0.108 | $1.08 |
| Claude Haiku 4.5 | 0.94 | 100% | 0.78 | 0.92 | $0.040 | $0.40 |
| GPT-4.1 mini | 0.84 | 90% | 0.62 | 0.87 | $0.0066 | $0.066 |

What the data shows:

1. **Resolution alone is blind.** The top three resolve 100% and GPT-4.1-mini 90%, yet composites span **0.84 – 0.99**. The capability gap barely registers in pass/fail; it lives in the **held-out regression** and **blast radius**. This is the entire argument for a multi-dimensional reward.
2. **Discrimination flows through blast radius.** A failed `regression_check` hard-zeros the blast dimension (a fix that breaks a held-out check is maximal collateral), costing the full 0.2 composite weight. The blast column (0.98 → 0.62) *is* the composite spread.
3. **Cost tracks capability, and the bill is honest.** Opus costs ~16× GPT-4.1-mini per run **and** scores 0.15 higher. If you only need the surface fix, GPT-4.1-mini is the value pick at **$0.0066/run**; when fix *correctness* matters, the flagships earn the premium.

### Which traps fire (composite per model, averaged over 6 runs)

| Scenario | Opus | GPT-5.5 | Haiku | 4.1-mini | spread | the trap |
|---|---|---|---|---|---|---|
| 06 layout-regression | 0.99 | 1.00 | 0.99 | **0.67** | 0.33 | naive z-index/margin fix breaks on mobile |
| 09 bad-dockerfile | 1.00 | 1.00 | 1.00 | **0.72** | 0.28 | a `templates/` asset a 2nd endpoint needs is never `COPY`d |
| 03 off-by-one | 1.00 | 0.99 | **0.76** | **0.76** | 0.24 | unguarded loop on partial / out-of-range pages |
| 01 payments-service-down | 0.96 | 0.95 | **0.80** | **0.75** | 0.21 | retry helper gives up one attempt early |
| 07 spinner-forever | 1.00 | 1.00 | 1.00 | **0.83** | 0.17 | cursor-paginated API; only page 1 loads |
| 05 dead-submit-button | 1.00 | 0.95 | 1.00 | 0.87 | 0.13 | inverted validation rejects valid input |
| 08 malformed-config | 1.00 | 1.00 | 0.91 | 0.88 | 0.12 | config-precedence merge shadows operator settings |
| 02 silent-data-bug | 1.00 | 1.00 | 1.00 | 0.95 | 0.05 | float money vs Decimal |
| 04 failing-test | 0.96 | 1.00 | 0.96 | 0.96 | 0.04 | per-line discount applied before tax |
| 10 wrong-join | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 | LEFT JOIN degraded to inner by a `WHERE` |

**7 of 10 scenarios discriminate** (spread > 0.05), with a clear ordering: **Opus ≈ GPT-5.5 > Haiku > GPT-4.1-mini**. The harder traps (06, 09, 07) cleanly isolate the weakest model; the off-by-one-class traps (03, 01) split *both* small models from the flagships.

**The methodological lesson of this run:** the trap recalibration looked like it *failed* on a single noisy run (spread fell to 0.060), but the scenarios that scored 0.00 spread there — 06, 07, 09 — are the **strongest** discriminators once averaged over 6 runs. Trusting a benchmark means averaging out the variance first. Two scenarios still don't separate the tiers: **10 wrong-join** is too easy (every model handles the LEFT-JOIN trap) and **04 failing-test** is marginal — calibrating each trap to the narrow band where flagships pass and small models don't, on a *trustworthy* average, is the ongoing work of building a gym.

### The read, by model

The headline finding is that **capability here is a smooth gradient, not pass/fail** — every model fixes the visible bug, but *how well* it fixes it spans 0.84–0.99, and each model occupies a distinct point on the cost–capability frontier:

- **Claude Opus 4.8 — precision.** Top composite (0.99) on the strength of the **tightest blast radius in the field (0.98)**: when it fixes, it touches only what it should. Resolves everything; its only dips are the payments-retry and failing-test edges, a hair off perfect. Priciest at **$0.107/run** — worth it when surgical correctness is non-negotiable.
- **GPT-5.5 — diagnostician.** Tied with Opus on composite (0.99) and the **best root-cause explanations here (diagnosis 1.00)**, but a slightly looser blast radius (0.95) — it occasionally over-touches. Same price tier. Pick it for the clearest *why*, Opus for the cleanest *fix*.
- **Claude Haiku 4.5 — value.** **0.94 composite at ~⅓ the flagship cost**: resolves 100%, diagnoses well (0.92), only 0.05 behind the flagships. Its gap is blast radius (0.78) — on the off-by-one and payments traps it takes the symptomatic fix. The rational default for the median incident.
- **GPT-4.1-mini — the floor.** 0.84 composite, the **only sub-100% resolver (90%)**, loosest blast (0.62). It trips the hardest traps — layout-on-mobile (0.67), the missing Dockerfile `COPY` (0.72) — and sometimes can't resolve the surface bug at all. But at **$0.0066/run (~16× cheaper than Opus)**, it's the throughput play where errors are cheap to catch.

**The frontier:** Haiku **strictly dominates** GPT-4.1-mini (better *and* still cheap), and the flagships buy the last ~0.05 of capability at ~3× Haiku's cost. For most incident response Haiku is the sweet spot; reach for a flagship when a wrong or messy fix is expensive. This is exactly the comparison a single blended score would hide, and the reason cost is kept as its own axis.

## Layout

```
gym/            FireDrillEnv (environment.py), the policy-agnostic protocol, and the tool action space
agent/          one LLM policy that drives the env (Claude + OpenAI), swappable
eval/           4-dimension scoring + LLM-as-judge
runner/         container entrypoint: reset → run policy → verify → score → upload results
scenarios/      the broken projects (filesystem/ + metadata.json each)
orchestrator/   launch the scenario × model job matrix
terraform/      ECS-on-EC2 + autoscaling, ECR, S3, secrets, dashboard infra
dashboard/      static results dashboard (firedrill.adamissah.com)
```

## Run a job locally

No Docker or AWS needed — one `(scenario × model)` job from your shell:

```bash
pip install -r requirements.txt
cp .env.example .env          # add your ANTHROPIC_API_KEY / OPENAI_API_KEY
python3 runner/run_job.py --scenario 01-payments-service-down --model claude-opus-4-8
```

The runner resets the env, drives it with the model, verifies the fix, judges the
diagnosis, scores all four dimensions, and writes the results payload to
`results/<model>/<scenario>.json` (including a unified diff of what the agent
changed). Exits non-zero if the incident wasn't resolved.

Models: `claude-opus-4-8`, `claude-haiku-4-5`, `gpt-5.5`, `gpt-4.1-mini`. The
core gym is dependency-free; the smoke tests run with no API keys:

```bash
for t in gym agent eval runner; do python3 tests/smoke_$t.py; done
```

## Run a job in a container

The same entrypoint runs in Docker (this is the image that runs on ECS). One
universal image bundles the gym + all scenarios; `SCENARIO` and `MODEL` are
runtime env vars:

```bash
./orchestrator/run_local_docker.sh 03-off-by-one claude-opus-4-8
# builds firedrill:latest, runs the job, writes results/<model>/<scenario>.json
```

Python, Node, SQLite, and Docker scenarios run in this universal image; the
React/Playwright UI scenarios run in a dedicated Playwright image
(`Dockerfile.ui`, `firedrill:ui`).

## Infrastructure

Each job is a self-contained container — one `(scenario × model)` episode that resets the env, runs the policy, scores all four dimensions, and writes a self-describing result to S3. Jobs are spawned across an **EC2 Auto Scaling Group** via an ECS managed-scaling capacity provider: ECS places containers on instances and scales the fleet out when at capacity, in when idle. Results render at **firedrill.adamissah.com**.

## Status

Live. Ten scenarios across Python, Node, React/Playwright, config, Docker, and
SQL, each gated by an objective verifier (broken → fixable → clean) and a
held-out regression trap. The full `scenario × model` matrix runs on ECS-on-EC2
autoscaling across four models, **6 runs/cell averaged**; the latest run shows a
clean capability ordering (composite spread **0.152**, Opus ≈ GPT-5.5 0.99 >
Haiku 0.94 > GPT-4.1-mini 0.84 — see Results). Results render at
**[firedrill.adamissah.com](https://firedrill.adamissah.com)**.
