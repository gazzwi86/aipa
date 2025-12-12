# AIPA - Implementation Plan

**Version:** 2.0
**Date:** 2025-12-12
**Status:** Phase 3 Complete - Ready for Deployment

---

## Executive Summary

AIPA (AI Personal Assistant) "Ultra" is a self-hosted Claude Code agent accessible via voice and text from anywhere. The implementation uses VoiceMode MCP with LiveKit for voice, deployed on AWS ECS Fargate with cost-optimized on-demand compute (~$4-9/month).

### Key Design Decisions

1. **Claude Max Subscription**: Uses OAuth token from `claude setup-token` - no API costs
2. **VoiceMode MCP**: Native Claude Code voice support via LiveKit
3. **On-Demand Compute**: Lambda wake-up pattern reduces costs by 80-90%
4. **ARM64/Graviton**: 20% cost savings on ECS Fargate
5. **Simple Auth**: Bcrypt passwords with DynamoDB sessions

---

## Architecture

```
┌───────────────┐         ┌──────────────┐         ┌──────────────┐
│    Browser    │◀───────▶│ LiveKit Cloud│         │  Claude API  │
│ (Voice + UI)  │  WebRTC │ (Free Tier)  │         │ (Pro/Max)    │
└───────┬───────┘         └──────────────┘         └──────┬───────┘
        │                                                  │
        │ HTTPS                                            │
        ▼                                                  ▼
┌──────────────────────────────────────────────────────────────────┐
│                     AWS (ap-southeast-2)                          │
│                                                                   │
│   ┌───────────────────────────────────────────────────────────┐  │
│   │                  API Gateway (HTTP API)                    │  │
│   │   /wake, /status, /shutdown ──▶ Lambda (on-demand)        │  │
│   │   /* ──▶ ECS Fargate (via VPC Link)                       │  │
│   └───────────────────────────────────────────────────────────┘  │
│                              │                                    │
│                              ▼                                    │
│   ┌──────────────────────────────────────────────────────────┐   │
│   │            ECS Fargate (ARM64, Spot)                      │   │
│   │                                                           │   │
│   │   ┌─────────────────────────────────────────────────┐    │   │
│   │   │                 AIPA Container                   │    │   │
│   │   │  ┌─────────┐  ┌───────────┐  ┌───────────────┐  │    │   │
│   │   │  │ FastAPI │  │  Voice    │  │  Claude Code  │  │    │   │
│   │   │  │  (UI)   │  │  Agent    │  │  (+ MCP)      │  │    │   │
│   │   │  └─────────┘  └───────────┘  └───────────────┘  │    │   │
│   │   └─────────────────────────────────────────────────┘    │   │
│   └──────────────────────────────────────────────────────────┘   │
│                              │                                    │
│                              ▼                                    │
│   ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌───────────┐  │
│   │    EFS     │  │     S3     │  │  DynamoDB  │  │ CloudWatch│  │
│   │ (workspace)│  │  (files)   │  │ (sessions) │  │  (logs)   │  │
│   └────────────┘  └────────────┘  └────────────┘  └───────────┘  │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Foundation (COMPLETE)

### Task 1.1: Claude Code Authentication
- [x] Use `claude setup-token` to generate long-lived OAuth token
- [x] Store token as `CLAUDE_CODE_OAUTH_TOKEN` in environment
- [x] Document setup process in README

### Task 1.2: FastAPI Server
- [x] Create basic FastAPI application
- [x] Implement bcrypt password authentication
- [x] Add rate limiting with exponential backoff
- [x] Session management with secure cookies

### Task 1.3: Docker Setup
- [x] Create Dockerfile with uv package manager
- [x] ARM64 compatible build
- [x] docker-compose.yml for local development
- [x] docker-compose.dev.yml with hot-reload

---

## Phase 2: Voice Interface (COMPLETE)

### Task 2.1: LiveKit Integration
- [x] Create LiveKit Cloud account (free tier: 10k mins/month)
- [x] Configure credentials in environment
- [x] Implement room token generation

### Task 2.2: VoiceMode MCP
- [x] Configure VoiceMode MCP server
- [x] Claude Code integration via subprocess
- [x] Voice agent service wrapper

### Task 2.3: Web UI
- [x] Voice interface in browser
- [x] Microphone button with status indicator
- [x] Auto silence detection (5 seconds)
- [x] Transcript display
- [x] Mobile-responsive design

---

## Phase 3: AWS Infrastructure (COMPLETE)

### Task 3.1: Core Infrastructure
- [x] VPC with public/private subnets
- [x] NAT Gateway for outbound traffic
- [x] Security groups with proper rules
- [x] Secrets Manager for credentials

### Task 3.2: Compute
- [x] ECS Cluster with Fargate Spot
- [x] ARM64/Graviton task definition
- [x] Container Insights disabled (cost savings)
- [x] Service Discovery integration

### Task 3.3: Storage
- [x] EFS for persistent workspace/state
- [x] S3 for file sharing with presigned URLs
- [x] S3 for daily backups
- [x] DynamoDB for session storage

### Task 3.4: Networking
- [x] API Gateway HTTP API
- [x] VPC Link to ECS
- [x] Custom domain support (optional)
- [x] TLS termination at API Gateway

### Task 3.5: Cost Optimization (On-Demand Pattern)
- [x] Lambda wake-up function
- [x] Lambda status check function
- [x] Lambda shutdown function
- [x] Idle checker (30 min timeout)
- [x] CloudWatch Events rule (5 min interval)
- [x] UI startup overlay with progress indicator

### Task 3.6: Backup System
- [x] Daily EFS to S3 backup via Lambda
- [x] 30-day retention policy
- [x] Restore documentation

---

## Phase 4: Deployment (READY)

### Prerequisites
- [ ] AWS account with permissions
- [ ] Terraform installed
- [ ] AWS CLI configured
- [ ] LiveKit Cloud credentials
- [ ] Claude setup-token generated

### Deployment Steps
1. [ ] Create S3 bucket for Terraform state
2. [ ] Configure `terraform.tfvars`
3. [ ] Create secrets in AWS Secrets Manager
4. [ ] Run `terraform apply`
5. [ ] Build and push Docker image to ECR
6. [ ] Test wake-up flow
7. [ ] Verify voice functionality

---

## Phase 5: Self-Improvement (PENDING)

### Task 5.1: Skill System
- [ ] Skill discovery from `.claude/skills/`
- [ ] Auto-commit hooks for new skills
- [ ] Skill documentation template

### Task 5.2: Context Persistence
- [ ] Load context on startup
- [ ] Context update hooks
- [ ] Survive container restarts

### Task 5.3: Approval Workflow
- [ ] Human-in-the-loop for sensitive actions
- [ ] Pending approval storage
- [ ] Notification system

---

## Outstanding Tasks

| Task | Priority | Status | Notes |
|------|----------|--------|-------|
| AWS Deployment | P0 | Ready | Run terraform apply |
| LiveKit configuration | P0 | Ready | Add credentials to Secrets Manager |
| Test voice E2E | P0 | Pending | After deployment |
| Skill system | P2 | Pending | Self-improvement |
| Approval workflow | P2 | Pending | Human-in-the-loop |
| Siri Shortcut integration | P3 | Future | Optional enhancement |

---

## Cost Estimates

### Production (AWS - On-Demand Pattern)

```
┌─────────────────────────────────────────────────────────┐
│  Service                          Cost                  │
├─────────────────────────────────────────────────────────┤
│  ECS Fargate (4 hrs/day, Spot)    $1-3                 │
│  API Gateway                       $1-2                 │
│  NAT Gateway                       $1-2                 │
│  EFS (1GB)                         $0.30               │
│  S3, DynamoDB, Lambda             ~$0 (free tier)      │
│  CloudWatch Logs                   $0.50               │
├─────────────────────────────────────────────────────────┤
│  TOTAL                             ~$4-9/month         │
│  (vs ~$16-23 always-on)            60-80% savings      │
└─────────────────────────────────────────────────────────┘
```

### External Services

| Service | Cost | Notes |
|---------|------|-------|
| Claude Max | $100/month | Already have |
| LiveKit Cloud | Free | 10k mins/month free tier |
| OpenAI (STT/TTS) | ~$5/month | Usage-based |

---

## Next Steps

1. **Deploy to AWS**
   ```bash
   cd terraform
   terraform init
   terraform apply
   ```

2. **Configure Secrets**
   ```bash
   aws secretsmanager put-secret-value \
     --secret-id aipa/api-keys \
     --secret-string '{...}'
   ```

3. **Build and Push Image**
   ```bash
   docker build --platform linux/arm64 -t aipa .
   aws ecr get-login-password | docker login ...
   docker push YOUR_ECR_URL:latest
   ```

4. **Access**
   - Get API Gateway URL from Terraform output
   - Open in browser
   - Wait for service to wake (~45s)
   - Login and test voice

---

## Removed/Deprecated Features

The following features from the original plan have been removed:

1. **Telegram Integration** - Replaced with web-based voice UI
2. **Siri Shortcut as primary interface** - PWA voice is more capable
3. **Always-on compute** - Replaced with on-demand pattern

---

*Last updated: 2025-12-12*
