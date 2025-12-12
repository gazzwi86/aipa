"""Authentication service with rate limiting."""

import secrets
import time
from dataclasses import dataclass, field

import bcrypt


@dataclass
class LoginAttempt:
    """Tracks login attempts for rate limiting."""

    attempts: int = 0
    locked_until: float = 0
    last_attempt: float = 0


@dataclass
class AuthService:
    """Authentication service with brute-force protection."""

    password_hash: str
    session_secret: str
    _attempts: dict[str, LoginAttempt] = field(default_factory=dict)
    _sessions: dict[str, float] = field(default_factory=dict)

    # Rate limiting config
    max_attempts: int = 5
    lockout_base: int = 60  # 1 minute base lockout
    lockout_max: int = 3600  # Max 1 hour lockout

    def _get_attempt(self, ip: str) -> LoginAttempt:
        """Get or create login attempt tracker for IP."""
        if ip not in self._attempts:
            self._attempts[ip] = LoginAttempt()
        return self._attempts[ip]

    def is_locked(self, ip: str) -> tuple[bool, int]:
        """Check if IP is locked out. Returns (locked, seconds_remaining)."""
        attempt = self._get_attempt(ip)
        now = time.time()

        if attempt.locked_until > now:
            return True, int(attempt.locked_until - now)

        return False, 0

    def check_password(self, password: str, ip: str) -> tuple[bool, str | None]:
        """
        Verify password with rate limiting.

        Returns (success, session_token or error_message).
        """
        locked, remaining = self.is_locked(ip)
        if locked:
            return False, f"Too many attempts. Try again in {remaining} seconds."

        attempt = self._get_attempt(ip)
        now = time.time()

        # Check if password hash is configured
        if not self.password_hash:
            return False, "Authentication not configured"

        # Verify password
        try:
            password_bytes = password.encode("utf-8")
            hash_bytes = self.password_hash.encode("utf-8")

            if bcrypt.checkpw(password_bytes, hash_bytes):
                # Success - reset attempts
                attempt.attempts = 0
                attempt.locked_until = 0

                # Create session token
                token = self._create_session()
                return True, token
        except Exception:
            pass

        # Failed attempt
        attempt.attempts += 1
        attempt.last_attempt = now

        if attempt.attempts >= self.max_attempts:
            # Exponential backoff: 1min, 2min, 4min, 8min, ... up to 1 hour
            lockout_time = min(
                self.lockout_base * (2 ** (attempt.attempts - self.max_attempts)),
                self.lockout_max,
            )
            attempt.locked_until = now + lockout_time
            return False, f"Too many attempts. Locked for {int(lockout_time)} seconds."

        remaining = self.max_attempts - attempt.attempts
        return False, f"Invalid password. {remaining} attempts remaining."

    def _create_session(self) -> str:
        """Create a new session token."""
        token = secrets.token_urlsafe(32)
        self._sessions[token] = time.time()
        return token

    def verify_session(self, token: str) -> bool:
        """Verify a session token is valid."""
        if not token or token not in self._sessions:
            return False

        # Sessions valid for 24 hours
        created = self._sessions[token]
        if time.time() - created > 86400:
            del self._sessions[token]
            return False

        return True

    def invalidate_session(self, token: str) -> None:
        """Invalidate a session token."""
        self._sessions.pop(token, None)


def hash_password(password: str) -> str:
    """Hash a password for storage."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


# Singleton instance
_auth_service: AuthService | None = None


def get_auth_service() -> AuthService:
    """Get the auth service singleton."""
    global _auth_service
    if _auth_service is None:
        from server.config import get_settings

        settings = get_settings()
        _auth_service = AuthService(
            password_hash=settings.auth_password_hash,
            session_secret=settings.session_secret,
        )
    return _auth_service
