---
name: self-testing
description: Verify agent capabilities through automated tests
triggers:
  - test yourself
  - verify capabilities
  - run self tests
  - check if you can
  - self test
  - capability check
---

# Self-Testing Skill

Run automated tests to verify the agent's capabilities are working correctly.

## When to Activate

- "Test yourself"
- "Verify your capabilities"
- "Run self-tests"
- "Check if the weather skill works"
- "Can you still do X?"
- "Run the test suite"

## Capabilities

### Unit Tests
Run unit tests for individual skills and components.

### Integration Tests
Test interactions with external services (with cleanup).

### Capability Verification
Quick checks to verify specific capabilities work.

### Regression Tests
Ensure previously working features still work.

## Test Categories

### Skill Tests
Test individual skill functionality:

```bash
# Test specific skill
pytest tests/evals/test_skills/test_time_lookup.py -v

# Test all skills
pytest tests/evals/test_skills/ -v
```

### Integration Tests
Test external service integration:

```bash
# Run with integration flag
pytest tests/evals/test_integrations/ --run-integration -v
```

### Agent Evals
Test agent response quality:

```bash
# Run evaluation tests
pytest tests/evals/test_agent_basics.py -v -m eval
```

## Quick Capability Checks

### Time Lookup
```python
from workspace/.claude/skills/time-lookup/time_utils import get_current_time
result = get_current_time("Melbourne")
assert result["success"], "Time lookup failed"
print(f"Time lookup OK: {result['formatted_brief']}")
```

### Script Runner
```python
from workspace/.claude/skills/script-runner/script_executor import run_python_script
result = run_python_script('print("test")', workspace="/tmp")
assert result.success, "Script runner failed"
print("Script runner OK")
```

### AWS Budget (requires AWS)
```bash
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-02 \
  --granularity MONTHLY \
  --metrics UnblendedCost
# Check for valid response
```

## Test Output Format

### Summary Report

```markdown
## Self-Test Results

**Run Time**: 2024-12-12 10:30:00 AEDT
**Duration**: 12.5 seconds

### Results

| Category | Passed | Failed | Skipped |
|----------|--------|--------|---------|
| Unit Tests | 45 | 0 | 2 |
| Skill Tests | 28 | 0 | 0 |
| Integration | 5 | 1 | 3 |
| Evals | 15 | 0 | 0 |
| **Total** | **93** | **1** | **5** |

### Failed Tests

1. `test_integrations/test_notion.py::test_create_page`
   - Error: Connection timeout
   - Likely cause: Network issue or API down

### Skipped Tests

- Integration tests without `--run-integration` flag
- Tests requiring unavailable services
```

### Voice Response

> "Self-test complete. 93 tests passed, 1 failed, 5 skipped. The failed test was a Notion connection timeout - that's likely a network issue, not a bug. All core capabilities are working."

## Running Tests

### Full Suite
```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=server --cov=workspace/.claude/skills
```

### Specific Categories
```bash
# Just evals
pytest tests/evals/ -v

# Just skills
pytest tests/evals/test_skills/ -v

# Just integration (requires flag)
pytest tests/evals/test_integrations/ --run-integration -v
```

### Quick Smoke Test
```bash
# Fast subset of critical tests
pytest tests/evals/test_agent_basics.py tests/evals/test_skills/test_time_lookup.py -v
```

## Cleanup After Tests

Integration tests should clean up after themselves:

```python
@pytest.fixture
def cleanup_registry():
    """Track resources for cleanup."""
    registry = CleanupRegistry()
    yield registry
    # Cleanup happens automatically via session fixture
```

If tests fail, check `/tests/.cleanup_registry.json` for resources that need manual cleanup.

## Response Format

### Voice (Brief)
> "All 45 tests passed. Your time lookup, script runner, and GitHub skills are all working correctly."

### Text (Detailed)
```markdown
## Self-Test Complete

### Summary
- **Status**: PASS
- **Tests Run**: 45
- **Duration**: 3.2s

### Capability Status

| Skill | Status | Notes |
|-------|--------|-------|
| time-lookup | OK | Tested 28 scenarios |
| script-runner | OK | Security constraints verified |
| aws-budget | SKIP | Requires AWS credentials |
| github-workflow | OK | Connected to GitHub API |

### Recommendations
- Consider running integration tests with `--run-integration`
- AWS credentials not configured for cost testing
```

## Scheduling Tests

### On Startup
```python
# In startup sequence
if os.environ.get("RUN_STARTUP_TESTS"):
    run_quick_smoke_tests()
```

### Periodic
```bash
# Via cron or CloudWatch Events
0 */6 * * * pytest tests/evals/ --tb=short -q
```

### On Demand
Trigger via conversation: "Run your tests"

## MCP Servers

None required for test execution itself. Individual tests may use MCP servers.

## Error Handling

### Test Infrastructure Failed
> "I couldn't run the tests: pytest not found. This suggests a dependency issue with the test framework."

### Many Failures
> "Multiple tests failed (15 of 45). This might indicate a systemic issue. Here are the most common errors: [list]. Should I investigate further?"

### Timeout
> "The tests are taking longer than expected (>5 minutes). I'll continue in the background and let you know when done."
