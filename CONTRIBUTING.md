# Contributing to AIPA

Thank you for your interest in contributing to AIPA! This guide will help you get started.

## Ways to Contribute

### 1. Add Skills

Skills are reusable capability modules that teach Claude how to perform specific tasks.

**Location:** `.claude/skills/<skill-name>/SKILL.md`

**Structure:**
```markdown
---
name: skill-name
description: What this skill does and when to use it
triggers:
  - keyword1
  - keyword2
---

# Skill Name

Instructions for Claude when this skill is active.

## When to Activate

- Context 1
- Context 2

## Guidelines

...
```

**Submission:**
1. Create your skill in `.claude/skills/`
2. Test it locally with Claude Code
3. Submit a PR with:
   - Clear description of what the skill does
   - Example use cases
   - Any dependencies

### 2. Add Agents

Agents are specialized personas with specific competencies and tools.

**Location:** `.claude/agents/<agent-name>.md`

**Structure:**
```markdown
---
name: agent-name
description: What this agent does and when to use it. Use PROACTIVELY for X, Y, Z.
model: opus|sonnet|haiku
---

# Agent Name

You are an expert in...

## Primary Competencies

- Area 1
- Area 2

## Behavioral Guidelines

...

## MCP Servers to Use

- server1 - for X
- server2 - for Y
```

**Model Selection:**
- `opus` - Critical decisions (architecture, security, code review)
- `sonnet` - Implementation work, planning
- `haiku` - Fast tasks, documentation

### 3. Add Commands

Commands are slash command templates for common workflows.

**Location:** `.claude/commands/<command-name>.md`

**Structure:**
```markdown
---
description: Short description shown in /help
---

Your prompt template here.

Use $ARGUMENTS for user input.
```

### 4. Improve Infrastructure

- **Terraform** in `terraform/`
- **Docker** configuration
- **GitHub Actions** in `.github/workflows/`

### 5. Improve Server

The FastAPI server in `server/`:
- Add handlers in `server/handlers/`
- Add services in `server/services/`
- Add models in `server/models/`

### 6. Documentation

- User guides in `docs/`
- API documentation
- Architecture diagrams

## Development Setup

### Prerequisites

- Python 3.12+
- Docker
- [uv](https://github.com/astral-sh/uv) package manager
- Claude Pro/Max subscription (for testing)

### Local Development

```bash
# Clone
git clone https://github.com/gazzwi86/aipa.git
cd aipa

# Copy environment template
cp .env.example .env

# Get Claude token
claude setup-token
# Add to .env as CLAUDE_CODE_OAUTH_TOKEN

# Generate password hash
python3 -c "import bcrypt; print(bcrypt.hashpw(b'dev', bcrypt.gensalt()).decode())"
# Add to .env as AUTH_PASSWORD_HASH

# Run with hot-reload
docker compose -f docker-compose.dev.yml up --build
```

### Running Tests

```bash
# All tests
uv run pytest

# With coverage
uv run pytest --cov=server --cov-report=html

# Specific tests
uv run pytest tests/unit/
uv run pytest tests/e2e/
```

### Agent Evaluation Tests

Agent evals use **Claude-as-judge** (Claude haiku) to semantically evaluate agent responses.
These are **local-only** tests - they cannot run in CI.

```bash
# Start AIPA server with chat API enabled
ENABLE_CHAT_API=true docker compose up -d

# Run agent evals (~28 tests, requires running AIPA server)
TEST_PASSWORD=your-password \
  uv run pytest tests/evals/test_agent.py --run-agent-evals -v
```

See [docs/TESTING.md](docs/TESTING.md) for detailed documentation.

### Code Quality

```bash
# Lint
uv run ruff check .

# Format
uv run ruff format .

# Type check
uv run mypy server/

# Security scan
uv run bandit -r server/
```

### Terraform

```bash
cd terraform

# Format
terraform fmt -recursive

# Validate
terraform validate

# Plan (requires AWS credentials)
terraform plan
```

## Pull Request Process

### 1. Create a Branch

```bash
git checkout -b feat/your-feature
# or
git checkout -b fix/your-fix
```

### 2. Make Changes

- Follow existing code patterns
- Add tests for new functionality
- Update documentation as needed

### 3. Commit

Use [conventional commits](https://www.conventionalcommits.org/):

```bash
git commit -m "feat(server): add new endpoint"
git commit -m "fix(terraform): correct IAM permissions"
git commit -m "docs: update deployment guide"
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `ci`

**Scopes:** `server`, `terraform`, `docker`, `agent`, `skill`, `docs`

### 4. Submit PR

- Clear description of changes
- Link any related issues
- Include test results
- Screenshots for UI changes

### 5. Review Process

- PRs require at least one review
- All CI checks must pass
- Address feedback promptly

## Code Standards

### Python

- Follow PEP 8
- Type hints on all function signatures
- Docstrings for public APIs
- Async/await for I/O operations

```python
async def process_request(
    request: CommandRequest,
    service: CommandService = Depends(get_service),
) -> CommandResponse:
    """Process a command request.

    Args:
        request: The command request
        service: The command service

    Returns:
        The command response
    """
    ...
```

### Terraform

- Use variables for configurable values
- Tag all resources
- Document with comments
- Follow naming convention: `${project}-${environment}-${resource}`

### Skills/Agents

- Clear, actionable descriptions
- Specific triggers (for skills)
- Appropriate model selection (for agents)
- MCP server recommendations

## Security

- Never commit secrets or API keys
- Use environment variables for sensitive values
- Report security issues privately to maintainers
- Run security scans before submitting

## Community

### Code of Conduct

Be respectful, inclusive, and constructive. We welcome contributors of all backgrounds and experience levels.

### Getting Help

- Open an issue for bugs or feature requests
- Discussions for questions and ideas
- Check existing issues before creating new ones

### License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to AIPA!
