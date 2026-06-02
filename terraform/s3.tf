resource "aws_s3_bucket" "results" {
  bucket = "${var.project}-results-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket_public_access_block" "results" {
  bucket = aws_s3_bucket.results.id

  # ACLs stay blocked; policy-based public access is allowed so the dashboard
  # (firedrill.adamissah.com) can fetch result JSONs from the browser. Only the
  # runs/ prefix is exposed (see the policy below).
  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = false
  restrict_public_buckets = false
}

# Public read for result files only (non-sensitive). Lets the dashboard fetch
# runs/manifest.json and runs/<model>/<scenario>.json anonymously.
resource "aws_s3_bucket_policy" "results_public_read" {
  bucket     = aws_s3_bucket.results.id
  depends_on = [aws_s3_bucket_public_access_block.results]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "PublicReadResults"
      Effect    = "Allow"
      Principal = "*"
      Action    = "s3:GetObject"
      Resource  = "${aws_s3_bucket.results.arn}/runs/*"
    }]
  })
}

resource "aws_s3_bucket_cors_configuration" "results" {
  bucket = aws_s3_bucket.results.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET"]
    allowed_origins = ["*"]
    max_age_seconds = 3000
  }
}
