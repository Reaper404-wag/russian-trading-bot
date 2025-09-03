#!/bin/bash

# Простой скрипт мониторинга для хостинга
# Запускается через cron каждые 5 минут

set -e

cd /opt/russian-trading-bot

# Функция отправки уведомления в Telegram
send_alert() {
    local message="$1"
    if [ ! -z "$TELEGRAM_BOT_TOKEN" ] && [ ! -z "$TELEGRAM_CHAT_ID" ]; then
        curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
            -d chat_id="$TELEGRAM_CHAT_ID" \
            -d text="🚨 ALERT: $message" > /dev/null
    fi
    echo "ALERT: $message"
}

# Проверка работы контейнеров
echo "🔍 Проверка контейнеров..."
if ! docker-compose -f docker-compose.hosting.yml ps | grep -q "Up"; then
    send_alert "Один или несколько контейнеров не работают!"
    exit 1
fi

# Проверка API
echo "🌐 Проверка API..."
if ! curl -f -s http://localhost:8000/health > /dev/null; then
    send_alert "API не отвечает!"
    
    # Попытка перезапуска
    echo "🔄 Попытка перезапуска..."
    docker-compose -f docker-compose.hosting.yml restart trading-bot
    sleep 30
    
    if ! curl -f -s http://localhost:8000/health > /dev/null; then
        send_alert "API не восстановился после перезапуска!"
        exit 1
    else
        send_alert "API восстановлен после перезапуска"
    fi
fi

# Проверка использования диска
echo "💾 Проверка свободного места..."
disk_usage=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $disk_usage -gt 85 ]; then
    send_alert "Мало свободного места на диске: ${disk_usage}% использовано"
fi

# Проверка использования памяти
echo "🧠 Проверка памяти..."
memory_usage=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
if [ $memory_usage -gt 90 ]; then
    send_alert "Высокое использование памяти: ${memory_usage}%"
fi

# Проверка логов на ошибки
echo "📝 Проверка логов на критические ошибки..."
if docker-compose -f docker-compose.hosting.yml logs --tail=100 trading-bot | grep -i "critical\|fatal\|emergency" > /dev/null; then
    send_alert "Обнаружены критические ошибки в логах!"
fi

# Проверка количества неудачных торговых операций
echo "📊 Проверка торговых операций..."
# Здесь можно добавить проверку базы данных на количество неудачных операций

echo "✅ Мониторинг завершен, все в порядке"