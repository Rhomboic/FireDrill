# FireDrill

**An agent gym for incident response.** It's 11pm, a startup's service is down, and the on-call engineer is an AI agent. FireDrill drops a policy into a sandboxed, broken software project and asks it to diagnose and fix the incident — then scores not just *whether* it fixed things, but *how* it reasoned, how efficiently it worked, and whether it broke anything else along the way.

FireDrill is a **gym**: the artifact is the *environment* — a reusable, reproducible, resettable world that **any** policy (an LLM agent, a human, or an RL training loop) can be dropped into and stepped through. Each environment is a stateful software project with a real filesystem, logs, and side effects; the agent acts through tools, and the world responds. Scoring is one consumer of the environment, not the point of it.

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
- **Reward** — four dimensions, queryable mid-episode:
  - **Resolution** — does the previously-broken thing work now? (objective verifier)
  - **Efficiency** — how many steps did it take?
  - **Blast radius** — did it touch/break anything outside the expected fix?
  - **Diagnosis quality** — an LLM-as-judge scores the agent's root-cause explanation 1–5.

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

## Layout

```
gym/            FireDrillEnv (environment.py), the policy-agnostic protocol, and the tool action space
agent/          one LLM policy that drives the env (Claude + OpenAI), swappable
eval/           4-dimension scoring + LLM-as-judge
runner/         container entrypoint: reset → run policy → verify → score → upload results
scenarios/      the 10 broken projects (filesystem/, metadata.json, Dockerfile each)
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

## Infrastructure

Each job is a self-contained container — one `(scenario × model)` episode that resets the env, runs the policy, scores all four dimensions, and writes a self-describing result to S3. Jobs are spawned across an **EC2 Auto Scaling Group** via an ECS managed-scaling capacity provider: ECS places containers on instances and scales the fleet out when at capacity, in when idle. Results render at **firedrill.adamissah.com**.

## Status

🚧 Under active construction.
