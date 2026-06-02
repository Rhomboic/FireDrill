# Use the default VPC and its subnets — no custom VPC needed.
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# Security group for the ECS EC2 instances. Outbound only (API calls, ECR, S3);
# no inbound — the jobs are batch containers, nothing listens externally.
resource "aws_security_group" "tasks" {
  name        = "${var.project}-tasks-sg"
  description = "Allow all outbound for API/ECR/S3, no inbound"
  vpc_id      = data.aws_vpc.default.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
