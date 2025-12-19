"""Configuration management for AIPA server."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    agent_name: str = Field(default="Blu", description="Name of the AI agent")
    agent_model: str = Field(
        default="claude-sonnet-4-5-20250514",
        description="Claude model to use (alias like 'sonnet' or full model ID)",
    )
    environment: Literal["development", "production"] = Field(default="development")
    log_level: str = Field(default="INFO")

    # Authentication
    auth_password_hash: str = Field(
        default="",
        description="Bcrypt hash of the login password",
    )
    session_secret: str = Field(
        default="change-me-in-production",
        description="Secret key for session signing",
    )

    # API Keys for MCP servers
    notion_api_key: str = Field(default="", description="Notion integration token")
    github_token: str = Field(default="", description="GitHub PAT")
    openai_api_key: str = Field(default="", description="OpenAI API key for VoiceMode")

    # LiveKit (for VoiceMode remote transport)
    livekit_url: str = Field(default="", description="LiveKit server URL (container internal)")
    livekit_api_key: str = Field(default="", description="LiveKit API key")
    livekit_api_secret: str = Field(default="", description="LiveKit API secret")
    livekit_browser_url: str = Field(
        default="",
        description="LiveKit URL for browser connections (falls back to livekit_url)",
    )

    # Paths
    workspace_path: str = Field(default="/workspace")

    # AWS / DynamoDB
    aws_region: str = Field(default="ap-southeast-2", description="AWS region")
    dynamodb_sessions_table: str = Field(
        default="",
        description="DynamoDB table name for session storage",
    )

    # Chat API (for testing/evaluation)
    enable_chat_api: bool = Field(
        default=False,
        description="Enable /api/chat endpoint (disabled in production by default)",
    )

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def has_session_storage(self) -> bool:
        """Check if DynamoDB session storage is configured."""
        return bool(self.dynamodb_sessions_table)

    @property
    def livekit_url_for_browser(self) -> str:
        """Get the LiveKit URL for browser connections.

        Uses livekit_browser_url if set, otherwise falls back to livekit_url.
        This allows running local LiveKit where container uses internal URL
        but browser needs localhost.
        """
        return self.livekit_browser_url or self.livekit_url


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
