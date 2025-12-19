# AIPA - AI Personal Assistant

## Project Brief

**Project Name:** AIPA (AI Personal Assistant)
**Codename:** Blu
**Owner:** Gareth
**Status:** In Development

---

## Vision

Build a self-hosted, self-improving AI assistant that acts as a digital twin - understanding your philosophy, approaches, and working style to autonomously handle tasks while maintaining human oversight for sensitive actions.

The assistant runs Claude Code with VoiceMode MCP, accessible via voice from anywhere through LiveKit.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              INTERNET                                        │
│                                                                              │
│   ┌─────────────────┐        ┌─────────────────┐        ┌─────────────────┐ │
│   │  Your Browser   │        │  LiveKit Cloud  │        │  Claude API     │ │
│   │  (Voice Client) │        │  (Free Tier)    │        │  (Pro/Max sub)  │ │
│   └────────┬────────┘        └────────┬────────┘        └────────┬────────┘ │
│            │                          │                          │          │
└────────────│──────────────────────────│──────────────────────────│──────────┘
             │                          │                          │
             ▼                          ▼                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          AWS (ap-southeast-2)                                │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                    API Gateway (HTTP API)                            │   │
│   │   /wake ─────┐  /status ──┐  /shutdown ─┐  /* ────────────────────┐ │   │
│   └──────────────│────────────│─────────────│────────────────────────│──┘   │
│                  │            │             │                        │       │
│                  ▼            ▼             ▼                        ▼       │
│   ┌──────────────────────────────────────────┐        ┌─────────────────┐   │
│   │          Wake-Up Lambda (free)           │        │   ECS Fargate   │   │
│   │                                          │        │   (on-demand)   │   │
│   │  • Sets desired_count = 1                │        │                 │   │
│   │  • Returns status immediately            │───────▶│  ┌───────────┐  │   │
│   │  • Health check polling by UI            │        │  │   AIPA    │  │   │
│   └──────────────────────────────────────────┘        │  │ Container │  │   │
│                                                        │  └───────────┘  │   │
│   ┌──────────────────────────────────────────┐        │                 │   │
│   │       Idle Checker Lambda (5min)         │        │  ARM64/Graviton │   │
│   │                                          │        │  Spot Pricing   │   │
│   │  • Checks API Gateway request count      │◀──────▶│  ~$0.01/hour    │   │
│   │  • 30 min idle → desired_count = 0       │        └────────┬────────┘   │
│   │  • CloudWatch Scheduled Rule             │                 │            │
│   └──────────────────────────────────────────┘                 │            │
│                                                                 │            │
│   ┌─────────────────────────────────────────────────────────────┘            │
│   │                                                                          │
│   ▼                                                                          │
│   ┌──────────────────────────────────────────────────────────────────────┐  │
│   │                         Storage Layer                                 │  │
│   │   ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────────┐ │  │
│   │   │    EFS     │  │     S3     │  │   S3       │  │   DynamoDB     │ │  │
│   │   │ /workspace │  │  /files    │  │  /backups  │  │   Sessions     │ │  │
│   │   │  /state    │  │ (sharing)  │  │  (daily)   │  │   (auth)       │ │  │
│   │   └────────────┘  └────────────┘  └────────────┘  └────────────────┘ │  │
│   └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Core Principles

1. **Voice First** - Natural voice conversations via VoiceMode MCP
2. **Autonomy with Oversight** - Operates independently, approval for sensitive actions
3. **Self-Improvement** - Can create new skills, tools, and agents
4. **Context Persistence** - Memory via `.claude/context/` folder
5. **Cost Efficiency** - On-demand compute, pay only when used (~$4-9/month)
6. **Simplicity** - Minimal dependencies, one-command deploy

---

## Key Features

### Voice Interface
- VoiceMode MCP with LiveKit transport
- Accessible from any browser
- STT via OpenAI Whisper, TTS via OpenAI
- Auto silence detection (5 seconds)

### Session Management
- Persistent conversation sessions in DynamoDB
- Auto-generated session names from first message (via Claude haiku)
- Multi-device sync (access sessions from any device)
- Unified voice/text - both input methods share same session
- Artifact tracking per session (files created during conversation)
- Session forking (branch new conversation from any point)

### On-Demand Compute
- Service starts cold (0 tasks)
- Lambda wakes service on UI access (~45s startup)
- Auto-shutdown after 30 min idle
- 80-90% cost reduction vs always-on

### File Sharing
- Files created in `/workspace/files/`
- Browsable via authenticated web UI
- S3 for external file sharing
- Presigned URLs for secure access

### MCP Integrations
- **Notion** - Knowledge base management
- **GitHub** - Repository management
- **VoiceMode** - Voice conversations
- **AWS** - Infrastructure inspection (read-only)

### Security
- Bcrypt password authentication
- Rate limiting with exponential backoff
- Session-based auth with DynamoDB
- HTTPS required (API Gateway handles TLS)
- Human-in-the-loop for sensitive actions

---

## Cost Breakdown

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Monthly Cost Estimate                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   ECS Fargate (on-demand, ARM64, Spot)                              │
│   ├── 4 hours/day × 30 days = 120 hours                             │
│   ├── 0.25 vCPU + 0.5GB @ Spot pricing                              │
│   └── Cost: ~$1-3/month                                             │
│                                                                      │
│   Supporting Services                                                │
│   ├── EFS (1GB): ~$0.30/month                                       │
│   ├── S3 (files + backups): ~$0.10/month                            │
│   ├── DynamoDB (sessions): ~$0 (free tier)                          │
│   ├── CloudWatch Logs: ~$0.50/month                                 │
│   ├── Lambda (wake-up): ~$0 (free tier)                             │
│   ├── API Gateway: ~$1-2/month                                      │
│   └── NAT Gateway (data): ~$1-2/month                               │
│                                                                      │
│   TOTAL: ~$4-9/month (varies with usage)                            │
│                                                                      │
│   Compare to always-on: ~$16-23/month                               │
│   Savings: 60-80%                                                   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Local Development

```bash
# 1. Clone and configure
git clone https://github.com/gazzwi86/aipa.git
cd aipa
cp .env.example .env

# 2. Generate credentials
claude setup-token                    # Get OAuth token
python3 -c "import bcrypt; ..."       # Generate password hash

# 3. Configure .env with:
#    - CLAUDE_CODE_OAUTH_TOKEN
#    - AUTH_PASSWORD_HASH
#    - SESSION_SECRET
#    - LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET
#    - DYNAMODB_SESSIONS_TABLE (optional, for persistent sessions)

# 4. Run
docker compose -f docker-compose.yml up --build

# 5. Access http://localhost:8000
```

### AWS Deployment

```bash
# 1. Configure AWS credentials
export AWS_PROFILE=your-profile

# 2. Initialize Terraform
cd terraform
terraform init

# 3. Create secrets in AWS Secrets Manager
# (See docs/DEPLOYMENT.md for details)

# 4. Deploy
terraform apply

# 5. Build and push Docker image
./scripts/deploy.sh
```

See [docs/DEPLOYMENT.md](./DEPLOYMENT.md) for detailed instructions.

---

## Requirements

### Minimum
- Docker (for local dev)
- Claude Pro/Max subscription
- LiveKit Cloud account (free tier: 10k mins/month)

### For AWS Deployment
- AWS account with appropriate permissions
- Terraform 1.0+
- AWS CLI configured

### Optional
- OpenAI API key (for voice when not using local STT/TTS)
- Notion integration token
- GitHub personal access token

---

## Project Structure

```
aipa/
├── .claude/              # Agent configuration
│   ├── CLAUDE.md        # Agent identity & instructions
│   ├── context/         # Persistent memory
│   ├── skills/          # Capability modules
│   ├── agents/          # Sub-agent definitions
│   └── mcp/             # MCP server configs
├── server/              # FastAPI application
│   ├── main.py         # Entry point & voice UI
│   ├── config.py       # Settings
│   ├── handlers/       # Route handlers (auth, files, sessions, voice)
│   ├── services/       # Business logic (auth, sessions, voice_agent)
│   ├── models/         # Pydantic models
│   └── templates/      # Jinja2 HTML templates (chat, login, files)
├── terraform/           # AWS infrastructure
│   ├── main.tf         # Core resources
│   ├── ecs.tf          # ECS Fargate service
│   ├── dynamodb.tf     # Session storage table
│   ├── api_gateway.tf  # API Gateway & routes
│   └── lambda_wakeup.tf # On-demand wake-up
├── docs/                # Documentation
│   ├── BRIEF.md        # This file
│   ├── ARCHITECTURE.md # Detailed architecture
│   └── DEPLOYMENT.md   # Deployment guide
├── Dockerfile           # Container definition
├── docker-compose.yml   # Production stack
```

---

## User Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           User Flow                                       │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│   1. OPEN APP                                                            │
│      ┌──────────┐                                                         │
│      │ Browser  │ ──GET /──▶ API Gateway ──▶ Lambda checks status        │
│      └──────────┘                                                         │
│                                                                           │
│   2. SERVICE WAKING (if cold)                                            │
│      ┌──────────────────────────────────────────────┐                    │
│      │  "Starting Blu..."                           │                    │
│      │  ████████░░░░░░░░░░░░░░░░░░░  35%           │                    │
│      │  ~45 seconds                                 │                    │
│      └──────────────────────────────────────────────┘                    │
│                                                                           │
│   3. LOGIN                                                               │
│      ┌────────────────────────┐                                          │
│      │  Password: ••••••••   │                                          │
│      │  [Login]              │                                          │
│      └────────────────────────┘                                          │
│                                                                           │
│   4. CONVERSATION (Voice or Text)                                        │
│      ┌────────────────────────────────────────────────────────────────┐ │
│      │ Sessions │          Chat                     │  Artifacts      │ │
│      │ ──────── │                                   │  ──────────     │ │
│      │ Tax plan │  🎤 "What meetings do I have?"    │  📄 doc.pdf     │ │
│      │ Code rev │  🤖 "Let me check calendar..."    │  📊 data.csv    │ │
│      │ Alpha ▶  │                                   │                 │ │
│      │ + New    │  [🎤 Voice] [Type here...] [→]   │                 │ │
│      └────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│   5. AUTO-SHUTDOWN (30 min idle)                                         │
│      Lambda detects no API requests → sets desired_count = 0            │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Documentation

- **[BRIEF.md](./BRIEF.md)** - This file, project overview
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - Detailed technical architecture
- **[DEPLOYMENT.md](./DEPLOYMENT.md)** - AWS deployment guide

---

*Last updated: 2025-12-12*
