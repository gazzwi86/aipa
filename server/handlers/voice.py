"""Voice handlers for LiveKit token generation."""

import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from server.config import Settings, get_settings
from server.services.auth import get_auth_service

router = APIRouter()


class TokenResponse(BaseModel):
    """LiveKit connection token response."""

    token: str
    url: str
    room: str


class ConnectionInfo(BaseModel):
    """Connection info for the voice UI."""

    configured: bool
    url: str
    room: str
    message: str


def get_session_token(request: Request) -> str | None:
    """Get session token from cookie."""
    return request.cookies.get("aipa_session")


@router.get("/api/voice/info", response_model=ConnectionInfo)
async def voice_info(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> ConnectionInfo:
    """Get voice connection info."""
    # Check auth
    auth = get_auth_service()
    token = get_session_token(request)
    if not token or not auth.verify_session(token):
        return ConnectionInfo(
            configured=False,
            url="",
            room="",
            message="Not authenticated",
        )

    if not settings.livekit_url or not settings.livekit_api_key:
        return ConnectionInfo(
            configured=False,
            url="",
            room="",
            message="LiveKit not configured. Set LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET in .env",
        )

    return ConnectionInfo(
        configured=True,
        url=settings.livekit_url_for_browser,
        room="voice-ultra",  # Default room name
        message="Ready",
    )


@router.get("/api/voice/token", response_model=TokenResponse)
async def get_voice_token(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    """Generate a LiveKit access token for the browser client."""
    # Check auth
    auth = get_auth_service()
    session = get_session_token(request)
    if not session or not auth.verify_session(session):
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    if not settings.livekit_url or not settings.livekit_api_key or not settings.livekit_api_secret:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LiveKit not configured",
        )

    # Import here to avoid startup errors if livekit not installed
    try:
        from livekit.api import AccessToken, VideoGrants
    except ImportError:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LiveKit SDK not installed",
        ) from None

    room_name = "voice-ultra"
    participant_name = f"user-{secrets.token_hex(4)}"

    # Create access token
    token = AccessToken(
        api_key=settings.livekit_api_key,
        api_secret=settings.livekit_api_secret,
    )
    token.with_identity(participant_name)
    token.with_name("User")
    token.with_ttl(timedelta(hours=1))
    token.with_grants(
        VideoGrants(
            room_join=True,
            room=room_name,
            can_publish=True,
            can_subscribe=True,
        )
    )

    jwt_token = token.to_jwt()

    return TokenResponse(
        token=jwt_token,
        url=settings.livekit_url_for_browser,
        room=room_name,
    )
