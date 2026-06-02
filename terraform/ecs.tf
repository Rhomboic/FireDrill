resource "aws_ecs_cluster" "firedrill" {
  name = var.project
}

resource "aws_cloudwatch_log_group" "firedrill" {
  name              = "/ecs/${var.project}"
  retention_in_days = 14
}

# Capacity provider backed by the ASG, with managed scaling: ECS adds instances
# when tasks are pending and removes them when idle (target 100% utilisation).
resource "aws_ecs_capacity_provider" "ec2" {
  name = "${var.project}-ec2"

  auto_scaling_group_provider {
    auto_scaling_group_arn         = aws_autoscaling_group.ecs.arn
    managed_termination_protection = "ENABLED"

    managed_scaling {
      status                    = "ENABLED"
      target_capacity           = 100
      minimum_scaling_step_size = 1
      maximum_scaling_step_size = var.asg_max_size
    }
  }
}

resource "aws_ecs_cluster_capacity_providers" "firedrill" {
  cluster_name       = aws_ecs_cluster.firedrill.name
  capacity_providers = [aws_ecs_capacity_provider.ec2.name]

  default_capacity_provider_strategy {
    capacity_provider = aws_ecs_capacity_provider.ec2.name
    weight            = 1
  }
}

# ── Task definitions ──────────────────────────────────────────────────────────
# Two: `job` (base image: python/node/sql scenarios) and `ui-job` (Playwright
# image: web scenarios). SCENARIO and MODEL are NOT baked in — they're supplied
# as container env overrides at run-task time, so one task def serves the whole
# matrix. The orchestrator picks ui-job for the web scenarios.

locals {
  common_env = [
    { name = "S3_BUCKET", value = aws_s3_bucket.results.bucket },
    { name = "S3_KEY_PREFIX", value = "runs/" },
    { name = "AWS_DEFAULT_REGION", value = var.aws_region },
  ]
  common_secrets = [
    { name = "ANTHROPIC_API_KEY", valueFrom = aws_secretsmanager_secret.anthropic_api_key.arn },
    { name = "OPENAI_API_KEY", valueFrom = aws_secretsmanager_secret.openai_api_key.arn },
  ]
}

resource "aws_ecs_task_definition" "job" {
  family                   = "${var.project}-job"
  requires_compatibilities = ["EC2"]
  network_mode             = "bridge"
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name        = "job"
    image       = "${aws_ecr_repository.firedrill.repository_url}:base"
    essential   = true
    environment = local.common_env
    secrets     = local.common_secrets
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.firedrill.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "job"
      }
    }
  }])
}

resource "aws_ecs_task_definition" "ui_job" {
  family                   = "${var.project}-ui-job"
  requires_compatibilities = ["EC2"]
  network_mode             = "bridge"
  cpu                      = 1024
  memory                   = 2560 # chromium headroom
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name        = "ui-job"
    image       = "${aws_ecr_repository.firedrill.repository_url}:ui"
    essential   = true
    environment = local.common_env
    secrets     = local.common_secrets
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.firedrill.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ui-job"
      }
    }
  }])
}
