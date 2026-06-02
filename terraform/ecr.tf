# One repository, two image tags: `base` (python/node/sql scenarios) and `ui`
# (the Playwright image for the web scenarios).
resource "aws_ecr_repository" "firedrill" {
  name                 = var.project
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = false
  }
}
