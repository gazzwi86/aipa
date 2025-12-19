"""Main FastAPI application for AIPA."""

import logging
from contextlib import asynccontextmanager
from datetime import datetime

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from server.config import get_settings
from server.handlers.auth import router as auth_router
from server.handlers.chat import router as chat_router
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

    # Reduce noise from verbose libraries
    logging.getLogger("livekit").setLevel(logging.WARNING)
    logging.getLogger("livekit.agents").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("opentelemetry").setLevel(logging.WARNING)
    logging.getLogger("silero").setLevel(logging.WARNING)


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
templates = Jinja2Templates(directory="server/templates")

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
app.include_router(chat_router, tags=["chat"])
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

    return templates.TemplateResponse(
        "chat.html",
        {
            "request": request,
            "agent_name": settings.agent_name,
        },
    )


# Legacy inline HTML removed - now using templates/chat.html


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger = logging.getLogger(__name__)
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "An internal error occurred."})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=not settings.is_production)
