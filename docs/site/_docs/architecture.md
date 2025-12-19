---
layout: doc
title: Architecture
nav_order: 2
---

AIPA runs as a containerized FastAPI application with Claude Code at its core.

## System Overview

```
┌─────────────────┐        ┌─────────────────┐        ┌─────────────────┐
│  Your Browser   │        │  LiveKit Cloud  │        │  Claude API     │
│  (Voice + UI)   │◀──────▶│  (Free Tier)    │        │  (Pro/Max sub)  │
└────────┬────────┘        └─────────────────┘        └────────┬────────┘
         │                                                      │
         │ HTTPS                                                │
         ▼                                                      ▼
┌───────────────────────────────────────────────────────────────────────┐
│                       AWS (your account)                               │
│   ┌───────────────────────────────────────────────────────────────┐   │
│   │  API Gateway → Lambda (wake) → ECS Fargate (AIPA Container)   │   │
│   │                                     ↓                          │   │
│   │              EFS (workspace) ← → S3 (files) ← → DynamoDB       │   │
│   └───────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────────┘
```

## Components

### FastAPI Server

The main application (`server/main.py`) provides:

- **Web UI** - Chat interface with voice support
- **Authentication** - Password-based login with sessions
- **File management** - Upload, download, and share files
- **Session management** - Persistent conversations in DynamoDB

### Claude Code

The AI backend runs as a subprocess:

- **VoiceMode MCP** - Handles voice input/output via LiveKit
- **Skills** - Capability modules in `.claude/skills/`
- **Agents** - Specialized personas in `.claude/agents/`
- **Context** - Persistent memory in `.claude/context/`

### Voice Pipeline

```
Browser Mic → LiveKit → VoiceMode MCP → Claude Code → VoiceMode MCP → LiveKit → Browser Speaker
               ↓                                                        ↑
           OpenAI Whisper (STT)                                   OpenAI TTS
```

### Storage

| Storage | Purpose |
|---------|---------|
| **EFS** | Workspace, context, state (persistent) |
| **S3** | File sharing, backups |
| **DynamoDB** | Session storage, auth state |

## On-Demand Compute

AIPA uses an on-demand pattern to minimize costs:

```
1. User opens app
   Browser → API Gateway → Lambda (status check)

2. If service is stopped
   Lambda: ecs.update_service(desiredCount=1)
   UI shows: "Starting Blu... 35%"

3. UI polls /status every 3s until running
   Lambda checks: ecs.describe_services()

4. Service starts (~45 seconds)
   - EFS mounts
   - Container pulls from ECR
   - FastAPI starts
   - Health check passes

5. User can now login and use voice

6. After 30 min idle (no API requests)
   Idle checker Lambda: ecs.update_service(desiredCount=0)
```

## Directory Structure

```
aipa/
├── .claude/              # Agent configuration
│   ├── CLAUDE.md        # Agent identity & instructions
│   ├── agents/          # Specialized agents
│   ├── skills/          # Capability modules
│   ├── commands/        # Slash commands
│   └── context/         # Persistent memory
├── server/              # FastAPI application
│   ├── main.py         # Entry point
│   ├── handlers/       # Route handlers
│   ├── services/       # Business logic
│   └── models/         # Pydantic models
├── terraform/           # AWS infrastructure
│   ├── ecs.tf          # ECS Fargate service
│   ├── api_gateway.tf  # API Gateway
│   └── lambda_wakeup.tf # On-demand wake system
└── docs/               # Documentation
```

## Security Model

### Authentication Flow

1. User enters password
2. Server verifies bcrypt hash
3. Server creates session token in DynamoDB
4. Session cookie sent to browser
5. Cookie validated on each request

### Rate Limiting

- Exponential backoff on failed logins
- Account lockout after repeated failures
- IP-based rate limiting

### Network Security

- All traffic over HTTPS (API Gateway TLS)
- ECS in private subnets
- Security groups with minimal rules
- VPC endpoints for AWS services

## Cost Optimization

| Strategy | Savings |
|----------|---------|
| On-demand compute | 80-90% vs always-on |
| Fargate Spot | ~70% on compute |
| ARM64 (Graviton) | ~20% on compute |
| HTTP API (vs REST) | ~70% on API Gateway |

**Result**: ~$4-9/month vs ~$25+ always-on
