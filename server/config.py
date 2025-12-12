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
    agent_name: str = Field(default="Ultra", description="Name of the AI agent")
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
    livekit_url: str = Field(default="", description="LiveKit server URL")
    livekit_api_key: str = Field(default="", description="LiveKit API key")
    livekit_api_secret: str = Field(default="", description="LiveKit API secret")

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


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
