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


@dataclass
class EvalResult:
    """Result of an agent evaluation."""

    test_name: str
    prompt: str
    response: str
    passed: bool
    criteria_met: dict[str, bool]
    latency_ms: float
    error: str | None = None


# ============================================================================
# Pytest Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def cleanup_registry() -> CleanupRegistry:
    """Get the cleanup registry for the test session."""
    return CleanupRegistry()


@pytest.fixture(scope="session")
def eval_config() -> dict:
    """Configuration for agent evaluations."""
    return {
        "api_endpoint": os.getenv("EVAL_API_ENDPOINT", "http://localhost:8000"),
        "timeout_seconds": int(os.getenv("EVAL_TIMEOUT", "60")),
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
    """Delete a Notion page. Returns True if successful."""
    # TODO: Implement using Notion MCP when available
    # For now, just log the cleanup request
    print(f"[CLEANUP] Would delete Notion page: {page_id}")
    return True


async def cleanup_github_repo(repo_name: str) -> bool:
    """Delete a GitHub repository. Returns True if successful."""
    # TODO: Implement using GitHub MCP
    print(f"[CLEANUP] Would delete GitHub repo: {repo_name}")
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


def pytest_collection_modifyitems(config, items):
    """Skip integration tests unless explicitly requested."""
    if not config.getoption("--run-integration", default=False):
        skip_integration = pytest.mark.skip(
            reason="Integration tests require --run-integration flag"
        )
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)


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
