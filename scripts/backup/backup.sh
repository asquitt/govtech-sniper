#!/bin/sh
set -eu

# ---- Configuration ----------------------------------------------------------
PGHOST="${POSTGRES_HOST:-postgres}"
PGUSER="${POSTGRES_USER:-rfpsniper}"
PGDATABASE="${POSTGRES_DB:-rfpsniper_db}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"

export PGPASSWORD="${POSTGRES_PASSWORD:-rfpsniper_secret}"

# ---- Backup -----------------------------------------------------------------
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="rfpsniper_${TIMESTAMP}.sql.gz"
FILEPATH="${BACKUP_DIR}/${FILENAME}"

echo "[backup] Starting backup: ${FILENAME}"
pg_dump -h "$PGHOST" -U "$PGUSER" -d "$PGDATABASE" | gzip > "$FILEPATH"
SIZE=$(du -h "$FILEPATH" | cut -f1)
echo "[backup] Complete: ${FILENAME} (${SIZE})"

# ---- Prune old backups ------------------------------------------------------
if [ "$RETENTION_DAYS" -gt 0 ]; then
    DELETED=$(find "$BACKUP_DIR" -name "rfpsniper_*.sql.gz" -mtime +"$RETENTION_DAYS" -print -delete | wc -l)
    echo "[backup] Pruned ${DELETED} backups older than ${RETENTION_DAYS} days"
fi
