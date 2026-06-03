#!/usr/bin/env bash
# Launch the (scenario × model) matrix as ECS tasks on the EC2 cluster. The
# capacity provider scales the ASG out to run them and in when idle; each
# container writes its result to s3://<results-bucket>/runs/<model>/<scenario>.json.
#
# Usage:
#   ./orchestrator/run_matrix.sh                 # every scenario × every model
#   ./orchestrator/run_matrix.sh 03-off-by-one   # one scenario × every model
#   ./orchestrator/run_matrix.sh 03-off-by-one claude-opus-4-8   # a single job
#
# gpt-5.5's upstream snapshot id can be overridden with GPT55_API_ID.
#
# Each cell runs REPEAT times (default 3) and the runner averages the scores, so
# the dashboard value is the mean over runs — single runs are too noisy to trust.
#   REPEAT=5 ./orchestrator/run_matrix.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TF="${ROOT}/terraform"
REGION="${AWS_REGION:-us-west-1}"
REPEAT="${REPEAT:-3}"

CLUSTER="$(terraform -chdir="${TF}" output -raw ecs_cluster)"
CP="$(terraform -chdir="${TF}" output -raw capacity_provider)"
JOB_TD="$(terraform -chdir="${TF}" output -raw job_task_definition)"
UI_TD="$(terraform -chdir="${TF}" output -raw ui_job_task_definition)"
BUCKET="$(terraform -chdir="${TF}" output -raw s3_bucket)"

MODELS=(claude-opus-4-8 claude-haiku-4-5 gpt-5.5 gpt-4.1-mini)

# Build the containerOverrides JSON for one job (SCENARIO/MODEL, +MODEL_API_ID for gpt-5.5).
overrides() {
  local container="$1" scenario="$2" model="$3"
  local env="[{\"name\":\"SCENARIO\",\"value\":\"${scenario}\"},{\"name\":\"MODEL\",\"value\":\"${model}\"},{\"name\":\"REPEAT\",\"value\":\"${REPEAT}\"}"
  if [ "${model}" = "gpt-5.5" ] && [ -n "${GPT55_API_ID:-}" ]; then
    env="${env},{\"name\":\"MODEL_API_ID\",\"value\":\"${GPT55_API_ID}\"}"
  fi
  echo "{\"containerOverrides\":[{\"name\":\"${container}\",\"environment\":${env}]}]}"
}

launch() {
  local scenario="$1" model="$2" stack td container
  stack="$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['stack'])" \
    "${ROOT}/scenarios/${scenario}/metadata.json")"
  if [ "${stack}" = "web" ]; then td="${UI_TD}"; container="ui-job"; else td="${JOB_TD}"; container="job"; fi

  local arn
  arn="$(aws ecs run-task --region "${REGION}" \
    --cluster "${CLUSTER}" \
    --capacity-provider-strategy "capacityProvider=${CP},weight=1" \
    --task-definition "${td}" \
    --overrides "$(overrides "${container}" "${scenario}" "${model}")" \
    --query 'tasks[0].taskArn' --output text)"
  printf '  %-22s × %-18s -> %s\n' "${scenario}" "${model}" "${arn##*/}"
}

# Single job, single scenario, or the full matrix.
if [ "${1:-}" ] && [ "${2:-}" ]; then
  launch "$1" "$2"; exit 0
fi
scenarios="$(ls "${ROOT}/scenarios" | grep -E '^[0-9]')"
[ "${1:-}" ] && scenarios="$1"

echo "==> launching each cell with REPEAT=${REPEAT} (scores averaged over ${REPEAT} runs)"
for s in ${scenarios}; do
  for m in "${MODELS[@]}"; do
    launch "${s}" "${m}"
  done
done

echo "==> launched. Watch the ASG scale out; results land in s3://${BUCKET}/runs/"
echo "    logs: CloudWatch /ecs/firedrill"
echo
echo "    IMPORTANT: once the tasks finish, run ./orchestrator/rebuild_manifest.sh"
echo "    to regenerate manifest.json — parallel jobs race on it, so rebuild it"
echo "    authoritatively from S3 so every completed cell shows on the dashboard."
