# AIPA Architecture

**Version:** 2.0
**Last Updated:** 2025-12-12

---

## Overview

AIPA (AI Personal Assistant) "Blu" is a cost-optimized, self-hosted Claude Code agent accessible via voice and web. The architecture prioritizes minimal running costs through on-demand compute while maintaining instant availability perception.

---

## System Architecture

### High-Level Overview

```
                                    ┌─────────────────────────┐
                                    │   LiveKit Cloud         │
                                    │   (Voice Relay)         │
                                    └───────────┬─────────────┘
                                                │ WebRTC
                                                │
┌───────────────────────────────────────────────┼───────────────────────────────────────────┐
│                                    AWS Cloud  │                                           │
│                                               │                                           │
│  ┌─────────────────────────────────────────────────────────────────────────────────────┐ │
│  │                              API Gateway (HTTP API)                                  │ │
│  │                                                                                      │ │
│  │   /wake ─────┐    /status ────┐    /shutdown ───┐    /* (all other) ────────────┐  │ │
│  └──────────────┼────────────────┼─────────────────┼───────────────────────────────┼──┘ │
│                 │                │                 │                               │     │
│                 ▼                ▼                 ▼                               │     │
│          ┌─────────────────────────────────────────────┐                          │     │
│          │            Lambda (Wake-Up)                  │                          │     │
│          │  • Check ECS status                          │                          │     │
│          │  • Start/stop service                        │                          │     │
│          │  • Return status JSON                        │                          │     │
│          └─────────────────────────────────────────────┘                          │     │
│                           │                                                        │     │
│                           ▼ Scale to 1                                            │     │
│          ┌─────────────────────────────────────────────┐                          │     │
│          │         ECS Fargate (Spot + ARM64)          │◀─────────────────────────┘     │
│          │  ┌─────────────────────────────────────────┐│                                │
│          │  │           AIPA Container                ││                                │
│          │  │  ┌───────────┐  ┌───────────────────┐  ││                                │
│          │  │  │  FastAPI  │  │   Voice Agent     │  ││                                │
│          │  │  │  (Web UI) │  │   (LiveKit)       │  ││                                │
│          │  │  └───────────┘  └─────────┬─────────┘  ││                                │
│          │  │                           │            ││                                │
│          │  │                           ▼            ││                                │
│          │  │              ┌─────────────────────┐   ││                                │
│          │  │              │   Claude Code CLI   │   ││                                │
│          │  │              │   (OAuth Token)     │   ││                                │
│          │  │              └─────────────────────┘   ││                                │
│          │  └─────────────────────────────────────────┘│                                │
│          └─────────────────────────────────────────────┘                                │
│                           │                                                             │
│          ┌────────────────┼────────────────┐                                           │
│          │                │                │                                           │
│          ▼                ▼                ▼                                           │
│    ┌──────────┐    ┌──────────┐    ┌──────────────┐                                   │
│    │   EFS    │    │    S3    │    │   Secrets    │                                   │
│    │/workspace│    │  /files  │    │   Manager    │                                   │
│    │ /state   │    │ /backups │    │  (API keys)  │                                   │
│    └──────────┘    └──────────┘    └──────────────┘                                   │
│                                                                                        │
│          ┌─────────────────────────────────────────────┐                              │
│          │      Lambda (Idle Checker) - Every 15 min   │                              │
│          │  • Check API Gateway request metrics        │                              │
│          │  • If <5 requests in 30 min → Scale to 0    │                              │
│          └─────────────────────────────────────────────┘                              │
│                                                                                        │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Cost Optimization Architecture

### On-Demand Wake Pattern

The system uses an "on-demand" pattern to minimize costs:

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              On-Demand Wake Flow                                     │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│    User Opens UI                                                                     │
│         │                                                                            │
│         ▼                                                                            │
│    ┌─────────────────┐                                                              │
│    │ Show "Waking    │                                                              │
│    │ Blu..." overlay  │                                                              │
│    └────────┬────────┘                                                              │
│             │                                                                        │
│             ▼                                                                        │
│    ┌─────────────────┐      GET /status        ┌─────────────────┐                 │
│    │ Check service   │─────────────────────────▶│ Lambda checks   │                 │
│    │ status          │◀─────────────────────────│ ECS status      │                 │
│    └────────┬────────┘   {"status":"stopped"}   └─────────────────┘                 │
│             │                                                                        │
│             ▼                                                                        │
│    ┌─────────────────┐      GET /wake          ┌─────────────────┐                 │
│    │ Wake service    │─────────────────────────▶│ Lambda scales   │                 │
│    │                 │◀─────────────────────────│ ECS to 1        │                 │
│    └────────┬────────┘   {"status":"starting"}  └─────────────────┘                 │
│             │                                                                        │
│             │ Poll every 3s                                                          │
│             ▼                                                                        │
│    ┌─────────────────┐                         ┌─────────────────┐                 │
│    │ Wait for        │      GET /status        │ ECS task        │                 │
│    │ service ready   │─────────────────────────▶│ starting...     │                 │
│    │ (30-60s)        │◀─────────────────────────│                 │                 │
│    └────────┬────────┘   {"status":"running"}   └─────────────────┘                 │
│             │                                                                        │
│             ▼                                                                        │
│    ┌─────────────────┐                                                              │
│    │ Hide overlay,   │                                                              │
│    │ connect to      │                                                              │
│    │ LiveKit voice   │                                                              │
│    └─────────────────┘                                                              │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### Auto-Shutdown Flow

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              Auto-Shutdown Flow                                      │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│    EventBridge                                                                       │
│    (every 15 min)                                                                    │
│         │                                                                            │
│         ▼                                                                            │
│    ┌─────────────────┐                                                              │
│    │ Idle Checker    │                                                              │
│    │ Lambda          │                                                              │
│    └────────┬────────┘                                                              │
│             │                                                                        │
│             ▼                                                                        │
│    ┌─────────────────┐      Get request count    ┌─────────────────┐               │
│    │ Check CloudWatch│──────────────────────────▶│ API Gateway     │               │
│    │ metrics         │◀──────────────────────────│ metrics         │               │
│    └────────┬────────┘        last 30 min        └─────────────────┘               │
│             │                                                                        │
│             ▼                                                                        │
│        ┌────────────┐                                                               │
│        │ Requests   │                                                               │
│        │   < 5 ?    │                                                               │
│        └─────┬──────┘                                                               │
│              │                                                                       │
│       ┌──────┴──────┐                                                               │
│       │ Yes         │ No                                                            │
│       ▼             ▼                                                               │
│ ┌───────────┐  ┌───────────┐                                                       │
│ │ Scale ECS │  │ Do nothing│                                                       │
│ │ to 0      │  │ (active)  │                                                       │
│ └───────────┘  └───────────┘                                                       │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. API Gateway (HTTP API)

Routes requests to appropriate backends:

| Route | Target | Purpose |
|-------|--------|---------|
| `GET /wake` | Lambda | Start ECS service |
| `GET /status` | Lambda | Check if running |
| `POST /shutdown` | Lambda | Stop ECS service |
| `GET /health` | ECS | Health check |
| `/*` (default) | ECS | All app routes |

### 2. Wake-Up Lambda

```
┌─────────────────────────────────────────────┐
│            Wake-Up Lambda                    │
├─────────────────────────────────────────────┤
│  Runtime: Python 3.12                        │
│  Architecture: ARM64 (Graviton)              │
│  Memory: 128 MB                              │
│  Timeout: 60s                                │
├─────────────────────────────────────────────┤
│  Functions:                                  │
│  • GET /wake    → Scale ECS to 1            │
│  • GET /status  → Return current state      │
│  • POST /shutdown → Scale ECS to 0          │
└─────────────────────────────────────────────┘
```

### 3. ECS Fargate Task

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ECS Task Definition                           │
├─────────────────────────────────────────────────────────────────────┤
│  CPU: 1024 (1 vCPU)      Memory: 2048 MB                            │
│  Architecture: ARM64 (Graviton) - 20% cheaper                        │
│  Capacity Provider: FARGATE_SPOT - 70% cheaper                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                      AIPA Container                             │ │
│  │                                                                 │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────┐ │ │
│  │  │    FastAPI      │  │   Voice Agent   │  │  Claude Code   │ │ │
│  │  │    (port 8000)  │  │   (LiveKit)     │  │  CLI           │ │ │
│  │  │                 │  │                 │  │                │ │ │
│  │  │  • Login UI     │  │  • STT/TTS      │  │  • OAuth Auth  │ │ │
│  │  │  • Voice UI     │  │  • Transcripts  │  │  • MCP Servers │ │ │
│  │  │  • Files UI     │  │  • Audio relay  │  │  • Notion      │ │ │
│  │  │  • Health check │  │                 │  │  • GitHub      │ │ │
│  │  └─────────────────┘  └─────────────────┘  └────────────────┘ │ │
│  │                                                                 │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  Volumes:                                                            │
│  • /workspace → EFS (workspace access point)                        │
│  • /state     → EFS (state access point)                            │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 4. Storage Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Storage Layer                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                         EFS File System                          ││
│  │                                                                  ││
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐       ││
│  │  │  /workspace   │  │    /state     │  │    /claude    │       ││
│  │  │               │  │               │  │               │       ││
│  │  │ • .claude/    │  │ • sessions    │  │ • credentials │       ││
│  │  │ • projects/   │  │ • pending     │  │ • config      │       ││
│  │  │ • files/      │  │ • history     │  │               │       ││
│  │  └───────────────┘  └───────────────┘  └───────────────┘       ││
│  │                                                                  ││
│  │  Features:                                                       ││
│  │  • Encrypted at rest                                            ││
│  │  • Lifecycle policy: IA after 30 days                           ││
│  │  • Access points with POSIX permissions                         ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                         S3 Buckets                               ││
│  │                                                                  ││
│  │  ┌─────────────────────────┐  ┌─────────────────────────┐      ││
│  │  │    aipa-*-files         │  │    aipa-*-backups       │      ││
│  │  │                         │  │                         │      ││
│  │  │ • Shared files          │  │ • Daily context backup  │      ││
│  │  │ • 30-day expiry         │  │ • Intelligent Tiering   │      ││
│  │  │ • Versioning enabled    │  │ • 365-day retention     │      ││
│  │  └─────────────────────────┘  └─────────────────────────┘      ││
│  │                                                                  ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Voice Architecture

### LiveKit Integration

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              Voice Pipeline                                          │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  Browser                          LiveKit Cloud                    AIPA Server      │
│  ┌──────────┐                    ┌──────────────┐                ┌──────────────┐  │
│  │  User    │                    │              │                │ Voice Agent  │  │
│  │  speaks  │ ─── WebRTC ───────▶│   Audio      │ ── WebRTC ───▶│              │  │
│  │          │                    │   Relay      │                │   ┌────────┐ │  │
│  └──────────┘                    │              │                │   │Silero  │ │  │
│                                  │              │                │   │VAD     │ │  │
│                                  │              │                │   └───┬────┘ │  │
│                                  │              │                │       │      │  │
│                                  │              │                │       ▼      │  │
│                                  │              │                │   ┌────────┐ │  │
│                                  │              │                │   │OpenAI  │ │  │
│                                  │              │                │   │STT     │ │  │
│                                  │              │                │   └───┬────┘ │  │
│                                  │              │                │       │      │  │
│                                  │              │                │       ▼      │  │
│  ┌──────────┐                    │              │                │   ┌────────┐ │  │
│  │  User    │                    │              │                │   │Claude  │ │  │
│  │  hears   │ ◀── WebRTC ────────│              │ ◀─ WebRTC ─────│   │Code    │ │  │
│  │          │                    │              │                │   └───┬────┘ │  │
│  └──────────┘                    │              │                │       │      │  │
│                                  │              │                │       ▼      │  │
│                                  └──────────────┘                │   ┌────────┐ │  │
│                                                                  │   │OpenAI  │ │  │
│                                                                  │   │TTS     │ │  │
│                                                                  │   └────────┘ │  │
│                                                                  └──────────────┘  │
│                                                                                      │
│  Data Channel (transcripts, state):                                                 │
│  Browser ◀────── LiveKit Data Channel ──────▶ Voice Agent                          │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Security Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              Security Layers                                         │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  1. Network Security                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │                                                                                  ││
│  │  Internet ──▶ API Gateway (HTTPS) ──▶ VPC Link ──▶ ECS (private)               ││
│  │                     │                                                            ││
│  │                     ▼                                                            ││
│  │              Security Groups:                                                    ││
│  │              • ECS: Inbound 8000 from VPC only                                  ││
│  │              • EFS: Inbound 2049 from ECS SG only                               ││
│  │              • Outbound: 443 (HTTPS) only                                       ││
│  │                                                                                  ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
│  2. Authentication                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │                                                                                  ││
│  │  Web UI:                                                                         ││
│  │  • Bcrypt password hash stored in Secrets Manager                               ││
│  │  • Session-based auth with secure cookies                                       ││
│  │  • Rate limiting with exponential backoff                                       ││
│  │                                                                                  ││
│  │  Claude Code:                                                                    ││
│  │  • Long-lived OAuth token from `claude setup-token`                             ││
│  │  • Token stored in Secrets Manager                                              ││
│  │  • Uses Claude Pro/Max subscription                                             ││
│  │                                                                                  ││
│  │  LiveKit:                                                                        ││
│  │  • Server-generated room tokens                                                 ││
│  │  • Short-lived JWT for each session                                             ││
│  │                                                                                  ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
│  3. Data Protection                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │                                                                                  ││
│  │  At Rest:                                                                        ││
│  │  • EFS: Encrypted with AWS-managed key                                          ││
│  │  • S3: Server-side encryption (AES-256)                                         ││
│  │  • Secrets Manager: AWS KMS encryption                                          ││
│  │                                                                                  ││
│  │  In Transit:                                                                     ││
│  │  • All API traffic over HTTPS                                                   ││
│  │  • EFS mount uses TLS (transit encryption)                                      ││
│  │  • LiveKit uses DTLS-SRTP for media                                             ││
│  │                                                                                  ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Cost Analysis

### Monthly Cost Breakdown

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         Cost Comparison (Monthly)                                    │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  24/7 Running (Previous)                     On-Demand (Current)                    │
│  ┌────────────────────────────┐             ┌────────────────────────────┐         │
│  │ ECS Fargate    $12-15/mo   │             │ ECS Fargate    $1-4/mo*    │         │
│  │ API Gateway    $1-3/mo     │             │ API Gateway    $1-2/mo     │         │
│  │ EFS            $1-2/mo     │             │ EFS            $1-2/mo     │         │
│  │ S3             $0.50/mo    │             │ S3             $0.50/mo    │         │
│  │ CloudWatch     $1-2/mo     │             │ CloudWatch     $0.50/mo    │         │
│  │ Lambda         -           │             │ Lambda         $0.02/mo    │         │
│  │ Secrets Mgr    $0.50/mo    │             │ Secrets Mgr    $0.50/mo    │         │
│  ├────────────────────────────┤             ├────────────────────────────┤         │
│  │ TOTAL:         $16-23/mo   │             │ TOTAL:         $4-9/mo     │         │
│  └────────────────────────────┘             └────────────────────────────┘         │
│                                                                                      │
│  * Based on ~2-3 hours actual usage per day                                         │
│                                                                                      │
│  Cost Optimizations Applied:                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │ Optimization              │ Savings                                         │   │
│  ├───────────────────────────┼─────────────────────────────────────────────────┤   │
│  │ ARM64 (Graviton)          │ ~20% on compute                                 │   │
│  │ Fargate Spot              │ ~70% on compute                                 │   │
│  │ On-demand scaling         │ ~80-90% (only pay when used)                    │   │
│  │ Reduced log retention     │ ~$0.50/mo                                       │   │
│  │ Container Insights off    │ ~$0.50/mo                                       │   │
│  └───────────────────────────┴─────────────────────────────────────────────────┘   │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Deployment Flow

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                            Deployment Pipeline                                       │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  1. Infrastructure (Terraform)                                                       │
│  ┌──────────────────────────────────────────────────────────────────────────────┐  │
│  │                                                                               │  │
│  │  terraform init ──▶ terraform plan ──▶ terraform apply                       │  │
│  │        │                   │                   │                              │  │
│  │        ▼                   ▼                   ▼                              │  │
│  │  S3 Backend         Review changes        Create:                            │  │
│  │  initialized        (72 resources)        • VPC, Subnets                     │  │
│  │                                           • ECS Cluster                       │  │
│  │                                           • Lambda Functions                  │  │
│  │                                           • API Gateway                       │  │
│  │                                           • EFS, S3                           │  │
│  │                                           • Secrets Manager                   │  │
│  │                                           • IAM Roles                         │  │
│  └──────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  2. Secrets Setup                                                                    │
│  ┌──────────────────────────────────────────────────────────────────────────────┐  │
│  │                                                                               │  │
│  │  aws secretsmanager put-secret-value \                                       │  │
│  │    --secret-id aipa-production/api-keys \                                    │  │
│  │    --secret-string '{                                                        │  │
│  │      "CLAUDE_CODE_OAUTH_TOKEN": "...",                                       │  │
│  │      "AUTH_PASSWORD_HASH": "...",                                            │  │
│  │      "SESSION_SECRET": "...",                                                │  │
│  │      "LIVEKIT_URL": "...",                                                   │  │
│  │      "LIVEKIT_API_KEY": "...",                                               │  │
│  │      "LIVEKIT_API_SECRET": "..."                                             │  │
│  │    }'                                                                        │  │
│  │                                                                               │  │
│  └──────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  3. Container Deployment                                                             │
│  ┌──────────────────────────────────────────────────────────────────────────────┐  │
│  │                                                                               │  │
│  │  docker build ──▶ docker tag ──▶ docker push ──▶ ecs update-service         │  │
│  │  --platform           │             │                   │                    │  │
│  │  linux/arm64          ▼             ▼                   ▼                    │  │
│  │                   Tag with       Push to ECR       Force new                 │  │
│  │                   :latest                          deployment                │  │
│  │                                                                               │  │
│  └──────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## User Flow Diagrams

### First Access (Cold Start)

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                            User First Access Flow                                    │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  User                          System                          Result               │
│                                                                                      │
│  Open URL ─────────────────────────────────────────────────────────────▶ Login page │
│      │                                                                               │
│      ▼                                                                               │
│  Enter password ───────────▶ Validate ───────────▶ Set session cookie               │
│      │                                                                               │
│      ▼                                                                               │
│  Redirect to /  ───────────▶ Show "Waking Blu..." overlay                           │
│      │                                                                               │
│      ▼                                                                               │
│  Auto-call /status ────────▶ Lambda returns {"status":"stopped"}                    │
│      │                                                                               │
│      ▼                                                                               │
│  Auto-call /wake ──────────▶ Lambda scales ECS to 1                                 │
│      │                                                                               │
│      ▼                                                                               │
│  Poll /status ─────────────▶ Wait for {"status":"running"}                          │
│  (every 3s, ~30-60s total)                                                          │
│      │                                                                               │
│      ▼                                                                               │
│  Hide overlay ─────────────▶ Connect to LiveKit ───────────▶ Ready to talk!         │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### Returning Access (Warm)

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                            Returning User Flow (Service Running)                     │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  User                          System                          Result               │
│                                                                                      │
│  Open URL ─────────────────────────────────────────────────────────────▶ Login page │
│      │                                                                 (or auto-    │
│      │                                                                  login if    │
│      │                                                                  session     │
│      │                                                                  valid)      │
│      ▼                                                                               │
│  Redirect to / ────────────▶ Show overlay briefly                                   │
│      │                                                                               │
│      ▼                                                                               │
│  Auto-call /status ────────▶ Lambda returns {"status":"running"}                    │
│      │                                                                               │
│      ▼                                                                               │
│  Hide overlay ─────────────▶ Connect to LiveKit ───────────▶ Ready! (instant)       │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Configuration Reference

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `CLAUDE_CODE_OAUTH_TOKEN` | OAuth token from `claude setup-token` | Yes |
| `AUTH_PASSWORD_HASH` | Bcrypt hash for web login | Yes |
| `SESSION_SECRET` | Random string for session signing | Yes |
| `LIVEKIT_URL` | LiveKit Cloud WebSocket URL | Yes |
| `LIVEKIT_API_KEY` | LiveKit API key | Yes |
| `LIVEKIT_API_SECRET` | LiveKit API secret | Yes |
| `OPENAI_API_KEY` | For STT/TTS (if not local) | Optional |
| `NOTION_API_KEY` | Notion MCP integration | Optional |
| `GITHUB_TOKEN` | GitHub MCP integration | Optional |

### Terraform Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `aws_region` | `ap-southeast-2` | AWS region |
| `aws_profile` | `gazzwi86` | AWS CLI profile |
| `environment` | `production` | Environment name |
| `ecs_cpu` | `1024` | CPU units (1024 = 1 vCPU) |
| `ecs_memory` | `2048` | Memory in MB |
| `use_fargate_spot` | `true` | Use Spot for ~70% savings |
| `use_arm64` | `true` | Use ARM64 for ~20% savings |
| `idle_timeout_minutes` | `30` | Auto-shutdown after idle |
| `start_on_deploy` | `false` | Start at 0 (on-demand) |

---

## Session Management Architecture

### Overview

AIPA implements persistent conversation sessions that survive container restarts and enable multi-device access. Sessions are stored in DynamoDB with automatic name generation.

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              Session Management Flow                                 │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  User starts new conversation                                                        │
│       │                                                                              │
│       ▼                                                                              │
│  ┌─────────────────┐     First message      ┌─────────────────┐                     │
│  │  Create Session │─────────────────────────│ Generate Name   │                     │
│  │  (UUID + user)  │                         │ (Claude haiku)  │                     │
│  └────────┬────────┘                         └────────┬────────┘                     │
│           │                                           │                              │
│           ▼                                           ▼                              │
│  ┌─────────────────┐                         ┌─────────────────┐                     │
│  │ Store in        │                         │ "Tax planning   │                     │
│  │ DynamoDB        │◀────────────────────────│  for 2025"      │                     │
│  └────────┬────────┘                         └─────────────────┘                     │
│           │                                                                          │
│           ▼                                                                          │
│  ┌─────────────────┐     --session-id       ┌─────────────────┐                     │
│  │ Voice/Text      │─────────────────────────│  Claude Code    │                     │
│  │ Messages        │                         │  CLI            │                     │
│  └────────┬────────┘                         └────────┬────────┘                     │
│           │                                           │                              │
│           ▼                                           ▼                              │
│  ┌─────────────────┐                         ┌─────────────────┐                     │
│  │ Messages stored │                         │ Response with   │                     │
│  │ PK=SESSION#id   │                         │ context from    │                     │
│  │ SK=MSG#ts       │                         │ session history │                     │
│  └─────────────────┘                         └─────────────────┘                     │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### DynamoDB Schema (Single-Table Design)

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              DynamoDB Table: aipa-sessions                           │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  Primary Key:                                                                        │
│  ├── PK (Partition Key): String                                                     │
│  └── SK (Sort Key): String                                                          │
│                                                                                      │
│  GSI1 (Global Secondary Index):                                                      │
│  ├── GSI1PK: String                                                                 │
│  └── GSI1SK: String (for date-sorted queries)                                       │
│                                                                                      │
│  Access Patterns:                                                                    │
│  ┌────────────────────────┬──────────────────┬─────────────────────────────────────┐│
│  │ Pattern                │ PK               │ SK                                  ││
│  ├────────────────────────┼──────────────────┼─────────────────────────────────────┤│
│  │ Get session metadata   │ SESSION#{id}     │ META                                ││
│  │ Get session messages   │ SESSION#{id}     │ MSG#{timestamp}                     ││
│  │ List user sessions     │ USER#default     │ SESSION#{id}                        ││
│  │ File → session lookup  │ ARTIFACT#{path}  │ SESSION#{id}                        ││
│  └────────────────────────┴──────────────────┴─────────────────────────────────────┘│
│                                                                                      │
│  TTL: Optional expiry for old sessions (ttl attribute)                              │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### Session Lifecycle

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              Session States                                          │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌──────────┐     User sends      ┌──────────┐     User clicks     ┌──────────┐    │
│  │  NEW     │─────────────────────│  ACTIVE  │─────────────────────│ ARCHIVED │    │
│  │          │    first message    │          │     "Archive"       │          │    │
│  └──────────┘                     └──────────┘                     └──────────┘    │
│       │                                │                                            │
│       │ Auto-generated name            │ Continue adding messages                   │
│       │ from first message             │ Track artifacts created                    │
│       │                                │                                            │
│       └────────────────────────────────┘                                            │
│                                                                                      │
│  Features per session:                                                               │
│  • Unique ID (UUID v4)                                                              │
│  • Auto-generated name (3-6 words via Claude haiku)                                 │
│  • Message history (voice + text, with timestamps)                                  │
│  • Artifact tracking (files created during session)                                 │
│  • Session forking (create new session from point in history)                       │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### Voice + Text Integration

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              Unified Session Experience                              │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                             Chat Interface                                     │  │
│  │  ┌─────────────┐  ┌─────────────────────────────────────┐  ┌───────────────┐ │  │
│  │  │  Sessions   │  │          Chat Area                   │  │   Artifacts   │ │  │
│  │  │  ─────────  │  │                                      │  │   ─────────   │ │  │
│  │  │ • Tax plan  │  │  [🎤 Voice message transcribed]      │  │  📄 doc.pdf   │ │  │
│  │  │ • Code rev  │  │  [💬 Text message typed]             │  │  📊 data.csv  │ │  │
│  │  │ • Alpha ▶   │  │  [🎤 Voice message transcribed]      │  │               │ │  │
│  │  │             │  │                                      │  │               │ │  │
│  │  │  + New      │  │  ┌────────────────────────────────┐  │  │               │ │  │
│  │  │             │  │  │ [🎤]     [Type message...]  [→]│  │  │               │ │  │
│  │  └─────────────┘  │  └────────────────────────────────┘  │  └───────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  Voice Input Flow:                                                                   │
│  User speaks → LiveKit → STT → Add to session → Claude (--session-id) → TTS → User │
│                                                                                      │
│  Text Input Flow:                                                                    │
│  User types → Add to session → Claude (--session-id) → Display → User               │
│                                                                                      │
│  Both modes share the same session and context                                       │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### Multi-Device Sync

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              Multi-Device Access                                     │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌──────────┐        ┌──────────┐        ┌──────────┐                              │
│  │  Phone   │        │  Laptop  │        │  Tablet  │                              │
│  │          │        │          │        │          │                              │
│  └────┬─────┘        └────┬─────┘        └────┬─────┘                              │
│       │                   │                   │                                      │
│       │                   │                   │                                      │
│       └───────────────────┼───────────────────┘                                      │
│                           │                                                          │
│                           ▼                                                          │
│                   ┌──────────────┐                                                   │
│                   │   DynamoDB   │                                                   │
│                   │   Sessions   │                                                   │
│                   └──────────────┘                                                   │
│                                                                                      │
│  Sync Behavior:                                                                      │
│  • Sessions sync via DynamoDB (not real-time)                                       │
│  • One active connection per session at a time                                      │
│  • Refresh to see updates from other devices                                        │
│  • Message history fully preserved                                                  │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### Graceful Degradation

When DynamoDB is not configured (local development):

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              Fallback Mode                                           │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  DynamoDB Available:          │  DynamoDB Not Available:                            │
│  ├── Sessions persist         │  ├── In-memory storage                              │
│  ├── Multi-device sync        │  ├── Sessions lost on restart                       │
│  ├── Full message history     │  ├── Single-device only                             │
│  └── Artifact tracking        │  └── Warning logged at startup                      │
│                                                                                      │
│  Configuration:                                                                      │
│  DYNAMODB_SESSIONS_TABLE=""   → Fallback to in-memory                               │
│  DYNAMODB_SESSIONS_TABLE="x"  → Use DynamoDB table "x"                              │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Appendix: Resource Summary

| Resource Type | Count | Purpose |
|---------------|-------|---------|
| VPC | 1 | Isolated network |
| Subnets | 2 | Multi-AZ availability |
| Security Groups | 2 | ECS + EFS |
| ECS Cluster | 1 | Container orchestration |
| ECS Service | 1 | AIPA application |
| ECS Task Definitions | 2 | Main + Backup |
| Lambda Functions | 2 | Wake-up + Idle checker |
| API Gateway | 1 | HTTP routing |
| EFS | 1 | Persistent storage |
| S3 Buckets | 2 | Files + Backups |
| DynamoDB Tables | 1 | Session storage |
| Secrets Manager | 1 | API credentials |
| CloudWatch Log Groups | 2 | ECS + API Gateway logs |
| IAM Roles | 5 | ECS, Lambda, EventBridge |
