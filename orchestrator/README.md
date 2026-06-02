# Orchestrator

Scripts to run the gym — locally in Docker, or as the full matrix on the ECS/EC2
cluster.

| Script | What |
|---|---|
| `run_local_docker.sh <scenario> <model>` | build + run one job locally in a container |
| `push_images.sh` | build + push the `base` and `ui` images to ECR |
| `run_matrix.sh [scenario] [model]` | launch jobs as ECS tasks (one container per job) |

## Cloud run

```bash
# 0. Infra is up (terraform apply) and the API keys are in Secrets Manager.

# 1. Push the images.
./orchestrator/push_images.sh

# 2. Launch jobs. The capacity provider scales the ASG out to run them.
./orchestrator/run_matrix.sh                       # every scenario × every model (10×4)
./orchestrator/run_matrix.sh 03-off-by-one         # one scenario × every model
./orchestrator/run_matrix.sh 03-off-by-one gpt-5.5 # a single job
```

Each task runs `runner/run_job.py` with `SCENARIO`/`MODEL` as container env
overrides; the `web` scenarios (05–07) run on the `ui-job` task definition
(Playwright image), everything else on `job`. Results land at
`s3://<results-bucket>/runs/<model>/<scenario>.json`; live tool traces are in
CloudWatch (`/ecs/firedrill`). Set `GPT55_API_ID` to pin gpt-5.5's snapshot.
