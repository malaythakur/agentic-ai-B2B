#!/bin/bash
# PostgreSQL Backup Script
# Run this script to backup the database

set -e

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
DB_NAME="${DB_NAME:-ai_saas}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/backup_${DB_NAME}_${TIMESTAMP}.sql"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

echo "Starting backup of database: $DB_NAME"
echo "Backup file: $BACKUP_FILE"

# Perform backup
if [ -n "$DATABASE_URL" ]; then
    # Use DATABASE_URL if available
    pg_dump "$DATABASE_URL" > "$BACKUP_FILE"
else
    # Use local connection
    pg_dump -Fc "$DB_NAME" > "${BACKUP_FILE}.dump"
fi

# Compress backup
gzip "$BACKUP_FILE"
echo "Backup completed: ${BACKUP_FILE}.gz"

# Cleanup old backups
find "$BACKUP_DIR" -name "backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete
echo "Cleaned up backups older than $RETENTION_DAYS days"

# Optional: Upload to S3 if configured
if [ -n "$S3_BUCKET" ]; then
    echo "Uploading to S3..."
    aws s3 cp "${BACKUP_FILE}.gz" "s3://$S3_BUCKET/backups/"
    echo "Upload completed"
fi

echo "Backup process completed successfully"
