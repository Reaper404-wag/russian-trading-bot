#!/bin/bash

# Простой скрипт развертывания на хостинге
# Использование: ./deploy-to-hosting.sh your-server-ip

set -e

if [ -z "$1" ]; then
    echo "❌ Укажите IP адрес сервера"
    echo "Использование: ./deploy-to-hosting.sh your-server-ip"
    exit 1
fi

SERVER_IP="$1"
SERVER_USER="root"  # Измените если нужно

echo "🚀 Развертывание Russian Trading Bot на сервере $SERVER_IP"

# Проверка наличия .env.production
if [ ! -f ".env.production" ]; then
    echo "❌ Файл .env.production не найден!"
    echo "Скопируйте .env.production.simple в .env.production и заполните настройки"
    exit 1
fi

# Создание архива для отправки
echo "📦 Подготовка файлов..."
tar -czf bot-deploy.tar.gz \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='.pytest_cache' \
    --exclude='node_modules' \
    --exclude='.venv' \
    --exclude='logs' \
    russian_trading_bot/ \
    models/ \
    docker-compose.hosting.yml \
    Dockerfile \
    requirements.txt \
    .env.production \
    deploy-scripts/

echo "📤 Копирование на сервер..."
scp bot-deploy.tar.gz $SERVER_USER@$SERVER_IP:/tmp/

echo "🔧 Установка и запуск на сервере..."
ssh $SERVER_USER@$SERVER_IP << 'ENDSSH'
    set -e
    
    echo "🛑 Остановка старой версии (если есть)..."
    cd /opt/russian-trading-bot 2>/dev/null && docker-compose -f docker-compose.hosting.yml down || true
    
    echo "📁 Создание директории проекта..."
    mkdir -p /opt/russian-trading-bot
    cd /opt/russian-trading-bot
    
    echo "📦 Распаковка новой версии..."
    tar -xzf /tmp/bot-deploy.tar.gz
    
    echo "📁 Создание рабочих директорий..."
    mkdir -p logs backups config data
    chmod 755 logs backups config data
    
    echo "🐳 Проверка Docker..."
    if ! command -v docker &> /dev/null; then
        echo "📥 Установка Docker..."
        curl -fsSL https://get.docker.com -o get-docker.sh
        sh get-docker.sh
        systemctl enable docker
        systemctl start docker
        rm get-docker.sh
    fi
    
    echo "🐙 Проверка Docker Compose..."
    if ! command -v docker-compose &> /dev/null; then
        echo "📥 Установка Docker Compose..."
        curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
    fi
    
    echo "🏗️ Сборка и запуск контейнеров..."
    docker-compose -f docker-compose.hosting.yml build
    docker-compose -f docker-compose.hosting.yml up -d
    
    echo "⏳ Ожидание запуска сервисов..."
    sleep 60
    
    echo "🏥 Проверка состояния сервисов..."
    docker-compose -f docker-compose.hosting.yml ps
    
    echo "🌐 Проверка API..."
    if curl -f http://localhost:8000/health; then
        echo "✅ API отвечает!"
    else
        echo "❌ API не отвечает, проверьте логи:"
        docker-compose -f docker-compose.hosting.yml logs trading-bot
    fi
    
    echo "🧹 Очистка временных файлов..."
    rm /tmp/bot-deploy.tar.gz
    
    echo "📋 Полезные команды:"
    echo "  Логи:           docker-compose -f docker-compose.hosting.yml logs -f trading-bot"
    echo "  Статус:         docker-compose -f docker-compose.hosting.yml ps"
    echo "  Перезапуск:     docker-compose -f docker-compose.hosting.yml restart"
    echo "  Остановка:      docker-compose -f docker-compose.hosting.yml down"
ENDSSH

echo ""
echo "🎉 Развертывание завершено!"
echo ""
echo "🌐 Ваш бот доступен по адресу: http://$SERVER_IP:8000"
echo "🏥 Проверка здоровья: http://$SERVER_IP:8000/health"
echo ""
echo "📋 Следующие шаги:"
echo "1. Проверьте работу бота в браузере"
echo "2. Убедитесь что PAPER_TRADING_MODE=true"
echo "3. Настройте торговые параметры через веб-интерфейс"
echo "4. Мониторьте логи первые дни"
echo ""
echo "🔧 Управление ботом на сервере:"
echo "ssh $SERVER_USER@$SERVER_IP"
echo "cd /opt/russian-trading-bot"
echo "docker-compose -f docker-compose.hosting.yml logs -f trading-bot"

# Очистка локального архива
rm bot-deploy.tar.gz