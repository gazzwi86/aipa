"""Chat API endpoint for text-based agent interaction.

This endpoint allows sending text messages to the agent and receiving responses.
Used primarily for testing and evaluation purposes.

Security:
- Requires authentication via session cookie
- Can be disabled in production via ENABLE_CHAT_API=false
"""

import asyncio
import contextlib
import logging
import os
import uuid
from collections.abc import MutableMapping
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from server.config import get_settings
from server.services.auth import get_auth_service

logger = logging.getLogger(__name__)

# Simple in-memory session tracking
# Key: session_id, Value: (created_at, last_used)
# Sessions older than SESSION_TTL are considered new
SESSION_TTL = timedelta(hours=24)
_active_sessions: MutableMapping[str, tuple[datetime, datetime]] = {}

router = APIRouter(prefix="/api", tags=["chat"])


def _is_existing_session(session_id: str) -> bool:
    """Check if a session ID represents an existing conversation.

    Returns True if the session exists and hasn't expired.
    """
    if session_id not in _active_sessions:
        return False

    _created_at, last_used = _active_sessions[session_id]
    if datetime.now() - last_used > SESSION_TTL:
        # Session expired, remove it
        del _active_sessions[session_id]
        return False

    return True


def _register_session(session_id: str) -> None:
    """Register a new session or update last_used time for existing one."""
    now = datetime.now()
    if session_id in _active_sessions:
        created_at, _ = _active_sessions[session_id]
        _active_sessions[session_id] = (created_at, now)
    else:
        _active_sessions[session_id] = (now, now)


def _cleanup_expired_sessions() -> None:
    """Remove expired sessions from tracking."""
    now = datetime.now()
    expired = [
        sid for sid, (_, last_used) in _active_sessions.items() if now - last_used > SESSION_TTL
    ]
    for sid in expired:
        del _active_sessions[sid]


def _require_auth(request: Request) -> None:
    """Verify user is authenticated via session cookie."""
    auth = get_auth_service()
    token = request.cookies.get("aipa_session")
    if not token or not auth.verify_session(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )


class ChatRequest(BaseModel):
    """Request body for chat endpoint."""

    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    """Response body for chat endpoint."""

    response: str
    session_id: str


class CancellableClaudeProcess:
    """Wrapper for a cancellable Claude CLI process."""

    def __init__(self) -> None:
        self.process: asyncio.subprocess.Process | None = None
        self.cancelled = False

    async def cancel(self) -> None:
        """Cancel the running process."""
        self.cancelled = True
        if self.process and self.process.returncode is None:
            logger.info("Cancelling Claude Code CLI process due to client disconnect")
            try:
                self.process.terminate()
                try:
                    await asyncio.wait_for(self.process.wait(), timeout=2.0)
                except TimeoutError:
                    logger.warning("Process didn't terminate, killing forcefully")
                    self.process.kill()
            except ProcessLookupError:
                pass  # Process already ended


# Track active processes for cancellation on disconnect
_active_processes: dict[str, CancellableClaudeProcess] = {}


async def call_claude_code(
    prompt: str,
    *,
    model: str = "sonnet",
    session_id: str | None = None,
    oauth_token: str | None = None,
    working_dir: str | None = None,
    request_id: str | None = None,
) -> tuple[str, str]:
    """Call Claude Code CLI and return the response.

    Args:
        prompt: The user's message
        model: Model to use (sonnet, opus, etc.)
        session_id: Optional session ID for conversation continuity
        oauth_token: OAuth token for authentication
        working_dir: Working directory for Claude (defaults to /workspace)
        request_id: Optional ID for tracking/cancellation

    Returns:
        Tuple of (response text, session_id used)
    """
    # Generate session ID if not provided
    if not session_id:
        session_id = str(uuid.uuid4())

    # Create cancellable wrapper
    req_id = request_id or str(uuid.uuid4())
    wrapper = CancellableClaudeProcess()
    _active_processes[req_id] = wrapper

    # Build CLI command with dangerous mode for full tool access
    # Note: This is safe because:
    # 1. Endpoint requires authentication
    # 2. Agent runs in isolated container with limited filesystem access
    # 3. Only enabled in dev/testing via ENABLE_CHAT_API
    cmd = [
        "claude",
        "-p",
        "--model",
        model,
        "--dangerously-skip-permissions",  # YOLO mode - agent can use all tools
    ]

    # Add session management flags
    # --session-id for new sessions, --resume for continuing
    if _is_existing_session(session_id):
        cmd.extend(["--resume", session_id])
        logger.info(f"Resuming existing session: {session_id[:8]}...")
    else:
        cmd.extend(["--session-id", session_id])
        logger.info(f"Starting new session: {session_id[:8]}...")

    # Set up environment with OAuth token
    env = os.environ.copy()
    token = oauth_token or os.getenv("CLAUDE_CODE_OAUTH_TOKEN")
    if token:
        env["CLAUDE_CODE_OAUTH_TOKEN"] = token

    # Use /workspace by default to pick up production agent config
    cwd = working_dir or os.getenv("WORKSPACE", "/workspace")

    logger.info(f"Calling Claude Code CLI from {cwd}, prompt length: {len(prompt)}")

    try:
        # Pass prompt via stdin
        wrapper.process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            cwd=cwd,
        )

        # Check for early cancellation
        if wrapper.cancelled:
            wrapper.process.terminate()
            raise asyncio.CancelledError("Request cancelled before processing")

        # Write prompt to stdin and get response
        stdout, stderr = await wrapper.process.communicate(input=prompt.encode("utf-8"))

        # Check if cancelled during processing
        if wrapper.cancelled:
            raise asyncio.CancelledError("Request cancelled during processing")

        if wrapper.process.returncode != 0:
            error_msg = stderr.decode("utf-8") if stderr else "Unknown error"
            logger.error(f"Claude Code CLI error: {error_msg}")
            raise RuntimeError(f"Agent error: {error_msg}")

        response = stdout.decode("utf-8").strip()
        logger.info(f"Claude Code response length: {len(response)}")

        # Register session for future continuation
        _register_session(session_id)

        # Periodically clean up expired sessions
        _cleanup_expired_sessions()

        return response, session_id

    except FileNotFoundError as e:
        raise RuntimeError(
            "Claude Code CLI not found. Ensure 'claude' is installed and in PATH."
        ) from e
    except asyncio.CancelledError:
        logger.info(f"Request {req_id[:8]} was cancelled")
        raise
    except Exception as e:
        logger.error(f"Error calling Claude Code CLI: {e}")
        raise
    finally:
        # Clean up tracking
        _active_processes.pop(req_id, None)


async def cancel_request(request_id: str) -> None:
    """Cancel a running request by ID."""
    wrapper = _active_processes.get(request_id)
    if wrapper:
        await wrapper.cancel()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: Request, body: ChatRequest) -> ChatResponse:
    """Send a text message to the agent and get a response.

    Requires authentication via session cookie.
    Can be disabled in production via ENABLE_CHAT_API=false.
    Automatically cancels if client disconnects (browser closed/refreshed).

    Args:
        request: FastAPI request object
        body: Chat request with message and optional session_id

    Returns:
        ChatResponse with agent's response and session_id
    """
    settings = get_settings()

    # Check if endpoint is enabled
    if settings.is_production and not settings.enable_chat_api:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found",
        )

    # Require authentication
    _require_auth(request)

    # Generate request ID for cancellation tracking
    request_id = str(uuid.uuid4())

    # Start disconnect monitoring in background
    async def check_disconnect() -> None:
        """Monitor for client disconnect and cancel if needed."""
        while request_id in _active_processes:
            if await request.is_disconnected():
                logger.info(f"Client disconnected, cancelling request {request_id[:8]}")
                await cancel_request(request_id)
                break
            await asyncio.sleep(0.5)  # Check every 500ms

    disconnect_task = asyncio.create_task(check_disconnect())

    try:
        response, session_id = await call_claude_code(
            body.message,
            session_id=body.session_id,
            request_id=request_id,
        )
    except asyncio.CancelledError:
        raise HTTPException(
            status_code=499,  # Client Closed Request (nginx convention)
            detail="Request cancelled - client disconnected",
        ) from None
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e
    finally:
        # Stop disconnect monitoring
        disconnect_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await disconnect_task

    return ChatResponse(response=response, session_id=session_id)
