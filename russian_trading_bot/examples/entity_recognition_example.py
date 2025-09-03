"""
Пример использования сервиса распознавания именованных сущностей российских компаний.

Этот пример демонстрирует основные возможности RussianEntityRecognizer:
- Распознавание компаний в тексте
- Связывание новостей с акциями
- Поиск компаний
- Анализ по секторам
"""

import sys
import os
from typing import List, Dict, Any

# Добавляем путь к модулям проекта
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from russian_trading_bot.services.entity_recognizer import RussianEntityRecognizer


def print_separator(title: str):
    """Печатает разделитель с заголовком."""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)


def demonstrate_basic_recognition():
    """Демонстрирует базовое распознавание сущностей."""
    print_separator("БАЗОВОЕ РАСПОЗНАВАНИЕ СУЩНОСТЕЙ")
    
    recognizer = RussianEntityRecognizer()
    
    # Примеры текстов для анализа
    test_texts = [
        "Акции Сбербанка выросли на 3% после публикации квартальной отчетности.",
        "Газпром и Лукойл показали лучшую динамику среди нефтегазовых компаний.",
        "Рекомендуем к покупке SBER, GAZP и LKOH на текущих уровнях.",
        "Яндекс объявил о запуске нового сервиса, акции компании выросли на 2%.",
        "Норникель увеличил производство никеля на 15% в третьем квартале."
    ]
    
    for i, text in enumerate(test_texts, 1):
        print(f"\n{i}. Анализируемый текст:")
        print(f"   '{text}'")
        
        result = recognizer.recognize_entities(text)
        
        print(f"   Найденные тикеры: {result.tickers_mentioned}")
        print(f"   Уверенность: {result.confidence_score:.2f}")
        print(f"   Время обработки: {result.processing_time:.3f}с")
        
        if result.companies:
            print("   Найденные компании:")
            for company in result.companies:
                print(f"     - {company.name} ({company.ticker}) - {company.sector}")
                print(f"       Уверенность: {company.confidence:.2f}")


def demonstrate_news_linking():
    """Демонстрирует связывание новостей с акциями."""
    print_separator("СВЯЗЫВАНИЕ НОВОСТЕЙ С АКЦИЯМИ")
    
    recognizer = RussianEntityRecognizer()
    
    # Примеры новостей
    news_examples = [
        {
            "title": "Сбербанк увеличил чистую прибыль на 20%",
            "text": """ПАО Сбербанк опубликовал финансовые результаты за третий квартал 2024 года. 
                      Чистая прибыль банка составила 450 млрд рублей, что на 20% больше 
                      аналогичного периода прошлого года. Рост обусловлен увеличением 
                      процентных доходов и снижением резервов на возможные потери."""
        },
        {
            "title": "Газпром подписал новый контракт на поставку газа",
            "text": """ПАО Газпром заключил долгосрочный контракт на поставку природного газа 
                      в Китай. Объем поставок составит 10 млрд кубометров в год. 
                      Контракт рассчитан на 30 лет и оценивается в $400 млрд."""
        },
        {
            "title": "IT-сектор под давлением регулятора",
            "text": """Акции российских IT-компаний снижаются на фоне новых инициатив регулятора. 
                      Яндекс потерял 3%, VK Group упал на 2,5%. Инвесторы опасаются 
                      ужесточения требований к технологическим компаниям."""
        }
    ]
    
    for i, news in enumerate(news_examples, 1):
        print(f"\n{i}. Новость: {news['title']}")
        print(f"   Текст: {news['text'][:100]}...")
        
        linking_result = recognizer.link_news_to_stocks(news['text'], news['title'])
        
        print(f"   Связанные тикеры: {linking_result['tickers']}")
        print(f"   Общая уверенность: {linking_result['overall_confidence']:.2f}")
        
        if linking_result['sectors_affected']:
            print("   Затронутые секторы:")
            for sector, companies in linking_result['sectors_affected'].items():
                print(f"     {sector}:")
                for company in companies:
                    print(f"       - {company['name']} ({company['ticker']}) - {company['confidence']:.2f}")


def demonstrate_company_search():
    """Демонстрирует поиск компаний."""
    print_separator("ПОИСК КОМПАНИЙ")
    
    recognizer = RussianEntityRecognizer()
    
    search_queries = ["сбер", "газ", "банк", "нефть", "технологии"]
    
    for query in search_queries:
        print(f"\nПоиск по запросу: '{query}'")
        results = recognizer.search_companies(query)
        
        if results:
            print(f"Найдено компаний: {len(results)}")
            for company in results[:3]:  # Показываем первые 3 результата
                print(f"  - {company['name']} ({company['ticker']}) - {company['sector']}")
        else:
            print("  Компании не найдены")


def demonstrate_sector_analysis():
    """Демонстрирует анализ по секторам."""
    print_separator("АНАЛИЗ ПО СЕКТОРАМ")
    
    recognizer = RussianEntityRecognizer()
    
    # Получаем статистику
    stats = recognizer.get_statistics()
    
    print(f"Общее количество компаний: {stats['total_companies']}")
    print(f"Общее количество алиасов: {stats['total_aliases']}")
    print(f"Среднее количество алиасов на компанию: {stats['average_aliases_per_company']:.1f}")
    
    print("\nРаспределение по секторам:")
    for sector, count in sorted(stats['sectors'].items()):
        print(f"  {sector}: {count} компаний")
    
    # Демонстрируем получение компаний по секторам
    print("\nПримеры компаний по секторам:")
    for sector in ['Банки', 'Нефть и газ', 'Технологии']:
        companies = recognizer.company_dict.get_companies_by_sector(sector)
        if companies:
            print(f"  {sector}: {', '.join(companies[:5])}")  # Первые 5 компаний


def demonstrate_confidence_tuning():
    """Демонстрирует настройку порога уверенности."""
    print_separator("НАСТРОЙКА ПОРОГА УВЕРЕННОСТИ")
    
    recognizer = RussianEntityRecognizer()
    
    # Тестовый текст с неоднозначными упоминаниями
    test_text = "В банке сегодня была очередь. Сбер работает хорошо. Газ подорожал."
    
    thresholds = [0.3, 0.5, 0.7, 0.9]
    
    print(f"Тестовый текст: '{test_text}'")
    print("\nРезультаты при разных порогах уверенности:")
    
    for threshold in thresholds:
        recognizer.set_confidence_threshold(threshold)
        result = recognizer.recognize_entities(test_text)
        
        print(f"  Порог {threshold}: найдено {len(result.companies)} компаний - {result.tickers_mentioned}")


def demonstrate_real_world_scenario():
    """Демонстрирует реальный сценарий использования."""
    print_separator("РЕАЛЬНЫЙ СЦЕНАРИЙ ИСПОЛЬЗОВАНИЯ")
    
    recognizer = RussianEntityRecognizer()
    
    # Имитируем обработку новостной ленты
    news_feed = [
        "Московская биржа: итоги торгов. Индекс MOEX вырос на 1,2%.",
        "Сбербанк увеличил кредитный портфель на 15% за год.",
        "Газпром объявил о рекордных поставках газа в Европу.",
        "Акции Яндекса выросли после новостей о партнерстве с ВТБ.",
        "Лукойл инвестирует $2 млрд в развитие нефтехимии.",
        "Норникель получил рекордную прибыль благодаря росту цен на металлы."
    ]
    
    print("Обработка новостной ленты:")
    
    all_mentioned_tickers = set()
    sector_mentions = {}
    
    for i, news in enumerate(news_feed, 1):
        print(f"\n{i}. {news}")
        
        result = recognizer.recognize_entities(news)
        
        if result.tickers_mentioned:
            print(f"   Тикеры: {result.tickers_mentioned}")
            all_mentioned_tickers.update(result.tickers_mentioned)
            
            # Подсчитываем упоминания по секторам
            for company in result.companies:
                sector = company.sector
                sector_mentions[sector] = sector_mentions.get(sector, 0) + 1
        else:
            print("   Компании не найдены")
    
    print(f"\nИтоговая статистика:")
    print(f"Всего упомянуто уникальных тикеров: {len(all_mentioned_tickers)}")
    print(f"Тикеры: {sorted(all_mentioned_tickers)}")
    
    if sector_mentions:
        print("\nУпоминания по секторам:")
        for sector, count in sorted(sector_mentions.items(), key=lambda x: x[1], reverse=True):
            print(f"  {sector}: {count} упоминаний")


def main():
    """Главная функция для запуска всех демонстраций."""
    print("ДЕМОНСТРАЦИЯ СЕРВИСА РАСПОЗНАВАНИЯ РОССИЙСКИХ КОМПАНИЙ")
    print("Версия: 1.0")
    print("Автор: Russian Trading Bot")
    
    try:
        demonstrate_basic_recognition()
        demonstrate_news_linking()
        demonstrate_company_search()
        demonstrate_sector_analysis()
        demonstrate_confidence_tuning()
        demonstrate_real_world_scenario()
        
        print_separator("ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА")
        print("Все функции сервиса распознавания сущностей работают корректно!")
        
    except Exception as e:
        print(f"\nОшибка при выполнении демонстрации: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()