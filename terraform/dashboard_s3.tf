# Static-website bucket serving the built Vite/React dashboard. CloudFront sits
# in front of it for TLS + the custom domain; the bucket itself is the origin.
# (Distinct from the results bucket in s3.tf — that one only holds run JSONs.)
resource "aws_s3_bucket" "dashboard" {
  bucket = "${var.project}-dashboard-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket_public_access_block" "dashboard" {
  bucket = aws_s3_bucket.dashboard.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_website_configuration" "dashboard" {
  bucket = aws_s3_bucket.dashboard.id

  index_document { suffix = "index.html" }
  # SPA fallback: unknown paths serve index.html so client routing/refresh works.
  error_document { key = "index.html" }
}

resource "aws_s3_bucket_policy" "dashboard" {
  bucket     = aws_s3_bucket.dashboard.id
  depends_on = [aws_s3_bucket_public_access_block.dashboard]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "PublicReadGetObject"
      Effect    = "Allow"
      Principal = "*"
      Action    = "s3:GetObject"
      Resource  = "${aws_s3_bucket.dashboard.arn}/*"
    }]
  })
}
