#!/bin/bash

# Скрипт обновления бота на хостинге
# Использование: ./update-bot.sh

set -e

cd /opt/russian-trading-bot

echo "🔄 Обновление Russian Trading Bot..."

# Создание бэкапа перед обновлением
echo "💾 Создание бэкапа перед обновлением..."
./deploy-scripts/backup.sh

# Остановка сервисов
echo "🛑 Остановка сервисов..."
docker-compose -f docker-compose.hosting.yml down

# Здесь должен быть код получения новой версии
# Например, из Git репозитория:
# git pull origin main

echo "🏗️ Пересборка образов..."
docker-compose -f docker-compose.hosting.yml build --no-cache

echo "🚀 Запуск обновленных сервисов..."
docker-compose -f docker-compose.hosting.yml up -d

echo "⏳ Ожидание запуска..."
sleep 60

echo "🏥 Проверка здоровья системы..."
if curl -f http://localhost:8000/health; then
    echo "✅ Обновление завершено успешно!"
    
    # Уведомление об успешном обновлении
    if [ ! -z "$TELEGRAM_BOT_TOKEN" ] && [ ! -z "$TELEGRAM_CHAT_ID" ]; then
        curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
            -d chat_id="$TELEGRAM_CHAT_ID" \
            -d text="✅ Бот обновлен успешно!" > /dev/null
    fi
else
    echo "❌ Система не отвечает после обновления!"
    echo "🔄 Попытка отката к предыдущей версии..."
    
    # Здесь должен быть код отката
    docker-compose -f docker-compose.hosting.yml down
    # Восстановление из бэкапа...
    
    echo "📞 Свяжитесь с администратором для ручного восстановления"
    exit 1
fi

echo "📋 Статус сервисов:"
docker-compose -f docker-compose.hosting.yml ps