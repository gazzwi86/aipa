"""Session name generation using Claude."""

import asyncio
import logging
import os

logger = logging.getLogger(__name__)


async def generate_session_name(first_message: str) -> str:
    """Generate a concise session name from the first message using Claude.

    Uses Claude haiku for fast, cheap summarization.
    Falls back to truncated message if Claude fails.

    Args:
        first_message: The first user message in the session.

    Returns:
        A 3-6 word session title.
    """
    # Short messages don't need summarization
    if len(first_message) < 50:
        return first_message.strip()

    prompt = f"""Generate a concise 3-6 word session title for this user request.
Be descriptive but brief. No quotes, punctuation, or formatting.
Just output the title, nothing else.

User request: {first_message[:500]}

Session title:"""

    try:
        # Use Claude Code CLI for quick summarization
        oauth_token = os.getenv("CLAUDE_CODE_OAUTH_TOKEN")

        cmd = ["claude", "-p", "--model", "haiku"]
        if not oauth_token:
            # No token, skip external call
            logger.debug("No OAuth token, using fallback session name")
            return _fallback_name(first_message)

        env = os.environ.copy()
        env["CLAUDE_CODE_OAUTH_TOKEN"] = oauth_token

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        stdout, stderr = await asyncio.wait_for(
            process.communicate(prompt.encode("utf-8")),
            timeout=10.0,
        )

        if process.returncode == 0:
            name = stdout.decode("utf-8").strip()
            # Clean up the response
            name = name.replace('"', "").replace("'", "")
            # Remove common prefixes Claude might add
            for prefix in ["Session:", "Title:", "Session title:"]:
                if name.lower().startswith(prefix.lower()):
                    name = name[len(prefix) :].strip()
            # Limit length
            if name and len(name) <= 60:
                return name

        if stderr:
            logger.debug(f"Session namer stderr: {stderr.decode()}")

    except TimeoutError:
        logger.warning("Session name generation timed out")
    except FileNotFoundError:
        logger.warning("Claude CLI not found, using fallback session name")
    except Exception as e:
        logger.warning(f"Session name generation failed: {e}")

    return _fallback_name(first_message)


def _fallback_name(message: str) -> str:
    """Generate a fallback name from the message itself."""
    # Take first 50 chars, try to break at word boundary
    name = message[:50].strip()
    if len(message) > 50:
        # Try to break at last space
        last_space = name.rfind(" ")
        if last_space > 20:
            name = name[:last_space]
        name += "..."
    return name
