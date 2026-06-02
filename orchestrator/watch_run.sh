#!/usr/bin/env bash
# Live, in-place monitor for a matrix run. The screen stays STATIC and only
# repaints when a task is added to the queue or a task changes status. Statuses
# are colour-coded:
#     provisioning = purple   running = blue   stopped = red   complete = green
# ("complete" = STOPPED with exit 0; "stopped" = STOPPED with a non-zero exit.)
#
# Tasks are tracked across their whole lifecycle: once seen active, a task stays
# on screen and flips to complete/stopped when it finishes. Safe to start before
# or after run_matrix.sh; Ctrl-C to stop.
#
#   ./orchestrator/watch_run.sh
#   INTERVAL=4 ./orchestrator/watch_run.sh
set -uo pipefail

REGION="${AWS_REGION:-us-west-1}"
CLUSTER="${CLUSTER:-firedrill}"
BUCKET="${BUCKET:-firedrill-results-673981388599}"
INTERVAL="${INTERVAL:-6}"      # poll cadence (the screen only repaints on change)
IDLE_STOP="${IDLE_STOP:-5}"    # exit after this many idle polls once tasks have run

T_TASKS=/tmp/fd_watch_tasks.json
T_CI=/tmp/fd_watch_ci.json
T_SIG=/tmp/fd_watch_sig
T_FRAME=/tmp/fd_watch_frame

# Track seen task ARNs in a temp file (not a bash-4 associative array, so this
# runs on macOS's stock bash 3.2 too).
SEEN_FILE="$(mktemp "${TMPDIR:-/tmp}/fd_watch_seen.XXXXXX")"
prev_sig="__init__"
idle=0
ever=0

cleanup() { printf '\033[?25h\n'; rm -f "$SEEN_FILE"; }   # restore cursor + clean up
trap cleanup EXIT INT TERM
printf '\033[?25l'                     # hide the cursor while we redraw

draw() { printf '\033[H\033[J'; cat "$T_FRAME"; }

while :; do
  active="$(aws ecs list-tasks --cluster "$CLUSTER" --region "$REGION" --query 'taskArns' --output text 2>/dev/null)"
  [ "$active" = "None" ] && active=""
  for a in $active; do grep -Fxq "$a" "$SEEN_FILE" 2>/dev/null || printf '%s\n' "$a" >> "$SEEN_FILE"; done
  all="$(cat "$SEEN_FILE")"

  # Nothing tracked yet — wait for the run to start.
  if [ -z "$all" ]; then
    if [ "$prev_sig" != "waiting" ]; then
      printf '\033[H\033[J\033[1mFireDrill matrix monitor\033[0m  \033[38;5;245m— waiting for tasks (start run_matrix.sh)…\033[0m\n'
      prev_sig="waiting"
    fi
    sleep "$INTERVAL"; continue
  fi
  ever=1

  aws ecs describe-tasks --cluster "$CLUSTER" --region "$REGION" --tasks $all \
    --query 'tasks[].{status:lastStatus,exit:containers[0].exitCode,ci:containerInstanceArn,env:overrides.containerOverrides[0].environment}' \
    --output json > "$T_TASKS" 2>/dev/null || { sleep "$INTERVAL"; continue; }

  cis="$(python3 -c "import json;print(' '.join({t['ci'] for t in json.load(open('$T_TASKS')) if t.get('ci')}))" 2>/dev/null)"
  if [ -n "$cis" ]; then
    aws ecs describe-container-instances --cluster "$CLUSTER" --region "$REGION" --container-instances $cis \
      --query 'containerInstances[].{ci:containerInstanceArn,ec2:ec2InstanceId}' --output json > "$T_CI" 2>/dev/null || echo "[]" > "$T_CI"
  else
    echo "[]" > "$T_CI"
  fi

  asg="$(aws autoscaling describe-auto-scaling-groups --region "$REGION" \
    --query "AutoScalingGroups[?contains(AutoScalingGroupName,'firedrill')].[DesiredCapacity,length(Instances)]" \
    --output text 2>/dev/null | tr '\t' '/')"

  # Build the frame + a change-signature (signature ignores ASG/time, so the
  # screen only repaints when a task is added or changes status).
  ASG="$asg" python3 - "$T_TASKS" "$T_CI" "$T_SIG" "$T_FRAME" <<'PY'
import json, os, sys, hashlib
tasks_f, ci_f, sig_f, frame_f = sys.argv[1:5]
asg = os.environ.get("ASG", "?")
COL = {"prov": "\033[38;5;141m", "run": "\033[38;5;39m", "done": "\033[38;5;46m",
       "stop": "\033[38;5;196m", "dim": "\033[38;5;245m", "rst": "\033[0m", "b": "\033[1m"}
try:
    ci = {c["ci"]: c["ec2"] for c in json.load(open(ci_f))}
except Exception:
    ci = {}
tasks = json.load(open(tasks_f))

def classify(t):
    s = t.get("status") or "?"
    if s in ("PROVISIONING", "PENDING"):
        return "PROVISIONING", "prov"
    if s in ("ACTIVATING", "RUNNING", "DEACTIVATING", "STOPPING", "DEPROVISIONING"):
        return "RUNNING", "run"
    if s == "STOPPED":
        return ("COMPLETE", "done") if t.get("exit") == 0 else ("STOPPED", "stop")
    return s, "dim"

rows, counts = [], {"prov": 0, "run": 0, "done": 0, "stop": 0}
for t in tasks:
    env = {x["name"]: x["value"] for x in (t.get("env") or [])}
    label, key = classify(t)
    counts[key] = counts.get(key, 0) + 1
    rows.append((env.get("SCENARIO", "?"), env.get("MODEL", "?"), ci.get(t.get("ci")) or "—", label, key))
rows.sort(key=lambda r: (r[0], r[1]))

# Signature: scenario+model+status only — NOT asg or timestamp.
sig = hashlib.md5("".join(f"{r[0]}|{r[1]}|{r[3]};" for r in rows).encode()).hexdigest()

out = []
out.append(f"{COL['b']}FireDrill matrix{COL['rst']}  {COL['dim']}ASG {asg}{COL['rst']}    "
           f"{COL['prov']}● prov {counts['prov']}{COL['rst']}   {COL['run']}● run {counts['run']}{COL['rst']}   "
           f"{COL['done']}● done {counts['done']}{COL['rst']}   {COL['stop']}● stop {counts['stop']}{COL['rst']}")
out.append("")
out.append(f"{COL['dim']}{'SCENARIO':24} {'MODEL':16} {'EC2 INSTANCE':21} STATUS{COL['rst']}")
for sc, mo, ec2, label, key in rows:
    out.append(f"{sc:24} {mo:16} {ec2:21} {COL[key]}{label}{COL['rst']}")

open(sig_f, "w").write(sig)
open(frame_f, "w").write("\n".join(out) + "\n")
PY

  sig="$(cat "$T_SIG" 2>/dev/null)"
  if [ "$sig" != "$prev_sig" ]; then
    draw
    prev_sig="$sig"
  fi

  if [ -n "$active" ]; then idle=0; else idle=$((idle + 1)); fi
  [ "$ever" -eq 1 ] && [ "$idle" -ge "$IDLE_STOP" ] && break
  sleep "$INTERVAL"
done

done_n="$(aws s3 ls "s3://${BUCKET}/runs/" --recursive --region "$REGION" 2>/dev/null | grep '\.json$' | grep -vc manifest)"
printf '\n\033[38;5;245mall tasks settled · %s results in S3 · run ./orchestrator/rebuild_manifest.sh\033[0m\n' "$done_n"
