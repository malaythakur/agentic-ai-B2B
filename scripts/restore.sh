#!/bin/bash
# PostgreSQL Restore Script
# Usage: ./restore.sh <backup_file>

set -e

if [ $# -eq 0 ]; then
    echo "Usage: $0 <backup_file>"
    echo "Example: $0 ./backups/backup_ai_saas_20240101_120000.sql.gz"
    exit 1
fi

BACKUP_FILE="$1"
DB_NAME="${DB_NAME:-ai_saas}"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "WARNING: This will overwrite the existing database: $DB_NAME"
echo "Backup file: $BACKUP_FILE"
read -p "Are you sure you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Restore cancelled"
    exit 0
fi

echo "Starting restore..."

# Handle compressed backups
if [[ $BACKUP_FILE == *.gz ]]; then
    echo "Decompressing backup..."
    gunzip -c "$BACKUP_FILE" | psql "$DB_NAME"
elif [[ $BACKUP_FILE == *.dump ]]; then
    echo "Restoring from custom format dump..."
    pg_restore -d "$DB_NAME" "$BACKUP_FILE"
else
    echo "Restoring from SQL file..."
    psql "$DB_NAME" < "$BACKUP_FILE"
fi

echo "Restore completed successfully"
