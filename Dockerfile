# Оптимизированный Dockerfile для хостинга
FROM python:3.10-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    locales \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Настройка русской локали
RUN sed -i '/ru_RU.UTF-8/s/^# //g' /etc/locale.gen && locale-gen
ENV LANG=ru_RU.UTF-8
ENV LANGUAGE=ru_RU:ru
ENV LC_ALL=ru_RU.UTF-8
ENV TZ=Europe/Moscow

# Рабочая директория
WORKDIR /app

# Копирование и установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода приложения
COPY russian_trading_bot/ ./russian_trading_bot/
COPY models/ ./models/

# Создание необходимых директорий
RUN mkdir -p logs backups config data

# Создание пользователя для безопасности
RUN useradd --create-home --shell /bin/bash trading && \
    chown -R trading:trading /app
USER trading

# Проверка здоровья
HEALTHCHECK --interval=60s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Порт приложения
EXPOSE 8000

# Команда запуска
CMD ["python", "-m", "russian_trading_bot.main"]