---
layout: doc
title: Getting Started
nav_order: 1
---

Get AIPA running locally in under 10 minutes.

## Prerequisites

- **Docker** - For running the container
- **Claude Pro/Max subscription** - Uses OAuth token, not API credits
- **LiveKit Cloud account** - Free tier includes 10,000 minutes/month

## Step 1: Clone the Repository

```bash
git clone https://github.com/gazzwi86/aipa.git
cd aipa
```

## Step 2: Configure Environment

```bash
cp .env.example .env
```

## Step 3: Get Claude Token

```bash
# This opens a browser for OAuth authentication
claude setup-token
```

Copy the token and add to `.env`:
```
CLAUDE_CODE_OAUTH_TOKEN=your-token-here
```

## Step 4: Generate Password Hash

```bash
python3 -c "import bcrypt; print(bcrypt.hashpw(b'YOUR_PASSWORD', bcrypt.gensalt()).decode())"
```

Add to `.env` (wrap in single quotes):
```
AUTH_PASSWORD_HASH='$2b$12$...'
```

## Step 5: Configure LiveKit

1. Sign up at [cloud.livekit.io](https://cloud.livekit.io)
2. Create a project
3. Copy credentials to `.env`:

```
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret
```

## Step 6: Generate Session Secret

```bash
openssl rand -hex 32
```

Add to `.env`:
```
SESSION_SECRET=your-generated-secret
```

## Step 7: Run

```bash
docker compose -f docker-compose.dev.yml up --build
```

## Step 8: Access

Open [http://localhost:8000](http://localhost:8000) in your browser.

1. Login with your password
2. Click the microphone button to start a voice conversation
3. Or type in the text box

## What's Next?

- [Deploy to AWS](deployment) for a production setup
- [Customize your assistant](customization) with skills and agents
- [Add MCP servers](mcp-servers) to connect to other services

## Environment Variables Reference

| Variable | Description | Required |
|----------|-------------|----------|
| `CLAUDE_CODE_OAUTH_TOKEN` | Token from `claude setup-token` | Yes |
| `AUTH_PASSWORD_HASH` | Bcrypt hash of login password | Yes |
| `SESSION_SECRET` | Random string for session signing | Yes |
| `LIVEKIT_URL` | LiveKit Cloud WebSocket URL | Yes |
| `LIVEKIT_API_KEY` | LiveKit API key | Yes |
| `LIVEKIT_API_SECRET` | LiveKit API secret | Yes |
| `OPENAI_API_KEY` | OpenAI key for STT/TTS | For voice |
| `NOTION_API_KEY` | Notion integration token | Optional |
| `GITHUB_TOKEN` | GitHub PAT | Optional |
