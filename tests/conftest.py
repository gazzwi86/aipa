"""Root conftest with shared fixtures for all tests."""

import os
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Set test environment variables before importing app
os.environ["ENVIRONMENT"] = "development"
os.environ["AGENT_NAME"] = "TestAgent"
os.environ["LOG_LEVEL"] = "WARNING"
os.environ["LIVEKIT_URL"] = ""  # Disable LiveKit for tests


@pytest.fixture(scope="session")
def temp_workspace() -> Generator[Path, None, None]:
    """Create a temporary workspace directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        (workspace / "files").mkdir(parents=True)
        yield workspace


@pytest.fixture
def test_settings(temp_workspace: Path):
    """Create test settings with temporary workspace."""
    import bcrypt

    os.environ["WORKSPACE_PATH"] = str(temp_workspace)
    # Create a valid bcrypt hash for 'testpass'
    password_hash = bcrypt.hashpw(b"testpass", bcrypt.gensalt()).decode("utf-8")
    os.environ["AUTH_PASSWORD_HASH"] = password_hash

    from server.config import get_settings
    from server.services import auth as auth_module

    # Clear the cached settings and auth service
    get_settings.cache_clear()
    auth_module._auth_service = None

    settings = get_settings()
    yield settings

    # Cleanup
    get_settings.cache_clear()
    auth_module._auth_service = None


@pytest.fixture
def client(test_settings) -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI app."""
    from server.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def authenticated_client(client: TestClient, test_settings) -> TestClient:
    """Create an authenticated test client."""
    # Login to get session cookie (response not needed, just need the side effect)
    client.post("/login", data={"password": "testpass"})
    # The cookie should be set automatically by TestClient
    return client
