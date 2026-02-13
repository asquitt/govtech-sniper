#!/bin/sh
set -eu

# ---- Configuration ----------------------------------------------------------
PGHOST="${POSTGRES_HOST:-postgres}"
PGUSER="${POSTGRES_USER:-rfpsniper}"
PGDATABASE="${POSTGRES_DB:-rfpsniper_db}"

export PGPASSWORD="${POSTGRES_PASSWORD:-rfpsniper_secret}"

# ---- Validate arguments -----------------------------------------------------
if [ $# -lt 1 ]; then
    echo "Usage: restore.sh <backup_file>"
    echo "Example: restore.sh /backups/rfpsniper_20260213_030000.sql.gz"
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "[restore] ERROR: File not found: ${BACKUP_FILE}"
    exit 1
fi

# ---- Safety prompt -----------------------------------------------------------
echo "========================================"
echo "  WARNING: This will DROP and recreate"
echo "  database '${PGDATABASE}' on ${PGHOST}"
echo "  from backup: ${BACKUP_FILE}"
echo "========================================"
echo "Proceeding in 5 seconds... (Ctrl+C to abort)"
sleep 5

# ---- Restore ----------------------------------------------------------------
echo "[restore] Dropping database ${PGDATABASE}..."
psql -h "$PGHOST" -U "$PGUSER" -d postgres -c "DROP DATABASE IF EXISTS \"${PGDATABASE}\";"
echo "[restore] Creating database ${PGDATABASE}..."
psql -h "$PGHOST" -U "$PGUSER" -d postgres -c "CREATE DATABASE \"${PGDATABASE}\" OWNER \"${PGUSER}\";"
echo "[restore] Restoring from ${BACKUP_FILE}..."
gunzip -c "$BACKUP_FILE" | psql -h "$PGHOST" -U "$PGUSER" -d "$PGDATABASE" --quiet
echo "[restore] Complete."
