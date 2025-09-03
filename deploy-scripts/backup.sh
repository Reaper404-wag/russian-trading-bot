#!/bin/bash

# Простой скрипт резервного копирования для хостинга
# Запускается через cron каждый день

set -e

BACKUP_DIR="/opt/russian-trading-bot/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=7

echo "💾 Создание резервной копии $DATE..."

# Создание директории для бэкапов
mkdir -p $BACKUP_DIR

# Резервная копия базы данных
echo "📊 Бэкап базы данных..."
cd /opt/russian-trading-bot
docker-compose -f docker-compose.hosting.yml exec -T postgres pg_dump -U trading_user russian_trading > $BACKUP_DIR/db_backup_$DATE.sql

# Сжатие бэкапа
gzip $BACKUP_DIR/db_backup_$DATE.sql

# Резервная копия конфигурации
echo "⚙️ Бэкап конфигурации..."
tar -czf $BACKUP_DIR/config_backup_$DATE.tar.gz .env.production docker-compose.hosting.yml

# Резервная копия логов
echo "📝 Бэкап логов..."
tar -czf $BACKUP_DIR/logs_backup_$DATE.tar.gz logs/

# Удаление старых бэкапов
echo "🧹 Удаление старых бэкапов (старше $RETENTION_DAYS дней)..."
find $BACKUP_DIR -name "*backup_*" -type f -mtime +$RETENTION_DAYS -delete

# Список созданных бэкапов
echo "✅ Резервное копирование завершено!"
echo "📁 Созданные файлы:"
ls -la $BACKUP_DIR/*$DATE*

# Отправка уведомления (если настроен Telegram)
if [ ! -z "$TELEGRAM_BOT_TOKEN" ] && [ ! -z "$TELEGRAM_CHAT_ID" ]; then
    curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
        -d chat_id="$TELEGRAM_CHAT_ID" \
        -d text="✅ Резервная копия создана: $DATE" > /dev/null
fi