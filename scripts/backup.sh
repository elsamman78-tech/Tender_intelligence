#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p backups
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
ARCHIVE="backups/tender-backup-${STAMP}.tar.gz"
tar -czf "$ARCHIVE" data
find backups -type f -name 'tender-backup-*.tar.gz' -mtime +30 -delete 2>/dev/null || true
echo "$ARCHIVE"
