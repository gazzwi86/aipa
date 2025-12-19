---
layout: doc
title: Customization
nav_order: 4
---

Make AIPA your own by customizing its personality, capabilities, and integrations.

## Agent Identity

The main agent configuration is in `.claude/CLAUDE.md`. This defines:
- Name and personality
- Core principles
- Behavioral guidelines
- Security rules

### Changing the Name

Edit `.claude/CLAUDE.md`:

```markdown
## Identity

- **Name**: Your Assistant Name
- **Owner**: Your Name
```

### Changing Personality

Update the communication style in `.claude/context/preferences/communication-style.md`:

```markdown
# Communication Style

- Tone: Professional but friendly
- Verbosity: Concise
- Formatting: Use markdown, code blocks
```

## Adding Capabilities

### Skills

Create new skills in `.claude/skills/`:

```bash
mkdir -p .claude/skills/my-skill
```

Create `SKILL.md`:
```markdown
---
name: my-skill
description: What this skill does
triggers:
  - keyword1
---

# My Skill

Instructions...
```

See [Creating Skills](skills) for details.

### Agents

Create specialized agents in `.claude/agents/`:

```bash
touch .claude/agents/my-agent.md
```

See [Creating Agents](agents) for details.

### Commands

Create slash commands in `.claude/commands/`:

```markdown
---
description: What this command does
---

Your prompt template.

Arguments: $ARGUMENTS
```

## Integrations

### Notion

1. Create a Notion integration at [notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Add to workspace pages
3. Add API key to `.env`:
   ```
   NOTION_API_KEY=secret_xxx
   ```

4. Configure MCP server in `.mcp.json`:
   ```json
   {
     "notion": {
       "type": "stdio",
       "command": "npx",
       "args": ["-y", "@notionhq/notion-mcp-server"],
       "env": {
         "NOTION_API_KEY": "${NOTION_API_KEY}"
       }
     }
   }
   ```

### GitHub

1. Create a Personal Access Token at [github.com/settings/tokens](https://github.com/settings/tokens)
2. Add to `.env`:
   ```
   GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxx
   ```

3. The GitHub MCP server is pre-configured in `.mcp.json`

### Custom APIs

Create a custom MCP server or use the generic HTTP server:

```json
{
  "custom-api": {
    "type": "stdio",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-fetch"],
    "env": {
      "API_KEY": "${CUSTOM_API_KEY}"
    }
  }
}
```

## Context Persistence

AIPA maintains memory across sessions via the context system:

```
.claude/context/
├── preferences/         # User preferences
│   ├── owner.md        # Owner information
│   └── communication-style.md
├── philosophy/          # Beliefs and approaches
│   ├── beliefs.md
│   ├── approaches.md
│   └── principles.md
├── learnings/          # Accumulated knowledge
└── projects/           # Per-project context
```

### Adding Context

Create markdown files in the appropriate directory:

```markdown
# My Preferences

- I prefer X over Y
- Always do Z before A
- Never use B when C
```

AIPA reads these files on startup and incorporates them into responses.

## Human-in-the-Loop

Configure what actions require approval in `.claude/CLAUDE.md`:

```markdown
## Human-in-the-Loop Requirements

**ALWAYS seek approval before:**
- Sending emails or messages
- Creating calendar events
- Any financial transaction
- Deleting important data
- Long-running tasks (>10 minutes)
```

## Environment-Specific Config

Use `docker-compose.yml` with:
- No hot reload
- JSON logging
- S3 file storage
- DynamoDB sessions

### Environment Variables

| Variable | Dev Default | Production |
|----------|-------------|------------|
| `ENVIRONMENT` | development | production |
| `LOG_LEVEL` | DEBUG | INFO |
| `DEBUG` | true | false |

## Extending Functionality

### Custom Handlers

Add new API endpoints in `server/handlers/`:

```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/my-endpoint")
async def my_endpoint():
    return {"status": "ok"}
```

Register in `server/main.py`:
```python
from server.handlers import my_handler
app.include_router(my_handler.router)
```

### Custom Services

Add business logic in `server/services/`:

```python
class MyService:
    async def do_something(self) -> str:
        return "done"
```

### Custom Models

Add Pydantic models in `server/models/`:

```python
from pydantic import BaseModel

class MyRequest(BaseModel):
    field: str
```

## Theming

### Web UI

The web UI uses inline styles in `server/templates/`. Modify:
- Colors
- Fonts
- Layout

### Voice

Voice settings are configured via VoiceMode MCP:
- Voice selection (OpenAI TTS voices)
- Speech rate
- Silence detection
