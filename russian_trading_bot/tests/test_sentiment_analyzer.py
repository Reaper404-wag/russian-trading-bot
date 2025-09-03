"""
Tests for Russian Financial News Sentiment Analysis Service
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import tempfile
import os

from russian_trading_bot.services.sentiment_analyzer import (
    RussianSentimentAnalyzer,
    RussianFinancialSentimentLexicon,
    SentimentFeatures
)
from russian_trading_bot.models.news_data import RussianNewsArticle, NewsSentiment


class TestRussianFinancialSentimentLexicon:
    """Тесты для словаря финансовых терминов."""
    
    def setup_method(self):
        self.lexicon = RussianFinancialSentimentLexicon()
    
    def test_positive_terms(self):
        """Тест позитивных терминов."""
        assert self.lexicon.get_term_sentiment('рост') == 1.0
        assert self.lexicon.get_term_sentiment('прибыль') == 1.0
        assert self.lexicon.get_term_sentiment('успех') == 1.0
        assert self.lexicon.get_term_sentiment('дивиденды') == 1.0
    
    def test_negative_terms(self):
        """Тест негативных терминов."""
        assert self.lexicon.get_term_sentiment('падение') == -1.0
        assert self.lexicon.get_term_sentiment('убыток') == -1.0
        assert self.lexicon.get_term_sentiment('кризис') == -1.0
        assert self.lexicon.get_term_sentiment('санкции') == -1.0
    
    def test_neutral_terms(self):
        """Тест нейтральных терминов."""
        assert self.lexicon.get_term_sentiment('акции') == 0.0
        assert self.lexicon.get_term_sentiment('рубль') == 0.0
        assert self.lexicon.get_term_sentiment('отчет') == 0.0
    
    def test_unknown_terms(self):
        """Тест неизвестных терминов."""
        assert self.lexicon.get_term_sentiment('неизвестныйтермин') == 0.0
        assert self.lexicon.get_term_sentiment('') == 0.0
    
    def test_intensifiers(self):
        """Тест усилителей."""
        assert self.lexicon.get_intensifier_weight('очень') == 1.5
        assert self.lexicon.get_intensifier_weight('крайне') == 1.8
        assert self.lexicon.get_intensifier_weight('немного') == 0.7
        assert self.lexicon.get_intensifier_weight('обычное_слово') == 1.0
    
    def test_negations(self):
        """Тест отрицаний."""
        assert self.lexicon.is_negation('не') is True
        assert self.lexicon.is_negation('нет') is True
        assert self.lexicon.is_negation('без') is True
        assert self.lexicon.is_negation('обычное_слово') is False
    
    def test_case_insensitive(self):
        """Тест нечувствительности к регистру."""
        assert self.lexicon.get_term_sentiment('РОСТ') == 1.0
        assert self.lexicon.get_term_sentiment('Падение') == -1.0
        assert self.lexicon.is_negation('НЕ') is True


class TestRussianSentimentAnalyzer:
    """Тесты для анализатора настроений."""
    
    def setup_method(self):
        # Создаем временную директорию для модели
        self.temp_dir = tempfile.mkdtemp()
        model_path = os.path.join(self.temp_dir, "test_model.pkl")
        self.analyzer = RussianSentimentAnalyzer(model_path=model_path)
    
    def teardown_method(self):
        # Очищаем временные файлы
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_article(self, title: str, content: str) -> RussianNewsArticle:
        """Создает тестовую статью."""
        return RussianNewsArticle(
            title=title,
            content=content,
            source="RBC",
            timestamp=datetime.now(),
            url="https://example.com/news/1"
        )
    
    def test_positive_sentiment_analysis(self):
        """Тест анализа позитивного настроения."""
        article = self.create_test_article(
            "Акции Сбербанка показали рекордный рост",
            "Акции Сбербанка выросли на 15% после публикации отличных финансовых результатов. "
            "Прибыль банка превзошла все ожидания аналитиков. Успешное развитие бизнеса "
            "радует инвесторов и укрепляет позиции банка на рынке."
        )
        
        sentiment = self.analyzer.analyze_sentiment(article)
        
        assert isinstance(sentiment, NewsSentiment)
        assert sentiment.overall_sentiment in ["POSITIVE", "VERY_POSITIVE"]
        assert sentiment.sentiment_score > 0
        assert 0 <= sentiment.confidence <= 1
        assert len(sentiment.positive_keywords) > 0
        assert sentiment.timestamp is not None
    
    def test_negative_sentiment_analysis(self):
        """Тест анализа негативного настроения."""
        article = self.create_test_article(
            "Акции Газпрома обвалились из-за санкций",
            "Акции Газпрома упали на 20% после введения новых санкций. "
            "Компания понесла серьезные убытки, что вызывает кризис доверия "
            "среди инвесторов. Проблемы могут привести к дальнейшему падению котировок."
        )
        
        sentiment = self.analyzer.analyze_sentiment(article)
        
        assert isinstance(sentiment, NewsSentiment)
        assert sentiment.overall_sentiment in ["NEGATIVE", "VERY_NEGATIVE"]
        assert sentiment.sentiment_score < 0
        assert 0 <= sentiment.confidence <= 1
        assert len(sentiment.negative_keywords) > 0
    
    def test_neutral_sentiment_analysis(self):
        """Тест анализа нейтрального настроения."""
        article = self.create_test_article(
            "Сбербанк опубликовал квартальный отчет",
            "Сбербанк представил отчет за третий квартал. В отчете содержатся "
            "данные о финансовых показателях банка. Аналитики изучают представленную "
            "информацию для составления прогнозов."
        )
        
        sentiment = self.analyzer.analyze_sentiment(article)
        
        assert isinstance(sentiment, NewsSentiment)
        assert sentiment.overall_sentiment == "NEUTRAL"
        assert -0.2 <= sentiment.sentiment_score <= 0.2
        assert 0 <= sentiment.confidence <= 1
    
    def test_empty_article(self):
        """Тест обработки пустой статьи."""
        article = self.create_test_article("", "")
        
        sentiment = self.analyzer.analyze_sentiment(article)
        
        assert isinstance(sentiment, NewsSentiment)
        assert sentiment.overall_sentiment == "NEUTRAL"
        assert sentiment.sentiment_score == 0.0
        assert sentiment.confidence >= 0
    
    def test_batch_analysis(self):
        """Тест пакетного анализа."""
        articles = [
            self.create_test_article(
                "Позитивные новости",
                "Отличные результаты, рост прибыли, успех компании"
            ),
            self.create_test_article(
                "Негативные новости",
                "Падение акций, убытки, кризис в компании"
            ),
            self.create_test_article(
                "Нейтральные новости",
                "Компания опубликовала отчет с данными за квартал"
            )
        ]
        
        sentiments = self.analyzer.batch_analyze_sentiment(articles)
        
        assert len(sentiments) == 3
        assert all(isinstance(s, NewsSentiment) for s in sentiments)
        
        # Проверяем, что настроения различаются
        sentiment_types = [s.overall_sentiment for s in sentiments]
        assert len(set(sentiment_types)) > 1  # Должны быть разные типы настроений
    
    def test_sentiment_with_intensifiers(self):
        """Тест анализа с усилителями."""
        article_normal = self.create_test_article(
            "Рост акций",
            "Акции компании показали рост"
        )
        
        article_intensified = self.create_test_article(
            "Очень сильный рост акций",
            "Акции компании показали очень сильный рост"
        )
        
        sentiment_normal = self.analyzer.analyze_sentiment(article_normal)
        sentiment_intensified = self.analyzer.analyze_sentiment(article_intensified)
        
        # Усиленное настроение должно быть более позитивным
        assert sentiment_intensified.sentiment_score >= sentiment_normal.sentiment_score
    
    def test_sentiment_with_negation(self):
        """Тест анализа с отрицанием."""
        article_positive = self.create_test_article(
            "Рост прибыли",
            "Компания показала рост прибыли"
        )
        
        article_negated = self.create_test_article(
            "Отсутствие роста прибыли",
            "Компания не показала рост прибыли"
        )
        
        sentiment_positive = self.analyzer.analyze_sentiment(article_positive)
        sentiment_negated = self.analyzer.analyze_sentiment(article_negated)
        
        # Отрицание должно изменить настроение
        assert sentiment_negated.sentiment_score < sentiment_positive.sentiment_score
    
    def test_financial_terms_detection(self):
        """Тест обнаружения финансовых терминов."""
        article = self.create_test_article(
            "Финансовые новости",
            "Акции, облигации, дивиденды, прибыль, капитализация, торги на бирже"
        )
        
        sentiment = self.analyzer.analyze_sentiment(article)
        
        # Должны быть обнаружены нейтральные финансовые термины
        assert len(sentiment.neutral_keywords) > 0
    
    def test_sentiment_statistics(self):
        """Тест статистики настроений."""
        sentiments = [
            NewsSentiment(
                article_id="1",
                overall_sentiment="POSITIVE",
                sentiment_score=0.7,
                confidence=0.8,
                timestamp=datetime.now()
            ),
            NewsSentiment(
                article_id="2",
                overall_sentiment="NEGATIVE",
                sentiment_score=-0.5,
                confidence=0.9,
                timestamp=datetime.now()
            ),
            NewsSentiment(
                article_id="3",
                overall_sentiment="NEUTRAL",
                sentiment_score=0.1,
                confidence=0.6,
                timestamp=datetime.now()
            )
        ]
        
        stats = self.analyzer.get_sentiment_statistics(sentiments)
        
        assert stats['total_articles'] == 3
        assert stats['average_sentiment_score'] == pytest.approx(0.1, abs=0.1)
        assert stats['average_confidence'] == pytest.approx(0.77, abs=0.01)
        assert stats['positive_ratio'] == pytest.approx(1/3, abs=0.01)
        assert stats['negative_ratio'] == pytest.approx(1/3, abs=0.01)
        assert stats['neutral_ratio'] == pytest.approx(1/3, abs=0.01)
    
    def test_empty_statistics(self):
        """Тест статистики для пустого списка."""
        stats = self.analyzer.get_sentiment_statistics([])
        assert stats == {}
    
    @patch('russian_trading_bot.services.sentiment_analyzer.logger')
    def test_error_handling(self, mock_logger):
        """Тест обработки ошибок."""
        # Создаем статью с проблемным содержимым
        article = self.create_test_article("Test", "Test content")
        
        # Мокаем NLP pipeline чтобы вызвать ошибку
        with patch.object(self.analyzer.nlp_pipeline, 'process_text', side_effect=Exception("Test error")):
            sentiment = self.analyzer.analyze_sentiment(article)
            
            # Должен вернуться нейтральный результат
            assert sentiment.overall_sentiment == "NEUTRAL"
            assert sentiment.sentiment_score == 0.0
            assert sentiment.confidence == 0.0
            
            # Должна быть записана ошибка в лог
            mock_logger.error.assert_called()
    
    def test_model_persistence(self):
        """Тест сохранения и загрузки модели."""
        # Создаем синтетические данные для обучения
        labeled_articles = [
            (self.create_test_article("Позитив", "Отличные результаты, рост прибыли"), "POSITIVE"),
            (self.create_test_article("Негатив", "Падение акций, убытки"), "NEGATIVE"),
            (self.create_test_article("Нейтрал", "Опубликован отчет"), "NEUTRAL")
        ]
        
        # Обучаем модель
        self.analyzer.train_on_labeled_data(labeled_articles)
        
        # Создаем новый анализатор с тем же путем к модели
        new_analyzer = RussianSentimentAnalyzer(model_path=self.analyzer.model_path)
        
        # Проверяем, что модель загрузилась
        assert new_analyzer.model is not None
        assert new_analyzer.vectorizer is not None
    
    def test_confidence_scoring(self):
        """Тест оценки уверенности."""
        # Статья с множеством финансовых терминов должна иметь высокую уверенность
        high_confidence_article = self.create_test_article(
            "Финансовые результаты",
            "Прибыль выросла, дивиденды увеличились, акции показали отличный рост, "
            "капитализация достигла рекорда, инвесторы довольны успехом компании"
        )
        
        # Статья с малым количеством терминов должна иметь низкую уверенность
        low_confidence_article = self.create_test_article(
            "Общие новости",
            "Сегодня хорошая погода в Москве"
        )
        
        high_conf_sentiment = self.analyzer.analyze_sentiment(high_confidence_article)
        low_conf_sentiment = self.analyzer.analyze_sentiment(low_confidence_article)
        
        assert high_conf_sentiment.confidence > low_conf_sentiment.confidence
    
    def test_keyword_extraction(self):
        """Тест извлечения ключевых слов."""
        article = self.create_test_article(
            "Смешанные новости",
            "Прибыль компании выросла, но возникли проблемы с убытками. "
            "Акции показали рост, однако аналитики предупреждают о рисках."
        )
        
        sentiment = self.analyzer.analyze_sentiment(article)
        
        # Должны быть извлечены и позитивные, и негативные ключевые слова
        assert len(sentiment.positive_keywords) > 0
        assert len(sentiment.negative_keywords) > 0
        
        # Проверяем, что ключевые слова соответствуют ожиданиям
        positive_found = any(word in ['прибыль', 'рост'] for word in sentiment.positive_keywords)
        negative_found = any(word in ['проблемы', 'убыток', 'риск'] for word in sentiment.negative_keywords)
        
        assert positive_found
        assert negative_found


class TestSentimentIntegration:
    """Интеграционные тесты для анализа настроений."""
    
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        model_path = os.path.join(self.temp_dir, "integration_model.pkl")
        self.analyzer = RussianSentimentAnalyzer(model_path=model_path)
    
    def teardown_method(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_real_world_scenarios(self):
        """Тест реальных сценариев новостей."""
        scenarios = [
            {
                "title": "Сбербанк увеличил чистую прибыль на 25%",
                "content": "Крупнейший российский банк Сбербанк объявил о значительном росте "
                          "чистой прибыли в третьем квартале. Показатели превзошли ожидания "
                          "аналитиков благодаря успешной работе всех подразделений.",
                "expected_sentiment": "POSITIVE"
            },
            {
                "title": "Газпром столкнулся с серьезными проблемами",
                "content": "Энергетический гигант Газпром сообщил о значительных убытках "
                          "из-за санкций и падения спроса на газ. Компания вынуждена "
                          "пересматривать свою стратегию в условиях кризиса.",
                "expected_sentiment": "NEGATIVE"
            },
            {
                "title": "Московская биржа опубликовала статистику торгов",
                "content": "MOEX представила данные о торговых оборотах за прошедший месяц. "
                          "В отчете содержится информация о различных сегментах рынка "
                          "и активности участников торгов.",
                "expected_sentiment": "NEUTRAL"
            }
        ]
        
        for scenario in scenarios:
            article = RussianNewsArticle(
                title=scenario["title"],
                content=scenario["content"],
                source="RBC",
                timestamp=datetime.now()
            )
            
            sentiment = self.analyzer.analyze_sentiment(article)
            
            # Проверяем, что настроение соответствует ожиданиям
            if scenario["expected_sentiment"] == "POSITIVE":
                assert sentiment.overall_sentiment in ["POSITIVE", "VERY_POSITIVE"]
                assert sentiment.sentiment_score > 0
            elif scenario["expected_sentiment"] == "NEGATIVE":
                assert sentiment.overall_sentiment in ["NEGATIVE", "VERY_NEGATIVE"]
                assert sentiment.sentiment_score < 0
            else:  # NEUTRAL
                assert sentiment.overall_sentiment == "NEUTRAL"
                assert abs(sentiment.sentiment_score) < 0.3
    
    def test_performance_benchmark(self):
        """Тест производительности анализа."""
        import time
        
        # Создаем 100 тестовых статей
        articles = []
        for i in range(100):
            article = RussianNewsArticle(
                title=f"Тестовая статья {i}",
                content=f"Содержание статьи {i} с финансовыми терминами: акции, прибыль, рост",
                source="RBC",
                timestamp=datetime.now()
            )
            articles.append(article)
        
        # Измеряем время обработки
        start_time = time.time()
        sentiments = self.analyzer.batch_analyze_sentiment(articles)
        end_time = time.time()
        
        processing_time = end_time - start_time
        avg_time_per_article = processing_time / len(articles)
        
        # Проверяем результаты
        assert len(sentiments) == 100
        assert all(isinstance(s, NewsSentiment) for s in sentiments)
        
        # Проверяем производительность (должно быть быстрее 1 секунды на статью)
        assert avg_time_per_article < 1.0
        
        print(f"Обработано {len(articles)} статей за {processing_time:.2f} секунд")
        print(f"Среднее время на статью: {avg_time_per_article:.3f} секунд")


if __name__ == "__main__":
    pytest.main([__file__])