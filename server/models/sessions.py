"""Session models for AIPA conversation management."""

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class MessageSource(str, Enum):
    """Source of a message (voice or text input)."""

    VOICE = "voice"
    TEXT = "text"


class MessageRole(str, Enum):
    """Role in the conversation."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class SessionStatus(str, Enum):
    """Status of a session."""

    ACTIVE = "active"
    ARCHIVED = "archived"


class SessionMessage(BaseModel):
    """A single message in a conversation session."""

    timestamp: datetime
    role: MessageRole
    content: str
    source: MessageSource = MessageSource.TEXT


class SessionArtifact(BaseModel):
    """An artifact (file) created during a session."""

    path: str
    created: datetime
    type: str  # MIME type
    size: int


class Session(BaseModel):
    """A conversation session."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(default="New Session")
    created: datetime = Field(default_factory=datetime.utcnow)
    updated: datetime = Field(default_factory=datetime.utcnow)
    status: SessionStatus = SessionStatus.ACTIVE
    message_count: int = 0
    artifacts: list[SessionArtifact] = Field(default_factory=list)
    preview: str = ""  # First ~100 chars of first user message


class SessionSummary(BaseModel):
    """Summary for session list (without full message history)."""

    id: str
    name: str
    created: datetime
    updated: datetime
    message_count: int
    preview: str


class SessionDetail(Session):
    """Full session with message history."""

    messages: list[SessionMessage] = Field(default_factory=list)


# =============================================================================
# API Request/Response Models
# =============================================================================


class CreateSessionRequest(BaseModel):
    """Request to create a new session."""

    name: str | None = None  # If None, auto-generate from first message


class CreateSessionResponse(BaseModel):
    """Response after creating a session."""

    session: Session


class SendMessageRequest(BaseModel):
    """Request to add a message to a session."""

    content: str
    source: MessageSource = MessageSource.TEXT


class SendMessageResponse(BaseModel):
    """Response after adding a message."""

    message: SessionMessage
    session_name: str | None = None  # Included if name was auto-generated


class ForkSessionRequest(BaseModel):
    """Request to fork (copy) an existing session."""

    name: str | None = None  # If None, use "Fork of {original_name}"


class UpdateSessionRequest(BaseModel):
    """Request to update session metadata."""

    name: str | None = None
    status: SessionStatus | None = None


class SessionListResponse(BaseModel):
    """Response for listing sessions."""

    sessions: list[SessionSummary]
    next_cursor: str | None = None  # For pagination
