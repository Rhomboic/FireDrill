variable "aws_region" {
  description = "AWS region"
  default     = "us-west-1"
}

variable "project" {
  description = "Project name used for naming resources"
  default     = "firedrill"
}

variable "instance_type" {
  description = "EC2 instance type for the ECS Auto Scaling Group. t3.large gives chromium (UI scenarios) enough memory."
  default     = "t3.large"
}

variable "asg_max_size" {
  description = "Max EC2 instances the capacity provider may scale the ASG out to."
  type        = number
  default     = 4
}
