"""LiveKit Voice Agent for AIPA.

This agent connects to a LiveKit room and responds to voice input using Claude.
Uses local Whisper (STT) and Kokoro (TTS) services.
Uses Claude Code CLI with OAuth token - no API key required.
"""

import asyncio
import contextlib
import json
import logging
import os
import threading
from collections.abc import Callable, Coroutine

import httpx
from livekit import rtc
from livekit.agents import Agent, AgentSession
from livekit.plugins import openai as lk_openai
from livekit.plugins import silero

# Import turn detector for smarter endpointing (prevents mid-sentence cutoffs)
try:
    from livekit.plugins.turn_detector import EOUModel

    TURN_DETECTOR_AVAILABLE = True
except ImportError:
    TURN_DETECTOR_AVAILABLE = False

from .claude_code_llm import ClaudeCodeLLM


class TranscriptBuffer:
    """Buffer for aggregating speech transcripts before processing.

    This helps prevent message fragmentation where natural pauses in speech
    result in multiple separate messages to the agent. The buffer collects
    transcripts and only sends them to the callback after a configurable delay
    of silence.
    """

    def __init__(self, delay_seconds: float = 2.0):
        """Initialize the transcript buffer.

        Args:
            delay_seconds: Time to wait after last transcript before sending
        """
        self.buffer: list[str] = []
        self.delay = delay_seconds
        self._pending_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

    async def add(
        self,
        transcript: str,
        callback: Callable[[str], Coroutine],
    ) -> None:
        """Add a transcript to the buffer.

        If a pending send task exists, it will be cancelled and rescheduled.
        This allows continuous speech to be aggregated.

        Args:
            transcript: The transcript text to buffer
            callback: Async function to call with the aggregated transcript
        """
        async with self._lock:
            self.buffer.append(transcript)

            # Cancel any pending send task
            if self._pending_task and not self._pending_task.done():
                self._pending_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._pending_task

            # Schedule a new send task
            self._pending_task = asyncio.create_task(self._send_after_delay(callback))

    async def _send_after_delay(
        self,
        callback: Callable[[str], Coroutine],
    ) -> None:
        """Wait for delay then send aggregated buffer to callback."""
        await asyncio.sleep(self.delay)
        async with self._lock:
            if self.buffer:
                # Join all buffered transcripts with spaces
                full_text = " ".join(self.buffer)
                self.buffer = []
                await callback(full_text)

    def clear(self) -> None:
        """Clear the buffer and cancel any pending task."""
        if self._pending_task and not self._pending_task.done():
            self._pending_task.cancel()
        self.buffer = []


def strip_markdown_for_display(text: str) -> str:
    """Strip markdown for cleaner display while keeping structure."""
    # This is a lighter strip - just remove code fences and excessive formatting
    # Full markdown rendering happens in frontend
    return text


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
        logger.info(f"Publishing to data channel: {message}")  # Debug
        await room.local_participant.publish_data(encoded, reliable=True)
        logger.info(f"Published {message_type} to UI successfully")  # Debug
    except Exception as e:
        logger.error(f"Failed to send UI message: {e}")


# Pre-load VAD model on main thread (required by LiveKit)
_vad_model = None
_vad_lock = threading.Lock()


class BluAssistant(Agent):
    """Blu voice assistant powered by Claude."""

    def __init__(self) -> None:
        super().__init__(
            instructions="""You are Blu, an AI personal assistant for Gareth.

You are helpful, friendly, and concise in your responses.
Keep responses brief and conversational since this is a voice interface.
Avoid complex formatting, bullet points, or long explanations.
If you don't know something, say so directly.
You have a warm but professional tone.""",
        )


async def run_voice_agent(is_reconnect: bool = False, reconnect_reason: str | None = None):
    """Run the voice agent, connecting to the configured LiveKit room.

    Args:
        is_reconnect: Whether this is a reconnection attempt
        reconnect_reason: Optional reason for the reconnection (e.g., "skill update", "error")
    """

    # Get configuration from environment
    livekit_url = os.getenv("LIVEKIT_URL")
    livekit_api_key = os.getenv("LIVEKIT_API_KEY")
    livekit_api_secret = os.getenv("LIVEKIT_API_SECRET")
    oauth_token = os.getenv("CLAUDE_CODE_OAUTH_TOKEN")

    # Model configuration (can be alias like 'sonnet' or full model ID)
    agent_model = os.getenv("AGENT_MODEL", "claude-sonnet-4-5-20250514")

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
        # Use PCM format for most reliable streaming (no codec issues)
        # Kokoro supports: mp3, wav, pcm, opus, flac, aac
        # PCM is raw audio - no encoding/decoding issues
        tts = lk_openai.TTS(
            base_url=tts_base_url,
            api_key="not-needed",
            model="kokoro",  # Use native model name for best quality
            voice=tts_voice,
            response_format="wav",  # WAV is more reliable than MP3 for streaming
        )
    else:
        logger.info("Using OpenAI TTS")
        tts = lk_openai.TTS(voice="alloy")

    # Create room first (needed for activity callback)
    room = rtc.Room()

    # Configure LLM - Claude via CLI (uses OAuth token, no API key needed)
    logger.info("Using Claude Code CLI for LLM (OAuth token)")

    # Activity callback to send Claude Code activity to UI
    def on_activity(activity_type: str, message: str, details: dict | None = None) -> None:
        """Forward activity events to the UI via data channel.

        Special handling for 'response' activity:
        - Sends the response text to UI as a chat message for display
        - This is the ONLY place assistant responses are sent to UI (not conversation_item_added)
        - The TTS is handled separately by ChatChunk emissions
        """
        if room.connection_state != rtc.ConnectionState.CONN_CONNECTED:
            return

        # Always send activity to activity log
        asyncio.create_task(
            send_to_ui(
                room,
                "activity",
                {
                    "activity_type": activity_type,
                    "message": message,
                },
            )
        )

        # For response activities, also send the full text to chat UI
        if activity_type == "response" and details and details.get("response_text"):
            asyncio.create_task(
                send_to_ui(
                    room,
                    "transcript",
                    {
                        "role": "assistant",
                        "text": details["response_text"],
                        "is_final": True,
                    },
                )
            )

    logger.info(f"Using model: {agent_model}")
    llm = ClaudeCodeLLM(
        model=agent_model,
        oauth_token=oauth_token,
        system_prompt="""You are Blu, an AI personal assistant for Gareth.
You are helpful, friendly, and concise in your responses.
Keep responses brief and conversational since this is a voice interface.
Avoid complex formatting, bullet points, or long explanations.
If you don't know something, say so directly.
You have a warm but professional tone.""",
        activity_callback=on_activity,
    )

    # Generate access token
    from livekit.api import AccessToken, VideoGrants

    token = AccessToken(
        api_key=livekit_api_key,
        api_secret=livekit_api_secret,
    )
    token.with_identity("blu-agent")
    token.with_name("Blu")
    token.with_grants(
        VideoGrants(
            room_join=True,
            room="voice-blu",
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
                _vad_model = silero.VAD.load(
                    min_speech_duration=0.3,  # Filter out short noises
                    min_silence_duration=1.5,  # Wait longer for natural pauses (was 1.0)
                )

        # Configure turn detection for smarter endpointing
        # Using EOUModel (End of Utterance) if available, otherwise fall back to VAD-only
        turn_detector = None
        if TURN_DETECTOR_AVAILABLE:
            try:
                turn_detector = EOUModel()
                logger.info("Using EOUModel for turn detection (smarter endpointing)")
            except Exception as e:
                logger.warning(f"Failed to load EOUModel, using VAD-only: {e}")

        # Create and start agent session with conservative interruption settings
        # The user's natural pauses between sentences shouldn't trigger interruptions
        # Higher thresholds prevent "in their blog." from interrupting the first request
        session = AgentSession(
            stt=stt,
            llm=llm,
            tts=tts,
            vad=_vad_model,
            turn_detection=turn_detector if turn_detector else "vad",
            allow_interruptions=True,
            min_interruption_duration=1.2,  # 1.2s of speech required (was 0.8s)
            min_interruption_words=4,  # At least 4 words needed to interrupt (was 2)
            min_endpointing_delay=5.0,  # Wait 5s of silence before ending turn (was 3.0)
        )

        # Set up event handlers to forward transcripts and state to UI
        # Event names for livekit-agents 1.3.6+
        @session.on("user_input_transcribed")
        def on_user_input(ev):
            """Forward user speech transcript to UI."""
            logger.info(
                f"user_input_transcribed: transcript='{ev.transcript}', is_final={ev.is_final}"
            )
            if ev.transcript and ev.is_final:
                asyncio.create_task(
                    send_to_ui(
                        room,
                        "transcript",
                        {"role": "user", "text": ev.transcript, "is_final": True},
                    )
                )

        @session.on("conversation_item_added")
        def on_conversation_item(ev):
            """Forward conversation messages to UI (for display only).

            NOTE: We only forward USER messages here. Assistant responses are NOT sent
            from this handler because TTS is already handled by ChatChunk emissions
            from ClaudeCodeLLMStream. Sending the response here would trigger duplicate
            TTS synthesis.
            """
            item = ev.item
            logger.info(f"conversation_item_added: role={getattr(item, 'role', 'unknown')}")
            # ChatMessage has role and content (content may be a list)
            if hasattr(item, "role") and hasattr(item, "content"):
                role = str(item.role.value) if hasattr(item.role, "value") else str(item.role)
                # Extract text from content - may be string or list of strings
                content = item.content
                if isinstance(content, list):
                    content = "".join(str(c) for c in content)
                elif not isinstance(content, str):
                    content = str(content)
                # Only forward user messages - assistant responses handled by LLM stream
                if role == "user" and content:
                    asyncio.create_task(
                        send_to_ui(
                            room, "transcript", {"role": "user", "text": content, "is_final": True}
                        )
                    )
                # NOTE: Removed assistant response emission - TTS handled by ChatChunk emissions

        @session.on("agent_state_changed")
        def on_agent_state(ev):
            """Notify UI of agent state changes."""
            logger.info(f"agent_state_changed: {ev.old_state} -> {ev.new_state}")
            # Map livekit states to UI states
            state_map = {
                "speaking": "speaking",
                "thinking": "thinking",
                "listening": "listening",
                "idle": "idle",
                "initializing": "connecting",
            }
            ui_state = state_map.get(ev.new_state, "idle")
            asyncio.create_task(send_to_ui(room, "agent_state", {"state": ui_state}))

        @session.on("user_state_changed")
        def on_user_state(ev):
            """Notify UI of user state changes."""
            logger.info(f"user_state_changed: {ev.old_state} -> {ev.new_state}")
            if ev.new_state == "speaking":
                asyncio.create_task(send_to_ui(room, "agent_state", {"state": "listening"}))

        # Handle incoming text messages from UI via data channel
        @room.on("data_received")
        def on_data_received(data: bytes, participant, *args, **kwargs):
            """Handle text messages from UI."""
            try:
                msg = json.loads(data.decode("utf-8"))
                logger.info(f"Received data from UI: {msg}")
                if msg.get("type") == "text" and msg.get("text"):
                    text = msg["text"]
                    logger.info(f"Processing text message: {text[:100]}...")
                    # Send transcript to UI
                    asyncio.create_task(
                        send_to_ui(
                            room, "transcript", {"role": "user", "text": text, "is_final": True}
                        )
                    )
                    # Generate reply using the agent session
                    asyncio.create_task(session.generate_reply(instructions=f"User typed: {text}"))
            except Exception as e:
                logger.error(f"Error handling data message: {e}")
                asyncio.create_task(
                    send_to_ui(room, "error", {"message": f"Failed to process message: {e}"})
                )

        await session.start(
            room=room,
            agent=BluAssistant(),
        )

        # Send notification and generate greeting
        if is_reconnect:
            # Notify user of reconnection via data channel
            reason_text = f" after {reconnect_reason}" if reconnect_reason else ""
            await send_to_ui(
                room, "system", {"message": f"Agent reconnected{reason_text}. Ready to continue."}
            )
            logger.info(f"Agent reconnected{reason_text}")
            # Generate reconnection greeting
            await session.generate_reply(
                instructions=f"You just reconnected{reason_text}. Briefly acknowledge this and ask if there's anything the user needs. Keep it very short."
            )
        else:
            # Generate initial greeting
            await session.generate_reply(
                instructions="Greet the user briefly. Say something like 'Hi, I'm Blu. How can I help you today?'"
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
            # Configure VAD with conservative settings to prevent cutting off mid-sentence
            # min_speech_duration: minimum speech to trigger detection (default 0.1s)
            # min_silence_duration: silence needed before end-of-speech
            # Higher values = more tolerant of natural pauses in speech
            _vad_model = silero.VAD.load(
                min_speech_duration=0.3,  # Filter out short noises
                min_silence_duration=1.5,  # Wait 1.5s before deciding speech ended
            )
            logger.info("VAD model loaded successfully")


def start_voice_agent_background():
    """Start the voice agent in a background task with auto-reconnect."""
    loop = asyncio.new_event_loop()

    async def run_with_reconnect():
        """Run voice agent with automatic reconnection on disconnect."""
        connection_count = 0
        last_error: str | None = None

        while True:
            is_reconnect = connection_count > 0
            reconnect_reason = last_error if is_reconnect else None

            try:
                await run_voice_agent(is_reconnect=is_reconnect, reconnect_reason=reconnect_reason)
                last_error = None  # Clear error on successful run
            except Exception as e:
                logger.error(f"Voice agent error: {e}")
                last_error = str(e)[:50]  # Truncate long error messages

            connection_count += 1

            # Wait before reconnecting
            logger.info("Voice agent disconnected, reconnecting in 3 seconds...")
            await asyncio.sleep(3)

    def run():
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_with_reconnect())
        except Exception as e:
            logger.error(f"Voice agent crashed permanently: {e}")
        finally:
            loop.close()

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread
