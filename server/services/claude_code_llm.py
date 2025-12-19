"""Custom LLM plugin for LiveKit that uses Claude Code CLI.

This allows the voice agent to use Claude Pro/Max subscription via the OAuth token
instead of requiring a separate ANTHROPIC_API_KEY.
"""

import asyncio
import json
import logging
import os
import re
import uuid
from collections.abc import AsyncIterator, Callable
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

# Activity callback type: (activity_type, message, details)
ActivityCallback = Callable[[str, str, dict | None], None]


def chunk_text_for_tts(text: str, max_chars: int = 500) -> list[str]:
    """Split text into chunks suitable for TTS processing.

    Splits on sentence boundaries to maintain natural speech flow.
    Falls back to word boundaries for very long sentences.
    """
    if len(text) <= max_chars:
        return [text] if text.strip() else []

    chunks = []
    current_chunk = ""

    # Split by sentence-ending punctuation
    sentences = re.split(r"(?<=[.!?])\s+", text)

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        # If adding this sentence exceeds limit, start new chunk
        if len(current_chunk) + len(sentence) + 1 > max_chars:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""

            # If single sentence is too long, split by word
            if len(sentence) > max_chars:
                words = sentence.split()
                for word in words:
                    if len(current_chunk) + len(word) + 1 > max_chars:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = word
                    else:
                        current_chunk = f"{current_chunk} {word}".strip()
            else:
                current_chunk = sentence
        else:
            current_chunk = f"{current_chunk} {sentence}".strip()

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


def strip_markdown_for_speech(text: str) -> str:
    """Strip markdown formatting from text for natural speech.

    Removes code blocks, links, emphasis, sources, URLs, etc.
    while preserving readable content for TTS.
    """
    # Remove Sources section (WebSearch results) - everything from "Sources:" to end or next section
    # Matches: "Sources:", "Source:", "\n\nSources:", etc.
    text = re.sub(r"\n*Sources?:\s*\n.*", "", text, flags=re.DOTALL | re.IGNORECASE)

    # Remove source citations in brackets: [Source: ...], [1], [Source 1], etc.
    text = re.sub(r"\[Source[^\]]*\]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\[\d+\]", "", text)

    # Remove standalone URLs (http/https)
    text = re.sub(r"https?://\S+", "", text)

    # Remove code blocks (```...```)
    text = re.sub(r"```[\s\S]*?```", "[code block]", text)

    # Remove inline code (`...`)
    text = re.sub(r"`([^`]+)`", r"\1", text)

    # Remove links but keep text: [text](url) -> text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

    # Remove images: ![alt](url)
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)

    # Remove bold/italic markers
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)  # **bold**
    text = re.sub(r"\*([^*]+)\*", r"\1", text)  # *italic*
    text = re.sub(r"__([^_]+)__", r"\1", text)  # __bold__
    text = re.sub(r"_([^_]+)_", r"\1", text)  # _italic_

    # Remove headers (# Header)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)

    # Remove horizontal rules
    text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)

    # Remove bullet points but keep content
    text = re.sub(r"^[\s]*[-*+]\s+", "", text, flags=re.MULTILINE)

    # Remove numbered list markers
    text = re.sub(r"^[\s]*\d+\.\s+", "", text, flags=re.MULTILINE)

    # Remove blockquotes
    text = re.sub(r"^>\s+", "", text, flags=re.MULTILINE)

    # Clean up multiple newlines
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Clean up multiple spaces
    text = re.sub(r"  +", " ", text)

    return text.strip()


@dataclass
class ClaudeCodeLLMOptions:
    """Configuration options for Claude Code LLM."""

    model: str = "sonnet"  # sonnet, opus, or full model name
    oauth_token: str | None = None
    system_prompt: str | None = None
    session_id: str | None = None  # For session continuity across calls
    activity_callback: ActivityCallback | None = None  # Callback for activity events


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
        self._process: asyncio.subprocess.Process | None = None
        self._cancelled = False

    async def aclose(self) -> None:
        """Cancel the running process when stream is closed."""
        self._cancelled = True
        if self._process and self._process.returncode is None:
            logger.info("Cancelling Claude Code CLI process due to stream close")
            try:
                self._process.terminate()
                # Give it a moment to terminate gracefully
                try:
                    await asyncio.wait_for(self._process.wait(), timeout=2.0)
                except TimeoutError:
                    logger.warning("Process didn't terminate, killing forcefully")
                    self._process.kill()
            except ProcessLookupError:
                pass  # Process already ended
        await super().aclose()

    def _emit_activity(self, activity_type: str, message: str, details: dict | None = None) -> None:
        """Emit an activity event via callback and log it."""
        # Always log activity for docker logs visibility
        logger.info(f"[ACTIVITY] {activity_type}: {message}")
        if details:
            logger.debug(f"[ACTIVITY DETAILS] {details}")

        # Call activity callback if registered
        if self._options.activity_callback:
            try:
                self._options.activity_callback(activity_type, message, details)
            except Exception as e:
                logger.error(f"Activity callback error: {e}")

    def _parse_tool_name(self, tool_name: str) -> tuple[str, str]:
        """Parse tool name into activity type and friendly name."""
        # Map Claude Code tools to activity types
        tool_mappings = {
            "WebSearch": ("search", "Searching the web"),
            "WebFetch": ("search", "Fetching web content"),
            "Read": ("read", "Reading file"),
            "Write": ("write", "Creating file"),
            "Edit": ("edit", "Editing file"),
            "Bash": ("code", "Running command"),
            "Glob": ("search", "Finding files"),
            "Grep": ("search", "Searching code"),
            "Task": ("agent", "Starting sub-agent"),
            "mcp__notion": ("notion", "Accessing Notion"),
            "mcp__github": ("github", "Accessing GitHub"),
        }

        for prefix, (activity_type, friendly) in tool_mappings.items():
            if tool_name.startswith(prefix):
                return activity_type, friendly

        # Default for unknown tools
        return "tool", f"Using {tool_name}"

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

        # Emit thinking activity at start
        self._emit_activity("thinking", "Processing your request...")

        # Build CLI command - stream-json mode with verbose for tool activity
        # Note: --print + --output-format=stream-json requires --verbose
        cmd = ["claude", "-p", "--output-format", "stream-json", "--verbose"]

        if self._options.model:
            cmd.extend(["--model", self._options.model])

        if self._options.system_prompt:
            cmd.extend(["--system-prompt", self._options.system_prompt])

        # Tools enabled - allows MCP servers (GitHub, Notion, etc.)
        # Claude Code will use configured MCP servers from ~/.config/claude/mcp.json

        # YOLO mode - skip all permission prompts for autonomous operation
        cmd.append("--dangerously-skip-permissions")

        # Session ID for continuity across calls
        if self._options.session_id:
            cmd.extend(["--session-id", self._options.session_id])

        # Set up environment with OAuth token
        env = os.environ.copy()
        if self._options.oauth_token:
            env["CLAUDE_CODE_OAUTH_TOKEN"] = self._options.oauth_token

        # Run from workspace directory so Claude picks up .claude/CLAUDE.md context
        workspace_dir = os.getenv("WORKSPACE", "/workspace")
        logger.info(f"Running Claude Code CLI from {workspace_dir}, prompt length: {len(prompt)}")

        try:
            # Pass prompt via stdin to handle special characters and newlines
            self._process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=workspace_dir,
            )

            # Check for early cancellation
            if self._cancelled:
                self._process.terminate()
                return

            # Write prompt to stdin and close it
            self._process.stdin.write(prompt.encode("utf-8"))
            await self._process.stdin.drain()
            self._process.stdin.close()
            await self._process.stdin.wait_closed()

            # Collect JSON stream events and extract text response
            full_response = []
            async for line in self._read_lines(self._process.stdout):
                if self._cancelled:
                    logger.info("Stream cancelled, stopping output")
                    break
                if not line.strip():
                    continue

                # Parse JSON event
                try:
                    event = json.loads(line)
                    event_type = event.get("type", "")

                    # Log all events for debugging
                    logger.info(f"[CLAUDE] Event: {event_type}")

                    # Handle different event types
                    if event_type == "assistant":
                        # Assistant message - extract text content
                        message = event.get("message", {})
                        content = message.get("content", [])
                        for block in content:
                            if block.get("type") == "text":
                                text = block.get("text", "")
                                if text:
                                    full_response.append(text)
                                    logger.info(f"[CLAUDE] Text: {text[:100]}...")

                    elif event_type == "content_block_delta":
                        # Streaming text delta
                        delta = event.get("delta", {})
                        if delta.get("type") == "text_delta":
                            full_response.append(delta.get("text", ""))

                    elif event_type == "tool_use":
                        # Tool being used - emit activity
                        tool_name = event.get("name", "unknown")
                        tool_input = event.get("input", {})
                        activity_type, friendly_name = self._parse_tool_name(tool_name)
                        logger.info(f"[CLAUDE] Tool: {tool_name}")
                        self._emit_activity(
                            activity_type, friendly_name, {"tool": tool_name, "input": tool_input}
                        )

                    elif event_type == "content_block_start":
                        # Content block starting - may contain tool_use
                        content_block = event.get("content_block", {})
                        if content_block.get("type") == "tool_use":
                            tool_name = content_block.get("name", "unknown")
                            tool_id = content_block.get("id", "")
                            activity_type, friendly_name = self._parse_tool_name(tool_name)
                            logger.info(f"[CLAUDE] Tool (block_start): {tool_name} [{tool_id}]")
                            self._emit_activity(
                                activity_type,
                                friendly_name,
                                {"tool": tool_name, "tool_id": tool_id},
                            )

                    elif event_type in ("tool_input", "tool_call"):
                        # Alternative tool event formats from some CLI versions
                        tool_name = event.get("name", event.get("tool", "unknown"))
                        tool_input = event.get("input", event.get("arguments", {}))
                        activity_type, friendly_name = self._parse_tool_name(tool_name)
                        logger.info(f"[CLAUDE] Tool ({event_type}): {tool_name}")
                        self._emit_activity(
                            activity_type, friendly_name, {"tool": tool_name, "input": tool_input}
                        )

                    elif event_type == "result":
                        # Final result - may contain text
                        result_text = event.get("result", "")
                        if result_text and isinstance(result_text, str):
                            full_response.append(result_text)
                            logger.info(f"[CLAUDE] Result: {result_text[:100]}...")

                    elif event_type == "system":
                        # System message (thinking, status, etc.)
                        msg = event.get("message", "")
                        if msg:
                            logger.info(f"[CLAUDE] System: {msg}")
                            self._emit_activity("thinking", msg)

                except json.JSONDecodeError:
                    # Not JSON - might be plain text fallback or verbose output
                    line_stripped = line.strip()
                    if line_stripped and not line_stripped.startswith("{"):
                        logger.info(f"[CLAUDE] Output: {line_stripped[:150]}")
                        full_response.append(line)

            # Process complete response
            if full_response and not self._cancelled:
                raw_text = "".join(full_response)
                # Strip markdown for speech - TTS will read this
                speech_text = strip_markdown_for_speech(raw_text)
                logger.info(
                    f"Response: {len(raw_text)} chars raw, {len(speech_text)} chars for speech"
                )

                # Emit response activity with full text for UI display
                # The activity callback will forward this to the UI as both:
                # 1. An activity log entry (for the activity panel)
                # 2. A response message (for the chat display)
                self._emit_activity(
                    "response",
                    f"Generated {len(speech_text)} character response",
                    {"response_text": raw_text},  # Include raw text (with markdown) for UI display
                )

                # Chunk the text for TTS (handles length limits)
                # Most TTS services have ~500-1000 char limits per request
                tts_chunks = chunk_text_for_tts(speech_text, max_chars=500)
                logger.info(f"Split into {len(tts_chunks)} TTS chunks")

                # Send each chunk to TTS pipeline
                for i, chunk_text in enumerate(tts_chunks):
                    if self._cancelled:
                        logger.info(f"Cancelled at chunk {i + 1}/{len(tts_chunks)}")
                        break

                    chunk = ChatChunk(
                        id=f"{self._request_id}-{i}",
                        delta=ChoiceDelta(
                            role="assistant",
                            content=chunk_text,
                        ),
                    )
                    self._event_ch.send_nowait(chunk)

            # Wait for process to complete (if not cancelled)
            if not self._cancelled:
                await self._process.wait()

                if self._process.returncode != 0:
                    stderr = await self._process.stderr.read()
                    logger.error(f"Claude Code CLI error: {stderr.decode()}")

        except Exception as e:
            logger.error(f"Error running Claude Code CLI: {e}")
            self._emit_activity("error", f"Error: {str(e)}")
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
        activity_callback: ActivityCallback | None = None,
    ) -> None:
        """Initialize Claude Code LLM.

        Args:
            model: Model alias (sonnet, opus) or full model name
            oauth_token: OAuth token from `claude setup-token`. If not provided,
                        uses CLAUDE_CODE_OAUTH_TOKEN environment variable.
            system_prompt: Optional system prompt for the conversation
            session_id: Optional session ID for conversation continuity
            activity_callback: Optional callback for activity events (type, message, details)
        """
        super().__init__()
        self._options = ClaudeCodeLLMOptions(
            model=model,
            oauth_token=oauth_token or os.getenv("CLAUDE_CODE_OAUTH_TOKEN"),
            system_prompt=system_prompt,
            session_id=session_id,
            activity_callback=activity_callback,
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
