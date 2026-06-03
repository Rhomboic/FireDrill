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

A gym is only useful if it separates policies. The first matrix (one well-signposted bug per scenario) was **quality-saturated**: every model resolved 8/10 and the composite spread across all four models was just **0.024** — no signal. Adding the regression trap to every scenario **quadrupled** the spread to **0.100** and produced a clean two-tier split.

**Most recent full run** — 10 scenarios × 4 models, reasoning flagships at high effort:

| Model | Composite | Resolution | Blast radius | Diagnosis | Regression pass | $ / job |
|---|---|---|---|---|---|---|
| **Claude Opus 4.8** | **0.98** | 100% | 0.90 | 0.98 | 9/10 | $0.096 |
| **GPT-5.5** | **0.97** | 100% | 0.90 | 0.96 | 9/10 | $0.108 |
| Claude Haiku 4.5 | 0.90 | 100% | 0.60 | 0.88 | 6/10 | $0.037 |
| GPT-4.1 mini | 0.88 | 100% | 0.60 | 0.78 | 6/10 | $0.0055 |

Three things the data shows:

1. **Resolution alone is blind.** Every model — including the cheapest — makes the visible success condition pass, so **resolution is 100% across the board**. The capability gap is invisible to pass/fail; it only surfaces in the held-out regression and blast radius. This is the entire argument for a multi-dimensional reward.
2. **The trap discriminates *through* blast radius.** A failed `regression_check` hard-zeros the blast-radius dimension (a fix that breaks a held-out check is maximal collateral damage), costing the full 0.2 composite weight. Flagships pass **9/10** regressions, small models **6/10** — which is exactly the blast gap (0.90 vs 0.60) and the composite gap.
3. **The flagships now *earn* their premium.** Before the trap they cost ~17–44× more for identical scores; now they cost ~17× more **and** pass the traps the cheap models fail. If you only need the surface fix, GPT-4.1-mini is the value pick at **$0.0055/job**; when fix *correctness* matters, the flagships are worth it.

**Which traps fired** (composite per model; `*` = took the bait — failed the held-out regression):

| Scenario | Opus | GPT-5.5 | Haiku | 4.1-mini | the trap |
|---|---|---|---|---|---|
| 08 malformed-config | 1.00 | 1.00 | 0.72\* | 0.72\* | config-precedence merge (defaults shadow operator settings) |
| 01 payments-service-down | 1.00 | 1.00 | 0.76\* | 0.76\* | retry helper gives up one attempt early |
| 03 off-by-one | 1.00 | 0.96 | 0.76\* | 0.76\* | unguarded loop on partial / out-of-range pages |
| 02 silent-data-bug | 0.76\* | 0.76\* | 0.76\* | 0.76\* | float money vs Decimal |
| 04 failing-test | 1.00 | 1.00 | 0.96 | 0.92 | empty-order edge |
| 05 dead-submit-button | 1.00 | 1.00 | 1.00 | 0.92 | inverted validation |
| 06 layout-regression | 1.00 | 1.00 | 1.00 | 0.92 | holds on mobile viewport |
| 07 spinner-forever | 1.00 | 1.00 | 1.00 | 1.00 | paginated-envelope response shape |
| 09 bad-dockerfile | 1.00 | 1.00 | 1.00 | 1.00 | shell-form CMD swallows SIGTERM |
| 10 wrong-join | 1.00 | 1.00 | 1.00 | 1.00 | one-to-many JOIN fan-out |

**6 of 10 scenarios now discriminate, up from 2** — and **three traps (08, 01, 03) fire on the small models only**, the ideal flagship-vs-baseline split.

**Honest calibration note.** A trap only discriminates in the narrow band where flagships catch it and small models don't, and four scenarios miss that band: **02 is too hard** (the float-vs-Decimal edge fools all four → everyone 0.76), and **07 / 09 / 10 are too easy** (every model handled the response-shape, SIGTERM, and JOIN-fan-out edges → all 1.00). The 04/05/06 dips come from the diagnosis judge and blast radius catching the *weakest* model, not from the trap firing. Tightening 02 (soften) and 07/09/10 (sharpen) is the next iteration — and the only way to find that band is empirically, by running the matrix and reading exactly this table. That tuning loop *is* the work of building a gym.

## Layout

```
gym/            FireDrillEnv (environment.py), the policy-agnostic protocol, and the tool action space
agent/          one LLM policy that drives the env (Claude + OpenAI), swappable
eval/           4-dimension scoring + LLM-as-judge
runner/         container entrypoint: reset → run policy → verify → score → upload results
scenarios/      the 10 broken projects (filesystem/ + metadata.json each)
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
autoscaling across four models; the latest run shows a clean two-tier capability
split (composite spread 0.100, reasoning flagships ~0.97 vs small baselines
~0.89 — see Results). Results render at
**[firedrill.adamissah.com](https://firedrill.adamissah.com)**.
