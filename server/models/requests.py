"""Request and response models for AIPA."""

from datetime import datetime

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(default="healthy")
    agent_name: str
    environment: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = Field(default="0.1.0")


class LoginRequest(BaseModel):
    """Login request."""

    password: str = Field(..., description="Login password")


class FileInfo(BaseModel):
    """Information about a file in the workspace."""

    name: str
    path: str
    size: int
    modified: datetime
    is_dir: bool
