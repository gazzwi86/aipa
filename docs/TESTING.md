# AIPA Testing Strategy

This document describes the testing approach for AIPA, covering unit tests, integration tests, and agent evaluation tests with LLM-as-judge.

## Overview

AIPA uses a multi-layered testing strategy:

| Test Type | Purpose | Requirements | Run Command |
|-----------|---------|--------------|-------------|
| Unit Tests | Test individual components | None | `uv run pytest` |
| Integration Tests | Test with external services | External services | `uv run pytest --run-integration` |
| Agent Eval Tests | Evaluate agent response quality | Running agent + Ollama | `uv run pytest --run-agent-evals` |

### Test Philosophy

Agent tests use two complementary approaches:

1. **Fast Assertion Tests** - Simple string checks for deterministic aspects (identity, basic behavior)
2. **LLM-as-Judge Tests** - Semantic evaluation for subjective quality (helpfulness, accuracy, safety)

## Test Directory Structure

```
tests/
├── conftest.py                 # Shared fixtures
├── unit/                       # Unit tests
│   ├── test_auth.py
│   ├── test_config.py
│   └── ...
├── e2e/                        # End-to-end tests (skipped by default)
│   └── test_voice_flow.py
└── evals/                      # Agent evaluation tests
    ├── conftest.py             # Eval-specific fixtures (auth, chat, judge)
    ├── test_conversations.py   # Fast assertion tests + multi-turn (10+ tests)
    ├── test_agent_evals.py     # LLM-as-judge semantic tests
    └── judge/                  # LLM-as-judge components
        ├── __init__.py
        ├── ollama_judge.py     # Custom Ollama model for DeepEval
        └── metrics.py          # Custom GEval metrics
```

## Running Tests

### Quick Start

```bash
# Run unit tests only (default)
uv run pytest

# Run with coverage
uv run pytest --cov=server --cov-report=term-missing

# Run specific test file
uv run pytest tests/unit/test_auth.py -v
```

### Test Markers

| Marker | Description |
|--------|-------------|
| `@pytest.mark.integration` | Requires external services |
| `@pytest.mark.agent_eval` | Requires running agent + Ollama |
| `@pytest.mark.slow` | Long-running tests |
| `@pytest.mark.e2e` | End-to-end browser tests |

### Running Integration Tests

Integration tests require external services (Notion, GitHub, etc.):

```bash
# Set required API keys
export NOTION_API_KEY=...
export GITHUB_TOKEN=...

# Run integration tests
uv run pytest --run-integration
```

## Agent Evaluation Tests

Agent evaluation tests use **LLM-as-judge** pattern with DeepEval and Ollama to semantically evaluate agent responses.

### Why LLM-as-Judge?

Traditional assertion-based tests fail for AI agents because:
- Responses are non-deterministic
- Multiple valid phrasings exist
- Quality is subjective (helpful, accurate, safe)

LLM-as-judge evaluates responses semantically:
- "Is this response helpful?" vs exact string matching
- "Did the agent refuse the harmful request?" vs checking for "I can't"

### Prerequisites

1. **Running AIPA Server**
   ```bash
   docker compose up -d
   ```

2. **Ollama with qwen3:8b** (recommended for speed)
   ```bash
   # Ollama should be running on localhost:11434
   ollama pull qwen3:8b

   # Or use gemma3:12b for higher quality (slower)
   # export OLLAMA_JUDGE_MODEL=gemma3:12b
   ```

3. **Environment Variables**
   ```bash
   # Password for authentication (same as AUTH_PASSWORD_HASH password)
   export TEST_PASSWORD="your-password"

   # Enable chat API for testing
   export ENABLE_CHAT_API=true
   ```

4. **Restart with Chat API enabled**
   ```bash
   docker compose up -d
   ```

### Running Agent Evals

```bash
# Run all agent evaluation tests (fast + LLM-judge)
uv run pytest tests/evals/ --run-agent-evals -v

# Run only fast assertion tests (no LLM judging, ~4 minutes)
uv run pytest tests/evals/test_conversations.py --run-agent-evals -v

# Run LLM-as-judge tests (requires Ollama, slower)
uv run pytest tests/evals/test_agent_evals.py --run-agent-evals -v

# Run specific test class
uv run pytest tests/evals/test_conversations.py::TestPhilosophy --run-agent-evals -v

# Run excluding integration-requiring tests
uv run pytest tests/evals/ --run-agent-evals -v -m "agent_eval and not integration"
```

### Evaluation Metrics

Custom metrics evaluate different quality aspects:

| Metric | Threshold | Description |
|--------|-----------|-------------|
| `IdentityMetric` | 0.7 | Does agent identify as Ultra? |
| `HelpfulnessMetric` | 0.7 | Is response helpful and actionable? |
| `SafetyMetric` | 0.9 | Does agent refuse harmful requests? |
| `AccuracyMetric` | 0.7 | Is response factually accurate? |
| `SkillActivationMetric` | 0.8 | Did correct skill activate? |
| `ConcisenessMetric` | 0.7 | Is response appropriately brief? |
| `ApprovalRequiredMetric` | 0.8 | Does agent ask approval for sensitive actions? |

### Test Categories

The 20 agent evaluation tests cover:

**Identity (3 tests)**
- Agent knows its name (Ultra)
- Agent knows its owner (Gareth)
- Agent can describe capabilities

**Skills (10 tests)**
- Weather skill (2 tests)
- Time lookup
- Notion task creation (integration)
- GitHub issues (integration)
- Web research
- YouTube summarization (integration)
- Document generation (2 tests)
- Script execution

**Safety (4 tests)**
- Refuses hacking requests
- Refuses unauthorized financial actions
- Asks approval for sensitive actions
- Doesn't leak secrets

**Quality (3 tests)**
- Voice responses are concise
- Complex queries get detailed responses
- Handles unknown/nonsense input gracefully

### Fast Assertion Tests (test_conversations.py)

For faster CI/CD feedback, many tests use simple string assertions instead of LLM judging:

```python
@pytest.mark.agent_eval
class TestIdentityFast:
    def test_name_contains_ultra(self, chat):
        """Agent should mention 'Ultra' when asked its name."""
        response = chat("What is your name?")
        assert "ultra" in response.lower()

    def test_owner_contains_gareth(self, chat):
        """Agent should mention 'Gareth' when asked about owner."""
        response = chat("Who created you?")
        assert "gareth" in response.lower()
```

**Test Classes:**

| Class | Tests | Description |
|-------|-------|-------------|
| `TestIdentityFast` | 2 | Name and owner checks |
| `TestSessionManagement` | 1 | Session ID generation |
| `TestPhilosophy` | 3 | Approval requests, transparency, helpfulness |
| `TestStateHandling` | 1 | Graceful incomplete input handling |
| `TestResponseQualityFast` | 3 | Math accuracy, response time, non-empty responses |

### Multi-Turn Session Limitations

Claude CLI requires different flags for session management:
- `--session-id <uuid>` - Create a new session
- `--resume <uuid>` - Continue an existing session

**Current Status**: Multi-turn tests are skipped pending server-side session tracking implementation. The chat API currently treats each call as independent.

```python
@pytest.mark.skip(reason="Multi-turn requires Claude CLI session management")
class TestMultiTurn:
    def test_remembers_context_within_session(self, chat):
        """Agent should remember context within same session."""
        # TODO: Implement session state tracking
```

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Test Runner (pytest)                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Test sends prompt ──────────► /api/chat endpoint         │
│                                                              │
│  2. Agent processes ───────────► Claude Code CLI             │
│                                                              │
│  3. Response returned ◄────────── Agent response             │
│                                                              │
│  4. DeepEval evaluates ─────────► Ollama (qwen3:8b)          │
│                                                              │
│  5. Metrics scored ◄────────────── Pass/Fail + scores        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Writing New Eval Tests

```python
import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase
from tests.evals.judge.metrics import create_helpfulness_metric

@pytest.mark.agent_eval
class TestMyFeature:
    def test_feature_works(self, chat, ollama_judge):
        """Test description."""
        response = chat("User query here")

        test_case = LLMTestCase(
            input="User query here",
            actual_output=response,
            expected_output="Description of expected behavior",
        )
        assert_test(test_case, [create_helpfulness_metric(model=ollama_judge)])
```

### Handling Non-Determinism

LLM responses vary. Mitigation strategies:

1. **Semantic evaluation** - Judge evaluates meaning, not exact match
2. **Threshold tuning** - 0.7-0.9 thresholds allow variation
3. **Multiple metrics** - Combine metrics for robustness
4. **Criteria focus** - Test what matters (helpfulness) not formatting

## Security Considerations

### Chat API Security

The `/api/chat` endpoint used for testing has three protection layers:

1. **Cookie Authentication** - Same `aipa_session` cookie as other APIs
2. **Development-Only Flag** - Disabled in production by default
3. **Rate Limiting** - Same rate limiting as login endpoint

```python
# Only enabled when ENABLE_CHAT_API=true
if settings.is_production and not settings.enable_chat_api:
    raise HTTPException(status_code=404, detail="Not found")
```

### Test Authentication

Tests authenticate via the login flow, same as the web UI:

```python
@pytest.fixture(scope="session")
def authenticated_client():
    client = httpx.Client(base_url="http://localhost:8000")
    client.post("/login", data={"password": os.environ["TEST_PASSWORD"]})
    return client  # Client now has aipa_session cookie
```

## Cleanup Registry

Integration tests may create resources (Notion pages, GitHub issues, etc.).
The cleanup registry tracks these for manual cleanup if tests fail.

```python
# tests/.cleanup_registry.json tracks created resources
# Manual cleanup instructions written to tests/.cleanup_instructions.md
```

## Linting and Type Checking

```bash
# Run linter
uv run ruff check .

# Run type checker
uv run mypy server/

# Run security scanner
uv run bandit -r server/
```

## Continuous Integration

Tests run in GitHub Actions:
- Unit tests on every PR
- Integration tests require secrets
- Agent eval tests are local-only (require Ollama)

See [CI_CD.md](CI_CD.md) for CI/CD configuration details.

## Troubleshooting

### Common Issues

**"Chat API disabled"**
```bash
# Enable the chat API
export ENABLE_CHAT_API=true
docker compose up -d
```

**"Authentication failed"**
```bash
# Set the test password (same as your login password)
export TEST_PASSWORD="your-password"
```

**"Cannot connect to agent"**
```bash
# Verify server is running
curl http://localhost:8000/health

# Check logs
docker compose logs aipa
```

**"Ollama not accessible"**
```bash
# Verify Ollama is running
curl http://localhost:11434/api/tags

# Pull the recommended model
ollama pull qwen3:8b
```

**LLM-as-judge timeout**
- DeepEval has internal timeout limits (~207s)
- Use faster models like `qwen3:8b` instead of `gemma3:12b`
- Fast assertion tests don't use LLM judging

**Agent identifies as "DEV Agent" instead of "Ultra"**
- Ensure docker-compose.yml mounts `./workspace:/workspace` (not `./.claude`)
- The agent should run from `/workspace` to pick up `workspace/.claude/CLAUDE.md`

### Environment Variables Reference

| Variable | Purpose | Default |
|----------|---------|---------|
| `TEST_PASSWORD` | Login password for auth | (required) |
| `ENABLE_CHAT_API` | Enable /api/chat endpoint | `false` |
| `EVAL_API_ENDPOINT` | Agent API base URL | `http://localhost:8000` |
| `OLLAMA_JUDGE_MODEL` | Model for LLM-as-judge | `qwen3:8b` |
| `EVAL_TIMEOUT` | Test timeout in seconds | `60` |
