#!/usr/bin/env bash
# Build the FireDrill job image and run one (scenario × model) job in a container.
# The same image + entrypoint runs on ECS; here we run it locally with `docker run`.
#
# Usage:  ./orchestrator/run_local_docker.sh <scenario> <model>
# Example: ./orchestrator/run_local_docker.sh 03-off-by-one claude-opus-4-8
#
# Reads ANTHROPIC_API_KEY / OPENAI_API_KEY (and optional MODEL_API_ID) from your
# shell. Results are written to ./results on the host.
set -euo pipefail

SCENARIO="${1:?usage: run_local_docker.sh <scenario> <model>}"
MODEL="${2:?usage: run_local_docker.sh <scenario> <model>}"
IMAGE="${FIREDRILL_IMAGE:-firedrill:latest}"

echo "==> building $IMAGE"
docker build -t "$IMAGE" .

echo "==> running $SCENARIO × $MODEL"
docker run --rm \
  -e SCENARIO="$SCENARIO" \
  -e MODEL="$MODEL" \
  -e MODEL_API_ID="${MODEL_API_ID:-}" \
  -e ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}" \
  -e OPENAI_API_KEY="${OPENAI_API_KEY:-}" \
  -v "$PWD/results:/opt/firedrill/results" \
  "$IMAGE"
