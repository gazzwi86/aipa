# =============================================================================
# Outputs
# =============================================================================

output "api_endpoint" {
  description = "API Gateway endpoint URL"
  value       = aws_apigatewayv2_api.main.api_endpoint
}

output "ecr_repository_url" {
  description = "ECR repository URL for pushing images"
  value       = aws_ecr_repository.main.repository_url
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  description = "ECS service name"
  value       = aws_ecs_service.main_with_discovery.name
}

output "s3_bucket_name" {
  description = "S3 bucket name for file sharing"
  value       = aws_s3_bucket.files.id
}

output "secrets_manager_arn" {
  description = "Secrets Manager ARN (populate this with API keys)"
  value       = aws_secretsmanager_secret.api_keys.arn
}

output "efs_file_system_id" {
  description = "EFS file system ID"
  value       = aws_efs_file_system.main.id
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group name"
  value       = aws_cloudwatch_log_group.main.name
}

output "backup_bucket_name" {
  description = "S3 bucket name for context backups"
  value       = aws_s3_bucket.backups.id
}

output "backup_schedule" {
  description = "EventBridge schedule for context backups"
  value       = aws_cloudwatch_event_rule.backup_schedule.schedule_expression
}

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "dynamodb_sessions_table" {
  description = "DynamoDB table name for session storage"
  value       = aws_dynamodb_table.sessions.id
}

# =============================================================================
# Deployment Instructions
# =============================================================================

output "deployment_instructions" {
  description = "Instructions for completing deployment"
  value       = <<-EOT

    ============================================================
    AIPA Infrastructure Deployed Successfully!
    ============================================================

    NEXT STEPS:

    1. Populate Secrets Manager with credentials:

       # Generate password hash:
       python3 -c "import bcrypt; print(bcrypt.hashpw(b'YOUR_PASSWORD', bcrypt.gensalt()).decode())"

       # Generate session secret:
       openssl rand -hex 32

       # Get OAuth token (run locally):
       claude setup-token

       aws secretsmanager put-secret-value \
         --secret-id ${aws_secretsmanager_secret.api_keys.name} \
         --secret-string '{
           "CLAUDE_CODE_OAUTH_TOKEN": "your-oauth-token",
           "AUTH_PASSWORD_HASH": "$2b$12$your-bcrypt-hash",
           "SESSION_SECRET": "your-random-hex-string",
           "LIVEKIT_URL": "wss://your-project.livekit.cloud",
           "LIVEKIT_API_KEY": "your-livekit-key",
           "LIVEKIT_API_SECRET": "your-livekit-secret",
           "NOTION_API_KEY": "ntn_...",
           "GITHUB_TOKEN": "github_pat_...",
           "OPENAI_API_KEY": "sk-..."
         }'

    2. Build and push Docker image:

       # Login to ECR
       aws ecr get-login-password --region ${var.aws_region} | \
         docker login --username AWS --password-stdin ${aws_ecr_repository.main.repository_url}

       # Build and push
       docker build -t ${aws_ecr_repository.main.repository_url}:latest .
       docker push ${aws_ecr_repository.main.repository_url}:latest

    3. Force ECS service update:

       aws ecs update-service \
         --cluster ${aws_ecs_cluster.main.name} \
         --service ${aws_ecs_service.main_with_discovery.name} \
         --force-new-deployment

    4. Access the UI:

       Open: ${aws_apigatewayv2_api.main.api_endpoint}
       Login with your password

    5. View logs:

       aws logs tail /ecs/aipa-production --follow

    ============================================================

  EOT
}
