# AIPA - AI Personal Assistant
# Dockerfile for cloud deployment
#
# Build for ARM64 (Graviton/Apple Silicon) - 20% cheaper on AWS:
#   docker build --platform linux/arm64 -t aipa .
#
# Build for x86_64 (Intel/AMD):
#   docker build --platform linux/amd64 -t aipa .
#
# Multi-arch build (both):
#   docker buildx build --platform linux/amd64,linux/arm64 -t aipa --push .

FROM python:3.12-slim

# Install system dependencies including audio support for VoiceMode
RUN apt-get update && apt-get install -y \
    git \
    curl \
    ffmpeg \
    portaudio19-dev \
    libasound2-dev \
    libsndfile1 \
    build-essential \
    python3-dev \
    awscli \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20 (for MCP servers)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs

# Create non-root user
RUN useradd -m -s /bin/bash aipa && \
    mkdir -p /home/aipa/.local/bin /home/aipa/.config/claude /home/aipa/.claude && \
    chown -R aipa:aipa /home/aipa

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    cp /root/.local/bin/uv /usr/local/bin/ && \
    cp /root/.local/bin/uvx /usr/local/bin/

# Install Claude Code CLI and MCP servers
RUN npm install -g @anthropic-ai/claude-code \
    @notionhq/notion-mcp-server \
    @modelcontextprotocol/server-github

# Set working directory
WORKDIR /app
RUN chown -R aipa:aipa /app

# Copy dependency files first (for caching)
COPY --chown=aipa:aipa pyproject.toml uv.lock /app/

# Switch to non-root user
USER aipa

# Install dependencies (includes livekit-agents and plugins)
# Use system Python to avoid symlinks to host system paths in the venv
RUN uv venv /app/.venv --python python3 && \
    uv sync --frozen --no-dev

# Copy application code
COPY --chown=aipa:aipa . /app

# Copy workspace template (contains .claude config for production agent)
# This will be used to initialize the EFS-mounted /workspace on first run
COPY --chown=aipa:aipa workspace/ /app/workspace-template/

# Copy entrypoint script
USER root
COPY --chown=aipa:aipa docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# Create workspace directory (will be EFS mount point at runtime)
RUN mkdir -p /workspace/files /workspace/projects && \
    chown -R aipa:aipa /workspace
USER aipa

# Environment
ENV WORKSPACE=/workspace
ENV PATH="/app/.venv/bin:/home/aipa/.local/bin:$PATH"
ENV VIRTUAL_ENV=/app/.venv
ENV HOME=/home/aipa

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Use entrypoint to initialize workspace on first run
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Start server
CMD ["python", "-m", "server.main"]
