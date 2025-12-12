"""Chat API endpoint for text-based agent interaction.

This endpoint allows sending text messages to the agent and receiving responses.
Used primarily for testing and evaluation purposes.

Security:
- Requires authentication via session cookie
- Can be disabled in production via ENABLE_CHAT_API=false
"""

import asyncio
import logging
import os
import uuid

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from server.config import get_settings
from server.services.auth import get_auth_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])


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


async def call_claude_code(
    prompt: str,
    *,
    model: str = "sonnet",
    session_id: str | None = None,
    oauth_token: str | None = None,
) -> str:
    """Call Claude Code CLI and return the response.

    Args:
        prompt: The user's message
        model: Model to use (sonnet, opus, etc.)
        session_id: Optional session ID for conversation continuity
        oauth_token: OAuth token for authentication

    Returns:
        The agent's response as a string
    """
    # Build CLI command
    cmd = ["claude", "-p", "--model", model, "--tools", ""]

    if session_id:
        cmd.extend(["--session-id", session_id])

    # Set up environment with OAuth token
    env = os.environ.copy()
    token = oauth_token or os.getenv("CLAUDE_CODE_OAUTH_TOKEN")
    if token:
        env["CLAUDE_CODE_OAUTH_TOKEN"] = token

    logger.info(f"Calling Claude Code CLI, prompt length: {len(prompt)}")

    try:
        # Pass prompt via stdin
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        # Write prompt to stdin and get response
        stdout, stderr = await process.communicate(input=prompt.encode("utf-8"))

        if process.returncode != 0:
            error_msg = stderr.decode("utf-8") if stderr else "Unknown error"
            logger.error(f"Claude Code CLI error: {error_msg}")
            raise RuntimeError(f"Agent error: {error_msg}")

        response = stdout.decode("utf-8").strip()
        logger.info(f"Claude Code response length: {len(response)}")
        return response

    except FileNotFoundError as e:
        raise RuntimeError(
            "Claude Code CLI not found. Ensure 'claude' is installed and in PATH."
        ) from e
    except Exception as e:
        logger.error(f"Error calling Claude Code CLI: {e}")
        raise


@router.post("/chat", response_model=ChatResponse)
async def chat(request: Request, body: ChatRequest) -> ChatResponse:
    """Send a text message to the agent and get a response.

    Requires authentication via session cookie.
    Can be disabled in production via ENABLE_CHAT_API=false.

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

    # Generate session ID if not provided
    session_id = body.session_id or str(uuid.uuid4())

    try:
        response = await call_claude_code(
            body.message,
            session_id=session_id,
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e

    return ChatResponse(response=response, session_id=session_id)
