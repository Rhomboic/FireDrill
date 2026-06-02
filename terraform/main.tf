terraform {
  required_version = ">= 1.10"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Remote state in S3 with native lockfile locking (no DynamoDB). The bucket is
  # defined in state.tf and created before this backend is initialized.
  # NOTE: the account id below must match your AWS account (same one as the
  # PuzzleChess infra). Update it if you deploy to a different account.
  backend "s3" {
    bucket       = "firedrill-tfstate-673981388599"
    key          = "firedrill/terraform.tfstate"
    region       = "us-west-1"
    encrypt      = true
    use_lockfile = true
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current" {}
