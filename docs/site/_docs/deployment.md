---
layout: doc
title: AWS Deployment
nav_order: 3
---

Deploy AIPA to AWS for production use.

## Prerequisites

- AWS account with admin access
- [Terraform](https://terraform.io) 1.0+
- AWS CLI configured
- Docker
- Claude Pro/Max subscription
- LiveKit Cloud account

## Step 1: Configure AWS Credentials

```bash
export AWS_PROFILE=your-profile
# or
export AWS_ACCESS_KEY_ID=xxx
export AWS_SECRET_ACCESS_KEY=xxx
```

Verify:
```bash
aws sts get-caller-identity
```

## Step 2: Create Secrets

Create secrets in AWS Secrets Manager:

```bash
aws secretsmanager create-secret \
  --name aipa/api-keys \
  --secret-string '{
    "CLAUDE_CODE_OAUTH_TOKEN": "your-oauth-token",
    "AUTH_PASSWORD_HASH": "$2b$12$...",
    "SESSION_SECRET": "random-64-char-string",
    "LIVEKIT_URL": "wss://your-project.livekit.cloud",
    "LIVEKIT_API_KEY": "your-key",
    "LIVEKIT_API_SECRET": "your-secret",
    "OPENAI_API_KEY": "sk-..."
  }'
```

## Step 3: Configure Terraform

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:

```hcl
project_name         = "aipa"
environment          = "prod"
aws_region           = "ap-southeast-2"

# Cost optimization
use_arm64            = true   # ARM64 (Graviton) - 20% cheaper
use_fargate_spot     = true   # Spot pricing - 70% cheaper
idle_timeout_minutes = 30     # Auto-shutdown after idle
start_on_deploy      = false  # Start cold (on-demand)

# Container config
container_cpu    = 256   # 0.25 vCPU
container_memory = 512   # 512 MB
```

## Step 4: Deploy Infrastructure

```bash
terraform init
terraform plan
terraform apply
```

This creates:
- VPC with public/private subnets
- ECS Fargate cluster
- API Gateway HTTP API
- Lambda functions (wake, status, idle check)
- EFS file system
- S3 bucket for files
- DynamoDB table for sessions
- CloudWatch logs

## Step 5: Build and Push Docker Image

Get ECR URL from Terraform output:
```bash
terraform output ecr_repository_url
```

Build and push:
```bash
# Login to ECR
aws ecr get-login-password --region ap-southeast-2 | \
  docker login --username AWS --password-stdin YOUR_ECR_URL

# Build for ARM64
docker build --platform linux/arm64 -t aipa .

# Tag and push
docker tag aipa:latest YOUR_ECR_URL:latest
docker push YOUR_ECR_URL:latest
```

## Step 6: Access AIPA

Get API Gateway URL:
```bash
terraform output api_gateway_url
```

Open the URL in your browser. The first access will wake the service (~45 seconds).

## Custom Domain (Optional)

### Route 53 + ACM

1. Create certificate in ACM (must be in us-east-1 for API Gateway)
2. Add custom domain in API Gateway
3. Create Route 53 alias record

```hcl
# Add to terraform/main.tf
resource "aws_apigatewayv2_domain_name" "api" {
  domain_name = "ultra.yourdomain.com"

  domain_name_configuration {
    certificate_arn = aws_acm_certificate.cert.arn
    endpoint_type   = "REGIONAL"
    security_policy = "TLS_1_2"
  }
}
```

## Cost Breakdown

| Service | Monthly Cost |
|---------|-------------|
| ECS Fargate (Spot, 4 hrs/day) | $1-3 |
| API Gateway | $1-2 |
| NAT Gateway | $1-2 |
| EFS (1GB) | $0.30 |
| S3, DynamoDB, Lambda | ~$0 (free tier) |
| CloudWatch Logs | $0.50 |
| **Total** | **~$4-9** |

## Updating

### Update Code

```bash
# Build new image
docker build --platform linux/arm64 -t aipa .
docker tag aipa:latest YOUR_ECR_URL:latest
docker push YOUR_ECR_URL:latest

# Force new deployment
aws ecs update-service \
  --cluster aipa-cluster \
  --service aipa-service \
  --force-new-deployment
```

### Update Infrastructure

```bash
cd terraform
terraform plan
terraform apply
```

## Cleanup

To destroy all resources:

```bash
# First, empty S3 bucket
aws s3 rm s3://aipa-files --recursive

# Destroy infrastructure
cd terraform
terraform destroy
```

## Security Considerations

1. **Secrets** - Stored in Secrets Manager, never in code
2. **Network** - ECS in private subnets, API Gateway for ingress
3. **IAM** - Least privilege roles for Lambda and ECS
4. **Encryption** - EFS and S3 encrypted at rest, TLS in transit
5. **Authentication** - Bcrypt password hashing, rate limiting

## Monitoring

### CloudWatch Logs

```bash
# View ECS logs
aws logs tail /aws/ecs/aipa --follow

# View Lambda logs
aws logs tail /aws/lambda/aipa-wake --follow
```

### Metrics

Key metrics to monitor:
- ECS CPU/Memory utilization
- API Gateway request count
- Lambda invocations
- DynamoDB read/write units

### Alarms

Set up alarms for:
- High ECS CPU (>80%)
- Lambda errors
- API Gateway 5xx errors
