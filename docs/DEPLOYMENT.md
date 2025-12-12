# AIPA Deployment Guide

**Version:** 2.0
**Last Updated:** 2025-12-12

This guide covers deploying AIPA to AWS with cost-optimized on-demand compute.

---

## Quick Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         Deployment Overview                                          │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│   1. Prerequisites     2. Terraform        3. Secrets         4. Docker             │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   ┌──────────────┐      │
│   │ AWS CLI      │    │ terraform    │    │ Populate     │   │ Build ARM64  │      │
│   │ Terraform    │───▶│ init         │───▶│ Secrets      │──▶│ image        │      │
│   │ Docker       │    │ plan         │    │ Manager      │   │ Push to ECR  │      │
│   │ LiveKit acct │    │ apply        │    │              │   │              │      │
│   └──────────────┘    └──────────────┘    └──────────────┘   └──────────────┘      │
│                                                                      │              │
│                                                                      ▼              │
│   5. Access             6. Use                                ┌──────────────┐      │
│   ┌──────────────┐    ┌──────────────┐                       │ ECS deploys  │      │
│   │ Open API URL │◀───│ /wake starts │◀──────────────────────│ automatically│      │
│   │ Login        │    │ service      │                       └──────────────┘      │
│   │ Talk!        │    │ on-demand    │                                              │
│   └──────────────┘    └──────────────┘                                              │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### Required Tools

```bash
# AWS CLI v2
aws --version  # aws-cli/2.x.x

# Terraform >= 1.10 (for native S3 locking)
terraform --version  # Terraform v1.10.x

# Docker with buildx (for ARM64 builds)
docker buildx version  # github.com/docker/buildx v0.x.x
```

### Required Accounts

1. **AWS Account** with credentials configured
2. **LiveKit Cloud** account ([cloud.livekit.io](https://cloud.livekit.io) - free tier)
3. **Claude Pro/Max** subscription

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                 AWS Cloud                                            │
│                                                                                      │
│  ┌─────────────────┐        ┌───────────────────────────────────────────────────┐  │
│  │  API Gateway    │        │              ECS Fargate Cluster                   │  │
│  │  (HTTP API)     │        │                                                    │  │
│  │                 │        │  ┌─────────────────────────────────────────────┐  │  │
│  │  /wake ────────────────▶│  │            AIPA Container                    │  │  │
│  │  /status        │  VPC  │  │  ┌─────────┐ ┌─────────┐ ┌─────────────────┐│  │  │
│  │  /shutdown      │  Link │  │  │FastAPI  │ │ Voice   │ │  Claude Code    ││  │  │
│  │  /* ───────────────────▶│  │  │(Web UI) │ │ Agent   │ │  (OAuth token)  ││  │  │
│  │                 │        │  │  └─────────┘ └─────────┘ └─────────────────┘│  │  │
│  └────────┬────────┘        │  └─────────────────────────────────────────────┘  │  │
│           │                 │                         │                          │  │
│           ▼                 └─────────────────────────┼──────────────────────────┘  │
│  ┌─────────────────┐                                  │                             │
│  │  Lambda         │                                  ▼                             │
│  │  (Wake/Status)  │                    ┌─────────────────────────┐                │
│  └─────────────────┘                    │  EFS          S3       │                │
│                                         │  /workspace   /files   │                │
│  ┌─────────────────┐                    │  /state       /backups │                │
│  │  Lambda         │                    └─────────────────────────┘                │
│  │  (Idle Checker) │                                                               │
│  │  every 15 min   │                    ┌─────────────────────────┐                │
│  └─────────────────┘                    │  Secrets Manager        │                │
│                                         │  (API keys, tokens)     │                │
│                                         └─────────────────────────┘                │
└─────────────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
   ┌──────────────┐
   │  LiveKit     │
   │  Cloud       │
   │  (External)  │
   └──────────────┘
```

---

## Step 1: Set up LiveKit Cloud

1. Go to [cloud.livekit.io](https://cloud.livekit.io/) and create a free account
2. Create a new project
3. Navigate to **Settings > Keys**
4. Note down:
   - **URL**: `wss://your-project.livekit.cloud`
   - **API Key**: Starts with `API...`
   - **API Secret**: Click eye icon to reveal

---

## Step 2: Generate Claude Code OAuth Token

```bash
# Install Claude Code CLI if needed
npm install -g @anthropic-ai/claude-code

# Generate long-lived OAuth token
claude setup-token

# Output will look like:
# sk-ant-oat01-xxxxxxxxxxxxx...
# Copy this token
```

---

## Step 3: Configure Terraform

### Create terraform.tfvars

```bash
cd terraform/
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:

```hcl
# AWS Configuration
aws_profile  = "your-aws-profile"
aws_region   = "ap-southeast-2"
environment  = "production"
project_name = "aipa"
agent_name   = "Ultra"

# ECS Configuration
ecs_cpu          = 1024  # 1 vCPU
ecs_memory       = 2048  # 2 GB
use_fargate_spot = true  # ~70% cheaper

# Cost Optimization
use_arm64            = true   # ~20% cheaper
idle_timeout_minutes = 30     # Auto-shutdown after idle
start_on_deploy      = false  # Start cold (on-demand)
```

### Initialize Terraform

```bash
cd terraform/

# Initialize with S3 backend
AWS_PROFILE=your-profile terraform init

# Review planned changes
AWS_PROFILE=your-profile terraform plan
```

---

## Step 4: Deploy Infrastructure

```bash
# Apply Terraform (creates ~72 resources)
AWS_PROFILE=your-profile terraform apply

# Note the outputs:
# - api_endpoint
# - ecr_repository_url
# - wakeup_endpoint
# - status_endpoint
```

### Resources Created

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         Resources Created                                            │
├────────────────────────────────────┬────────────────────────────────────────────────┤
│ Category                           │ Resources                                       │
├────────────────────────────────────┼────────────────────────────────────────────────┤
│ Networking                         │ VPC, 2 Subnets, Internet Gateway, Route Tables │
│ Compute                            │ ECS Cluster, Task Definitions, Service          │
│ Serverless                         │ 2 Lambda Functions, API Gateway                │
│ Storage                            │ EFS (3 access points), 2 S3 Buckets            │
│ Security                           │ IAM Roles (5), Security Groups (2)             │
│ Secrets                            │ Secrets Manager secret                          │
│ Monitoring                         │ CloudWatch Log Groups, EventBridge Rules       │
│ Container Registry                 │ ECR Repository                                  │
└────────────────────────────────────┴────────────────────────────────────────────────┘
```

---

## Step 5: Populate Secrets

### Generate Required Values

```bash
# Generate password hash
python3 -c "import bcrypt; print(bcrypt.hashpw(b'YOUR_PASSWORD', bcrypt.gensalt()).decode())"

# Generate session secret
openssl rand -hex 32
```

### Store in Secrets Manager

```bash
AWS_PROFILE=your-profile aws secretsmanager put-secret-value \
  --secret-id aipa-production/api-keys \
  --secret-string '{
    "CLAUDE_CODE_OAUTH_TOKEN": "sk-ant-oat01-your-token",
    "AUTH_PASSWORD_HASH": "$2b$12$your-bcrypt-hash",
    "SESSION_SECRET": "your-64-char-hex-string",
    "LIVEKIT_URL": "wss://your-project.livekit.cloud",
    "LIVEKIT_API_KEY": "APIxxxxx",
    "LIVEKIT_API_SECRET": "your-secret",
    "NOTION_API_KEY": "",
    "GITHUB_TOKEN": "",
    "OPENAI_API_KEY": ""
  }'
```

---

## Step 6: Build and Push Docker Image

### Build for ARM64 (Graviton)

```bash
# Get ECR login
ECR_URL=$(AWS_PROFILE=your-profile terraform output -raw ecr_repository_url)

AWS_PROFILE=your-profile aws ecr get-login-password --region ap-southeast-2 | \
  docker login --username AWS --password-stdin $ECR_URL

# Build ARM64 image
docker build --platform linux/arm64 -t aipa-production .

# Tag and push
docker tag aipa-production:latest $ECR_URL:latest
docker push $ECR_URL:latest
```

### Multi-Architecture Build (Optional)

```bash
# Create builder for multi-arch
docker buildx create --name multiarch --use

# Build and push both AMD64 and ARM64
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t $ECR_URL:latest \
  --push .
```

---

## Step 7: Verify Deployment

### Check Service Status

```bash
# Get API endpoint
API_URL=$(AWS_PROFILE=your-profile terraform output -raw api_endpoint)

# Check status (should return "stopped" initially)
curl $API_URL/status

# Wake the service
curl $API_URL/wake

# Poll until running
watch -n 5 "curl -s $API_URL/status | jq"
```

### View Logs

```bash
# ECS logs
AWS_PROFILE=your-profile aws logs tail /ecs/aipa-production --follow

# Lambda logs
AWS_PROFILE=your-profile aws logs tail /aws/lambda/aipa-production-wakeup --follow
```

---

## How On-Demand Works

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                            On-Demand Flow                                            │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  1. User Opens UI                                                                    │
│     ┌─────────────────────────────────────────────────────────────────────────────┐ │
│     │                                                                              │ │
│     │   Browser shows:  ┌──────────────────────────┐                              │ │
│     │                   │     🤖                    │                              │ │
│     │                   │   Waking Ultra...        │                              │ │
│     │                   │   [━━━━━━━━━━━━━━━━━━━━] │                              │ │
│     │                   │   ~30-60 seconds         │                              │ │
│     │                   └──────────────────────────┘                              │ │
│     │                                                                              │ │
│     └─────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                      │
│  2. Auto-Wake Sequence                                                               │
│     ┌─────────────────────────────────────────────────────────────────────────────┐ │
│     │                                                                              │ │
│     │   UI ──▶ GET /status ──▶ Lambda ──▶ {"status":"stopped"}                    │ │
│     │   UI ──▶ GET /wake   ──▶ Lambda ──▶ Scale ECS to 1                          │ │
│     │   UI ──▶ Poll /status every 3s until "running"                              │ │
│     │                                                                              │ │
│     └─────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                      │
│  3. Ready to Use                                                                     │
│     ┌─────────────────────────────────────────────────────────────────────────────┐ │
│     │                                                                              │ │
│     │   Overlay hides ──▶ Connect to LiveKit ──▶ Ready to talk!                   │ │
│     │                                                                              │ │
│     └─────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                      │
│  4. Auto-Shutdown (After 30 min idle)                                               │
│     ┌─────────────────────────────────────────────────────────────────────────────┐ │
│     │                                                                              │ │
│     │   EventBridge (every 15 min) ──▶ Idle Checker Lambda                        │ │
│     │                                        │                                     │ │
│     │                                        ▼                                     │ │
│     │                          Check API Gateway metrics                           │ │
│     │                                        │                                     │ │
│     │                          If <5 requests in 30 min                           │ │
│     │                                        │                                     │ │
│     │                                        ▼                                     │ │
│     │                              Scale ECS to 0                                  │ │
│     │                                                                              │ │
│     └─────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Cost Breakdown

### Estimated Monthly Cost

| Component | Cost | Notes |
|-----------|------|-------|
| ECS Fargate Spot (ARM64) | $1-4 | ~2-3 hrs/day usage |
| API Gateway | $1-2 | Per million requests |
| Lambda | $0.02 | Wake + idle check |
| EFS | $1-2 | Pay per GB stored |
| S3 | $0.50 | Minimal storage |
| CloudWatch | $0.50 | 7-day retention |
| Secrets Manager | $0.50 | 1 secret |
| **Total** | **$4-9/month** | |

### Cost Comparison

```
┌────────────────────────────────────────────────────────────────┐
│                    Monthly Cost Comparison                      │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  24/7 Running        On-Demand (This Setup)                    │
│  ┌─────────────┐     ┌─────────────┐                           │
│  │             │     │             │                           │
│  │   $16-23    │     │    $4-9     │    ~60-70% savings       │
│  │             │     │             │                           │
│  └─────────────┘     └─────────────┘                           │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

---

## Updating the Application

### Deploy New Code

```bash
# Build new image
docker build --platform linux/arm64 -t aipa-production .

# Tag and push
docker tag aipa-production:latest $ECR_URL:latest
docker push $ECR_URL:latest

# Force new deployment (if service is running)
AWS_PROFILE=your-profile aws ecs update-service \
  --cluster aipa-production \
  --service aipa-production-with-discovery \
  --force-new-deployment
```

### Update Infrastructure

```bash
cd terraform/
AWS_PROFILE=your-profile terraform plan
AWS_PROFILE=your-profile terraform apply
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check ECS task status
AWS_PROFILE=your-profile aws ecs describe-tasks \
  --cluster aipa-production \
  --tasks $(aws ecs list-tasks --cluster aipa-production --query 'taskArns[0]' --output text)

# Check logs
AWS_PROFILE=your-profile aws logs tail /ecs/aipa-production --since 1h
```

### Wake Lambda Errors

```bash
# Check Lambda logs
AWS_PROFILE=your-profile aws logs tail /aws/lambda/aipa-production-wakeup --since 1h

# Test Lambda directly
AWS_PROFILE=your-profile aws lambda invoke \
  --function-name aipa-production-wakeup \
  --payload '{"rawPath":"/status"}' \
  response.json && cat response.json
```

### Voice Not Working

1. Verify LiveKit credentials in Secrets Manager
2. Check ECS task can reach LiveKit Cloud (port 443 outbound)
3. Check browser console for WebSocket errors
4. Verify `LIVEKIT_URL` starts with `wss://`

### API Gateway 502 Errors

1. ECS task may not be running - check `/status`
2. VPC Link connectivity - verify security groups
3. Service Discovery may have stale records - force new deployment

---

## Teardown

```bash
cd terraform/

# Destroy all resources
AWS_PROFILE=your-profile terraform destroy
```

**Warning**: This deletes:
- EFS (all workspace data)
- S3 buckets (files and backups)
- CloudWatch logs
- Secrets Manager secrets

---

## Security Notes

1. **Secrets**: Never commit API keys or tokens to git
2. **Network**: ECS runs in VPC, only accessible via API Gateway
3. **Auth**: Password protected with bcrypt + rate limiting
4. **Encryption**: EFS and S3 encrypted at rest, TLS in transit
5. **IAM**: Least-privilege roles for each component
