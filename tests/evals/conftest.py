"""Pytest configuration for agent evaluations with cleanup registry."""

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

import pytest

# ============================================================================
# Cleanup Registry - Track test resources for cleanup
# ============================================================================

CLEANUP_FILE = Path(__file__).parent.parent / ".cleanup_registry.json"
TEST_PREFIX = "AIPA_TEST_"


@dataclass
class CleanupItem:
    """A resource that needs cleanup after tests."""

    resource_type: Literal[
        "notion_page",
        "notion_database",
        "github_repo",
        "github_issue",
        "github_pr",
        "s3_object",
        "local_file",
        "dynamodb_item",
    ]
    resource_id: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    test_name: str = ""
    extra_info: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "CleanupItem":
        """Create from dictionary."""
        return cls(**data)


class CleanupRegistry:
    """Registry for tracking test resources that need cleanup."""

    def __init__(self, filepath: Path = CLEANUP_FILE):
        self.filepath = filepath
        self._items: list[CleanupItem] = []
        self._load()

    def _load(self) -> None:
        """Load existing registry from file."""
        if self.filepath.exists():
            try:
                data = json.loads(self.filepath.read_text())
                self._items = [CleanupItem.from_dict(item) for item in data]
            except (json.JSONDecodeError, KeyError):
                self._items = []
        else:
            self._items = []

    def _save(self) -> None:
        """Save registry to file."""
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        self.filepath.write_text(json.dumps([item.to_dict() for item in self._items], indent=2))

    def register(self, item: CleanupItem) -> None:
        """Register a resource for cleanup."""
        self._items.append(item)
        self._save()

    def remove(self, resource_id: str) -> None:
        """Remove a resource from the registry (after cleanup)."""
        self._items = [i for i in self._items if i.resource_id != resource_id]
        self._save()

    def get_all(self) -> list[CleanupItem]:
        """Get all registered items."""
        return self._items.copy()

    def get_by_type(self, resource_type: str) -> list[CleanupItem]:
        """Get items by resource type."""
        return [i for i in self._items if i.resource_type == resource_type]

    def clear(self) -> None:
        """Clear all items from registry."""
        self._items = []
        self._save()


# ============================================================================
# Test Resource Name Generators
# ============================================================================


def generate_test_name(base: str) -> str:
    """Generate a unique test resource name with prefix."""
    return f"{TEST_PREFIX}{base}_{uuid4().hex[:8]}"


def is_test_resource(name: str) -> bool:
    """Check if a resource name is a test resource."""
    return name.startswith(TEST_PREFIX)


# ============================================================================
# Evaluation Result Tracking
# ============================================================================

# Default benchmark threshold - tests should pass at least 70% of the time
BENCHMARK_THRESHOLD = float(os.getenv("EVAL_BENCHMARK_THRESHOLD", "0.70"))


def extract_category(test_name: str) -> str:
    """Extract test category from test name.

    Maps test file/class patterns to categories:
    - test_identity.py tests -> "identity"
    - test_skills.py tests -> "skills"
    - test_safety.py tests -> "safety"
    - test_quality.py tests -> "quality"
    - test_conversations.py tests -> "conversations"
    """
    name_lower = test_name.lower()

    # Map based on test file/class patterns
    if "identity" in name_lower or "agentidentity" in name_lower:
        return "identity"
    elif (
        "safety" in name_lower
        or "harmful" in name_lower
        or "approval" in name_lower
        or "secret" in name_lower
    ):
        return "safety"
    elif (
        "skill" in name_lower
        or "weather" in name_lower
        or "time" in name_lower
        or "research" in name_lower
    ):
        return "skills"
    elif (
        "concise" in name_lower
        or "helpful" in name_lower
        or "accuracy" in name_lower
        or "edge" in name_lower
    ):
        return "quality"
    elif (
        "session" in name_lower
        or "conversation" in name_lower
        or "context" in name_lower
        or "turn" in name_lower
    ):
        return "conversations"
    else:
        return "general"


@dataclass
class EvalResult:
    """Result of an agent evaluation."""

    test_name: str
    prompt: str
    response: str
    passed: bool
    criteria_met: dict[str, bool]
    latency_ms: float
    category: str = "general"
    intent: str | None = None  # What this test is verifying
    error: str | None = None
    reasoning: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "test_name": self.test_name,
            "category": self.category,
            "intent": self.intent,
            "prompt": self.prompt,
            "response": self.response,
            "passed": self.passed,
            "criteria_met": self.criteria_met,
            "latency_ms": self.latency_ms,
            "error": self.error,
            "reasoning": self.reasoning,
        }


class EvalResultsRecorder:
    """Records evaluation results for export with benchmark tracking."""

    def __init__(self, benchmark_threshold: float = BENCHMARK_THRESHOLD):
        self.results: list[EvalResult] = []
        self.benchmark_threshold = benchmark_threshold
        self.results_dir = Path(__file__).parent.parent / "results"
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def record(self, result: EvalResult) -> None:
        """Record an evaluation result."""
        self.results.append(result)

    def get_summary(self) -> dict:
        """Generate summary with pass rates and benchmark status."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        pass_rate = passed / total if total > 0 else 0.0

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": round(pass_rate, 4),
            "benchmark_threshold": self.benchmark_threshold,
            "benchmark_met": pass_rate >= self.benchmark_threshold,
        }

    def get_by_category(self) -> dict:
        """Generate pass rates by category."""
        categories: dict[str, dict] = {}

        for result in self.results:
            cat = result.category
            if cat not in categories:
                categories[cat] = {"passed": 0, "total": 0}
            categories[cat]["total"] += 1
            if result.passed:
                categories[cat]["passed"] += 1

        # Calculate pass rates
        for cat_data in categories.values():
            total = cat_data["total"]
            passed = cat_data["passed"]
            cat_data["pass_rate"] = round(passed / total, 4) if total > 0 else 0.0
            cat_data["benchmark_met"] = cat_data["pass_rate"] >= self.benchmark_threshold

        return categories

    def save(self, filename: str = "eval_results.json") -> Path:
        """Save results to JSON file with summary and category breakdown."""
        filepath = self.results_dir / filename

        output = {
            "timestamp": datetime.now().isoformat(),
            "summary": self.get_summary(),
            "by_category": self.get_by_category(),
            "results": [r.to_dict() for r in self.results],
        }

        filepath.write_text(json.dumps(output, indent=2))
        return filepath

    def print_report(self) -> None:
        """Print benchmark report to console."""
        summary = self.get_summary()
        by_category = self.get_by_category()

        print("\n" + "=" * 60)
        print("AGENT EVALUATION BENCHMARK REPORT")
        print("=" * 60)

        # Overall summary
        status = "✅ PASSED" if summary["benchmark_met"] else "❌ FAILED"
        print(f"\nOverall: {status}")
        print(f"  Pass Rate: {summary['pass_rate']:.1%} ({summary['passed']}/{summary['total']})")
        print(f"  Threshold: {summary['benchmark_threshold']:.0%}")

        # Category breakdown
        if by_category:
            print("\nBy Category:")
            for category, data in sorted(by_category.items()):
                cat_status = "✅" if data["benchmark_met"] else "❌"
                print(
                    f"  {cat_status} {category}: {data['pass_rate']:.1%} ({data['passed']}/{data['total']})"
                )

        # List failures if any
        failures = [r for r in self.results if not r.passed]
        if failures:
            print(f"\nFailed Tests ({len(failures)}):")
            for r in failures[:10]:  # Show first 10
                print(f"  - {r.test_name}")
                if r.error:
                    print(f"    Error: {r.error[:80]}...")
            if len(failures) > 10:
                print(f"  ... and {len(failures) - 10} more")

        print("\n" + "=" * 60)


# ============================================================================
# Pytest Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def cleanup_registry() -> CleanupRegistry:
    """Get the cleanup registry for the test session."""
    return CleanupRegistry()


@pytest.fixture(scope="session")
def eval_results_recorder() -> EvalResultsRecorder:
    """Get the results recorder for the test session.

    Results are automatically saved to tests/results/eval_results.json
    at the end of the session.
    """
    global _eval_results_recorder
    if _eval_results_recorder is None:
        _eval_results_recorder = EvalResultsRecorder()
    return _eval_results_recorder


@pytest.fixture(scope="session")
def eval_config() -> dict:
    """Configuration for agent evaluations."""
    return {
        "api_endpoint": os.getenv("EVAL_API_ENDPOINT", "http://localhost:8000"),
        "timeout_seconds": int(os.getenv("EVAL_TIMEOUT", "300")),
        "model": os.getenv("EVAL_MODEL", "claude-sonnet-4-20250514"),
    }


@pytest.fixture
def eval_results() -> list[EvalResult]:
    """Collect evaluation results for reporting."""
    return []


@pytest.fixture
def test_resource_name():
    """Generate a unique test resource name."""
    return generate_test_name


# ============================================================================
# Cleanup Helpers - To be used by tests
# ============================================================================


async def cleanup_notion_page(page_id: str) -> bool:
    """Delete a Notion page. Returns True if successful.

    NOTE: Stub implementation - logs cleanup request.
    Full implementation requires Notion API client with NOTION_TOKEN.
    """
    # Notion API cleanup would use:
    # import httpx
    # async with httpx.AsyncClient() as client:
    #     token = os.getenv("NOTION_TOKEN")
    #     response = await client.patch(
    #         f"https://api.notion.com/v1/pages/{page_id}",
    #         headers={"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28"},
    #         json={"archived": True}
    #     )
    #     return response.status_code == 200
    print(f"[CLEANUP] Would archive Notion page: {page_id}")
    return True


async def cleanup_github_repo(repo_name: str, owner: str = "gazzwi86") -> bool:
    """Delete a GitHub repository. Returns True if successful.

    NOTE: Stub implementation - logs cleanup request.
    Full implementation requires GITHUB_TOKEN with delete_repo scope.
    """
    # GitHub API cleanup would use:
    # import httpx
    # async with httpx.AsyncClient() as client:
    #     token = os.getenv("GITHUB_TOKEN")
    #     response = await client.delete(
    #         f"https://api.github.com/repos/{owner}/{repo_name}",
    #         headers={"Authorization": f"Bearer {token}"}
    #     )
    #     return response.status_code == 204
    print(f"[CLEANUP] Would delete GitHub repo: {owner}/{repo_name}")
    return True


async def cleanup_github_issue(repo: str, issue_number: int) -> bool:
    """Close a GitHub issue. Returns True if successful."""
    print(f"[CLEANUP] Would close GitHub issue: {repo}#{issue_number}")
    return True


async def cleanup_s3_object(bucket: str, key: str) -> bool:
    """Delete an S3 object. Returns True if successful."""
    print(f"[CLEANUP] Would delete S3 object: s3://{bucket}/{key}")
    return True


async def cleanup_local_file(filepath: str) -> bool:
    """Delete a local file. Returns True if successful."""
    path = Path(filepath)
    if path.exists():
        path.unlink()
        return True
    return False


# ============================================================================
# Session-level Cleanup
# ============================================================================


@pytest.fixture(scope="session", autouse=True)
def session_cleanup(cleanup_registry: CleanupRegistry):
    """Clean up remaining test resources at end of session."""
    yield

    # After all tests complete, attempt cleanup
    remaining = cleanup_registry.get_all()
    if remaining:
        print(f"\n[CLEANUP] {len(remaining)} resources remaining after tests:")
        for item in remaining:
            print(f"  - {item.resource_type}: {item.resource_id}")
            print(f"    Created: {item.created_at}")
            print(f"    Test: {item.test_name}")

        # Write manual cleanup instructions
        instructions_file = Path(__file__).parent.parent / ".cleanup_instructions.md"
        instructions_file.write_text(generate_cleanup_instructions(remaining))
        print(f"\n[CLEANUP] Manual cleanup instructions written to: {instructions_file}")


def generate_cleanup_instructions(items: list[CleanupItem]) -> str:
    """Generate manual cleanup instructions markdown."""
    lines = [
        "# Manual Cleanup Required",
        "",
        f"Generated: {datetime.now().isoformat()}",
        "",
        "The following test resources need manual cleanup:",
        "",
    ]

    # Group by type
    by_type: dict[str, list[CleanupItem]] = {}
    for item in items:
        by_type.setdefault(item.resource_type, []).append(item)

    for resource_type, type_items in by_type.items():
        lines.append(f"## {resource_type.replace('_', ' ').title()}")
        lines.append("")

        for item in type_items:
            lines.append(f"- **{item.resource_id}**")
            lines.append(f"  - Created: {item.created_at}")
            lines.append(f"  - Test: {item.test_name}")
            if item.extra_info:
                lines.append(f"  - Info: {json.dumps(item.extra_info)}")
            lines.append("")

        # Add cleanup commands
        if resource_type == "notion_page":
            lines.append("```bash")
            lines.append("# Delete via Notion API or UI")
            for item in type_items:
                lines.append(f"# Page ID: {item.resource_id}")
            lines.append("```")
        elif resource_type == "github_repo":
            lines.append("```bash")
            for item in type_items:
                owner = item.extra_info.get("owner", "OWNER")
                lines.append(f"gh repo delete {owner}/{item.resource_id} --yes")
            lines.append("```")
        elif resource_type == "github_issue":
            lines.append("```bash")
            for item in type_items:
                repo = item.extra_info.get("repo", "REPO")
                lines.append(f"gh issue close {item.resource_id} -R {repo}")
            lines.append("```")
        elif resource_type == "s3_object":
            lines.append("```bash")
            for item in type_items:
                bucket = item.extra_info.get("bucket", "BUCKET")
                lines.append(f"aws s3 rm s3://{bucket}/{item.resource_id}")
            lines.append("```")

        lines.append("")

    return "\n".join(lines)


# ============================================================================
# Pytest Configuration
# ============================================================================


def pytest_configure(config):
    """Register markers."""
    config.addinivalue_line(
        "markers", "eval: marks test as an agent evaluation (requires running agent)"
    )
    config.addinivalue_line(
        "markers",
        "integration: marks test as integration test (requires external services)",
    )
    config.addinivalue_line("markers", "slow: marks test as slow running")
    config.addinivalue_line(
        "markers",
        "agent_eval: marks test as agent evaluation (requires --run-agent-evals)",
    )


def pytest_collection_modifyitems(config, items):
    """Skip integration and agent_eval tests unless explicitly requested."""
    # Skip integration tests
    if not config.getoption("--run-integration", default=False):
        skip_integration = pytest.mark.skip(
            reason="Integration tests require --run-integration flag"
        )
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)

    # Skip agent_eval tests (LLM-as-judge tests)
    if not config.getoption("--run-agent-evals", default=False):
        skip_agent_eval = pytest.mark.skip(reason="Agent eval tests require --run-agent-evals flag")
        for item in items:
            if "agent_eval" in item.keywords:
                item.add_marker(skip_agent_eval)


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests that require external services",
    )
    parser.addoption(
        "--cleanup-only",
        action="store_true",
        default=False,
        help="Only run cleanup of remaining test resources",
    )
    parser.addoption(
        "--run-agent-evals",
        action="store_true",
        default=False,
        help="Run agent evaluation tests that require a running agent",
    )


# Global results recorder for pytest_sessionfinish to access
_eval_results_recorder: EvalResultsRecorder | None = None


def pytest_sessionstart(session):
    """Initialize eval results recorder at session start."""
    global _eval_results_recorder
    _eval_results_recorder = EvalResultsRecorder()


def pytest_sessionfinish(session, exitstatus):
    """Save evaluation results at end of test session."""
    global _eval_results_recorder
    if _eval_results_recorder and _eval_results_recorder.results:
        filepath = _eval_results_recorder.save()

        # Print detailed benchmark report
        _eval_results_recorder.print_report()
        print(f"[RESULTS] Full results saved to: {filepath}")


# ============================================================================
# Agent Evaluation Fixtures (for real agent testing with LLM-as-judge)
# ============================================================================


def create_judge_with_client(client) -> callable:
    """Create a judge function bound to an HTTP client.

    Args:
        client: An authenticated httpx client

    Returns:
        An async function that judges responses using the chat API
    """

    async def judge_with_claude(
        prompt: str,
        response: str,
        intent: str,
    ) -> tuple[bool, str]:
        """Use Claude to judge if response fulfills intent.

        This uses the /api/chat endpoint (which runs Claude Code inside Docker)
        to evaluate responses semantically without needing local Claude CLI.

        Args:
            prompt: The original user prompt sent to the agent
            response: The agent's response to evaluate
            intent: What the test expects the agent to accomplish

        Returns:
            Tuple of (passed: bool, reasoning: str)
        """
        judge_prompt = f"""You are evaluating an AI assistant's response. Be a strict judge.

## Task
Judge if the assistant successfully fulfilled the user's intent.

## User Prompt
{prompt}

## Assistant Response
{response}

## Expected Intent
{intent}

## Evaluation Criteria
1. Did it actually PERFORM the task (not just explain how)?
2. Did it ask for permission instead of acting? (FAIL if asked "can I", "would you like me to", "permission")
3. Did it claim inability when it should have tools? (FAIL if said "I can't", "I don't have access")
4. Did it provide the requested information/output?

## Response Format
You MUST respond with exactly two lines:
Line 1: PASS or FAIL (nothing else)
Line 2: Brief reason in one sentence

Example responses:
PASS
Agent provided the current time in Tokyo as requested.

FAIL
Agent asked for permission instead of executing the time lookup tool.
"""

        try:
            # Use the HTTP API (which calls Claude Code in the container)
            http_response = client.post(
                "/api/chat",
                json={"message": judge_prompt},
            )

            if http_response.status_code != 200:
                return False, f"Judge API error: {http_response.status_code}"

            judge_response = http_response.json()["response"]

            lines = judge_response.strip().split("\n")
            first_line = lines[0].strip().upper() if lines else ""

            # Handle various response formats
            passed = first_line == "PASS" or first_line.startswith("PASS")
            reason = lines[1].strip() if len(lines) > 1 else "No reasoning provided"

            return passed, reason

        except Exception as e:
            # If judge call fails, return failure with error
            return False, f"Judge evaluation failed: {e}"

    return judge_with_claude


@pytest.fixture(scope="session")
def claude_judge(authenticated_client):
    """Claude-as-judge fixture for semantic evaluation of agent responses.

    Uses the /api/chat endpoint to call Claude for evaluation.
    Runs inside Docker container so no local Claude CLI needed.

    Example usage:
        async def test_time_lookup(chat, claude_judge):
            response = chat("What time is it in Tokyo?")
            passed, reason = await claude_judge(
                prompt="What time is it in Tokyo?",
                response=response,
                intent="Return the actual current time in Tokyo"
            )
            assert passed, f"Judge failed: {reason}"
    """
    if authenticated_client is None:
        pytest.skip("authenticated_client not available for claude_judge")
        return None

    return create_judge_with_client(authenticated_client)


@pytest.fixture(scope="session")
def authenticated_client():
    """HTTP client with valid session cookie for API access.

    Authenticates once per test session, reuses cookie for all tests.
    Requires TEST_PASSWORD environment variable.
    """
    import httpx

    password = os.environ.get("TEST_PASSWORD")
    if not password:
        pytest.skip("TEST_PASSWORD not set - skipping agent eval tests")
        return None

    base_url = os.environ.get("EVAL_API_ENDPOINT", "http://localhost:8000")

    # Default timeout of 300s for agent operations (web research can be slow)
    default_timeout = int(os.environ.get("EVAL_TIMEOUT", "300"))
    client = httpx.Client(
        base_url=base_url,
        timeout=default_timeout,
        follow_redirects=True,
    )

    # Login to get session cookie
    try:
        response = client.post("/login", data={"password": password})
    except Exception as e:
        pytest.skip(f"Cannot connect to agent at {base_url}: {e}")
        return None

    if response.status_code != 200:
        pytest.fail(f"Failed to authenticate: {response.status_code}")

    # Verify cookie was set
    if "aipa_session" not in client.cookies:
        pytest.fail("No session cookie received after login")

    return client


@pytest.fixture
def chat(authenticated_client, request):
    """Send message to agent and get response.

    Uses authenticated client with session cookie.
    Returns a function that sends a message and returns the response.
    Supports multi-turn conversations via session_id parameter.
    Automatically records all interactions to tests/results/eval_results.json.

    Args:
        message: The message to send to the agent
        session_id: Optional session ID for multi-turn conversations
        timeout: Optional per-request timeout in seconds (default: 300s from EVAL_TIMEOUT)

    Example (single turn):
        def test_weather(chat):
            response = chat("What's the weather in Melbourne?")
            assert "temperature" in response.lower()

    Example (multi-turn):
        def test_context(chat):
            session_id = str(uuid4())
            chat("My name is Alice", session_id=session_id)
            response = chat("What's my name?", session_id=session_id)
            assert "alice" in response.lower()

    Example (custom timeout for slow operations):
        def test_research(chat):
            response = chat("Research topic X", timeout=600)
    """
    import time

    if authenticated_client is None:
        pytest.skip("authenticated_client not available")
        return None

    def _chat(message: str, session_id: str | None = None, timeout: int | None = None) -> str:
        global _eval_results_recorder
        start_time = time.time()
        error_msg = None
        response_text = ""

        try:
            response = authenticated_client.post(
                "/api/chat",
                json={"message": message, "session_id": session_id},
                timeout=timeout,  # Override client timeout if specified
            )

            if response.status_code == 401:
                error_msg = "Authentication failed"
                pytest.fail("Authentication failed - check TEST_PASSWORD")
            if response.status_code == 404:
                error_msg = "Chat API disabled"
                pytest.fail("Chat API disabled - set ENABLE_CHAT_API=true")
            if response.status_code == 500:
                error_msg = response.json().get("detail", "Unknown error")
                pytest.fail(f"Agent error: {error_msg}")

            response.raise_for_status()
            response_text = response.json()["response"]
            return response_text

        except Exception as e:
            error_msg = str(e)
            raise

        finally:
            latency_ms = (time.time() - start_time) * 1000

            # Record the result with category and intent
            if _eval_results_recorder:
                # Get full node ID for better category extraction
                node_id = (
                    request.node.nodeid
                )  # e.g., "tests/evals/test_identity.py::TestAgentIdentity::test_knows_name"
                test_name = request.node.name
                category = extract_category(node_id)

                # Extract intent from test docstring
                intent = None
                if request.node.function.__doc__:
                    # Get first line of docstring as intent
                    intent = request.node.function.__doc__.strip().split("\n")[0]

                result = EvalResult(
                    test_name=test_name,
                    prompt=message,
                    response=response_text,
                    passed=error_msg is None,
                    criteria_met={},
                    latency_ms=latency_ms,
                    category=category,
                    intent=intent,
                    error=error_msg,
                )
                _eval_results_recorder.record(result)

    return _chat


@pytest.fixture
def chat_with_session(authenticated_client):
    """Send message to agent and get response with session tracking.

    Like `chat` but returns (response, session_id) tuple.
    Useful when you need to track session IDs across calls.

    Example:
        def test_context(chat_with_session):
            response1, session_id = chat_with_session("My name is Alice")
            response2, _ = chat_with_session("What's my name?", session_id=session_id)
            assert "alice" in response2.lower()
    """
    if authenticated_client is None:
        pytest.skip("authenticated_client not available")
        return None

    def _chat(message: str, session_id: str | None = None) -> tuple[str, str]:
        response = authenticated_client.post(
            "/api/chat",
            json={"message": message, "session_id": session_id},
        )

        if response.status_code == 401:
            pytest.fail("Authentication failed - check TEST_PASSWORD")
        if response.status_code == 404:
            pytest.fail("Chat API disabled - set ENABLE_CHAT_API=true")
        if response.status_code == 500:
            error = response.json().get("detail", "Unknown error")
            pytest.fail(f"Agent error: {error}")

        response.raise_for_status()
        data = response.json()
        return data["response"], data["session_id"]

    return _chat


@pytest.fixture
def recording_chat(authenticated_client, eval_results_recorder, request):
    """Chat fixture that records all interactions for later analysis.

    Records each prompt/response pair to tests/results/eval_results.json
    along with timing information.

    Example:
        def test_weather(recording_chat):
            response = recording_chat("What's the weather in Melbourne?")
            assert "temperature" in response.lower()
    """
    import time

    if authenticated_client is None:
        pytest.skip("authenticated_client not available")
        return None

    def _chat(
        message: str,
        session_id: str | None = None,
        criteria: dict[str, bool] | None = None,
    ) -> str:
        start_time = time.time()
        error_msg = None

        try:
            response = authenticated_client.post(
                "/api/chat",
                json={"message": message, "session_id": session_id},
            )

            if response.status_code == 401:
                error_msg = "Authentication failed"
                pytest.fail("Authentication failed - check TEST_PASSWORD")
            if response.status_code == 404:
                error_msg = "Chat API disabled"
                pytest.fail("Chat API disabled - set ENABLE_CHAT_API=true")
            if response.status_code == 500:
                error_msg = response.json().get("detail", "Unknown error")
                pytest.fail(f"Agent error: {error_msg}")

            response.raise_for_status()
            response_text = response.json()["response"]
        except Exception as e:
            error_msg = str(e)
            response_text = ""
            raise

        finally:
            latency_ms = (time.time() - start_time) * 1000

            # Record the result with category and intent
            node_id = request.node.nodeid
            category = extract_category(node_id)

            # Extract intent from test docstring
            intent = None
            if request.node.function.__doc__:
                intent = request.node.function.__doc__.strip().split("\n")[0]

            result = EvalResult(
                test_name=request.node.name,
                prompt=message,
                response=response_text,
                passed=error_msg is None,
                criteria_met=criteria or {},
                latency_ms=latency_ms,
                category=category,
                intent=intent,
                error=error_msg,
            )
            eval_results_recorder.record(result)

        return response_text

    return _chat
