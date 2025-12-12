# AIPA - AI Personal Assistant

[![CI](https://github.com/gazzwi86/aipa/actions/workflows/ci.yml/badge.svg)](https://github.com/gazzwi86/aipa/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Documentation](https://img.shields.io/badge/docs-github.io-blue)](https://gazzwi86.github.io/aipa)

A self-hosted AI personal assistant powered by Claude Code. Voice-first, self-improving, and cost-optimized.

**Key Features:**
- Voice conversations via LiveKit + VoiceMode MCP
- Uses your Claude Pro/Max subscription (not API credits)
- On-demand compute on AWS (~$4-9/month)
- Self-improving with skills and agents
- Fully open source (MIT)

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
│   │   /wake ──▶ Lambda   │   /* ──▶ ECS (via VPC Link)        │  │
│   │   /status ──▶ Lambda │                                     │  │
│   │   /shutdown ──▶ Lambda│                                    │  │
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

## Features

- **Voice Interface** - Natural conversations via browser microphone
- **On-Demand Compute** - Starts cold, wakes in ~45s, auto-shuts after 30min idle
- **Cost Optimized** - ARM64 + Spot pricing = ~$4-9/month
- **Claude Pro/Max** - Uses your subscription, not API credits
- **MCP Integrations** - Notion, GitHub, AWS inspection
- **Secure** - Bcrypt auth, rate limiting, DynamoDB sessions

## Quick Start

### Local Development

```bash
# 1. Clone and configure
git clone https://github.com/gazzwi86/aipa.git
cd aipa
cp .env.example .env

# 2. Get Claude Code token
claude setup-token
# Copy token to .env as CLAUDE_CODE_OAUTH_TOKEN

# 3. Generate password hash
python3 -c "import bcrypt; print(bcrypt.hashpw(b'YOUR_PASSWORD', bcrypt.gensalt()).decode())"
# Add to .env as AUTH_PASSWORD_HASH (wrap in single quotes)

# 4. Configure LiveKit (https://cloud.livekit.io - free tier)
# Add LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET to .env

# 5. Run
docker compose -f docker-compose.dev.yml up --build

# 6. Open http://localhost:8000
```

### AWS Deployment

```bash
# 1. Configure AWS
export AWS_PROFILE=your-profile
cd terraform
terraform init

# 2. Create secrets (see docs/DEPLOYMENT.md)
aws secretsmanager create-secret --name aipa/api-keys --secret-string '{...}'

# 3. Deploy infrastructure
terraform apply

# 4. Build and push image
aws ecr get-login-password | docker login --username AWS --password-stdin YOUR_ECR_URL
docker build --platform linux/arm64 -t aipa .
docker tag aipa:latest YOUR_ECR_URL:latest
docker push YOUR_ECR_URL:latest

# 5. Access via API Gateway URL from terraform output
```

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed instructions.

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `CLAUDE_CODE_OAUTH_TOKEN` | Token from `claude setup-token` | Yes |
| `AUTH_PASSWORD_HASH` | Bcrypt hash of login password | Yes |
| `SESSION_SECRET` | Random string for session signing | Yes |
| `LIVEKIT_URL` | LiveKit Cloud WebSocket URL | Yes |
| `LIVEKIT_API_KEY` | LiveKit API key | Yes |
| `LIVEKIT_API_SECRET` | LiveKit API secret | Yes |
| `OPENAI_API_KEY` | OpenAI key (for STT/TTS) | For voice |
| `NOTION_API_KEY` | Notion integration token | Optional |
| `GITHUB_TOKEN` | GitHub PAT | Optional |

### Cost Optimization Settings

In `terraform/terraform.tfvars`:

```hcl
use_arm64            = true   # ARM64 (Graviton) - 20% cheaper
use_fargate_spot     = true   # Spot pricing - 70% cheaper
idle_timeout_minutes = 30     # Auto-shutdown after idle
start_on_deploy      = false  # Start cold (on-demand)
```

## Monthly Cost Estimate

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
│  (vs ~$16-23 always-on)                                │
└─────────────────────────────────────────────────────────┘
```

## Project Structure

```
aipa/
├── .claude/              # Agent configuration
│   ├── CLAUDE.md        # Agent identity & instructions
│   ├── context/         # Persistent memory
│   └── mcp/             # MCP server configs
├── server/              # FastAPI application
│   ├── main.py         # Entry point & voice UI
│   ├── handlers/       # Route handlers (auth, files, voice)
│   └── services/       # Business logic
├── terraform/           # AWS infrastructure
│   ├── ecs.tf          # ECS Fargate service
│   ├── api_gateway.tf  # API Gateway + routes
│   └── lambda_wakeup.tf # On-demand wake-up system
├── docs/
│   ├── BRIEF.md        # Project overview
│   ├── ARCHITECTURE.md # Detailed architecture
│   └── DEPLOYMENT.md   # AWS deployment guide
├── Dockerfile           # Container (ARM64 compatible)
└── docker-compose.yml   # Local development
```

## On-Demand Wake Pattern

```
┌────────────────────────────────────────────────────────────────┐
│                    On-Demand Wake Flow                          │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. User opens app                                              │
│     Browser ──GET /──▶ API Gateway ──▶ Lambda (status check)   │
│                                                                 │
│  2. If service is stopped                                       │
│     Lambda: ecs.update_service(desiredCount=1)                 │
│     UI shows: "Starting Ultra... ████░░░░░░░░ 35%"             │
│                                                                 │
│  3. UI polls /status every 3s until running                    │
│     Lambda checks: ecs.describe_services()                     │
│                                                                 │
│  4. Service starts (~45 seconds)                               │
│     - EFS mounts                                               │
│     - Container pulls from ECR                                 │
│     - FastAPI starts                                           │
│     - Health check passes                                      │
│                                                                 │
│  5. User can now login and use voice                           │
│                                                                 │
│  6. After 30 min idle (no API requests)                        │
│     Idle checker Lambda: ecs.update_service(desiredCount=0)   │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

## Development

```bash
# Install dependencies
uv sync

# Run server locally
uv run python -m server.main

# Run tests
uv run pytest

# Lint
uv run ruff check .

# Format Terraform
cd terraform && terraform fmt
```

## Troubleshooting

### "Starting Ultra..." stuck
- Check Lambda logs in CloudWatch
- Verify ECS task can pull from ECR
- Check EFS mount points exist

### Voice not working
1. Check browser microphone permissions
2. Verify LiveKit credentials in Secrets Manager
3. Check container logs: `aws logs tail /aws/ecs/aipa`

### Login not working
1. Ensure `AUTH_PASSWORD_HASH` is correct in Secrets Manager
2. Check DynamoDB sessions table exists
3. Verify SESSION_SECRET is set

### Service not waking
1. Check Lambda execution role has ECS permissions
2. Verify API Gateway routes to Lambda correctly
3. Check CloudWatch Events rule is enabled

## Documentation

- [Full Documentation](https://gazzwi86.github.io/aipa) - Comprehensive guides
- [Getting Started](https://gazzwi86.github.io/aipa/docs/getting-started) - Quick setup guide
- [Architecture](https://gazzwi86.github.io/aipa/docs/architecture) - How it works
- [Deployment](https://gazzwi86.github.io/aipa/docs/deployment) - AWS deployment
- [Customization](https://gazzwi86.github.io/aipa/docs/customization) - Make it yours

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

Ways to contribute:
- **Add Skills** - Create capability modules in `.claude/skills/`
- **Add Agents** - Define specialized personas in `.claude/agents/`
- **Improve Infrastructure** - Terraform, Docker, CI/CD
- **Documentation** - Guides, examples, translations

## Community

- [GitHub Issues](https://github.com/gazzwi86/aipa/issues) - Bug reports, feature requests
- [GitHub Discussions](https://github.com/gazzwi86/aipa/discussions) - Questions, ideas

## License

MIT License - see [LICENSE](LICENSE) for details.

## Author

Built by [Gareth](https://github.com/gazzwi86) with Claude Code.

---

*AIPA is not affiliated with Anthropic. Claude is a trademark of Anthropic.*
