#!/bin/bash

# ClawSquad Backup Script
# Run this daily via cron or systemd timer

set -e

cd "$(dirname "$0")"

echo "🦞 ClawSquad Backup - $(date)"

# Check if database exists
if [ ! -f "clawsquad.db" ]; then
    echo "❌ Database file not found: clawsquad.db"
    echo "   Make sure ClawSquad is running and has created the database."
    exit 1
fi

# Create backups directory if it doesn't exist
mkdir -p backups

# Run Python backup script
python3 backup.py create --keep-days 7

# Show backup statistics
echo ""
echo "📊 Current backup status:"
python3 backup.py stats

# Optional: Sync to remote storage (GitHub/S3)
# Uncomment and configure as needed
# echo ""
# echo "🌐 Syncing to remote storage..."
# ./sync_backups.sh

echo ""
echo "✅ Backup completed at $(date)"