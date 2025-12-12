#!/bin/bash
# Backup context to S3
# Called by EventBridge schedule or pre-restart hook

set -e

REASON=${1:-"scheduled"}
WORKSPACE_DIR=${WORKSPACE:-/workspace}
CONTEXT_DIR="$WORKSPACE_DIR/.claude/context"
S3_BUCKET=${AIPA_BACKUP_BUCKET:-""}
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

if [ -z "$S3_BUCKET" ]; then
  echo "AIPA_BACKUP_BUCKET not set, skipping backup"
  exit 0
fi

echo "Starting context backup: $REASON"

# Create backup archive
BACKUP_FILE="/tmp/context-backup-$TIMESTAMP.tar.gz"
tar -czf "$BACKUP_FILE" -C "$WORKSPACE_DIR/.claude" context/

# Upload to S3 with intelligent tiering
aws s3 cp "$BACKUP_FILE" "s3://$S3_BUCKET/backups/context/$TIMESTAMP.tar.gz" \
  --storage-class INTELLIGENT_TIERING \
  --metadata "reason=$REASON,timestamp=$TIMESTAMP"

# Also sync current state (for quick restores)
aws s3 sync "$CONTEXT_DIR" "s3://$S3_BUCKET/current/context/" \
  --storage-class INTELLIGENT_TIERING \
  --delete

# Clean up
rm -f "$BACKUP_FILE"

# Keep only last 30 days of backups (handled by S3 lifecycle policy, but log)
echo "Backup completed: s3://$S3_BUCKET/backups/context/$TIMESTAMP.tar.gz"

# Record backup in state
echo "$REASON - $TIMESTAMP" >> "$WORKSPACE_DIR/.claude/state/backup-history.txt"
