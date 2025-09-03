"""
Пример использования русского NLP pipeline для анализа финансовых новостей.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.russian_nlp import RussianNLPPipeline


def main():
    """Демонстрация работы русского NLP pipeline."""
    
    # Создаем экземпляр pipeline
    nlp = RussianNLPPipeline()
    
    # Пример финансовой новости на русском языке
    news_text = """
    Акции Сбербанка выросли на 2.5% после публикации квартальных результатов.
    Чистая прибыль банка составила 150 миллиардов рублей, что превысило ожидания аналитиков.
    Газпром также показал хорошие результаты, увеличив дивиденды на 15%.
    """
    
    print("=== АНАЛИЗ РУССКОЙ ФИНАНСОВОЙ НОВОСТИ ===\n")
    print(f"Исходный текст:\n{news_text}\n")
    
    # Обрабатываем текст
    result = nlp.process_text(news_text)
    
    print(f"Очищенный текст:\n{result.cleaned_text}\n")
    
    print(f"Токены: {result.tokens[:10]}...")  # Показываем первые 10 токенов
    print(f"Леммы: {result.lemmas[:10]}...")   # Показываем первые 10 лемм
    print(f"Части речи: {result.pos_tags[:10]}...")  # Показываем первые 10 частей речи
    
    print(f"\nФинансовые термины: {result.financial_terms}")
    print(f"Денежные суммы: {result.money_amounts}")
    print(f"Именованные сущности: {result.entities}")
    
    # Извлекаем тикеры компаний
    tickers = nlp.get_company_tickers(news_text)
    print(f"Найденные тикеры компаний: {tickers}")
    
    print("\n=== ТЕСТИРОВАНИЕ ОТДЕЛЬНЫХ ФУНКЦИЙ ===\n")
    
    # Тестируем словарь финансовых терминов
    terms = nlp.financial_terms
    test_words = ["акция", "прибыль", "собака", "газпром", "сбер"]
    
    for word in test_words:
        is_financial = terms.is_financial_term(word)
        ticker = terms.get_ticker_by_company(word)
        print(f"'{word}': финансовый термин = {is_financial}, тикер = {ticker}")


if __name__ == "__main__":
    main()