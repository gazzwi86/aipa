"""Main FastAPI application for AIPA."""

import logging
from contextlib import asynccontextmanager
from datetime import datetime

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from server.config import get_settings
from server.handlers.auth import router as auth_router
from server.handlers.files import router as files_router
from server.handlers.sessions import router as sessions_router
from server.handlers.voice import router as voice_router
from server.models.requests import HealthResponse
from server.services.auth import get_auth_service


def setup_logging() -> None:
    """Configure structured logging."""
    settings = get_settings()

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
            if settings.is_production
            else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, settings.log_level.upper()),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger = logging.getLogger(__name__)
    settings = get_settings()

    logger.info(f"Starting {settings.agent_name} ({settings.environment})")

    if not settings.auth_password_hash:
        logger.warning("AUTH_PASSWORD_HASH not set - authentication disabled!")

    if settings.has_session_storage:
        logger.info(f"Session storage: DynamoDB ({settings.dynamodb_sessions_table})")
    else:
        logger.warning("DYNAMODB_SESSIONS_TABLE not set - sessions will be in-memory only")

    if not settings.livekit_url:
        logger.warning("LIVEKIT_URL not set - voice will not work!")
    else:
        # Start voice agent in background
        try:
            from server.services.voice_agent import (
                preload_voice_plugins,
                start_voice_agent_background,
            )

            # Pre-load plugins on main thread (required by LiveKit)
            preload_voice_plugins()
            logger.info("Starting voice agent...")
            start_voice_agent_background()
            logger.info("Voice agent started in background")
        except Exception as e:
            logger.error(f"Failed to start voice agent: {e}")

    logger.info("Application started")
    yield
    logger.info("Shutting down...")


# Create FastAPI app
setup_logging()
settings = get_settings()

app = FastAPI(
    title=f"AIPA - {settings.agent_name}",
    description="AI Personal Assistant",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url=None,
)

# Include routers
app.include_router(auth_router, tags=["auth"])
app.include_router(files_router, tags=["files"])
app.include_router(sessions_router, tags=["sessions"])
app.include_router(voice_router, tags=["voice"])


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint (no auth required)."""
    return HealthResponse(
        status="healthy",
        agent_name=settings.agent_name,
        environment=settings.environment,
        timestamp=datetime.utcnow(),
    )


@app.get("/")
async def index(request: Request) -> HTMLResponse:
    """Main voice UI page."""
    auth = get_auth_service()
    token = request.cookies.get("aipa_session")

    if not token or not auth.verify_session(token):
        return RedirectResponse(url="/login", status_code=302)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>{settings.agent_name}</title>
    <meta name="theme-color" content="#1a1a2e">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e8e8e8;
            min-height: 100vh;
            min-height: -webkit-fill-available;
            min-height: 100dvh;
            display: flex;
            flex-direction: column;
        }}
        html {{ height: -webkit-fill-available; }}

        .header {{
            padding: 0.75rem 1rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            flex-shrink: 0;
        }}
        .header h1 {{ font-size: 1.1rem; font-weight: 600; }}
        .header-links {{ display: flex; gap: 1rem; }}
        .header a {{ color: #8b8b9e; text-decoration: none; font-size: 0.8rem; }}
        .header a:hover {{ color: #e8e8e8; }}

        .chat-container {{
            flex: 1;
            overflow-y: auto;
            padding: 1rem;
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
            -webkit-overflow-scrolling: touch;
        }}
        .message {{
            max-width: 85%;
            padding: 0.75rem 1rem;
            border-radius: 1rem;
            font-size: 0.95rem;
            line-height: 1.4;
            word-break: break-word;
            animation: fadeIn 0.2s ease-out;
        }}
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(8px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        .message.user {{
            align-self: flex-end;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-bottom-right-radius: 0.25rem;
        }}
        .message.assistant {{
            align-self: flex-start;
            background: rgba(255,255,255,0.1);
            border-bottom-left-radius: 0.25rem;
        }}
        .message.system {{
            align-self: center;
            background: rgba(255,255,255,0.05);
            color: #8b8b9e;
            font-size: 0.85rem;
            padding: 0.5rem 1rem;
        }}
        .message.error {{
            background: rgba(239, 68, 68, 0.2);
            border: 1px solid rgba(239, 68, 68, 0.4);
            color: #fca5a5;
        }}
        .message.voice {{
            opacity: 0.8;
            font-style: italic;
        }}
        .message .source-label {{
            display: block;
            font-size: 0.7rem;
            opacity: 0.6;
            margin-bottom: 0.25rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        /* Error banner for critical errors */
        .error-banner {{
            background: linear-gradient(135deg, rgba(239, 68, 68, 0.9) 0%, rgba(185, 28, 28, 0.9) 100%);
            color: white;
            padding: 0.75rem 1rem;
            display: none;
            align-items: center;
            gap: 0.75rem;
            font-size: 0.9rem;
            flex-shrink: 0;
        }}
        .error-banner.visible {{ display: flex; }}
        .error-banner .error-icon {{ font-size: 1.2rem; }}
        .error-banner .error-text {{ flex: 1; }}
        .error-banner .error-dismiss {{
            background: rgba(255,255,255,0.2);
            border: none;
            color: white;
            padding: 0.25rem 0.75rem;
            border-radius: 0.25rem;
            cursor: pointer;
            font-size: 0.8rem;
        }}
        .error-banner .error-dismiss:hover {{ background: rgba(255,255,255,0.3); }}

        .input-area {{
            padding: 0.75rem 1rem 1rem;
            padding-bottom: max(1rem, env(safe-area-inset-bottom));
            border-top: 1px solid rgba(255,255,255,0.1);
            display: flex;
            gap: 0.75rem;
            align-items: flex-end;
            flex-shrink: 0;
            background: rgba(0,0,0,0.2);
        }}
        .text-input {{
            flex: 1;
            background: rgba(255,255,255,0.1);
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 1.5rem;
            padding: 0.75rem 1rem;
            color: #e8e8e8;
            font-size: 16px; /* Prevents iOS zoom */
            resize: none;
            max-height: 120px;
            line-height: 1.4;
            min-height: 48px;
        }}
        .text-input:focus {{ outline: none; border-color: #667eea; }}
        .text-input::placeholder {{ color: #6b6b7e; }}

        .voice-btn {{
            width: 48px;
            height: 48px;
            min-width: 48px;
            border-radius: 50%;
            border: none;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            font-size: 1.25rem;
            cursor: pointer;
            flex-shrink: 0;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
            -webkit-tap-highlight-color: transparent;
        }}
        .voice-btn:hover {{ transform: scale(1.05); }}
        .voice-btn:active {{ transform: scale(0.95); }}
        .voice-btn.listening {{
            background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
            animation: pulse 1.5s infinite;
        }}
        .voice-btn.speaking {{
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        }}
        .voice-btn.processing {{
            background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
            animation: processingPulse 2s infinite;
        }}
        .voice-btn:disabled {{ opacity: 0.5; cursor: not-allowed; }}
        @keyframes pulse {{
            0%, 100% {{ box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }}
            50% {{ box-shadow: 0 0 0 12px rgba(239, 68, 68, 0); }}
        }}
        @keyframes processingPulse {{
            0%, 100% {{ box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.4); }}
            50% {{ box-shadow: 0 0 0 8px rgba(245, 158, 11, 0); }}
        }}

        .send-btn {{
            width: 48px;
            height: 48px;
            min-width: 48px;
            border-radius: 50%;
            border: none;
            background: #667eea;
            color: white;
            font-size: 1.25rem;
            cursor: pointer;
            flex-shrink: 0;
            transition: all 0.2s;
            -webkit-tap-highlight-color: transparent;
        }}
        .send-btn:hover {{ background: #5a67d8; }}
        .send-btn:disabled {{ opacity: 0.5; cursor: not-allowed; }}

        .status-bar {{
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 0.5rem;
            font-size: 0.75rem;
            color: #6b6b7e;
            flex-shrink: 0;
        }}
        .status-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 0.5rem;
            background: #6b6b7e;
            flex-shrink: 0;
        }}
        .status-dot.connected {{ background: #10b981; }}
        .status-dot.connecting {{ background: #fbbf24; animation: blink 1s infinite; }}
        .status-dot.error {{ background: #ef4444; }}
        .status-dot.processing {{ background: #f59e0b; animation: blink 0.5s infinite; }}
        .status-dot.listening {{ background: #ef4444; animation: pulse-small 1s infinite; }}
        .status-dot.speaking {{ background: #10b981; animation: pulse-small 1s infinite; }}
        @keyframes blink {{ 50% {{ opacity: 0.5; }} }}
        @keyframes pulse-small {{
            0%, 100% {{ transform: scale(1); }}
            50% {{ transform: scale(1.3); }}
        }}

        /* Processing indicator (animated brain/thinking) */
        .processing-indicator {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.75rem 1rem;
            background: rgba(245, 158, 11, 0.1);
            border-radius: 1rem;
            border-bottom-left-radius: 0.25rem;
            animation: fadeIn 0.2s ease-out;
        }}
        .processing-indicator .brain-icon {{
            font-size: 1.2rem;
            animation: think 1s infinite;
        }}
        @keyframes think {{
            0%, 100% {{ transform: scale(1); }}
            50% {{ transform: scale(1.1); }}
        }}
        .processing-indicator .processing-text {{
            color: #fbbf24;
            font-size: 0.9rem;
        }}
        .processing-dots {{
            display: inline-flex;
            gap: 2px;
        }}
        .processing-dots span {{
            width: 4px;
            height: 4px;
            background: #fbbf24;
            border-radius: 50%;
            animation: processingDot 1.4s infinite;
        }}
        .processing-dots span:nth-child(2) {{ animation-delay: 0.2s; }}
        .processing-dots span:nth-child(3) {{ animation-delay: 0.4s; }}
        @keyframes processingDot {{
            0%, 60%, 100% {{ opacity: 0.3; }}
            30% {{ opacity: 1; }}
        }}

        .typing-indicator {{
            display: flex;
            gap: 4px;
            padding: 0.75rem 1rem;
        }}
        .typing-indicator span {{
            width: 8px;
            height: 8px;
            background: #667eea;
            border-radius: 50%;
            animation: typing 1.4s infinite;
        }}
        .typing-indicator span:nth-child(2) {{ animation-delay: 0.2s; }}
        .typing-indicator span:nth-child(3) {{ animation-delay: 0.4s; }}
        @keyframes typing {{
            0%, 60%, 100% {{ transform: translateY(0); }}
            30% {{ transform: translateY(-4px); }}
        }}

        /* Mobile responsiveness */
        @media (max-width: 480px) {{
            .header {{ padding: 0.5rem 0.75rem; }}
            .header h1 {{ font-size: 1rem; }}
            .header-links {{ gap: 0.75rem; }}
            .header a {{ font-size: 0.75rem; }}
            .chat-container {{ padding: 0.75rem; gap: 0.5rem; }}
            .message {{ max-width: 90%; padding: 0.6rem 0.85rem; font-size: 0.9rem; }}
            .input-area {{ padding: 0.5rem 0.75rem 0.75rem; gap: 0.5rem; }}
            .text-input {{ padding: 0.6rem 0.85rem; }}
            .voice-btn, .send-btn {{ width: 44px; height: 44px; min-width: 44px; font-size: 1.1rem; }}
        }}

        /* Large screens */
        @media (min-width: 768px) {{
            .chat-container {{ padding: 1.5rem 2rem; max-width: 800px; margin: 0 auto; width: 100%; }}
            .message {{ max-width: 75%; }}
        }}

        /* Service startup overlay */
        .startup-overlay {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            transition: opacity 0.5s ease-out;
        }}
        .startup-overlay.hidden {{
            opacity: 0;
            pointer-events: none;
        }}
        .startup-content {{
            text-align: center;
            padding: 2rem;
        }}
        .startup-icon {{
            font-size: 4rem;
            margin-bottom: 1.5rem;
            animation: float 2s ease-in-out infinite;
        }}
        @keyframes float {{
            0%, 100% {{ transform: translateY(0); }}
            50% {{ transform: translateY(-10px); }}
        }}
        .startup-title {{
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
        }}
        .startup-status {{
            color: #8b8b9e;
            font-size: 1rem;
            margin-bottom: 1.5rem;
        }}
        .startup-progress {{
            width: 200px;
            height: 4px;
            background: rgba(255,255,255,0.1);
            border-radius: 2px;
            overflow: hidden;
            margin: 0 auto;
        }}
        .startup-progress-bar {{
            height: 100%;
            width: 30%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            border-radius: 2px;
            animation: progress 1.5s ease-in-out infinite;
        }}
        @keyframes progress {{
            0% {{ transform: translateX(-100%); }}
            100% {{ transform: translateX(400%); }}
        }}
        .startup-hint {{
            margin-top: 2rem;
            font-size: 0.85rem;
            color: #6b6b7e;
        }}
    </style>
</head>
<body>
    <!-- Service startup overlay (shown while waking cold service) -->
    <div class="startup-overlay" id="startupOverlay">
        <div class="startup-content">
            <div class="startup-icon">🤖</div>
            <div class="startup-title">Waking {settings.agent_name}</div>
            <div class="startup-status" id="startupStatus">Checking service status...</div>
            <div class="startup-progress">
                <div class="startup-progress-bar"></div>
            </div>
            <div class="startup-hint">This takes 30-60 seconds on first access</div>
        </div>
    </div>

    <div class="header">
        <h1>{settings.agent_name}</h1>
        <div class="header-links">
            <a href="/files-page">Files</a>
            <a href="/logout">Logout</a>
        </div>
    </div>

    <div class="error-banner" id="errorBanner">
        <span class="error-icon">⚠️</span>
        <span class="error-text" id="errorText">An error occurred</span>
        <button class="error-dismiss" id="errorDismiss">Dismiss</button>
    </div>

    <div class="status-bar">
        <span class="status-dot connecting" id="statusDot"></span>
        <span id="statusText">Connecting...</span>
    </div>

    <div class="chat-container" id="chat">
        <div class="message system">Welcome! Click the microphone to start talking (auto-stops after 5s silence) or type a message.</div>
    </div>

    <div class="input-area">
        <textarea class="text-input" id="textInput" placeholder="Type a message..." rows="1"></textarea>
        <button class="voice-btn" id="voiceBtn" disabled title="Click to talk">🎤</button>
        <button class="send-btn" id="sendBtn" title="Send message">➤</button>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/livekit-client@2/dist/livekit-client.umd.min.js"></script>
    <script>
        // State
        let room = null;
        let isConnected = false;
        let isListening = false;
        let isSpeaking = false;
        let isProcessing = false;
        let audioContext = null;

        // Elements
        const chat = document.getElementById('chat');
        const textInput = document.getElementById('textInput');
        const voiceBtn = document.getElementById('voiceBtn');
        const sendBtn = document.getElementById('sendBtn');
        const statusDot = document.getElementById('statusDot');
        const statusText = document.getElementById('statusText');
        const errorBanner = document.getElementById('errorBanner');
        const errorText = document.getElementById('errorText');
        const errorDismiss = document.getElementById('errorDismiss');

        // Error banner handling
        function showError(message, autoDismiss = true) {{
            errorText.textContent = message;
            errorBanner.classList.add('visible');
            playErrorBeep();
            if (autoDismiss) {{
                setTimeout(() => hideError(), 10000);
            }}
        }}

        function hideError() {{
            errorBanner.classList.remove('visible');
        }}

        errorDismiss.addEventListener('click', hideError);

        // Audio feedback
        function getAudioContext() {{
            if (!audioContext) {{
                audioContext = new (window.AudioContext || window.webkitAudioContext)();
            }}
            if (audioContext.state === 'suspended') audioContext.resume();
            return audioContext;
        }}

        function playBeep(freq, duration, type = 'sine') {{
            try {{
                const ctx = getAudioContext();
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.type = type;
                osc.frequency.value = freq;
                gain.gain.value = 0.3;
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.start();
                gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + duration/1000);
                osc.stop(ctx.currentTime + duration/1000);
            }} catch(e) {{ console.log('Audio error:', e); }}
        }}

        function playStartBeep() {{ playBeep(440, 100); setTimeout(() => playBeep(660, 100), 120); }}
        function playStopBeep() {{ playBeep(660, 100); setTimeout(() => playBeep(440, 100), 120); }}
        function playErrorBeep() {{ playBeep(220, 200, 'sawtooth'); }}

        // Status
        function setStatus(status, text) {{
            statusDot.className = 'status-dot ' + status;
            statusText.textContent = text;
        }}

        // Update button states based on current state
        function updateButtonState() {{
            voiceBtn.classList.remove('listening', 'speaking', 'processing');
            if (isListening) {{
                voiceBtn.classList.add('listening');
            }} else if (isSpeaking) {{
                voiceBtn.classList.add('speaking');
            }} else if (isProcessing) {{
                voiceBtn.classList.add('processing');
            }}
        }}

        // Messages
        function addMessage(text, type, source = null) {{
            removeProcessing();
            const msg = document.createElement('div');
            msg.className = 'message ' + type;
            if (source === 'voice') {{
                msg.classList.add('voice');
            }}
            if (source) {{
                const label = document.createElement('span');
                label.className = 'source-label';
                label.textContent = source === 'voice' ? (type === 'user' ? '🎤 You said:' : '🔊 Ultra says:') : '';
                if (source === 'voice') {{
                    msg.appendChild(label);
                }}
            }}
            const content = document.createTextNode(text);
            msg.appendChild(content);
            chat.appendChild(msg);
            chat.scrollTop = chat.scrollHeight;
            return msg;
        }}

        function addTyping() {{
            removeTyping();
            const typing = document.createElement('div');
            typing.className = 'message assistant';
            typing.id = 'typing';
            typing.innerHTML = '<div class="typing-indicator"><span></span><span></span><span></span></div>';
            chat.appendChild(typing);
            chat.scrollTop = chat.scrollHeight;
        }}

        function removeTyping() {{
            const typing = document.getElementById('typing');
            if (typing) typing.remove();
        }}

        function addProcessing(message = 'Thinking') {{
            removeProcessing();
            removeTyping();
            isProcessing = true;
            updateButtonState();
            setStatus('processing', message + '...');
            const proc = document.createElement('div');
            proc.className = 'processing-indicator';
            proc.id = 'processing';
            proc.innerHTML = `
                <span class="brain-icon">🧠</span>
                <span class="processing-text">${{message}}<span class="processing-dots"><span></span><span></span><span></span></span></span>
            `;
            chat.appendChild(proc);
            chat.scrollTop = chat.scrollHeight;
        }}

        function removeProcessing() {{
            const proc = document.getElementById('processing');
            if (proc) proc.remove();
            if (isProcessing) {{
                isProcessing = false;
                updateButtonState();
                if (isConnected) {{
                    setStatus('connected', 'Connected');
                }}
            }}
        }}

        // LiveKit connection
        async function connect() {{
            setStatus('connecting', 'Connecting...');

            try {{
                // Get token from server
                const resp = await fetch('/api/voice/token');
                if (!resp.ok) {{
                    const err = await resp.json();
                    throw new Error(err.detail || 'Failed to get token');
                }}
                const {{ token, url, room: roomName }} = await resp.json();

                // Connect to LiveKit
                room = new LivekitClient.Room({{
                    adaptiveStream: true,
                    dynacast: true,
                }});

                room.on(LivekitClient.RoomEvent.Connected, () => {{
                    isConnected = true;
                    setStatus('connected', 'Connected');
                    voiceBtn.disabled = false;
                    addMessage('Voice connected. Ready to talk!', 'system');
                }});

                room.on(LivekitClient.RoomEvent.Disconnected, (reason) => {{
                    isConnected = false;
                    isProcessing = false;
                    isSpeaking = false;
                    setStatus('error', 'Disconnected');
                    voiceBtn.disabled = true;
                    updateButtonState();
                    if (reason) {{
                        showError('Disconnected: ' + reason);
                    }}
                }});

                room.on(LivekitClient.RoomEvent.Reconnecting, () => {{
                    setStatus('connecting', 'Reconnecting...');
                }});

                room.on(LivekitClient.RoomEvent.Reconnected, () => {{
                    setStatus('connected', 'Reconnected');
                    addMessage('Connection restored', 'system');
                }});

                room.on(LivekitClient.RoomEvent.TrackSubscribed, (track, publication, participant) => {{
                    if (track.kind === 'audio') {{
                        const audio = track.attach();
                        audio.volume = 1.0;
                        document.body.appendChild(audio);
                        // Track when audio starts/stops playing
                        audio.onplay = () => {{
                            isSpeaking = true;
                            updateButtonState();
                            setStatus('speaking', 'Speaking...');
                        }};
                        audio.onended = audio.onpause = () => {{
                            isSpeaking = false;
                            updateButtonState();
                            if (isConnected && !isListening && !isProcessing) {{
                                setStatus('connected', 'Connected');
                            }}
                        }};
                    }}
                }});

                room.on(LivekitClient.RoomEvent.TrackUnsubscribed, (track, publication, participant) => {{
                    if (track.kind === 'audio') {{
                        isSpeaking = false;
                        updateButtonState();
                    }}
                }});

                // Handle transcription and agent state events via data channel
                room.on(LivekitClient.RoomEvent.DataReceived, (data, participant) => {{
                    try {{
                        const msg = JSON.parse(new TextDecoder().decode(data));
                        console.log('Data received:', msg);

                        // Handle different message types
                        if (msg.type === 'transcript' || msg.type === 'transcription') {{
                            // User speech transcription (STT result)
                            if (msg.role === 'user' || msg.is_final) {{
                                addMessage(msg.text, 'user', 'voice');
                                addProcessing('Thinking');
                            }}
                        }} else if (msg.type === 'response' || msg.type === 'llm_response') {{
                            // Assistant response (before TTS)
                            removeProcessing();
                            addMessage(msg.text, 'assistant', 'voice');
                        }} else if (msg.type === 'agent_state') {{
                            // Handle agent state changes
                            if (msg.state === 'thinking' || msg.state === 'processing') {{
                                addProcessing('Thinking');
                            }} else if (msg.state === 'speaking') {{
                                removeProcessing();
                                setStatus('speaking', 'Speaking...');
                            }} else if (msg.state === 'listening') {{
                                removeProcessing();
                                setStatus('listening', 'Listening...');
                            }} else if (msg.state === 'idle') {{
                                removeProcessing();
                                setStatus('connected', 'Connected');
                            }}
                        }} else if (msg.type === 'error') {{
                            showError(msg.message || msg.error || 'An error occurred');
                            addMessage(msg.message || msg.error, 'error');
                        }}
                    }} catch(e) {{
                        console.log('Data parse error:', e);
                    }}
                }});

                // Handle participant events for agent presence
                room.on(LivekitClient.RoomEvent.ParticipantConnected, (participant) => {{
                    if (participant.identity.includes('agent') || participant.identity.includes('ultra')) {{
                        addMessage('Agent connected', 'system');
                    }}
                }});

                room.on(LivekitClient.RoomEvent.ParticipantDisconnected, (participant) => {{
                    if (participant.identity.includes('agent') || participant.identity.includes('ultra')) {{
                        addMessage('Agent disconnected', 'system');
                        showError('Voice agent disconnected. It may restart automatically.');
                    }}
                }});

                await room.connect(url, token);

            }} catch (error) {{
                console.error('Connection error:', error);
                setStatus('error', 'Connection failed');
                showError('Connection failed: ' + error.message);
                addMessage('Connection failed: ' + error.message, 'error');

                // Retry in 5 seconds
                setTimeout(connect, 5000);
            }}
        }}

        // Voice recording with silence detection
        let localAudioTrack = null;
        let silenceTimer = null;
        let analyser = null;
        let silenceCheckInterval = null;
        const SILENCE_THRESHOLD = 0.01;  // Audio level threshold
        const SILENCE_DURATION = 5000;   // 5 seconds of silence to stop

        async function startListening() {{
            if (isListening || !isConnected) return;

            try {{
                // Create and publish audio track to LiveKit
                localAudioTrack = await LivekitClient.createLocalAudioTrack({{
                    echoCancellation: true,
                    noiseSuppression: true,
                }});
                await room.localParticipant.publishTrack(localAudioTrack);

                // Set up audio analysis for silence detection
                const stream = localAudioTrack.mediaStream;
                if (stream) {{
                    const audioCtx = getAudioContext();
                    const source = audioCtx.createMediaStreamSource(stream);
                    analyser = audioCtx.createAnalyser();
                    analyser.fftSize = 256;
                    source.connect(analyser);

                    // Start monitoring for silence
                    startSilenceDetection();
                }}

                isListening = true;
                voiceBtn.classList.add('listening');
                playStartBeep();
                setStatus('connected', 'Listening...');

            }} catch (error) {{
                console.error('Mic error:', error);
                addMessage('Could not access microphone', 'error');
                playErrorBeep();
            }}
        }}

        function startSilenceDetection() {{
            const dataArray = new Uint8Array(analyser.frequencyBinCount);
            let lastSoundTime = Date.now();

            silenceCheckInterval = setInterval(() => {{
                if (!analyser || !isListening) return;

                analyser.getByteFrequencyData(dataArray);
                const average = dataArray.reduce((a, b) => a + b) / dataArray.length / 255;

                if (average > SILENCE_THRESHOLD) {{
                    lastSoundTime = Date.now();
                    setStatus('connected', 'Listening...');
                }} else {{
                    const silentFor = Date.now() - lastSoundTime;
                    if (silentFor > 1000) {{
                        setStatus('connected', `Silent ${{Math.floor(silentFor/1000)}}s...`);
                    }}
                    if (silentFor >= SILENCE_DURATION) {{
                        stopListening();
                    }}
                }}
            }}, 100);
        }}

        async function stopListening() {{
            if (!isListening) return;

            isListening = false;
            voiceBtn.classList.remove('listening');
            playStopBeep();
            setStatus('connected', 'Connected');

            // Clear silence detection
            if (silenceCheckInterval) {{
                clearInterval(silenceCheckInterval);
                silenceCheckInterval = null;
            }}
            analyser = null;

            // Unpublish and stop local audio track
            if (localAudioTrack) {{
                try {{
                    await room.localParticipant.unpublishTrack(localAudioTrack);
                    localAudioTrack.stop();
                }} catch (e) {{
                    console.log('Error stopping track:', e);
                }}
                localAudioTrack = null;
            }}
        }}

        function toggleListening() {{
            if (isListening) {{
                stopListening();
            }} else {{
                startListening();
            }}
        }}

        // Text input
        textInput.addEventListener('input', () => {{
            textInput.style.height = 'auto';
            textInput.style.height = Math.min(textInput.scrollHeight, 120) + 'px';
        }});

        textInput.addEventListener('keydown', (e) => {{
            if (e.key === 'Enter' && !e.shiftKey) {{
                e.preventDefault();
                sendText();
            }}
        }});

        sendBtn.addEventListener('click', sendText);

        async function sendText() {{
            const text = textInput.value.trim();
            if (!text) return;

            addMessage(text, 'user');
            textInput.value = '';
            textInput.style.height = 'auto';

            if (isConnected && room) {{
                // Send via LiveKit data channel
                const data = JSON.stringify({{ type: 'text', text }});
                try {{
                    room.localParticipant.publishData(new TextEncoder().encode(data), {{ reliable: true }});
                    addProcessing('Processing');
                }} catch (e) {{
                    console.error('Failed to send message:', e);
                    showError('Failed to send message');
                    removeProcessing();
                }}
            }} else {{
                showError('Not connected to voice service');
                addMessage('Not connected to voice service', 'error');
            }}
        }}

        // Voice button - click to toggle
        voiceBtn.addEventListener('click', toggleListening);

        // Initialize audio context on first interaction
        document.addEventListener('click', () => getAudioContext(), {{ once: true }});
        document.addEventListener('touchstart', () => getAudioContext(), {{ once: true }});

        // Service startup management
        const startupOverlay = document.getElementById('startupOverlay');
        const startupStatus = document.getElementById('startupStatus');

        function hideStartupOverlay() {{
            startupOverlay.classList.add('hidden');
            setTimeout(() => startupOverlay.style.display = 'none', 500);
        }}

        function showStartupOverlay() {{
            startupOverlay.style.display = 'flex';
            startupOverlay.classList.remove('hidden');
        }}

        async function checkAndWakeService() {{
            try {{
                // First check if we're running locally (no wake needed)
                const healthResp = await fetch('/health', {{ method: 'GET' }});
                if (healthResp.ok) {{
                    // Service is running locally, skip wake check
                    hideStartupOverlay();
                    connect();
                    return;
                }}
            }} catch (e) {{
                // Health check failed, try wake flow
            }}

            try {{
                startupStatus.textContent = 'Checking service status...';

                // Check status
                const statusResp = await fetch('/status');
                if (!statusResp.ok) {{
                    // Status endpoint not available (maybe local dev), just connect
                    hideStartupOverlay();
                    connect();
                    return;
                }}

                const status = await statusResp.json();
                console.log('Service status:', status);

                if (status.status === 'running') {{
                    startupStatus.textContent = 'Service ready!';
                    hideStartupOverlay();
                    connect();
                    return;
                }}

                if (status.status === 'stopped') {{
                    startupStatus.textContent = 'Starting service...';
                    // Wake the service
                    await fetch('/wake');
                }}

                // Poll for running status
                startupStatus.textContent = 'Waiting for service to start...';
                await pollUntilRunning();

            }} catch (error) {{
                console.log('Wake check error (may be local dev):', error);
                // If wake endpoints don't exist, just connect directly
                hideStartupOverlay();
                connect();
            }}
        }}

        async function pollUntilRunning(maxAttempts = 40) {{
            for (let i = 0; i < maxAttempts; i++) {{
                await new Promise(r => setTimeout(r, 3000)); // Wait 3 seconds

                try {{
                    const resp = await fetch('/status');
                    if (resp.ok) {{
                        const status = await resp.json();
                        console.log('Poll status:', status);

                        if (status.status === 'running') {{
                            startupStatus.textContent = 'Service ready!';
                            hideStartupOverlay();
                            connect();
                            return;
                        }}

                        const elapsed = (i + 1) * 3;
                        startupStatus.textContent = `Starting... (${{elapsed}}s)`;
                    }}
                }} catch (e) {{
                    console.log('Poll error:', e);
                }}
            }}

            // Timeout after maxAttempts
            startupStatus.textContent = 'Service taking too long. Please refresh.';
            showError('Service failed to start. Please refresh the page.');
        }}

        // Handle page visibility - pause/resume activity tracking
        document.addEventListener('visibilitychange', () => {{
            if (document.hidden) {{
                // Page is hidden - could notify server to track activity
                console.log('Page hidden');
            }} else {{
                // Page visible again
                console.log('Page visible');
            }}
        }});

        // Optional: notify on page close (for activity tracking, not immediate shutdown)
        window.addEventListener('beforeunload', () => {{
            // Use sendBeacon to reliably send data on page close
            // This just notifies the server - idle checker handles actual shutdown
            if (navigator.sendBeacon) {{
                navigator.sendBeacon('/api/voice/activity', JSON.stringify({{ event: 'page_close' }}));
            }}
        }});

        // Start the wake flow
        checkAndWakeService();
    </script>
</body>
</html>"""
    return HTMLResponse(content=html)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger = logging.getLogger(__name__)
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "An internal error occurred."})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=not settings.is_production)
