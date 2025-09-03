#!/bin/bash

# Russian Trading Bot Backup Script
# Complies with Russian data residency requirements

set -e

# Configuration
BACKUP_DIR="/backups"
DB_NAME="russian_trading"
DB_USER="trading_user"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RETENTION_DAYS=30

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

echo "Starting backup process at $(date)"

# Database backup
echo "Backing up PostgreSQL database..."
pg_dump -h postgres -U "$DB_USER" -d "$DB_NAME" > "$BACKUP_DIR/db_backup_$TIMESTAMP.sql"

# Compress database backup
gzip "$BACKUP_DIR/db_backup_$TIMESTAMP.sql"

# Redis backup
echo "Backing up Redis data..."
redis-cli -h redis --rdb "$BACKUP_DIR/redis_backup_$TIMESTAMP.rdb"

# Application logs backup
echo "Backing up application logs..."
tar -czf "$BACKUP_DIR/logs_backup_$TIMESTAMP.tar.gz" /app/logs/

# Configuration backup
echo "Backing up configuration files..."
tar -czf "$BACKUP_DIR/config_backup_$TIMESTAMP.tar.gz" /app/config/

# Models backup (Russian sentiment models, etc.)
echo "Backing up ML models..."
tar -czf "$BACKUP_DIR/models_backup_$TIMESTAMP.tar.gz" /app/models/

# Create backup manifest
echo "Creating backup manifest..."
cat > "$BACKUP_DIR/backup_manifest_$TIMESTAMP.json" << EOF
{
  "timestamp": "$TIMESTAMP",
  "date": "$(date -Iseconds)",
  "timezone": "Europe/Moscow",
  "files": {
    "database": "db_backup_$TIMESTAMP.sql.gz",
    "redis": "redis_backup_$TIMESTAMP.rdb",
    "logs": "logs_backup_$TIMESTAMP.tar.gz",
    "config": "config_backup_$TIMESTAMP.tar.gz",
    "models": "models_backup_$TIMESTAMP.tar.gz"
  },
  "compliance": {
    "data_residency": "Russia",
    "retention_policy": "$RETENTION_DAYS days",
    "encryption": "AES-256"
  }
}
EOF

# Encrypt backups for Russian data protection compliance
echo "Encrypting backups..."
for file in "$BACKUP_DIR"/*_$TIMESTAMP.*; do
    if [[ "$file" != *.enc ]]; then
        openssl enc -aes-256-cbc -salt -in "$file" -out "$file.enc" -pass env:BACKUP_ENCRYPTION_KEY
        rm "$file"
    fi
done

# Clean up old backups
echo "Cleaning up old backups (older than $RETENTION_DAYS days)..."
find "$BACKUP_DIR" -name "*backup_*" -type f -mtime +$RETENTION_DAYS -delete

# Verify backup integrity
echo "Verifying backup integrity..."
for encrypted_file in "$BACKUP_DIR"/*_$TIMESTAMP.*.enc; do
    if openssl enc -aes-256-cbc -d -in "$encrypted_file" -pass env:BACKUP_ENCRYPTION_KEY > /dev/null 2>&1; then
        echo "✓ $encrypted_file - OK"
    else
        echo "✗ $encrypted_file - FAILED"
        exit 1
    fi
done

echo "Backup process completed successfully at $(date)"
echo "Backup files created:"
ls -la "$BACKUP_DIR"/*_$TIMESTAMP.*

# Send backup notification
curl -X POST "http://trading-bot:8000/api/notifications/backup" \
    -H "Content-Type: application/json" \
    -d "{\"status\": \"success\", \"timestamp\": \"$TIMESTAMP\", \"message\": \"Резервное копирование завершено успешно\"}"