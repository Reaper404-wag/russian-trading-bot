# 🚀 Руководство по развертыванию Russian Trading Bot

## 📋 Обзор

Это руководство поможет развернуть Russian Trading Bot на различных платформах - от локальной разработки до продакшн-серверов.

## 🏠 Локальное развертывание

### Системные требования
- **ОС**: Windows 10+, macOS 10.15+, Ubuntu 18.04+
- **RAM**: 4 ГБ (рекомендуется 8 ГБ)
- **Диск**: 20 ГБ свободного места
- **Docker**: 20.10+
- **Docker Compose**: 2.0+

### Быстрый старт

1. **Подготовка**
```bash
git clone https://github.com/yourusername/russian-trading-bot.git
cd russian-trading-bot
cp .env.production.simple .env.production
```

2. **Настройка API ключей**
Отредактируйте `.env.production`:
```env
TINKOFF_API_TOKEN=ваш_токен_тинькофф
TELEGRAM_BOT_TOKEN=ваш_telegram_токен
TELEGRAM_CHAT_ID=ваш_chat_id
DB_PASSWORD=надежный_пароль
REDIS_PASSWORD=надежный_пароль
JWT_SECRET_KEY=случайная_строка_32_символа
BACKUP_ENCRYPTION_KEY=ключ_шифрования_32_символа
PAPER_TRADING_MODE=true
```

3. **Запуск**
```bash
# Разработка
docker-compose up -d

# Продакшн
docker-compose -f docker-compose.hosting.yml up -d
```

4. **Проверка**
- Веб-интерфейс: http://localhost:8000
- API здоровья: http://localhost:8000/health
- Grafana: http://localhost:3000

## ☁️ Облачное развертывание

### Рекомендуемые провайдеры

#### 🇷🇺 Российские (500-1500₽/месяц)
- **Timeweb** - простота, надежность
- **Beget** - доступные цены
- **REG.RU** - известный бренд
- **FirstVDS** - хорошее соотношение цена/качество

#### 🌍 Международные ($10-20/месяц)
- **DigitalOcean** - отличная документация
- **Vultr** - быстрые SSD
- **Linode** - стабильность
- **Hetzner** - европейские дата-центры

### Автоматическое развертывание

```bash
# Сделайте скрипт исполняемым
chmod +x deploy-to-hosting.sh

# Запустите развертывание
./deploy-to-hosting.sh your-server-ip
```

Скрипт автоматически:
- Установит Docker и Docker Compose
- Скопирует код на сервер
- Соберет и запустит контейнеры
- Проверит работоспособность

### Ручное развертывание

1. **Подготовка сервера**
```bash
# Подключение к серверу
ssh root@your-server-ip

# Обновление системы
apt update && apt upgrade -y

# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Установка Docker Compose
curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
```

2. **Копирование кода**
```bash
# Локально
tar -czf bot.tar.gz --exclude='.git' --exclude='__pycache__' .
scp bot.tar.gz root@your-server-ip:/opt/

# На сервере
cd /opt
tar -xzf bot.tar.gz
mv russian-trading-bot /opt/trading-bot
cd /opt/trading-bot
```

3. **Настройка и запуск**
```bash
# Создание рабочих директорий
mkdir -p logs backups data

# Запуск
docker-compose -f docker-compose.hosting.yml up -d
```

## 🐳 Docker конфигурации

### Разработка (docker-compose.yml)
- Открытые порты для отладки
- Монтирование исходного кода
- Режим разработки
- Подробное логирование

### Продакшн (docker-compose.hosting.yml)
- Минимальные открытые порты
- Оптимизированные образы
- Автоматический перезапуск
- Healthcheck'и

### Переменные окружения

#### Обязательные
```env
# API токены
TINKOFF_API_TOKEN=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Пароли
DB_PASSWORD=
REDIS_PASSWORD=

# Безопасность
JWT_SECRET_KEY=
BACKUP_ENCRYPTION_KEY=
```

#### Опциональные
```env
# Дополнительные брокеры
FINAM_API_KEY=
SBERBANK_API_TOKEN=

# Email уведомления
EMAIL_SMTP_HOST=
EMAIL_USERNAME=
EMAIL_PASSWORD=

# Настройки торговли
MAX_POSITION_SIZE=0.02
STOP_LOSS_PERCENTAGE=0.03
```

## 🔧 Управление сервисами

### Основные команды

```bash
# Статус сервисов
docker-compose -f docker-compose.hosting.yml ps

# Логи
docker-compose -f docker-compose.hosting.yml logs -f trading-bot

# Перезапуск
docker-compose -f docker-compose.hosting.yml restart trading-bot

# Остановка
docker-compose -f docker-compose.hosting.yml down

# Обновление
docker-compose -f docker-compose.hosting.yml pull
docker-compose -f docker-compose.hosting.yml up -d
```

### Мониторинг

```bash
# Использование ресурсов
docker stats

# Проверка здоровья
curl http://localhost:8000/health

# Системные метрики
htop
df -h
free -h
```

## 🛡️ Безопасность

### Базовая настройка

1. **Файрвол**
```bash
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp     # SSH
ufw allow 8000/tcp   # Trading Bot
ufw enable
```

2. **SSH безопасность**
```bash
# Смена порта SSH
nano /etc/ssh/sshd_config
# Port 2222

# Отключение root login
# PermitRootLogin no

systemctl restart sshd
```

3. **SSL сертификат**
```bash
# Установка Certbot
apt install certbot

# Получение сертификата
certbot certonly --standalone -d yourdomain.com

# Настройка автообновления
crontab -e
# 0 12 * * * /usr/bin/certbot renew --quiet
```

### Продвинутая безопасность

1. **Fail2Ban**
```bash
apt install fail2ban
systemctl enable fail2ban
```

2. **Мониторинг логов**
```bash
# Установка Logwatch
apt install logwatch

# Настройка ежедневных отчетов
echo "logwatch --output mail --mailto admin@yourdomain.com --detail high" > /etc/cron.daily/logwatch
```

## 📊 Мониторинг и алерты

### Grafana Dashboard

1. **Доступ**: http://your-server-ip:3000
2. **Логин**: admin / ваш_grafana_пароль
3. **Импорт дашборда**: используйте готовые шаблоны

### Prometheus метрики

- **Торговые сигналы**: количество, точность
- **Производительность**: P&L, Sharpe ratio
- **Система**: CPU, RAM, диск
- **API**: время отклика, ошибки

### Telegram алерты

Бот автоматически отправляет:
- ✅ Уведомления о запуске/остановке
- 🚨 Критические ошибки
- 📊 Ежедневные отчеты
- 💰 Крупные сделки

## 🔄 Резервное копирование

### Автоматические бэкапы

```bash
# Настройка cron
crontab -e

# Ежедневный бэкап в 3:00
0 3 * * * /opt/trading-bot/deploy-scripts/backup.sh

# Еженедельная очистка старых бэкапов
0 4 * * 0 find /opt/trading-bot/backups -name "*.tar.gz" -mtime +7 -delete
```

### Ручной бэкап

```bash
# Создание бэкапа
./deploy-scripts/backup.sh

# Восстановление
./deploy-scripts/restore.sh backup-2024-01-15.tar.gz
```

## 🆘 Устранение неполадок

### Частые проблемы

#### Сервисы не запускаются
```bash
# Проверка логов
docker-compose logs

# Проверка ресурсов
free -h
df -h

# Перезапуск
docker-compose down
docker-compose up -d
```

#### API не отвечает
```bash
# Проверка портов
netstat -tlnp | grep 8000

# Проверка процессов
docker ps

# Проверка конфигурации
cat .env.production
```

#### Высокое использование ресурсов
```bash
# Мониторинг ресурсов
docker stats

# Оптимизация
docker system prune -a

# Перезапуск сервисов
docker-compose restart
```

### Логи и диагностика

```bash
# Основные логи
tail -f logs/trading_bot.log

# Системные логи
journalctl -u docker
journalctl -f

# Логи конкретного контейнера
docker logs -f trading-bot
```

## 📈 Масштабирование

### Вертикальное масштабирование
- Увеличение CPU/RAM сервера
- Оптимизация конфигурации Docker
- Настройка пулов соединений

### Горизонтальное масштабирование
- Load balancer (nginx)
- Несколько экземпляров бота
- Распределенная база данных

### Оптимизация производительности
```yaml
# docker-compose.yml
services:
  trading-bot:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
```

## 📞 Поддержка

При возникновении проблем:

1. **Проверьте логи** - большинство проблем видны в логах
2. **GitHub Issues** - создайте issue с описанием проблемы
3. **Telegram** - @russian_trading_bot_support
4. **Email** - support@russian-trading-bot.ru

---

**🎯 Успешного развертывания!**