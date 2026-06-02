#!/usr/bin/env bash
# Live monitor for a matrix run: every few seconds, print the ASG state and a
# placement map — which scenario/model (container) is on which EC2 instance, and
# each task's status. Polls until the cluster has been idle for a few cycles,
# then prints the final S3 result tally. Safe to start before or after launching
# run_matrix.sh. Ctrl-C to stop early.
#
#   ./orchestrator/watch_run.sh            # default 12s interval
#   INTERVAL=20 ./orchestrator/watch_run.sh
set -uo pipefail

REGION="${AWS_REGION:-us-west-1}"
CLUSTER="${CLUSTER:-firedrill}"
BUCKET="${BUCKET:-firedrill-results-673981388599}"
INTERVAL="${INTERVAL:-12}"
IDLE_STOP="${IDLE_STOP:-3}"     # stop after this many consecutive empty polls

idle=0
while :; do
  ts="$(date +%H:%M:%S)"
  arns="$(aws ecs list-tasks --cluster "$CLUSTER" --region "$REGION" --query 'taskArns' --output text 2>/dev/null)"
  n=$(echo $arns | wc -w | tr -d ' ')

  if [ "$n" -eq 0 ]; then
    echo "[$ts] no running tasks"
    idle=$((idle + 1))
    [ "$idle" -ge "$IDLE_STOP" ] && break
    sleep "$INTERVAL"; continue
  fi
  idle=0

  asg="$(aws autoscaling describe-auto-scaling-groups --region "$REGION" \
    --query "AutoScalingGroups[?contains(AutoScalingGroupName,'firedrill')].[DesiredCapacity,length(Instances)]" \
    --output text)"
  echo "[$ts] tasks=$n  ASG(desired/instances)=$asg"

  aws ecs describe-tasks --cluster "$CLUSTER" --region "$REGION" --tasks $arns \
    --query 'tasks[].{ci:containerInstanceArn,status:lastStatus,env:overrides.containerOverrides[0].environment}' \
    --output json > /tmp/fd_tasks.json || { sleep "$INTERVAL"; continue; }

  cis="$(python3 -c "import json;print(' '.join({t['ci'] for t in json.load(open('/tmp/fd_tasks.json')) if t.get('ci')}))")"
  if [ -n "$cis" ]; then
    aws ecs describe-container-instances --cluster "$CLUSTER" --region "$REGION" --container-instances $cis \
      --query 'containerInstances[].{ci:containerInstanceArn,ec2:ec2InstanceId}' --output json > /tmp/fd_ci.json
  else
    echo "{}" > /tmp/fd_ci.json
  fi

  python3 - <<'PY'
import json
try:
    ci = {c["ci"]: c["ec2"] for c in json.load(open("/tmp/fd_ci.json"))}
except Exception:
    ci = {}
rows = sorted(json.load(open("/tmp/fd_tasks.json")),
              key=lambda t: (ci.get(t.get("ci"), "~"), t.get("status", "")))
print(f"    {'EC2 INSTANCE':21} {'SCENARIO':24} {'MODEL':16} STATUS")
for t in rows:
    e = {x["name"]: x["value"] for x in (t.get("env") or [])}
    ec2 = ci.get(t.get("ci")) or "(pending placement)"
    print(f"    {ec2:21} {e.get('SCENARIO','?'):24} {e.get('MODEL','?'):16} {t.get('status','?')}")
PY

  sleep "$INTERVAL"
done

done_n=$(aws s3 ls "s3://${BUCKET}/runs/" --recursive --region "$REGION" 2>/dev/null | grep '\.json$' | grep -vc manifest)
echo "=== idle; results in S3: ${done_n}/36 ==="
echo "    when finished, run: ./orchestrator/rebuild_manifest.sh"
