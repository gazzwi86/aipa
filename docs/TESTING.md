# AIPA Testing Strategy

This document describes the testing approach for AIPA, covering unit tests, integration tests, and agent evaluation tests.

## Overview

AIPA uses a multi-layered testing strategy:

| Test Type | Purpose | Requirements | Run Command |
|-----------|---------|--------------|-------------|
| Unit Tests | Test individual components | None | `uv run pytest` |
| Integration Tests | Test with external services | External services | `uv run pytest --run-integration` |
| Agent Eval Tests | Core agent functionality with Claude-as-judge | Running agent | `uv run pytest tests/evals/test_agent.py --run-agent-evals` |

### Test Philosophy

- **Unit tests** validate individual components in isolation (mocked dependencies)
- **Agent eval tests** use Claude-as-judge for semantic quality evaluation (~28 tests)
- **No fake/canned tests** - all eval tests call the real agent via `/api/chat`
- **Benchmark threshold** - 70% pass rate required for pre-deployment confidence
- **Dangerous mode** - Agent runs with `--dangerously-skip-permissions` for full tool access
- **Claude-as-judge** - Uses Claude haiku to evaluate if agent actually performed tasks

## Test Directory Structure

```
tests/
├── conftest.py                 # Shared fixtures
├── unit/                       # Unit tests (fast, no external deps)
│   ├── test_auth.py            # Authentication logic
│   ├── test_config.py          # Configuration parsing
│   └── skills/                 # Skill utility tests (mocked APIs)
│       └── ...                 # Various skill utility tests
├── e2e/                        # End-to-end tests (skipped by default)
│   └── test_voice_flow.py
├── results/                    # Test output
│   └── eval_results.json       # Agent eval results with benchmark + intent
└── evals/                      # Agent evaluation tests
    ├── conftest.py             # Eval fixtures (auth, chat, claude_judge, benchmark)
    └── test_agent.py           # All agent evaluation tests (~28 tests)
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

Agent evaluation tests use **Claude-as-judge** pattern to semantically evaluate agent responses. Claude haiku evaluates whether the agent actually performed tasks vs just explaining how.

### Why Claude-as-Judge?

Traditional assertion-based tests fail for AI agents because:
- Responses are non-deterministic
- Multiple valid phrasings exist
- Quality is subjective (helpful, accurate, safe)
- Keyword assertions can pass when agent asked for permission or explained inability

Claude-as-judge evaluates responses semantically:
- "Did it actually PERFORM the task?" not just explain how
- "Did it ask for permission instead of acting?"
- "Did it claim inability when it should have tools?"

### Prerequisites

1. **Running AIPA Server**
   ```bash
   docker compose up -d
   ```

2. **Environment Variables**
   ```bash
   # Password for authentication (same as AUTH_PASSWORD_HASH password)
   export TEST_PASSWORD="your-password"

   # Enable chat API for testing
   export ENABLE_CHAT_API=true
   ```

3. **Restart with Chat API enabled**
   ```bash
   docker compose up -d
   ```

### Running Agent Evals

```bash
# Run all agent evaluation tests (~28 tests)
uv run pytest tests/evals/test_agent.py --run-agent-evals -v

# Run specific test class
uv run pytest tests/evals/test_agent.py::TestTimeSkill --run-agent-evals -v

# Run excluding integration-requiring tests (Notion, GitHub, YouTube)
uv run pytest tests/evals/test_agent.py --run-agent-evals -v -m "agent_eval and not integration"
```

### Benchmark Threshold

Results are saved to `tests/results/eval_results.json` with benchmark reporting:

```json
{
  "timestamp": "2025-12-15T10:30:00",
  "summary": {
    "total": 21,
    "passed": 20,
    "failed": 1,
    "pass_rate": 0.9524,
    "benchmark_threshold": 0.7,
    "benchmark_met": true
  },
  "by_category": {
    "skills": {"passed": 10, "total": 10, "pass_rate": 1.0, "benchmark_met": true},
    "conversations": {"passed": 5, "total": 5, "pass_rate": 1.0, "benchmark_met": true},
    "safety": {"passed": 2, "total": 2, "pass_rate": 1.0, "benchmark_met": true},
    "quality": {"passed": 2, "total": 2, "pass_rate": 1.0, "benchmark_met": true},
    "general": {"passed": 1, "total": 2, "pass_rate": 0.5, "benchmark_met": false}
  },
  "results": [
    {
      "test_name": "test_time_specific_timezone",
      "category": "skills",
      "intent": "Agent should return current time for a specific city/timezone.",
      "prompt": "What time is it in Tokyo?",
      "response": "The current time in Tokyo is 2:30 PM (JST)...",
      "passed": true,
      "criteria_met": {},
      "latency_ms": 2500.5,
      "error": null,
      "reasoning": null
    }
  ]
}
```

Set custom threshold via environment variable:
```bash
export EVAL_BENCHMARK_THRESHOLD=0.80  # Require 80% pass rate
```

### Claude-as-Judge Evaluation

Each test provides an **intent** that describes what the agent should accomplish. Claude haiku evaluates:

| Criteria | Description |
|----------|-------------|
| Task Performance | Did it actually PERFORM the task (not just explain)? |
| No Permission Requests | Did it NOT ask for permission before acting? |
| Tool Utilization | Did it NOT claim inability when tools are available? |
| Output Quality | Did it provide the requested information/output? |

Cost: ~$0.001-0.002 per judgment, ~$0.06 per full test run.

### Test Categories

All tests are in `test_agent.py` and use Claude-as-judge for semantic evaluation.

**Dangerous Mode (1 test)**
- `test_executes_without_permission_prompt` - Agent runs in YOLO mode without permission prompts

**Time Skill (2 tests)**
- `test_time_specific_timezone` - Time for specific city (e.g., Tokyo)
- `test_time_local` - Local time lookup

**Weather Skill (1 test)**
- `test_weather_specific_city` - Weather for specific city (e.g., Melbourne)

**Document Skills (3 tests)**
- `test_create_presentation` - PPTX presentation creation
- `test_create_spreadsheet` - XLSX spreadsheet creation
- `test_create_document` - DOCX document creation

**Code Skill (1 test)**
- `test_run_python_code` - Execute Python code

**GitHub Skill (1 test)**
- `test_github_repo_info` - Repository information retrieval

**Notion Skills (2 tests)**
- `test_create_task` - Task creation in Notion
- `test_create_notion_note` - Note creation in Notion

**YouTube Skill (1 test)**
- `test_summarize_youtube` - Video summarization

**File Handling (2 tests)**
- `test_creates_downloadable_file` - File generation and access path
- `test_references_existing_file` - Reading uploaded/existing files

**Web Research (1 test)**
- `test_web_research` - Web research capability

**Session Persistence (5 tests)**
- `test_remembers_preference_within_session` - Remembers stated preferences
- `test_remembers_context_within_session` - Remembers context/facts
- `test_new_session_isolation` - New session has no previous context
- `test_continues_task_after_resume` - Task continuation after resume
- `test_multi_turn_topic_tracking` - Topic tracking across turns

**Philosophy Alignment (2 tests)**
- `test_concise_responses` - Brief responses for simple questions
- `test_direct_communication` - Direct communication without excess

**Quality & Factual (2 tests)**
- `test_factual_accuracy` - Factual accuracy on simple questions
- `test_research_helpfulness` - Research response quality

**Conversation Handling (2 tests)**
- `test_handles_ambiguous_request` - Handles ambiguous requests
- `test_handles_topic_change` - Handles topic changes gracefully

**Session API (2 tests)**
- `test_session_id_returned` - Session ID returned in API response
- `test_preserves_provided_session_id` - API preserves session ID

**Safety Boundaries (2 tests)**
- `test_refuses_harmful_request` - Refuses genuinely harmful requests
- `test_asks_approval_for_sensitive_action` - Asks approval for sensitive actions

### Unit Tests for Skills

Skill utility functions have separate unit tests in `tests/unit/skills/`:

```bash
# Run skill unit tests only (fast, no external deps)
uv run pytest tests/unit/skills/ -v
```

| Test File | Coverage |
|-----------|----------|
| `test_time_utils.py` | Timezone resolution, time formatting |
| `test_weather_format.py` | Weather API response formatting, geocoding |
| `test_script_executor.py` | Security validation, sandboxed execution |
| `test_document_generation.py` | PPTX, DOCX, XLSX generation |
| `test_youtube_api.py` | URL parsing, transcript processing |
| `test_file_analysis.py` | File reading, PDF extraction |

These tests use mocked APIs and don't require external services.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Test Runner (pytest)                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Test sends prompt ──────────► /api/chat endpoint         │
│                                                              │
│  2. Agent processes ───────────► Claude Code CLI (sonnet)    │
│                                                              │
│  3. Response returned ◄────────── Agent response             │
│                                                              │
│  4. Claude-as-judge ───────────► Claude haiku                │
│                                                              │
│  5. Evaluation result ◄─────────── PASS/FAIL + reasoning     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Writing New Eval Tests

Use Claude-as-judge for semantic evaluation:

```python
import pytest

@pytest.mark.agent_eval
class TestMyFeature:
    async def test_feature_works(self, chat, claude_judge):
        """Test description goes here - this becomes the 'intent' in results."""
        prompt = "What time is it in London?"
        response = chat(prompt)

        # Use Claude-as-judge for semantic evaluation
        passed, reason = await claude_judge(
            prompt=prompt,
            response=response,
            intent="Return the actual current time in London with HH:MM format"
        )
        assert passed, f"Claude judge failed: {reason}\nResponse: {response[:300]}"
```

For simple deterministic checks, you can also use assertions:

```python
@pytest.mark.agent_eval
class TestSimpleCheck:
    def test_math_result(self, chat):
        """Agent should compute simple math correctly."""
        response = chat("What is 25 * 4?")
        assert "100" in response
        assert len(response) < 200  # Should be concise
```

### Handling Non-Determinism

LLM responses vary. Mitigation strategies:

1. **Semantic evaluation** - Claude-as-judge evaluates meaning, not exact match
2. **Intent-based testing** - Focus on what the test expects, not specific wording
3. **Clear criteria** - Judge prompt explicitly states pass/fail criteria
4. **Reasoning capture** - Judge provides reasoning for debugging failures

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
- **Unit tests** run on every PR (including `tests/unit/skills/`)
- **Integration tests** skipped unless secrets are configured
- **Agent eval tests** are **local-only** - they require a running agent and Ollama (cannot run in CI)

```yaml
# CI runs these:
uv run pytest tests/unit/ -v

# CI does NOT run these (require local agent + Ollama):
uv run pytest tests/evals/ --run-agent-evals
```

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

**Agent identifies as "DEV Agent" instead of "Ultra"**
- Ensure docker-compose.yml mounts `./workspace:/workspace` (not `./.claude`)
- The agent should run from `/workspace` to pick up `workspace/.claude/CLAUDE.md`

**Claude-as-judge timeout**
- Tests may take 20-35 minutes for full suite (~28 tests)
- Each agent call: ~15-45 seconds
- Each judge call: ~3-8 seconds (haiku is fast)

### Environment Variables Reference

| Variable | Purpose | Default |
|----------|---------|---------|
| `TEST_PASSWORD` | Login password for auth | (required) |
| `ENABLE_CHAT_API` | Enable /api/chat endpoint | `false` |
| `EVAL_API_ENDPOINT` | Agent API base URL | `http://localhost:8000` |
| `EVAL_TIMEOUT` | Test timeout in seconds | `60` |
| `EVAL_BENCHMARK_THRESHOLD` | Minimum pass rate required | `0.70` |
