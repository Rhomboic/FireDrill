# CloudFront requires its ACM certificate in us-east-1, regardless of where the
# rest of the infra lives (us-west-1 here). A second provider alias gives us a
# us-east-1 client just for the cert.
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}

resource "aws_acm_certificate" "firedrill" {
  provider          = aws.us_east_1
  domain_name       = "firedrill.adamissah.com"
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

# DNS-validation CNAME, written into the existing (chess-owned) hosted zone.
resource "aws_route53_record" "firedrill_cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.firedrill.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      type   = dvo.resource_record_type
      record = dvo.resource_record_value
    }
  }

  zone_id = data.aws_route53_zone.main.zone_id
  name    = each.value.name
  type    = each.value.type
  records = [each.value.record]
  ttl     = 60
}

resource "aws_acm_certificate_validation" "firedrill" {
  provider                = aws.us_east_1
  certificate_arn         = aws_acm_certificate.firedrill.arn
  validation_record_fqdns = [for r in aws_route53_record.firedrill_cert_validation : r.fqdn]
}
