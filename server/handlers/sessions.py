"""Session management API endpoints."""

from fastapi import APIRouter, HTTPException, Query, Request, status

from server.models.sessions import (
    CreateSessionRequest,
    CreateSessionResponse,
    ForkSessionRequest,
    MessageRole,
    SendMessageRequest,
    SendMessageResponse,
    SessionDetail,
    SessionListResponse,
    UpdateSessionRequest,
)
from server.services.auth import get_auth_service
from server.services.session_namer import generate_session_name
from server.services.sessions import get_session_service

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def _require_auth(request: Request) -> None:
    """Verify user is authenticated via session cookie."""
    auth = get_auth_service()
    token = request.cookies.get("aipa_session")
    if not token or not auth.verify_session(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
) -> SessionListResponse:
    """List all sessions, most recent first."""
    _require_auth(request)

    service = get_session_service()
    sessions, next_cursor = await service.list_sessions(limit=limit, cursor=cursor)

    return SessionListResponse(sessions=sessions, next_cursor=next_cursor)


@router.post("", response_model=CreateSessionResponse)
async def create_session(
    request: Request,
    body: CreateSessionRequest,
) -> CreateSessionResponse:
    """Create a new session."""
    _require_auth(request)

    service = get_session_service()
    session = await service.create_session(name=body.name)

    return CreateSessionResponse(session=session)


@router.get("/{session_id}", response_model=SessionDetail)
async def get_session(
    request: Request,
    session_id: str,
) -> SessionDetail:
    """Get a session with all its messages."""
    _require_auth(request)

    service = get_session_service()
    session = await service.get_session(session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    return session


@router.delete("/{session_id}")
async def delete_session(
    request: Request,
    session_id: str,
) -> dict:
    """Delete a session and all its messages."""
    _require_auth(request)

    service = get_session_service()
    deleted = await service.delete_session(session_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    return {"success": True, "session_id": session_id}


@router.patch("/{session_id}")
async def update_session(
    request: Request,
    session_id: str,
    body: UpdateSessionRequest,
) -> dict:
    """Update session metadata (name, status)."""
    _require_auth(request)

    service = get_session_service()

    # Verify session exists
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    if body.name is not None:
        await service.update_session_name(session_id, body.name)

    # Note: status updates would go here if needed

    return {"success": True, "session_id": session_id}


@router.post("/{session_id}/messages", response_model=SendMessageResponse)
async def add_message(
    request: Request,
    session_id: str,
    body: SendMessageRequest,
) -> SendMessageResponse:
    """Add a message to a session.

    This is used for tracking messages in the session history.
    Actual AI processing happens via the voice/chat endpoints.
    """
    _require_auth(request)

    service = get_session_service()

    # Verify session exists
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    # Add the message
    message = await service.add_message(
        session_id=session_id,
        role=MessageRole.USER,
        content=body.content,
        source=body.source,
    )

    # Auto-generate name on first message if still default
    generated_name = None
    if session.name == "New Session" and session.message_count == 0:
        generated_name = await generate_session_name(body.content)
        await service.update_session_name(session_id, generated_name)

    return SendMessageResponse(message=message, session_name=generated_name)


@router.post("/{session_id}/fork", response_model=CreateSessionResponse)
async def fork_session(
    request: Request,
    session_id: str,
    body: ForkSessionRequest,
) -> CreateSessionResponse:
    """Fork a session (create a copy with message history)."""
    _require_auth(request)

    service = get_session_service()
    new_session = await service.fork_session(
        from_session_id=session_id,
        name=body.name,
    )

    if not new_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source session not found",
        )

    return CreateSessionResponse(session=new_session)


@router.get("/{session_id}/storage-mode")
async def get_storage_mode(request: Request, session_id: str) -> dict:
    """Get the current storage mode (persistent or in-memory)."""
    _require_auth(request)

    service = get_session_service()
    return {
        "persistent": service.is_persistent,
        "storage_type": "dynamodb" if service.is_persistent else "in-memory",
    }
