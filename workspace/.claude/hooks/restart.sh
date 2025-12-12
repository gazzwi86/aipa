#!/bin/bash
# Pre-restart hook - saves state before container restart
# Called when agent needs to restart (new skill, dependency added, etc.)

set -e

REASON=${1:-"manual"}
WORKSPACE_DIR=${WORKSPACE:-/workspace}
STATE_DIR="$WORKSPACE_DIR/.claude/state"

echo "Preparing for restart: $REASON"

# Ensure state directory exists
mkdir -p "$STATE_DIR"

# Save current task if one exists
if [ -f /tmp/current-task.json ]; then
  cp /tmp/current-task.json "$STATE_DIR/pending-task.json"
  echo "Saved pending task"
fi

# Export conversation context if claude supports it
if command -v claude &> /dev/null; then
  claude --export-context > "$STATE_DIR/conversation.json" 2>/dev/null || true
fi

# Record restart reason with timestamp
echo "$REASON - $(date -Iseconds)" >> "$STATE_DIR/restart-history.txt"

# Update last-healthy timestamp
date -Iseconds > "$STATE_DIR/last-healthy.txt"

# Trigger context backup to S3 before restart
if [ -f "$WORKSPACE_DIR/.claude/hooks/backup-context.sh" ]; then
  "$WORKSPACE_DIR/.claude/hooks/backup-context.sh" "pre-restart" || echo "Backup failed, continuing with restart"
fi

echo "State saved, ready for restart"
