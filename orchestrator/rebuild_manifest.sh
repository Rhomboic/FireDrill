#!/usr/bin/env bash
# Rebuild runs/manifest.json authoritatively from the result objects actually
# present in the results bucket.
#
# Why this exists: each job updates the manifest with a read-modify-write
# (get -> add its entry -> put). Under the parallel matrix fan-out, jobs that
# finish within the same get/put window race and the last write wins, silently
# dropping a (model, scenario) pair — the per-job JSON is still in S3, but the
# manifest (and therefore the dashboard) loses the cell. This script ignores the
# manifest's current contents and regenerates it from a fresh listing of
# runs/<model>/<scenario>.json, so it is always correct and is also safe to run
# repeatedly (after reruns, partial runs, etc.).
#
# Usage:
#   ./orchestrator/rebuild_manifest.sh          # bucket from terraform output
#   BUCKET=my-bucket ./orchestrator/rebuild_manifest.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TF="${ROOT}/terraform"
REGION="${AWS_REGION:-us-west-1}"
PREFIX="runs/"

BUCKET="${BUCKET:-$(terraform -chdir="${TF}" output -raw s3_bucket)}"
echo "==> rebuilding s3://${BUCKET}/${PREFIX}manifest.json"

# List every result object key under runs/ (handles pagination).
keys="$(aws s3api list-objects-v2 --bucket "${BUCKET}" --prefix "${PREFIX}" \
  --query 'Contents[].Key' --output text 2>/dev/null | tr '\t' '\n')"

# Build the manifest { model: [scenario, ...] } from keys shaped like
# runs/<model>/<scenario>.json (manifest.json itself and any nested paths are
# ignored). stdlib only — no boto3 needed locally.
manifest="$(printf '%s\n' "${keys}" | python3 -c '
import json, sys
data = {}
for line in sys.stdin:
    key = line.strip()
    if not key or not key.endswith(".json"):
        continue
    parts = key.split("/")            # ["runs", "<model>", "<scenario>.json"]
    if len(parts) != 3 or parts[2] == "manifest.json":
        continue
    model, scenario = parts[1], parts[2][:-len(".json")]
    data.setdefault(model, set()).add(scenario)
print(json.dumps({m: sorted(s) for m, s in sorted(data.items())}, indent=2))
')"

if [ -z "${manifest}" ] || [ "${manifest}" = "{}" ]; then
  echo "    no result objects found under ${PREFIX} — nothing to write."
  exit 0
fi

echo "${manifest}" | aws s3 cp - "s3://${BUCKET}/${PREFIX}manifest.json" \
  --content-type application/json --region "${REGION}"

total="$(printf '%s' "${manifest}" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(sum(len(v) for v in d.values()))')"
echo "==> wrote manifest: ${total} jobs across $(printf '%s' "${manifest}" | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))') models."
