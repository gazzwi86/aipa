"""Unit tests for the auth service and endpoints."""

import pytest
from fastapi.testclient import TestClient

from server.services.auth import AuthService, hash_password


class TestAuthService:
    """Tests for the AuthService class."""

    @pytest.fixture
    def auth_service(self):
        """Create an AuthService with a known password."""
        password_hash = hash_password("testpassword")
        return AuthService(
            password_hash=password_hash,
            session_secret="testsecret",
        )

    def test_check_password_correct(self, auth_service: AuthService):
        """Test correct password verification."""
        success, result = auth_service.check_password("testpassword", "127.0.0.1")
        assert success is True
        assert result is not None
        assert len(result) > 0

    def test_check_password_incorrect(self, auth_service: AuthService):
        """Test incorrect password verification."""
        success, result = auth_service.check_password("wrongpassword", "127.0.0.1")
        assert success is False
        assert "Invalid password" in result
        assert "attempts remaining" in result

    def test_rate_limiting_after_max_attempts(self, auth_service: AuthService):
        """Test rate limiting kicks in after max attempts."""
        ip = "192.168.1.1"

        # Make max_attempts failed attempts
        for _ in range(auth_service.max_attempts):
            success, _ = auth_service.check_password("wrong", ip)
            assert success is False

        # Next attempt should be locked
        success, result = auth_service.check_password("wrong", ip)
        assert success is False
        assert "Locked" in result or "Too many" in result

    def test_rate_limiting_different_ips(self, auth_service: AuthService):
        """Test that rate limiting is per-IP."""
        ip1 = "192.168.1.1"
        ip2 = "192.168.1.2"

        # Lock out ip1
        for _ in range(auth_service.max_attempts + 1):
            auth_service.check_password("wrong", ip1)

        # ip2 should still work
        success, _ = auth_service.check_password("wrong", ip2)
        assert success is False
        assert "Invalid password" in auth_service.check_password("wrong", ip2)[1]

    def test_successful_login_resets_attempts(self, auth_service: AuthService):
        """Test that successful login resets attempt counter."""
        ip = "192.168.1.1"

        # Make some failed attempts
        for _ in range(3):
            auth_service.check_password("wrong", ip)

        # Successful login
        success, _ = auth_service.check_password("testpassword", ip)
        assert success is True

        # Should have full attempts again
        success, result = auth_service.check_password("wrong", ip)
        assert f"{auth_service.max_attempts - 1} attempts remaining" in result

    def test_session_creation(self, auth_service: AuthService):
        """Test session token is created on successful login."""
        success, token = auth_service.check_password("testpassword", "127.0.0.1")
        assert success is True
        assert auth_service.verify_session(token) is True

    def test_session_verification_invalid(self, auth_service: AuthService):
        """Test invalid session tokens are rejected."""
        assert auth_service.verify_session("invalid_token") is False
        assert auth_service.verify_session("") is False
        assert auth_service.verify_session(None) is False

    def test_session_invalidation(self, auth_service: AuthService):
        """Test session invalidation."""
        success, token = auth_service.check_password("testpassword", "127.0.0.1")
        assert auth_service.verify_session(token) is True

        auth_service.invalidate_session(token)
        assert auth_service.verify_session(token) is False

    def test_is_locked_returns_remaining_time(self, auth_service: AuthService):
        """Test is_locked returns remaining lockout time."""
        ip = "192.168.1.100"

        # Lock the IP
        for _ in range(auth_service.max_attempts + 1):
            auth_service.check_password("wrong", ip)

        locked, remaining = auth_service.is_locked(ip)
        assert locked is True
        assert remaining > 0


class TestHashPassword:
    """Tests for the hash_password function."""

    def test_hash_password_returns_string(self):
        """Test hash_password returns a string."""
        result = hash_password("mypassword")
        assert isinstance(result, str)
        assert result.startswith("$2b$")

    def test_hash_password_different_each_time(self):
        """Test hash_password produces different hashes (due to salt)."""
        hash1 = hash_password("mypassword")
        hash2 = hash_password("mypassword")
        assert hash1 != hash2


class TestAuthEndpoints:
    """Tests for auth-related API endpoints."""

    def test_login_page_loads(self, client: TestClient):
        """Test login page is accessible."""
        response = client.get("/login")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        assert "Login" in response.text

    def test_login_with_correct_password(self, client: TestClient, test_settings):
        """Test login with correct password."""
        response = client.post(
            "/login",
            data={"password": "testpass"},
            follow_redirects=False,
        )
        # Should redirect to home
        assert response.status_code == 302
        assert response.headers.get("location") == "/"

    def test_login_with_wrong_password(self, client: TestClient, test_settings):
        """Test login with wrong password shows error."""
        response = client.post(
            "/login",
            data={"password": "wrongpassword"},
        )
        assert response.status_code == 200
        assert "Invalid password" in response.text

    def test_logout_clears_session(self, authenticated_client: TestClient):
        """Test logout clears session."""
        # Should be able to access protected page
        response = authenticated_client.get("/")
        assert response.status_code == 200

        # Logout
        response = authenticated_client.get("/logout", follow_redirects=False)
        assert response.status_code == 302

        # Should be redirected to login now (need new client to clear cookies)
        response = authenticated_client.get("/", follow_redirects=False)
        # After logout, should redirect to login
        assert response.status_code == 302

    def test_protected_route_requires_auth(self, client: TestClient):
        """Test that protected routes require authentication."""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers.get("location", "")


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_check(self, client: TestClient):
        """Test health endpoint returns correct data."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "agent_name" in data
        assert "environment" in data
        assert "timestamp" in data
