"""Custom LLM plugin for LiveKit that uses Claude Code CLI.

This allows the voice agent to use Claude Pro/Max subscription via the OAuth token
instead of requiring a separate ANTHROPIC_API_KEY.
"""

import asyncio
import logging
import os
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from livekit.agents.llm import (
    LLM,
    ChatChunk,
    ChatContext,
    ChoiceDelta,
    LLMStream,
)
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS, APIConnectOptions

logger = logging.getLogger(__name__)


@dataclass
class ClaudeCodeLLMOptions:
    """Configuration options for Claude Code LLM."""

    model: str = "sonnet"  # sonnet, opus, or full model name
    oauth_token: str | None = None
    system_prompt: str | None = None
    session_id: str | None = None  # For session continuity across calls


class ClaudeCodeLLMStream(LLMStream):
    """Stream responses from Claude Code CLI."""

    def __init__(
        self,
        llm: "ClaudeCodeLLM",
        *,
        chat_ctx: ChatContext,
        conn_options: APIConnectOptions,
        options: ClaudeCodeLLMOptions,
    ) -> None:
        super().__init__(llm, chat_ctx=chat_ctx, tools=[], conn_options=conn_options)
        self._options = options
        self._request_id = str(uuid.uuid4())

    async def _run(self) -> None:
        """Execute the Claude Code CLI and stream results."""
        # Build the prompt from chat context
        messages = []
        logger.debug(f"Chat context has {len(self._chat_ctx.items)} items")

        for msg in self._chat_ctx.items:
            logger.debug(f"Message type: {type(msg)}, attrs: {dir(msg)[:10]}...")
            role = None
            content = ""

            # Try to get role
            if hasattr(msg, "role"):
                role = str(msg.role.value) if hasattr(msg.role, "value") else str(msg.role)

            # Try to get content
            if hasattr(msg, "content"):
                if isinstance(msg.content, str):
                    content = msg.content
                elif isinstance(msg.content, list):
                    # Handle content blocks
                    for block in msg.content:
                        if hasattr(block, "text"):
                            content += block.text
                        elif isinstance(block, str):
                            content += block
                        elif hasattr(block, "content"):
                            content += str(block.content)
            elif hasattr(msg, "text"):
                content = msg.text

            if role and content:
                messages.append(f"{role}: {content}")
            elif content:
                messages.append(content)

        # Get the last user message as the primary prompt
        prompt = "\n".join(messages) if messages else ""

        if not prompt:
            logger.warning("No prompt content found in chat context")
            # Emit an empty response
            chunk = ChatChunk(
                id=self._request_id,
                delta=ChoiceDelta(
                    role="assistant", content="I didn't catch that. Could you repeat?"
                ),
            )
            self._event_ch.send_nowait(chunk)
            return

        logger.info(f"Prompt for Claude: {prompt[:100]}...")

        # Build CLI command - use stdin for prompt to handle special characters
        # Using text output mode (no --output-format) since stream-json requires --verbose
        # which tries to write debug files
        cmd = ["claude", "-p"]

        if self._options.model:
            cmd.extend(["--model", self._options.model])

        if self._options.system_prompt:
            cmd.extend(["--system-prompt", self._options.system_prompt])

        # Disable tools for voice - we just want text responses
        cmd.extend(["--tools", ""])

        # Session ID for continuity across calls
        if self._options.session_id:
            cmd.extend(["--session-id", self._options.session_id])

        # Set up environment with OAuth token
        env = os.environ.copy()
        if self._options.oauth_token:
            env["CLAUDE_CODE_OAUTH_TOKEN"] = self._options.oauth_token

        logger.info(f"Running Claude Code CLI, prompt length: {len(prompt)}")

        try:
            # Pass prompt via stdin to handle special characters and newlines
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )

            # Write prompt to stdin and close it
            process.stdin.write(prompt.encode("utf-8"))
            await process.stdin.drain()
            process.stdin.close()
            await process.stdin.wait_closed()

            # Read plain text output line by line and stream as chunks
            async for line in self._read_lines(process.stdout):
                if line:
                    chunk = ChatChunk(
                        id=self._request_id,
                        delta=ChoiceDelta(
                            role="assistant",
                            content=line,
                        ),
                    )
                    self._event_ch.send_nowait(chunk)

            # Wait for process to complete
            await process.wait()

            if process.returncode != 0:
                stderr = await process.stderr.read()
                logger.error(f"Claude Code CLI error: {stderr.decode()}")

        except Exception as e:
            logger.error(f"Error running Claude Code CLI: {e}")
            raise

    async def _read_lines(self, stream: asyncio.StreamReader | None) -> AsyncIterator[str]:
        """Read lines from stream asynchronously."""
        if not stream:
            return
        while True:
            line = await stream.readline()
            if not line:
                break
            yield line.decode("utf-8")


class ClaudeCodeLLM(LLM):
    """LLM implementation using Claude Code CLI.

    This uses the Claude Code CLI with a long-lived OAuth token to access
    Claude Pro/Max subscription without requiring an API key.
    """

    def __init__(
        self,
        *,
        model: str = "sonnet",
        oauth_token: str | None = None,
        system_prompt: str | None = None,
        session_id: str | None = None,
    ) -> None:
        """Initialize Claude Code LLM.

        Args:
            model: Model alias (sonnet, opus) or full model name
            oauth_token: OAuth token from `claude setup-token`. If not provided,
                        uses CLAUDE_CODE_OAUTH_TOKEN environment variable.
            system_prompt: Optional system prompt for the conversation
            session_id: Optional session ID for conversation continuity
        """
        super().__init__()
        self._options = ClaudeCodeLLMOptions(
            model=model,
            oauth_token=oauth_token or os.getenv("CLAUDE_CODE_OAUTH_TOKEN"),
            system_prompt=system_prompt,
            session_id=session_id,
        )

        if not self._options.oauth_token:
            raise ValueError(
                "OAuth token required. Set CLAUDE_CODE_OAUTH_TOKEN environment variable "
                "or pass oauth_token parameter. Generate with: claude setup-token"
            )

    @property
    def model(self) -> str:
        return self._options.model

    @property
    def provider(self) -> str:
        return "claude-code"

    def chat(
        self,
        *,
        chat_ctx: ChatContext,
        tools: Any = None,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
        parallel_tool_calls: Any = None,
        tool_choice: Any = None,
        extra_kwargs: dict[str, Any] | None = None,
    ) -> LLMStream:
        """Create a chat completion stream.

        Args:
            chat_ctx: Chat context with conversation history
            tools: Function tools (not supported via CLI)
            conn_options: Connection options (retry settings)
            parallel_tool_calls: Not supported
            tool_choice: Not supported
            extra_kwargs: Additional arguments (ignored)

        Returns:
            LLMStream that yields ChatChunk objects
        """
        return ClaudeCodeLLMStream(
            self,
            chat_ctx=chat_ctx,
            conn_options=conn_options,
            options=self._options,
        )
