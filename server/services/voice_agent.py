"""LiveKit Voice Agent for AIPA.

This agent connects to a LiveKit room and responds to voice input using Claude.
Uses local Whisper (STT) and Kokoro (TTS) services.
Uses Claude Code CLI with OAuth token - no API key required.
"""

import asyncio
import json
import logging
import os
import threading

import httpx
from livekit import rtc
from livekit.agents import Agent, AgentSession
from livekit.plugins import openai as lk_openai
from livekit.plugins import silero

from .claude_code_llm import ClaudeCodeLLM

logger = logging.getLogger(__name__)

# Increased timeout for STT (Whisper model loading can take 30+ seconds on first request)
STT_TIMEOUT = 60.0


async def wait_for_service(url: str, name: str, timeout: float = 60.0) -> bool:
    """Wait for a service to become healthy.

    Args:
        url: Health check URL
        name: Service name for logging
        timeout: Maximum time to wait in seconds

    Returns:
        True if service is healthy, False if timeout
    """
    start = asyncio.get_event_loop().time()
    async with httpx.AsyncClient() as client:
        while (asyncio.get_event_loop().time() - start) < timeout:
            try:
                response = await client.get(url, timeout=5.0)
                if response.status_code == 200:
                    logger.info(f"{name} is healthy")
                    return True
            except Exception:
                pass
            logger.debug(f"Waiting for {name}...")
            await asyncio.sleep(1.0)
    logger.error(f"{name} did not become healthy within {timeout}s")
    return False


async def prewarm_stt_model(stt_base_url: str) -> bool:
    """Pre-warm the STT model by sending a small audio sample.

    This triggers model loading before actual use, reducing latency on first request.

    Args:
        stt_base_url: Base URL for the STT service (e.g., http://whisper:8000/v1)

    Returns:
        True if pre-warming succeeded
    """
    import io
    import struct
    import wave

    logger.info("Pre-warming STT model (this may take 30+ seconds on first run)...")

    # Create a minimal valid WAV file (1 second of silence)
    sample_rate = 16000
    duration = 0.5  # 0.5 seconds
    num_samples = int(sample_rate * duration)

    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        # Write silent audio (zeros)
        wav_file.writeframes(struct.pack("<" + "h" * num_samples, *([0] * num_samples)))

    wav_buffer.seek(0)

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(90.0)) as client:
            # Send a transcription request to trigger model loading
            files = {"file": ("warmup.wav", wav_buffer, "audio/wav")}
            data = {"model": "whisper-1"}

            response = await client.post(
                f"{stt_base_url}/audio/transcriptions",
                files=files,
                data=data,
            )

            if response.status_code == 200:
                logger.info("STT model pre-warmed successfully")
                return True
            else:
                logger.warning(
                    f"STT pre-warm returned status {response.status_code}: {response.text}"
                )
                return True  # Model might still be loaded even on error

    except Exception as e:
        logger.warning(f"STT pre-warm failed (model may still load on first use): {e}")
        return False


async def send_to_ui(room: rtc.Room, message_type: str, data: dict) -> None:
    """Send a message to all participants in the room via data channel.

    Args:
        room: LiveKit room instance
        message_type: Type of message (transcript, response, agent_state, error)
        data: Message data to send
    """
    try:
        message = {"type": message_type, **data}
        encoded = json.dumps(message).encode("utf-8")
        await room.local_participant.publish_data(encoded, reliable=True)
    except Exception as e:
        logger.debug(f"Failed to send UI message: {e}")


# Pre-load VAD model on main thread (required by LiveKit)
_vad_model = None
_vad_lock = threading.Lock()


class UltraAssistant(Agent):
    """Ultra voice assistant powered by Claude."""

    def __init__(self) -> None:
        super().__init__(
            instructions="""You are Ultra, an AI personal assistant for Gareth.

You are helpful, friendly, and concise in your responses.
Keep responses brief and conversational since this is a voice interface.
Avoid complex formatting, bullet points, or long explanations.
If you don't know something, say so directly.
You have a warm but professional tone.""",
        )


async def run_voice_agent():
    """Run the voice agent, connecting to the configured LiveKit room."""

    # Get configuration from environment
    livekit_url = os.getenv("LIVEKIT_URL")
    livekit_api_key = os.getenv("LIVEKIT_API_KEY")
    livekit_api_secret = os.getenv("LIVEKIT_API_SECRET")
    oauth_token = os.getenv("CLAUDE_CODE_OAUTH_TOKEN")

    # Local service URLs (optional)
    stt_base_url = os.getenv("STT_BASE_URL")  # e.g., http://whisper:8000/v1
    tts_base_url = os.getenv("TTS_BASE_URL")  # e.g., http://kokoro:8880/v1
    tts_voice = os.getenv("TTS_VOICE", "af_heart")

    if not all([livekit_url, livekit_api_key, livekit_api_secret]):
        logger.error("LiveKit credentials not configured")
        return

    if not oauth_token:
        logger.error(
            "CLAUDE_CODE_OAUTH_TOKEN not configured - run 'claude setup-token' to generate"
        )
        return

    logger.info(f"Starting voice agent, connecting to {livekit_url}")

    # Wait for STT and TTS services to be healthy before starting
    if stt_base_url:
        # Extract base URL (remove /v1 if present) for health check
        stt_health_url = stt_base_url.rstrip("/").replace("/v1", "") + "/health"
        logger.info(f"Waiting for STT service at {stt_health_url}...")
        if not await wait_for_service(stt_health_url, "STT (Whisper)"):
            logger.error("STT service not available, voice agent cannot start")
            return

    if tts_base_url:
        tts_health_url = tts_base_url.rstrip("/").replace("/v1", "") + "/health"
        logger.info(f"Waiting for TTS service at {tts_health_url}...")
        if not await wait_for_service(tts_health_url, "TTS (Kokoro)"):
            logger.error("TTS service not available, voice agent cannot start")
            return

    logger.info("All voice services are healthy, starting agent...")

    # Pre-warm STT model to avoid timeout on first request
    if stt_base_url:
        await prewarm_stt_model(stt_base_url)

    # Configure STT - use local Whisper if available, else OpenAI
    if stt_base_url:
        logger.info(f"Using local STT at {stt_base_url}")
        stt = lk_openai.STT(
            base_url=stt_base_url,
            api_key="not-needed",  # Local service doesn't need key
            model="whisper-1",  # faster-whisper-server maps this to configured model
        )
    else:
        logger.info("Using OpenAI STT")
        stt = lk_openai.STT()

    # Configure TTS - use local Kokoro if available, else OpenAI
    if tts_base_url:
        logger.info(f"Using local TTS at {tts_base_url}")
        tts = lk_openai.TTS(
            base_url=tts_base_url,
            api_key="not-needed",
            model="tts-1",  # Kokoro supports: tts-1, tts-1-hd, kokoro
            voice=tts_voice,
        )
    else:
        logger.info("Using OpenAI TTS")
        tts = lk_openai.TTS(voice="alloy")

    # Configure LLM - Claude via CLI (uses OAuth token, no API key needed)
    logger.info("Using Claude Code CLI for LLM (OAuth token)")
    llm = ClaudeCodeLLM(
        model="sonnet",
        oauth_token=oauth_token,
        system_prompt="""You are Ultra, an AI personal assistant for Gareth.
You are helpful, friendly, and concise in your responses.
Keep responses brief and conversational since this is a voice interface.
Avoid complex formatting, bullet points, or long explanations.
If you don't know something, say so directly.
You have a warm but professional tone.""",
    )

    # Create room and connect
    room = rtc.Room()

    # Generate access token
    from livekit.api import AccessToken, VideoGrants

    token = AccessToken(
        api_key=livekit_api_key,
        api_secret=livekit_api_secret,
    )
    token.with_identity("ultra-agent")
    token.with_name("Ultra")
    token.with_grants(
        VideoGrants(
            room_join=True,
            room="voice-ultra",
            can_publish=True,
            can_subscribe=True,
        )
    )

    jwt_token = token.to_jwt()

    try:
        await room.connect(livekit_url, jwt_token)
        logger.info("Connected to room: voice-ultra")

        # Use pre-loaded VAD model (must be loaded on main thread)
        global _vad_model
        with _vad_lock:
            if _vad_model is None:
                logger.warning("VAD not pre-loaded, loading now (may fail if not on main thread)")
                _vad_model = silero.VAD.load()

        # Create and start agent session
        session = AgentSession(
            stt=stt,
            llm=llm,
            tts=tts,
            vad=_vad_model,
        )

        # Set up event handlers to forward transcripts and state to UI
        @session.on("user_speech_committed")
        def on_user_speech(user_msg):
            """Forward user speech transcript to UI."""
            if hasattr(user_msg, "content") and user_msg.content:
                text = (
                    user_msg.content if isinstance(user_msg.content, str) else str(user_msg.content)
                )
                asyncio.create_task(
                    send_to_ui(room, "transcript", {"role": "user", "text": text, "is_final": True})
                )
                asyncio.create_task(send_to_ui(room, "agent_state", {"state": "thinking"}))
                logger.debug(f"User said: {text}")

        @session.on("agent_speech_committed")
        def on_agent_speech(agent_msg):
            """Forward agent response transcript to UI."""
            if hasattr(agent_msg, "content") and agent_msg.content:
                text = (
                    agent_msg.content
                    if isinstance(agent_msg.content, str)
                    else str(agent_msg.content)
                )
                asyncio.create_task(
                    send_to_ui(room, "response", {"role": "assistant", "text": text})
                )
                logger.debug(f"Agent said: {text}")

        @session.on("agent_started_speaking")
        def on_agent_speaking():
            """Notify UI that agent is speaking."""
            asyncio.create_task(send_to_ui(room, "agent_state", {"state": "speaking"}))

        @session.on("agent_stopped_speaking")
        def on_agent_done_speaking():
            """Notify UI that agent stopped speaking."""
            asyncio.create_task(send_to_ui(room, "agent_state", {"state": "idle"}))

        @session.on("user_started_speaking")
        def on_user_speaking():
            """Notify UI that user is speaking."""
            asyncio.create_task(send_to_ui(room, "agent_state", {"state": "listening"}))

        await session.start(
            room=room,
            agent=UltraAssistant(),
        )

        # Generate initial greeting
        await session.generate_reply(
            instructions="Greet the user briefly. Say something like 'Hi, I'm Ultra. How can I help you today?'"
        )

        # Keep running until disconnected
        while room.connection_state == rtc.ConnectionState.CONN_CONNECTED:
            await asyncio.sleep(1)

    except Exception as e:
        logger.error(f"Voice agent error: {e}")
        raise
    finally:
        await room.disconnect()
        logger.info("Disconnected from room")


def preload_voice_plugins():
    """Pre-load VAD and other plugins on the main thread.

    This must be called from the main thread before starting the voice agent.
    """
    global _vad_model
    with _vad_lock:
        if _vad_model is None:
            logger.info("Pre-loading Silero VAD model...")
            _vad_model = silero.VAD.load()
            logger.info("VAD model loaded successfully")


def start_voice_agent_background():
    """Start the voice agent in a background task."""
    loop = asyncio.new_event_loop()

    def run():
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_voice_agent())
        except Exception as e:
            logger.error(f"Voice agent crashed: {e}")
        finally:
            loop.close()

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread
