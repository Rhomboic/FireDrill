# EC2 Auto Scaling Group that backs the ECS cluster. The capacity provider
# (ecs.tf) drives desired_capacity: it scales the ASG OUT when tasks can't be
# placed and IN when instances are idle. We start at 0 — no cost until a job runs.

# Latest ECS-optimized Amazon Linux 2 AMI.
data "aws_ssm_parameter" "ecs_ami" {
  name = "/aws/service/ecs/optimized-ami/amazon-linux-2/recommended/image_id"
}

resource "aws_launch_template" "ecs" {
  name_prefix   = "${var.project}-ecs-"
  image_id      = data.aws_ssm_parameter.ecs_ami.value
  instance_type = var.instance_type

  iam_instance_profile {
    arn = aws_iam_instance_profile.ecs_instance.arn
  }

  vpc_security_group_ids = [aws_security_group.tasks.id]

  # Join the cluster on boot.
  user_data = base64encode(<<-EOF
    #!/bin/bash
    echo "ECS_CLUSTER=${var.project}" >> /etc/ecs/ecs.config
  EOF
  )

  # Roomy root volume — the UI image (chromium) is large.
  block_device_mappings {
    device_name = "/dev/xvda"
    ebs {
      volume_size = 30
      volume_type = "gp3"
    }
  }

  tag_specifications {
    resource_type = "instance"
    tags          = { Name = "${var.project}-ecs" }
  }
}

resource "aws_autoscaling_group" "ecs" {
  name_prefix         = "${var.project}-asg-"
  min_size            = 0
  max_size            = var.asg_max_size
  desired_capacity    = 0
  vpc_zone_identifier = data.aws_subnets.default.ids

  launch_template {
    id      = aws_launch_template.ecs.id
    version = "$Latest"
  }

  # The capacity provider manages scale-in via instance protection.
  protect_from_scale_in = true

  tag {
    key                 = "AmazonECSManaged"
    value               = "true"
    propagate_at_launch = true
  }

  tag {
    key                 = "Name"
    value               = "${var.project}-ecs"
    propagate_at_launch = true
  }

  lifecycle {
    create_before_destroy = true
  }
}
