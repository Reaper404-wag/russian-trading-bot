# 🤝 Руководство по участию в проекте

Спасибо за интерес к Russian Trading Bot! Мы приветствуем любой вклад в развитие проекта.

## 📋 Как помочь проекту

### 🐛 Сообщение о багах
- Используйте [GitHub Issues](https://github.com/yourusername/russian-trading-bot/issues)
- Проверьте, что баг еще не был зарепорчен
- Приложите подробное описание и шаги воспроизведения
- Добавьте логи и скриншоты при необходимости

### 💡 Предложение новых функций
- Создайте Issue с меткой `enhancement`
- Опишите проблему, которую решает функция
- Предложите возможную реализацию
- Обсудите с сообществом перед началом разработки

### 📝 Улучшение документации
- Исправление опечаток и неточностей
- Добавление примеров использования
- Перевод на другие языки
- Создание туториалов и гайдов

### 🧪 Написание тестов
- Увеличение покрытия тестами
- Интеграционные тесты
- Тесты производительности
- Тестирование на разных платформах

## 🚀 Процесс разработки

### 1. Подготовка окружения

```bash
# Форк репозитория на GitHub
# Клонирование вашего форка
git clone https://github.com/yourusername/russian-trading-bot.git
cd russian-trading-bot

# Добавление upstream репозитория
git remote add upstream https://github.com/originalowner/russian-trading-bot.git

# Установка зависимостей
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Настройка pre-commit хуков
pre-commit install
```

### 2. Создание ветки

```bash
# Синхронизация с upstream
git fetch upstream
git checkout main
git merge upstream/main

# Создание feature ветки
git checkout -b feature/your-feature-name
```

### 3. Разработка

#### Стиль кода
- **Python**: следуйте PEP 8
- **JavaScript**: используйте ESLint конфигурацию
- **Комментарии**: на русском языке для бизнес-логики
- **Docstrings**: на английском языке

#### Именование
```python
# Классы - PascalCase
class MarketAnalyzer:
    pass

# Функции и переменные - snake_case
def analyze_market_sentiment():
    market_data = get_market_data()
    return market_data

# Константы - UPPER_CASE
MAX_POSITION_SIZE = 0.05
```

#### Структура коммитов
```bash
# Формат коммита
type(scope): краткое описание

# Примеры
feat(api): добавить endpoint для анализа настроений
fix(trading): исправить расчет стоп-лосса
docs(readme): обновить инструкции по установке
test(risk): добавить тесты для риск-менеджера
```

### 4. Тестирование

```bash
# Запуск всех тестов
pytest

# Тесты с покрытием
pytest --cov=russian_trading_bot

# Линтинг
flake8 russian_trading_bot/
black --check russian_trading_bot/

# Проверка типов
mypy russian_trading_bot/
```

### 5. Отправка изменений

```bash
# Коммит изменений
git add .
git commit -m "feat(trading): добавить поддержку новых индикаторов"

# Пуш в ваш форк
git push origin feature/your-feature-name

# Создание Pull Request на GitHub
```

## 📝 Требования к Pull Request

### Чек-лист перед отправкой
- [ ] Код соответствует стилю проекта
- [ ] Добавлены тесты для новой функциональности
- [ ] Все тесты проходят
- [ ] Документация обновлена
- [ ] Нет конфликтов с main веткой
- [ ] Коммиты имеют понятные сообщения

### Описание PR
```markdown
## Описание
Краткое описание изменений и их цель.

## Тип изменений
- [ ] Исправление бага
- [ ] Новая функция
- [ ] Улучшение производительности
- [ ] Рефакторинг
- [ ] Обновление документации

## Тестирование
- [ ] Добавлены unit тесты
- [ ] Добавлены интеграционные тесты
- [ ] Протестировано вручную

## Скриншоты (если применимо)
Добавьте скриншоты интерфейса или графики.

## Связанные Issues
Closes #123
```

## 🏗️ Архитектура проекта

### Основные принципы
- **SOLID принципы** - чистая архитектура
- **DRY** - не повторяйтесь
- **KISS** - простота решений
- **Separation of Concerns** - разделение ответственности

### Структура модулей
```
russian_trading_bot/
├── api/           # Внешние API интерфейсы
├── config/        # Конфигурация
├── database/      # Работа с БД
├── models/        # Модели данных
├── services/      # Бизнес-логика
├── infrastructure/ # Инфраструктурные компоненты
└── web/           # Веб-интерфейс
```

### Паттерны проектирования
- **Repository Pattern** - для работы с данными
- **Strategy Pattern** - для торговых стратегий
- **Observer Pattern** - для уведомлений
- **Factory Pattern** - для создания объектов

## 🧪 Тестирование

### Типы тестов

#### Unit тесты
```python
# test_risk_manager.py
import pytest
from russian_trading_bot.services.risk_manager import RiskManager

class TestRiskManager:
    def test_calculate_position_size(self):
        risk_manager = RiskManager()
        position_size = risk_manager.calculate_position_size(
            portfolio_value=100000,
            risk_per_trade=0.02
        )
        assert position_size == 2000
```

#### Интеграционные тесты
```python
# test_trading_integration.py
@pytest.mark.integration
async def test_full_trading_cycle():
    # Тест полного цикла торговли
    market_data = await market_monitor.get_data()
    signals = await ai_engine.generate_signals(market_data)
    filtered_signals = await risk_manager.filter_signals(signals)
    result = await portfolio_manager.execute_trades(filtered_signals)
    
    assert result.success is True
```

#### Тесты производительности
```python
# test_performance.py
@pytest.mark.performance
def test_market_analysis_performance():
    start_time = time.time()
    
    # Выполнение анализа
    result = market_analyzer.analyze_large_dataset()
    
    execution_time = time.time() - start_time
    assert execution_time < 5.0  # Должно выполняться менее 5 секунд
```

### Моки и фикстуры
```python
# conftest.py
@pytest.fixture
def mock_moex_api():
    with patch('russian_trading_bot.api.moex_interface.MOEXClient') as mock:
        mock.return_value.get_securities.return_value = [
            {'SECID': 'SBER', 'LAST': 250.0}
        ]
        yield mock

@pytest.fixture
def sample_market_data():
    return {
        'timestamp': datetime.now(),
        'securities': [
            {'symbol': 'SBER', 'price': 250.0, 'volume': 1000000}
        ]
    }
```

## 📚 Документация

### Docstrings
```python
def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.075) -> float:
    """
    Рассчитывает коэффициент Шарпа для серии доходностей.
    
    Args:
        returns: Список доходностей в виде десятичных дробей
        risk_free_rate: Безрисковая ставка (по умолчанию ставка ЦБ РФ)
        
    Returns:
        Коэффициент Шарпа
        
    Raises:
        ValueError: Если список доходностей пуст или содержит некорректные данные
        
    Example:
        >>> returns = [0.01, 0.02, -0.01, 0.03]
        >>> sharpe = calculate_sharpe_ratio(returns)
        >>> print(f"Sharpe ratio: {sharpe:.2f}")
    """
```

### README для модулей
Каждый модуль должен содержать README.md с описанием:
- Назначение модуля
- Основные классы и функции
- Примеры использования
- Зависимости

## 🔍 Code Review

### Что проверяем
- **Функциональность** - код работает как ожидается
- **Читаемость** - код понятен другим разработчикам
- **Производительность** - нет очевидных проблем с производительностью
- **Безопасность** - нет уязвимостей
- **Тестируемость** - код легко тестировать

### Комментарии в PR
```markdown
# Конструктивные комментарии
💡 Предложение: Можно использовать list comprehension для упрощения кода
❓ Вопрос: Почему выбран именно этот алгоритм?
🐛 Баг: Здесь может быть division by zero
✅ Одобрено: Отличное решение!
```

## 🏷️ Релизы

### Версионирование
Используем [Semantic Versioning](https://semver.org/):
- **MAJOR** (1.0.0) - несовместимые изменения API
- **MINOR** (0.1.0) - новая функциональность с обратной совместимостью
- **PATCH** (0.0.1) - исправления багов

### Changelog
```markdown
## [1.2.0] - 2024-01-15

### Added
- Поддержка новых торговых индикаторов
- Интеграция с API Сбербанк Инвестиции

### Changed
- Улучшена производительность анализа новостей
- Обновлен веб-интерфейс

### Fixed
- Исправлена ошибка в расчете стоп-лосса
- Устранена утечка памяти в модуле мониторинга

### Security
- Обновлены зависимости с уязвимостями
```

## 🎯 Приоритеты развития

### Высокий приоритет
- Исправление критических багов
- Улучшение безопасности
- Оптимизация производительности
- Покрытие тестами

### Средний приоритет
- Новые торговые стратегии
- Дополнительные брокеры
- Улучшение UI/UX
- Документация

### Низкий приоритет
- Экспериментальные функции
- Рефакторинг legacy кода
- Дополнительные метрики
- Интеграции с внешними сервисами

## 📞 Связь с сообществом

### Каналы общения
- **GitHub Discussions** - обсуждение идей и вопросов
- **Telegram чат** - @russian_trading_bot_dev
- **Discord сервер** - для голосового общения
- **Email** - dev@russian-trading-bot.ru

### Еженедельные встречи
- **Время**: каждую среду в 19:00 МСК
- **Платформа**: Discord
- **Повестка**: обсуждение PR, планирование, Q&A

## 🏆 Признание вклада

### Contributors
Все участники проекта указываются в:
- README.md
- CONTRIBUTORS.md
- Release notes
- Коммиты с co-authored-by

### Система наград
- 🥇 **Gold Contributor** - 50+ коммитов
- 🥈 **Silver Contributor** - 20+ коммитов  
- 🥉 **Bronze Contributor** - 5+ коммитов
- ⭐ **First Timer** - первый коммит

## 📄 Лицензия

Участвуя в проекте, вы соглашаетесь с тем, что ваш вклад будет лицензирован под [MIT License](LICENSE).

---

**Спасибо за ваш вклад в развитие Russian Trading Bot! 🚀**