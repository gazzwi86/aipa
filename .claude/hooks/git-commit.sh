#!/bin/bash
# Auto-commit hook for .claude/ changes
# Usage: git-commit.sh <event_type>
# Event types: skill_created, agent_created, context_updated, command_created

set -e

EVENT_TYPE="${1:-unknown}"
CLAUDE_DIR="$(dirname "$(dirname "$0")")"
cd "$CLAUDE_DIR/.."

# Determine commit message based on event
case "$EVENT_TYPE" in
    skill_created)
        MSG="[auto] skill: Add new skill"
        ;;
    agent_created)
        MSG="[auto] agent: Add new agent"
        ;;
    context_updated)
        MSG="[auto] context: Update context files"
        ;;
    command_created)
        MSG="[auto] command: Add new command"
        ;;
    *)
        MSG="[auto] Update .claude configuration"
        ;;
esac

# Check if there are changes to commit
if git diff --quiet .claude/ && git diff --cached --quiet .claude/; then
    echo "No changes to commit in .claude/"
    exit 0
fi

# Stage and commit changes
git add .claude/
git commit -m "$MSG" || true

echo "Committed: $MSG"
