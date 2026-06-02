#!/usr/bin/env bash
# Build the two job images and push them to ECR (tags: base, ui).
# Run after `terraform apply` has created the ECR repo.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TF="${ROOT}/terraform"
REGION="${AWS_REGION:-us-west-1}"

ECR="$(terraform -chdir="${TF}" output -raw ecr_repository_url)"
echo "==> ECR: ${ECR}"

aws ecr get-login-password --region "${REGION}" \
  | docker login --username AWS --password-stdin "${ECR%%/*}"

echo "==> build + push :base (python/node/sql scenarios)"
docker build --platform linux/amd64 -t "${ECR}:base" "${ROOT}"
docker push "${ECR}:base"

echo "==> build + push :ui (Playwright web scenarios)"
docker build --platform linux/amd64 -f "${ROOT}/Dockerfile.ui" -t "${ECR}:ui" "${ROOT}"
docker push "${ECR}:ui"

echo "==> done."
