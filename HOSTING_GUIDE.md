# 🌐 Руководство по развертыванию на хостинге

## 💰 Дешевые варианты хостинга (300-1500₽/месяц)

### 🇷🇺 Российские провайдеры

#### 1. **Timeweb** (рекомендуется) ⭐⭐⭐⭐⭐
```
Конфигурация: 1 CPU, 2GB RAM, 25GB SSD
Стоимость: ~500₽/месяц
Плюсы: Простая панель, хорошая поддержка, российская юрисдикция
Сайт: timeweb.com
```

#### 2. **Beget**
```
Конфигурация: 1 CPU, 2GB RAM, 20GB SSD  
Стоимость: ~400₽/месяц
Плюсы: Дешево, стабильно
Сайт: beget.com
```

#### 3. **REG.RU**
```
Конфигурация: 2 CPU, 2GB RAM, 30GB SSD
Стоимость: ~800₽/месяц  
Плюсы: Известный бренд, много дополнительных услуг
Сайт: reg.ru
```

#### 4. **FirstVDS**
```
Конфигурация: 1 CPU, 2GB RAM, 25GB SSD
Стоимость: ~600₽/месяц
Плюсы: Хорошее соотношение цена/качество
Сайт: firstvds.ru
```

### 🌍 Зарубежные провайдеры (если нет ограничений)

#### 1. **DigitalOcean**
```
Конфигурация: 1 CPU, 2GB RAM, 50GB SSD
Стоимость: ~$12/месяц (≈900₽)
Плюсы: Отличная документация, стабильность
```

#### 2. **Vultr**
```
Конфигурация: 1 CPU, 2GB RAM, 55GB SSD
Стоимость: ~$10/месяц (≈750₽)
Плюсы: Быстрые SSD, много локаций
```

## 🚀 Пошаговое развертывание

### Шаг 1: Подготовка локально (5 минут)

```bash
# 1. Скопируйте конфигурацию
cp .env.production.simple .env.production

# 2. Отредактируйте .env.production (заполните ваши данные):
nano .env.production
```

**Обязательно заполните:**
- `TINKOFF_API_TOKEN` - токен из Тинькофф Инвестиции
- `TELEGRAM_BOT_TOKEN` - токен Telegram бота
- `TELEGRAM_CHAT_ID` - ваш chat ID
- `DB_PASSWORD` - пароль для базы данных
- `REDIS_PASSWORD` - пароль для Redis
- `JWT_SECRET_KEY` - случайная строка 32+ символа
- `BACKUP_ENCRYPTION_KEY` - случайная строка 32+ символа

### Шаг 2: Заказ и настройка сервера (10 минут)

1. **Зарегистрируйтесь** у выбранного провайдера
2. **Закажите VPS** с Ubuntu 20.04/22.04
3. **Получите IP адрес** и данные для подключения
4. **Подключитесь по SSH:**
   ```bash
   ssh root@your-server-ip
   ```

### Шаг 3: Развертывание (5 минут)

```bash
# Сделайте скрипт исполняемым
chmod +x deploy-to-hosting.sh

# Запустите развертывание
./deploy-to-hosting.sh your-server-ip
```

**Скрипт автоматически:**
- Установит Docker и Docker Compose
- Скопирует код на сервер
- Соберет и запустит контейнеры
- Проверит работоспособность

### Шаг 4: Проверка работы (2 минуты)

```bash
# Откройте в браузере
http://your-server-ip:8000

# Проверьте здоровье API
http://your-server-ip:8000/health
```

## 🔧 Управление ботом на сервере

### Подключение к серверу
```bash
ssh root@your-server-ip
cd /opt/russian-trading-bot
```

### Основные команды
```bash
# Просмотр логов
docker-compose -f docker-compose.hosting.yml logs -f trading-bot

# Статус сервисов
docker-compose -f docker-compose.hosting.yml ps

# Перезапуск бота
docker-compose -f docker-compose.hosting.yml restart trading-bot

# Остановка всех сервисов
docker-compose -f docker-compose.hosting.yml down

# Запуск всех сервисов
docker-compose -f docker-compose.hosting.yml up -d

# Обновление бота
./deploy-scripts/update-bot.sh

# Создание бэкапа
./deploy-scripts/backup.sh
```

## 📊 Настройка автоматизации

### Автоматические бэкапы
```bash
# Добавьте в cron (выполните на сервере)
crontab -e

# Добавьте строку (бэкап каждый день в 3:00)
0 3 * * * /opt/russian-trading-bot/deploy-scripts/backup.sh
```

### Автоматический мониторинг
```bash
# Добавьте в cron (проверка каждые 5 минут)
*/5 * * * * /opt/russian-trading-bot/deploy-scripts/monitor.sh
```

## 🛡️ Базовая безопасность

### Настройка файрвола
```bash
# Выполните на сервере
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH
ufw allow 8000/tcp  # Ваш бот
ufw enable
```

### Смена SSH порта (рекомендуется)
```bash
# Отредактируйте конфигурацию SSH
nano /etc/ssh/sshd_config

# Найдите строку #Port 22 и замените на:
Port 2222

# Перезапустите SSH
systemctl restart sshd

# Не забудьте открыть новый порт в файрволе
ufw allow 2222/tcp
ufw delete allow 22/tcp
```

## 📈 Мониторинг и алерты

### Telegram уведомления
Бот автоматически отправляет уведомления в Telegram:
- ✅ Успешный запуск
- 🚨 Критические ошибки
- 💾 Результаты бэкапов
- 📊 Важные торговые события

### Проверка логов
```bash
# Последние 100 строк логов
docker-compose -f docker-compose.hosting.yml logs --tail=100 trading-bot

# Следить за логами в реальном времени
docker-compose -f docker-compose.hosting.yml logs -f trading-bot

# Поиск ошибок в логах
docker-compose -f docker-compose.hosting.yml logs trading-bot | grep -i error
```

## 🆘 Решение проблем

### Бот не запускается
```bash
# Проверьте статус контейнеров
docker-compose -f docker-compose.hosting.yml ps

# Посмотрите логи
docker-compose -f docker-compose.hosting.yml logs trading-bot

# Проверьте конфигурацию
cat .env.production
```

### API не отвечает
```bash
# Проверьте порт
netstat -tlnp | grep 8000

# Перезапустите контейнер
docker-compose -f docker-compose.hosting.yml restart trading-bot

# Проверьте здоровье
curl http://localhost:8000/health
```

### Нехватка места на диске
```bash
# Проверьте использование диска
df -h

# Очистите старые Docker образы
docker system prune -a

# Очистите старые логи
docker-compose -f docker-compose.hosting.yml logs --tail=0 trading-bot
```

### Высокое использование памяти
```bash
# Проверьте использование памяти
free -h

# Перезапустите сервисы
docker-compose -f docker-compose.hosting.yml restart
```

## 💡 Оптимизация расходов

### Минимальная конфигурация (300-500₽/месяц)
- 1 CPU, 1GB RAM, 20GB SSD
- Подходит для начального тестирования
- Может работать медленно при высокой нагрузке

### Рекомендуемая конфигурация (500-800₽/месяц)
- 1-2 CPU, 2GB RAM, 25-40GB SSD
- Комфортная работа
- Запас для роста

### Расширенная конфигурация (800-1500₽/месяц)
- 2-4 CPU, 4GB RAM, 50-80GB SSD
- Для активной торговли
- Быстрая обработка данных

## 📋 Чек-лист после развертывания

- [ ] ✅ Бот запустился и отвечает на http://your-ip:8000
- [ ] ✅ API здоровья работает: http://your-ip:8000/health
- [ ] ✅ Получено уведомление в Telegram о запуске
- [ ] ✅ PAPER_TRADING_MODE=true (обязательно для начала!)
- [ ] ✅ Настроены автоматические бэкапы
- [ ] ✅ Настроен мониторинг
- [ ] ✅ Проверены логи на ошибки
- [ ] ✅ Настроен файрвол
- [ ] ✅ Изменен SSH порт (рекомендуется)

## 🎯 Следующие шаги

1. **Тестирование (1-2 недели)**
   - Запустите в режиме бумажной торговли
   - Мониторьте работу системы
   - Настройте торговые параметры

2. **Переход на реальную торговлю**
   - Убедитесь в стабильности системы
   - Установите PAPER_TRADING_MODE=false
   - Начните с минимальных сумм

3. **Масштабирование**
   - При необходимости увеличьте ресурсы сервера
   - Добавьте дополнительные инструменты
   - Оптимизируйте стратегии

---

**🎉 Поздравляем! Ваш торговый бот теперь работает в облаке 24/7!**