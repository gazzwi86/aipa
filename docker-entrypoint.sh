#!/bin/bash
# AIPA Docker Entrypoint
# Initializes workspace and Claude Code configuration on first run

set -e

WORKSPACE_DIR=${WORKSPACE:-/workspace}
TEMPLATE_DIR="/app/workspace-template/.claude"
MCP_CONFIG_DIR="/home/aipa/.config/claude"

echo "AIPA Docker Entrypoint starting..."

# Initialize workspace .claude directory if empty
if [ ! -f "$WORKSPACE_DIR/.claude/CLAUDE.md" ]; then
    echo "Initializing workspace .claude directory from template..."

    # Create the directory structure
    mkdir -p "$WORKSPACE_DIR/.claude"

    # Copy template if it exists
    if [ -d "$TEMPLATE_DIR" ]; then
        cp -r "$TEMPLATE_DIR"/* "$WORKSPACE_DIR/.claude/"
        echo "Workspace .claude directory initialized"
    else
        echo "Warning: Template directory not found at $TEMPLATE_DIR"
    fi
fi

# Copy MCP config to workspace if template exists and workspace config doesn't
if [ -f "/app/workspace-template/.mcp.json" ] && [ ! -f "$WORKSPACE_DIR/.mcp.json" ]; then
    echo "Copying MCP config to workspace..."
    cp "/app/workspace-template/.mcp.json" "$WORKSPACE_DIR/.mcp.json"
fi

# Set up global MCP config for Claude Code
mkdir -p "$MCP_CONFIG_DIR"
if [ -f "$WORKSPACE_DIR/.mcp.json" ]; then
    echo "Linking MCP config to global location..."
    ln -sf "$WORKSPACE_DIR/.mcp.json" "$MCP_CONFIG_DIR/mcp.json"
fi

# Set up backup bucket environment variable from infrastructure
if [ -n "$S3_BUCKET" ] && [ -z "$AIPA_BACKUP_BUCKET" ]; then
    # Derive backup bucket name from files bucket name (replace -files- with -backups-)
    export AIPA_BACKUP_BUCKET="${S3_BUCKET/-files-/-backups-}"
fi

# Ensure state directory exists
mkdir -p "$WORKSPACE_DIR/.claude/state"

# Check for pending tasks from previous run
if [ -f "$WORKSPACE_DIR/.claude/state/pending-task.json" ]; then
    echo "Found pending task from previous session"
fi

echo "AIPA Docker Entrypoint complete"
echo "Workspace: $WORKSPACE_DIR"
echo "MCP Config: $MCP_CONFIG_DIR/mcp.json"

# Execute the main command
exec "$@"
