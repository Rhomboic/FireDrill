# GitHub Actions → AWS auth via OIDC (no stored credentials).
#
# The OIDC provider is one-per-account and already exists in this account (the
# PuzzleChess infra created it), so we reference it rather than create a
# duplicate. If you deploy FireDrill to a fresh account, create the provider
# first (see PuzzleChess/terraform/github_oidc.tf for the resource block).
data "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
}

# Role the Terraform CI workflow assumes: plan on PRs, apply on pushes to main.
# Trust is scoped to those two subjects only; fork PRs get a different `sub`.
resource "aws_iam_role" "github_actions_terraform" {
  name = "${var.project}-github-actions-terraform"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = data.aws_iam_openid_connect_provider.github.arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
        StringLike = {
          "token.actions.githubusercontent.com:sub" = [
            "repo:Rhomboic/FireDrill:ref:refs/heads/main",
            "repo:Rhomboic/FireDrill:pull_request",
          ]
        }
      }
    }]
  })
}

# Permissions for every service this Terraform config manages. Broad by
# necessity (it provisions IAM, ECS, EC2/ASG, ECR, S3, secrets) — acceptable for
# a single-owner project; scope down for shared/prod use.
resource "aws_iam_role_policy" "github_actions_terraform" {
  name = "${var.project}-github-actions-terraform-policy"
  role = aws_iam_role.github_actions_terraform.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ManageProjectServices"
        Effect = "Allow"
        Action = [
          "s3:*",
          "ecr:*",
          "ecs:*",
          "iam:*",
          "secretsmanager:*",
          "logs:*",
          "autoscaling:*",
          "application-autoscaling:*",
          "ssm:GetParameter",
          "ssm:GetParameters",
          "sts:GetCallerIdentity",
        ]
        Resource = "*"
      },
      {
        Sid      = "ManageCompute"
        Effect   = "Allow"
        Action   = ["ec2:*"]
        Resource = "*"
      },
    ]
  })
}

output "github_actions_terraform_role_arn" {
  description = "Add this as the AWS_TF_ROLE_ARN variable in the GitHub repo settings"
  value       = aws_iam_role.github_actions_terraform.arn
}
