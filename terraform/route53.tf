# The adamissah.com hosted zone is OWNED by the PuzzleChess Terraform state
# (it also pins the domain registrar to the zone's nameservers). FireDrill must
# NOT create or manage that zone — it would create a duplicate zone and fight
# chess over the registration. Instead we look it up and write only our own
# records (the ACM validation CNAME + the firedrill A record) into it.
data "aws_route53_zone" "main" {
  name = "adamissah.com"
}
