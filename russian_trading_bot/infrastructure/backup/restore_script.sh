#!/bin/bash

# Russian Trading Bot Restore Script
# Complies with Russian data residency requirements

set -e

# Configuration
BACKUP_DIR="/backups"
DB_NAME="russian_trading"
DB_USER="trading_user"

# Check if timestamp is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <backup_timestamp>"
    echo "Available backups:"
    ls -la "$BACKUP_DIR"/backup_manifest_*.json | sed 's/.*backup_manifest_\(.*\)\.json/\1/'
    exit 1
fi

TIMESTAMP=$1

echo "Starting restore process for backup $TIMESTAMP at $(date)"

# Verify backup files exist
MANIFEST_FILE="$BACKUP_DIR/backup_manifest_$TIMESTAMP.json"
if [ ! -f "$MANIFEST_FILE" ]; then
    echo "Error: Backup manifest not found: $MANIFEST_FILE"
    exit 1
fi

# Read manifest
echo "Reading backup manifest..."
cat "$MANIFEST_FILE"

# Decrypt backup files
echo "Decrypting backup files..."
for encrypted_file in "$BACKUP_DIR"/*_$TIMESTAMP.*.enc; do
    if [ -f "$encrypted_file" ]; then
        decrypted_file="${encrypted_file%.enc}"
        openssl enc -aes-256-cbc -d -in "$encrypted_file" -out "$decrypted_file" -pass env:BACKUP_ENCRYPTION_KEY
        echo "✓ Decrypted: $(basename "$decrypted_file")"
    fi
done

# Stop services before restore
echo "Stopping services..."
docker-compose -f /app/infrastructure/docker-compose.prod.yml stop trading-bot

# Restore database
echo "Restoring PostgreSQL database..."
DB_BACKUP_FILE="$BACKUP_DIR/db_backup_$TIMESTAMP.sql.gz"
if [ -f "$DB_BACKUP_FILE" ]; then
    # Drop existing database and recreate
    psql -h postgres -U "$DB_USER" -c "DROP DATABASE IF EXISTS $DB_NAME;"
    psql -h postgres -U "$DB_USER" -c "CREATE DATABASE $DB_NAME WITH ENCODING='UTF8' LC_COLLATE='ru_RU.UTF-8' LC_CTYPE='ru_RU.UTF-8';"
    
    # Restore from backup
    gunzip -c "$DB_BACKUP_FILE" | psql -h postgres -U "$DB_USER" -d "$DB_NAME"
    echo "✓ Database restored successfully"
else
    echo "Warning: Database backup file not found: $DB_BACKUP_FILE"
fi

# Restore Redis data
echo "Restoring Redis data..."
REDIS_BACKUP_FILE="$BACKUP_DIR/redis_backup_$TIMESTAMP.rdb"
if [ -f "$REDIS_BACKUP_FILE" ]; then
    docker-compose -f /app/infrastructure/docker-compose.prod.yml stop redis
    docker cp "$REDIS_BACKUP_FILE" russian-trading-cache:/data/dump.rdb
    docker-compose -f /app/infrastructure/docker-compose.prod.yml start redis
    echo "✓ Redis data restored successfully"
else
    echo "Warning: Redis backup file not found: $REDIS_BACKUP_FILE"
fi

# Restore application logs
echo "Restoring application logs..."
LOGS_BACKUP_FILE="$BACKUP_DIR/logs_backup_$TIMESTAMP.tar.gz"
if [ -f "$LOGS_BACKUP_FILE" ]; then
    tar -xzf "$LOGS_BACKUP_FILE" -C /
    echo "✓ Application logs restored successfully"
else
    echo "Warning: Logs backup file not found: $LOGS_BACKUP_FILE"
fi

# Restore configuration
echo "Restoring configuration files..."
CONFIG_BACKUP_FILE="$BACKUP_DIR/config_backup_$TIMESTAMP.tar.gz"
if [ -f "$CONFIG_BACKUP_FILE" ]; then
    tar -xzf "$CONFIG_BACKUP_FILE" -C /
    echo "✓ Configuration files restored successfully"
else
    echo "Warning: Configuration backup file not found: $CONFIG_BACKUP_FILE"
fi

# Restore ML models
echo "Restoring ML models..."
MODELS_BACKUP_FILE="$BACKUP_DIR/models_backup_$TIMESTAMP.tar.gz"
if [ -f "$MODELS_BACKUP_FILE" ]; then
    tar -xzf "$MODELS_BACKUP_FILE" -C /
    echo "✓ ML models restored successfully"
else
    echo "Warning: Models backup file not found: $MODELS_BACKUP_FILE"
fi

# Clean up decrypted files
echo "Cleaning up temporary files..."
rm -f "$BACKUP_DIR"/*_$TIMESTAMP.sql.gz
rm -f "$BACKUP_DIR"/*_$TIMESTAMP.rdb
rm -f "$BACKUP_DIR"/*_$TIMESTAMP.tar.gz

# Restart services
echo "Restarting services..."
docker-compose -f /app/infrastructure/docker-compose.prod.yml start trading-bot

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 30

# Verify restore
echo "Verifying restore..."
if curl -f http://trading-bot:8000/health > /dev/null 2>&1; then
    echo "✓ Trading bot service is healthy"
else
    echo "✗ Trading bot service health check failed"
    exit 1
fi

echo "Restore process completed successfully at $(date)"

# Send restore notification
curl -X POST "http://trading-bot:8000/api/notifications/restore" \
    -H "Content-Type: application/json" \
    -d "{\"status\": \"success\", \"timestamp\": \"$TIMESTAMP\", \"message\": \"Восстановление из резервной копии завершено успешно\"}"