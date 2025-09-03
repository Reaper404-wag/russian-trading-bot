# 🚀 Быстрый запуск Russian Trading Bot

## 📋 Что нужно сделать перед запуском

### 1. Получить API ключи

#### MOEX API (обязательно)
- Регистрация не требуется для базового доступа
- Для расширенного доступа: https://www.moex.com/

#### Брокерские API (выберите один)
**Тинькофф Инвестиции (рекомендуется):**
1. Откройте счет: https://www.tinkoff.ru/invest/
2. В приложении: Еще → Настройки → Токен для API
3. Создайте токен с правами на торговлю

**Альтернативы:**
- Финам: https://finam.ru/
- Сбербанк Инвестиции: https://www.sberbank.ru/ru/person/investments
- ВТБ Инвестиции: https://broker.vtb.ru/

#### Уведомления (опционально)
**Telegram бот:**
1. Найдите @BotFather в Telegram
2. Создайте бота: `/newbot`
3. Получите токен
4. Узнайте свой chat_id: напишите боту, затем откройте:
   `https://api.telegram.org/bot<ВАШ_ТОКЕН>/getUpdates`

### 2. Установить Docker
- **Windows**: https://docs.docker.com/desktop/windows/install/
- **Linux**: `sudo apt install docker.io docker-compose`
- **macOS**: https://docs.docker.com/desktop/mac/install/

## ⚡ Запуск за 5 минут

### 1. Скачать и настроить
```bash
# Клонировать репозиторий
git clone <repository-url>
cd russian-trading-bot

# Скопировать конфигурацию
cp russian_trading_bot/infrastructure/.env.production.template .env.production
```

### 2. Минимальная настройка
Отредактируйте `.env.production` и заполните **только эти поля**:
```env
# Обязательные настройки
TINKOFF_API_TOKEN=ваш_токен_tinkoff_здесь
TELEGRAM_BOT_TOKEN=ваш_telegram_токен_здесь
TELEGRAM_CHAT_ID=ваш_chat_id_здесь

# Пароли (придумайте свои)
DB_PASSWORD=ваш_пароль_базы_данных
REDIS_PASSWORD=ваш_пароль_redis
GRAFANA_PASSWORD=ваш_пароль_grafana

# Безопасность (сгенерируйте случайные строки)
BACKUP_ENCRYPTION_KEY=32_символа_для_шифрования_бэкапов
JWT_SECRET_KEY=секретный_ключ_для_jwt_токенов
```

### 3. Запустить систему
```bash
# Режим разработки (для тестирования)
docker-compose up -d

# ИЛИ продакшн режим
# Linux:
./russian_trading_bot/infrastructure/deployment/deploy.sh

# Windows:
russian_trading_bot\infrastructure\deployment\deploy.bat
```

### 4. Проверить запуск
```bash
# Проверить статус сервисов
docker-compose ps

# Проверить логи
docker-compose logs -f trading-bot

# Открыть веб-интерфейс
# http://localhost
```

## 🎯 Первые шаги после запуска

### 1. Веб-интерфейс
Откройте http://localhost в браузере:
- Главная страница: обзор системы
- Портфель: текущие позиции
- Аналитика: графики и метрики
- Настройки: конфигурация торговли

### 2. Настройка торговли
В веб-интерфейсе → Настройки:
- **Режим торговли**: начните с "Бумажная торговля"
- **Размер позиции**: 1-5% от портфеля
- **Стоп-лосс**: 2-5%
- **Инструменты**: выберите 5-10 ликвидных акций (SBER, GAZP, LKOH, ROSN, NVTK)

### 3. Мониторинг
- **Grafana**: http://localhost:3000 (admin/ваш_пароль_grafana)
- **Telegram**: получите уведомление о запуске
- **Логи**: `docker-compose logs -f trading-bot`

## 🛡️ Безопасный старт

### Режим бумажной торговли
**ОБЯЗАТЕЛЬНО** начните с тестирования:
```env
# В .env.production
PAPER_TRADING_MODE=true
DEBUG_MODE=true
```

### Тестирование системы
1. Запустите в бумажном режиме на 1-2 недели
2. Проверьте качество сигналов
3. Убедитесь в стабильности системы
4. Только потом переходите к реальной торговле

### Ограничения рисков
```env
# Консервативные настройки для начала
MAX_POSITION_SIZE=0.01  # 1% на позицию
MAX_DAILY_LOSS=0.005    # 0.5% максимальная дневная потеря
STOP_LOSS_PERCENTAGE=0.02  # 2% стоп-лосс
```

## 🆘 Если что-то пошло не так

### Частые проблемы

#### "Не могу подключиться к API"
```bash
# Проверьте токены в .env.production
# Проверьте интернет соединение
curl -I https://iss.moex.com/iss/engines.json
```

#### "Сервисы не запускаются"
```bash
# Проверьте Docker
docker --version
docker-compose --version

# Перезапустите
docker-compose down
docker-compose up -d
```

#### "Веб-интерфейс не открывается"
```bash
# Проверьте порты
netstat -an | grep :8000
netstat -an | grep :80

# Проверьте логи nginx
docker-compose logs nginx
```

### Получить помощь
1. Проверьте логи: `docker-compose logs trading-bot`
2. Посмотрите статус: `docker-compose ps`
3. Проверьте здоровье: `curl http://localhost:8000/health`

## 📞 Контакты и поддержка

- **GitHub Issues**: для багов и предложений
- **Telegram**: @russian_trading_bot_support
- **Email**: support@russian-trading-bot.ru

## ⚠️ Важные напоминания

1. **Начинайте с бумажной торговли**
2. **Не инвестируйте больше, чем можете потерять**
3. **Регулярно проверяйте систему**
4. **Делайте резервные копии настроек**
5. **Следите за новостями и обновлениями**

---

**Удачной торговли! 🚀📈**