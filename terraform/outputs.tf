output "ecr_repository_url" {
  description = "ECR repository URL — tag/push the base and ui images here"
  value       = aws_ecr_repository.firedrill.repository_url
}

output "s3_bucket" {
  description = "S3 bucket where result JSONs are written"
  value       = aws_s3_bucket.results.bucket
}

output "ecs_cluster" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.firedrill.name
}

output "capacity_provider" {
  description = "ECS capacity provider (use with run-task)"
  value       = aws_ecs_capacity_provider.ec2.name
}

output "job_task_definition" {
  description = "Task definition family for python/node/sql scenarios"
  value       = aws_ecs_task_definition.job.family
}

output "ui_job_task_definition" {
  description = "Task definition family for the Playwright (web) scenarios"
  value       = aws_ecs_task_definition.ui_job.family
}

output "security_group_id" {
  description = "Security group ID for the ECS instances"
  value       = aws_security_group.tasks.id
}

output "subnet_ids" {
  description = "Default subnet IDs the ASG launches into"
  value       = data.aws_subnets.default.ids
}
