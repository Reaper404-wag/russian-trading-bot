"""
Пример использования анализатора настроений для русских финансовых новостей.

Этот скрипт демонстрирует основные возможности анализатора настроений:
- Анализ отдельных статей
- Пакетный анализ
- Обучение на размеченных данных
- Получение статистики
"""

import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from russian_trading_bot.services.sentiment_analyzer import RussianSentimentAnalyzer
from russian_trading_bot.models.news_data import RussianNewsArticle


def create_sample_articles():
    """Создает примеры новостных статей для демонстрации."""
    articles = [
        RussianNewsArticle(
            title="Сбербанк показал рекордную прибыль за квартал",
            content="""
            Крупнейший российский банк Сбербанк объявил о рекордной чистой прибыли 
            в размере 350 миллиардов рублей за третий квартал 2024 года. Результаты 
            значительно превзошли ожидания аналитиков и продемонстрировали отличную 
            динамику роста всех ключевых показателей. Успешное развитие цифрового 
            банкинга и эффективное управление рисками позволили банку укрепить свои 
            позиции на рынке. Инвесторы положительно отреагировали на новости, 
            акции банка выросли на 8% в ходе торгов.
            """,
            source="RBC",
            timestamp=datetime.now() - timedelta(hours=2),
            url="https://example.com/sber-profit"
        ),
        
        RussianNewsArticle(
            title="Газпром столкнулся с серьезными проблемами из-за санкций",
            content="""
            Энергетический гигант Газпром сообщил о значительных убытках в размере 
            150 миллиардов рублей за отчетный период. Компания столкнулась с серьезными 
            вызовами из-за введенных санкций и сокращения экспорта газа в Европу. 
            Падение доходов привело к необходимости пересмотра инвестиционных планов 
            и сокращения расходов. Аналитики предупреждают о возможном дальнейшем 
            ухудшении ситуации и рекомендуют инвесторам проявлять осторожность. 
            Акции компании упали на 12% на фоне негативных новостей.
            """,
            source="VEDOMOSTI",
            timestamp=datetime.now() - timedelta(hours=4),
            url="https://example.com/gazprom-problems"
        ),
        
        RussianNewsArticle(
            title="Московская биржа опубликовала статистику торгов за октябрь",
            content="""
            Московская биржа (MOEX) представила официальную статистику торговых 
            оборотов за октябрь 2024 года. Общий объем торгов составил 2.5 триллиона 
            рублей, что соответствует среднемесячным показателям. На фондовом рынке 
            наблюдалась умеренная активность с преобладанием операций с акциями 
            крупных компаний. Валютный сегмент показал стабильные обороты без 
            значительных колебаний. Представители биржи отметили сбалансированную 
            структуру торгов и участие как институциональных, так и частных инвесторов.
            """,
            source="INTERFAX",
            timestamp=datetime.now() - timedelta(hours=6),
            url="https://example.com/moex-stats"
        ),
        
        RussianNewsArticle(
            title="Яндекс объявил о запуске нового сервиса для инвесторов",
            content="""
            Технологическая компания Яндекс анонсировала запуск инновационного 
            сервиса для частных инвесторов. Новая платформа предоставит пользователям 
            доступ к аналитике, рекомендациям и инструментам для управления 
            инвестиционным портфелем. Разработка велась в течение двух лет с 
            привлечением ведущих экспертов финансового рынка. Компания планирует 
            привлечь более 100 тысяч пользователей в первый год работы сервиса. 
            Это стратегически важный шаг для расширения экосистемы Яндекса в 
            финансовом секторе.
            """,
            source="RBC",
            timestamp=datetime.now() - timedelta(hours=8),
            url="https://example.com/yandex-service"
        ),
        
        RussianNewsArticle(
            title="ЦБ РФ сохранил ключевую ставку на уровне 21%",
            content="""
            Центральный банк России принял решение сохранить ключевую ставку на 
            текущем уровне 21% годовых. Решение было принято единогласно на заседании 
            Совета директоров с учетом текущей макроэкономической ситуации и 
            инфляционных ожиданий. Регулятор отметил необходимость поддержания 
            жесткой денежно-кредитной политики для достижения целевого уровня 
            инфляции. Следующее заседание по вопросу ключевой ставки запланировано 
            на декабрь. Участники рынка ожидали такого решения, поэтому реакция 
            была сдержанной.
            """,
            source="TASS",
            timestamp=datetime.now() - timedelta(hours=10),
            url="https://example.com/cbr-rate"
        )
    ]
    
    return articles


def demonstrate_single_analysis(analyzer, article):
    """Демонстрирует анализ одной статьи."""
    print(f"\n{'='*60}")
    print(f"АНАЛИЗ СТАТЬИ: {article.title}")
    print(f"{'='*60}")
    print(f"Источник: {article.source}")
    print(f"Время: {article.timestamp.strftime('%Y-%m-%d %H:%M')}")
    print(f"\nСодержание (первые 200 символов):")
    print(f"{article.content[:200].strip()}...")
    
    # Анализируем настроение
    sentiment = analyzer.analyze_sentiment(article)
    
    print(f"\n{'='*40}")
    print(f"РЕЗУЛЬТАТЫ АНАЛИЗА НАСТРОЕНИЯ")
    print(f"{'='*40}")
    print(f"Общее настроение: {sentiment.overall_sentiment}")
    print(f"Оценка настроения: {sentiment.sentiment_score:.3f}")
    print(f"Уверенность: {sentiment.confidence:.3f}")
    
    if sentiment.positive_keywords:
        print(f"\nПозитивные ключевые слова:")
        print(f"  {', '.join(sentiment.positive_keywords[:5])}")
    
    if sentiment.negative_keywords:
        print(f"\nНегативные ключевые слова:")
        print(f"  {', '.join(sentiment.negative_keywords[:5])}")
    
    if sentiment.neutral_keywords:
        print(f"\nНейтральные ключевые слова:")
        print(f"  {', '.join(sentiment.neutral_keywords[:5])}")


def demonstrate_batch_analysis(analyzer, articles):
    """Демонстрирует пакетный анализ статей."""
    print(f"\n{'='*60}")
    print(f"ПАКЕТНЫЙ АНАЛИЗ {len(articles)} СТАТЕЙ")
    print(f"{'='*60}")
    
    # Выполняем пакетный анализ
    sentiments = analyzer.batch_analyze_sentiment(articles)
    
    # Выводим краткие результаты
    print(f"\nКраткие результаты:")
    print(f"{'Статья':<40} {'Настроение':<15} {'Оценка':<8} {'Уверенность':<12}")
    print(f"{'-'*75}")
    
    for article, sentiment in zip(articles, sentiments):
        title = article.title[:37] + "..." if len(article.title) > 40 else article.title
        print(f"{title:<40} {sentiment.overall_sentiment:<15} "
              f"{sentiment.sentiment_score:>6.3f} {sentiment.confidence:>10.3f}")
    
    # Получаем статистику
    stats = analyzer.get_sentiment_statistics(sentiments)
    
    print(f"\n{'='*40}")
    print(f"СТАТИСТИКА НАСТРОЕНИЙ")
    print(f"{'='*40}")
    print(f"Всего статей: {stats['total_articles']}")
    print(f"Средняя оценка настроения: {stats['average_sentiment_score']:.3f}")
    print(f"Средняя уверенность: {stats['average_confidence']:.3f}")
    print(f"\nРаспределение настроений:")
    print(f"  Позитивные: {stats['positive_ratio']:.1%}")
    print(f"  Негативные: {stats['negative_ratio']:.1%}")
    print(f"  Нейтральные: {stats['neutral_ratio']:.1%}")
    
    # Детальное распределение
    sentiment_counts = {}
    for sentiment in sentiments:
        sentiment_counts[sentiment.overall_sentiment] = sentiment_counts.get(
            sentiment.overall_sentiment, 0
        ) + 1
    
    print(f"\nДетальное распределение:")
    for sentiment_type, count in sorted(sentiment_counts.items()):
        percentage = count / len(sentiments) * 100
        print(f"  {sentiment_type}: {count} ({percentage:.1f}%)")


def demonstrate_training(analyzer):
    """Демонстрирует обучение модели на размеченных данных."""
    print(f"\n{'='*60}")
    print(f"ОБУЧЕНИЕ МОДЕЛИ НА РАЗМЕЧЕННЫХ ДАННЫХ")
    print(f"{'='*60}")
    
    # Создаем размеченные данные для обучения
    labeled_data = [
        # Позитивные примеры
        (RussianNewsArticle(
            title="Отличные результаты компании",
            content="Прибыль выросла на 50%, дивиденды увеличены, акционеры довольны успехом",
            source="RBC",
            timestamp=datetime.now()
        ), "POSITIVE"),
        
        (RussianNewsArticle(
            title="Рекордные показатели банка",
            content="Банк показал рекордную прибыль, превзошел все ожидания аналитиков",
            source="VEDOMOSTI",
            timestamp=datetime.now()
        ), "POSITIVE"),
        
        # Негативные примеры
        (RussianNewsArticle(
            title="Серьезные проблемы компании",
            content="Убытки достигли критического уровня, акции обвалились, кризис углубляется",
            source="INTERFAX",
            timestamp=datetime.now()
        ), "NEGATIVE"),
        
        (RussianNewsArticle(
            title="Банкротство угрожает компании",
            content="Долги превысили активы, санкции нанесли серьезный ущерб бизнесу",
            source="TASS",
            timestamp=datetime.now()
        ), "NEGATIVE"),
        
        # Нейтральные примеры
        (RussianNewsArticle(
            title="Компания опубликовала отчет",
            content="В отчете представлены финансовые показатели за квартал и планы развития",
            source="RBC",
            timestamp=datetime.now()
        ), "NEUTRAL"),
        
        (RussianNewsArticle(
            title="Биржа обновила правила торгов",
            content="Новые правила вступят в силу с начала следующего месяца",
            source="RBC",
            timestamp=datetime.now()
        ), "NEUTRAL")
    ]
    
    print(f"Подготовлено {len(labeled_data)} размеченных примеров для обучения:")
    for i, (article, label) in enumerate(labeled_data, 1):
        print(f"  {i}. {label}: {article.title}")
    
    # Обучаем модель
    print(f"\nОбучение модели...")
    try:
        analyzer.train_on_labeled_data(labeled_data)
        print(f"✓ Модель успешно обучена!")
    except Exception as e:
        print(f"✗ Ошибка при обучении: {e}")
    
    # Тестируем обученную модель
    print(f"\nТестирование обученной модели:")
    test_article = RussianNewsArticle(
        title="Тестовая статья",
        content="Компания показала превосходные результаты, прибыль выросла значительно",
        source="RBC",
        timestamp=datetime.now()
    )
    
    sentiment = analyzer.analyze_sentiment(test_article)
    print(f"Тестовая статья: {test_article.content}")
    print(f"Результат: {sentiment.overall_sentiment} (оценка: {sentiment.sentiment_score:.3f})")


def demonstrate_advanced_features(analyzer, articles):
    """Демонстрирует продвинутые возможности анализатора."""
    print(f"\n{'='*60}")
    print(f"ПРОДВИНУТЫЕ ВОЗМОЖНОСТИ")
    print(f"{'='*60}")
    
    # Анализ по источникам
    print(f"\nАнализ настроений по источникам:")
    source_sentiments = {}
    
    for article in articles:
        sentiment = analyzer.analyze_sentiment(article)
        if article.source not in source_sentiments:
            source_sentiments[article.source] = []
        source_sentiments[article.source].append(sentiment.sentiment_score)
    
    for source, scores in source_sentiments.items():
        avg_score = sum(scores) / len(scores)
        print(f"  {source}: {avg_score:.3f} (статей: {len(scores)})")
    
    # Анализ по времени
    print(f"\nАнализ настроений по времени:")
    time_sentiments = []
    
    for article in sorted(articles, key=lambda x: x.timestamp):
        sentiment = analyzer.analyze_sentiment(article)
        time_str = article.timestamp.strftime("%H:%M")
        time_sentiments.append((time_str, sentiment.sentiment_score))
    
    for time_str, score in time_sentiments:
        print(f"  {time_str}: {score:.3f}")
    
    # Поиск наиболее эмоциональных статей
    print(f"\nНаиболее эмоциональные статьи:")
    article_sentiments = []
    
    for article in articles:
        sentiment = analyzer.analyze_sentiment(article)
        article_sentiments.append((article, sentiment))
    
    # Сортируем по абсолютному значению оценки настроения
    article_sentiments.sort(key=lambda x: abs(x[1].sentiment_score), reverse=True)
    
    for i, (article, sentiment) in enumerate(article_sentiments[:3], 1):
        title = article.title[:50] + "..." if len(article.title) > 50 else article.title
        print(f"  {i}. {title}")
        print(f"     Настроение: {sentiment.overall_sentiment} ({sentiment.sentiment_score:.3f})")


def main():
    """Главная функция демонстрации."""
    print("🤖 ДЕМОНСТРАЦИЯ АНАЛИЗАТОРА НАСТРОЕНИЙ РУССКИХ ФИНАНСОВЫХ НОВОСТЕЙ")
    print("=" * 80)
    
    # Инициализируем анализатор
    print("Инициализация анализатора настроений...")
    analyzer = RussianSentimentAnalyzer()
    print("✓ Анализатор готов к работе!")
    
    # Создаем примеры статей
    articles = create_sample_articles()
    print(f"✓ Подготовлено {len(articles)} тестовых статей")
    
    # Демонстрируем анализ отдельных статей
    for i, article in enumerate(articles[:2], 1):  # Показываем первые 2 статьи
        demonstrate_single_analysis(analyzer, article)
        if i < 2:
            input("\nНажмите Enter для продолжения...")
    
    # Демонстрируем пакетный анализ
    demonstrate_batch_analysis(analyzer, articles)
    input("\nНажмите Enter для продолжения...")
    
    # Демонстрируем обучение модели
    demonstrate_training(analyzer)
    input("\nНажмите Enter для продолжения...")
    
    # Демонстрируем продвинутые возможности
    demonstrate_advanced_features(analyzer, articles)
    
    print(f"\n{'='*80}")
    print("🎉 ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА!")
    print("Анализатор настроений готов к использованию в реальных проектах.")
    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Демонстрация прервана пользователем")
    except Exception as e:
        print(f"\n\n❌ Ошибка при выполнении демонстрации: {e}")
        import traceback
        traceback.print_exc()