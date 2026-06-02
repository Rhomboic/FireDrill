#!/usr/bin/env bash
# One-time bootstrap: create the S3 bucket that holds Terraform remote state, so
# the S3 backend in main.tf works on the very first `terraform init` (no
# chicken-and-egg, and Terraform never manages its own state bucket).
#
# Idempotent — safe to re-run. Needs AWS credentials.
#
# Usage:  ./bootstrap.sh        # uses your default account + AWS_REGION (or us-west-1)
set -euo pipefail

PROJECT="firedrill"
REGION="${AWS_REGION:-us-west-1}"
ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
BUCKET="${PROJECT}-tfstate-${ACCOUNT}"

echo "==> Terraform state bucket: ${BUCKET}  (region ${REGION})"

if aws s3api head-bucket --bucket "${BUCKET}" 2>/dev/null; then
  echo "    already exists — skipping create"
else
  # us-east-1 must NOT get a LocationConstraint; every other region must.
  if [ "${REGION}" = "us-east-1" ]; then
    aws s3api create-bucket --bucket "${BUCKET}" --region "${REGION}"
  else
    aws s3api create-bucket --bucket "${BUCKET}" --region "${REGION}" \
      --create-bucket-configuration LocationConstraint="${REGION}"
  fi
  echo "    created"
fi

# Versioning (roll back a bad state), encryption, and lock down public access.
aws s3api put-bucket-versioning --bucket "${BUCKET}" \
  --versioning-configuration Status=Enabled

aws s3api put-bucket-encryption --bucket "${BUCKET}" \
  --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

aws s3api put-public-access-block --bucket "${BUCKET}" \
  --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

echo "==> Done."
echo "    main.tf's backend bucket must be: ${BUCKET}"
echo "    Next:  terraform init  &&  terraform apply"
