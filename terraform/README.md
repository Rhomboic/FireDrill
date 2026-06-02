# FireDrill infrastructure (Terraform)

Provisions the cloud half of the gym: ECR, an S3 results bucket, Secrets Manager
for API keys, and an **ECS cluster on EC2** backed by an **Auto Scaling Group via
a managed-scaling capacity provider** — ECS places one container per
`(scenario × model)` job and scales the fleet out when at capacity, in when idle.
The ASG starts at 0 instances, so there's no cost until a job runs.

## Resources

| File | What |
|---|---|
| `state.tf` | S3 bucket for remote terraform state (versioned, encrypted) |
| `ecr.tf` | one repo, tags `base` (python/node/sql) and `ui` (Playwright) |
| `s3.tf` | results bucket; `runs/*` is public-read for the dashboard |
| `secrets.tf` | `firedrill/anthropic-api-key`, `firedrill/openai-api-key` |
| `iam.tf` | task execution role (ECR/logs/secrets), task role (S3), EC2 instance role |
| `asg.tf` | ECS-optimized launch template + ASG (min 0) |
| `ecs.tf` | cluster, capacity provider (managed scaling), `job` + `ui-job` task defs |

## Deploy

```bash
# 0. The remote-state backend bucket must exist before `init` can use it.
#    Bootstrap it once with local state, then migrate:
terraform init -backend=false
terraform apply -target=aws_s3_bucket.tfstate    # creates firedrill-tfstate-<acct>
terraform init -migrate-state                    # move state into S3

# 1. Stand everything up.
terraform apply

# 2. Put the API keys in Secrets Manager (once).
aws secretsmanager put-secret-value --secret-id firedrill/anthropic-api-key --secret-string "$ANTHROPIC_API_KEY"
aws secretsmanager put-secret-value --secret-id firedrill/openai-api-key    --secret-string "$OPENAI_API_KEY"

# 3. Build + push both images to ECR.
ECR=$(terraform output -raw ecr_repository_url)
aws ecr get-login-password | docker login --username AWS --password-stdin "$ECR"
docker build              -t "$ECR:base" --platform linux/amd64 ..
docker build -f ../Dockerfile.ui -t "$ECR:ui" --platform linux/amd64 ..
docker push "$ECR:base" && docker push "$ECR:ui"
```

Running the `scenario × model` matrix as ECS tasks (SCENARIO/MODEL as container
overrides) is driven by `orchestrator/` — added next.

> The backend `bucket` in `main.tf` hardcodes the AWS account id. Update it if
> you deploy to a different account.
