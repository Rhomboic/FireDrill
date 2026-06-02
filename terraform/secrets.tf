# API keys live in Secrets Manager — never in code or task definitions. Populate
# them once after apply:
#   aws secretsmanager put-secret-value --secret-id firedrill/anthropic-api-key --secret-string sk-ant-...
#   aws secretsmanager put-secret-value --secret-id firedrill/openai-api-key    --secret-string sk-...
resource "aws_secretsmanager_secret" "anthropic_api_key" {
  name                    = "${var.project}/anthropic-api-key"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret" "openai_api_key" {
  name                    = "${var.project}/openai-api-key"
  recovery_window_in_days = 0
}
