"""
Тесты для русского NLP pipeline.
"""

import pytest
from unittest.mock import Mock, patch
from russian_trading_bot.services.russian_nlp import (
    RussianNLPPipeline, 
    RussianFinancialTerms, 
    ProcessedText
)


class TestRussianFinancialTerms:
    """Тесты для словаря финансовых терминов."""
    
    def setup_method(self):
        self.terms = RussianFinancialTerms()
    
    def test_is_financial_term_basic_terms(self):
        """Тест распознавания основных финансовых терминов."""
        assert self.terms.is_financial_term('акция')
        assert self.terms.is_financial_term('прибыль')
        assert self.terms.is_financial_term('дивиденд')
        assert self.terms.is_financial_term('рубль')
        assert not self.terms.is_financial_term('собака')
        assert not self.terms.is_financial_term('стол')
    
    def test_is_financial_term_case_insensitive(self):
        """Тест нечувствительности к регистру."""
        assert self.terms.is_financial_term('АКЦИЯ')
        assert self.terms.is_financial_term('Прибыль')
        assert self.terms.is_financial_term('РУБЛЬ')
    
    def test_get_ticker_by_company(self):
        """Тест получения тикера по названию компании."""
        assert self.terms.get_ticker_by_company('сбер') == 'SBER'
        assert self.terms.get_ticker_by_company('газпром') == 'GAZP'
        assert self.terms.get_ticker_by_company('ЛУКОЙЛ') == 'LKOH'
        assert self.terms.get_ticker_by_company('неизвестная_компания') is None
    
    def test_company_variations(self):
        """Тест различных вариаций названий компаний."""
        assert self.terms.get_ticker_by_company('сбербанк') == 'SBER'
        assert self.terms.get_ticker_by_company('газпрома') == 'GAZP'
        assert self.terms.get_ticker_by_company('лукойла') == 'LKOH'


class TestRussianNLPPipeline:
    """Тесты для основного NLP pipeline."""
    
    @pytest.fixture
    def nlp_pipeline(self):
        """Фикстура для создания NLP pipeline с мокированными моделями."""
        with patch('russian_trading_bot.services.russian_nlp.Segmenter'), \
             patch('russian_trading_bot.services.russian_nlp.MorphVocab'), \
             patch('russian_trading_bot.services.russian_nlp.NewsEmbedding'), \
             patch('russian_trading_bot.services.russian_nlp.NewsMorphTagger'), \
             patch('russian_trading_bot.services.russian_nlp.NewsNERTagger'), \
             patch('russian_trading_bot.services.russian_nlp.NewsSyntaxParser'), \
             patch('russian_trading_bot.services.russian_nlp.pymorphy2.MorphAnalyzer'), \
             patch('russian_trading_bot.services.russian_nlp.MoneyExtractor'), \
             patch('russian_trading_bot.services.russian_nlp.NamesExtractor'):
            
            pipeline = RussianNLPPipeline()
            return pipeline
    
    def test_clean_text_basic(self, nlp_pipeline):
        """Тест базовой очистки текста."""
        dirty_text = "  Это   текст\n\nс лишними   пробелами  "
        clean_text = nlp_pipeline.clean_text(dirty_text)
        assert clean_text == "Это текст с лишними пробелами"
    
    def test_clean_text_html_removal(self, nlp_pipeline):
        """Тест удаления HTML тегов."""
        html_text = "Текст с <b>жирным</b> и <a href='#'>ссылкой</a>"
        clean_text = nlp_pipeline.clean_text(html_text)
        assert clean_text == "Текст с жирным и ссылкой"
    
    def test_clean_text_url_removal(self, nlp_pipeline):
        """Тест удаления URL."""
        url_text = "Читайте на https://example.com/news новости"
        clean_text = nlp_pipeline.clean_text(url_text)
        assert clean_text == "Читайте на новости"
    
    def test_clean_text_email_removal(self, nlp_pipeline):
        """Тест удаления email адресов."""
        email_text = "Пишите на test@example.com для связи"
        clean_text = nlp_pipeline.clean_text(email_text)
        assert clean_text == "Пишите на для связи"
    
    def test_clean_text_quotes_normalization(self, nlp_pipeline):
        """Тест нормализации кавычек."""
        quotes_text = '«Текст» в "разных" „кавычках" и "еще"'
        clean_text = nlp_pipeline.clean_text(quotes_text)
        assert '"' in clean_text
        assert '«' not in clean_text
        assert '»' not in clean_text
    
    def test_clean_text_empty_input(self, nlp_pipeline):
        """Тест обработки пустого ввода."""
        assert nlp_pipeline.clean_text("") == ""
        assert nlp_pipeline.clean_text(None) == ""
    
    @patch('russian_trading_bot.services.russian_nlp.Doc')
    def test_tokenize_and_lemmatize_basic(self, mock_doc, nlp_pipeline):
        """Тест базовой токенизации и лемматизации."""
        # Мокируем pymorphy2
        mock_parsed = Mock()
        mock_parsed.normal_form = "тест"
        mock_parsed.tag.POS = "NOUN"
        nlp_pipeline.pymorphy.parse.return_value = [mock_parsed]
        
        # Мокируем Doc и токены
        mock_token = Mock()
        mock_token.text = "тесты"
        mock_doc_instance = Mock()
        mock_doc_instance.tokens = [mock_token]
        mock_doc.return_value = mock_doc_instance
        
        tokens, lemmas, pos_tags = nlp_pipeline.tokenize_and_lemmatize("тесты")
        
        assert len(tokens) == 1
        assert tokens[0] == "тесты"
        assert len(lemmas) == 1
        assert lemmas[0] == "тест"
        assert len(pos_tags) == 1
        assert pos_tags[0] == "NOUN"
    
    def test_tokenize_and_lemmatize_empty_input(self, nlp_pipeline):
        """Тест токенизации пустого ввода."""
        tokens, lemmas, pos_tags = nlp_pipeline.tokenize_and_lemmatize("")
        assert tokens == []
        assert lemmas == []
        assert pos_tags == []
    
    @patch('russian_trading_bot.services.russian_nlp.Doc')
    def test_extract_entities_basic(self, mock_doc, nlp_pipeline):
        """Тест извлечения именованных сущностей."""
        # Мокируем span
        mock_span = Mock()
        mock_span.text = "Сбербанк"
        mock_span.type = "ORG"
        mock_span.start = 0
        mock_span.stop = 8
        
        mock_doc_instance = Mock()
        mock_doc_instance.spans = [mock_span]
        mock_doc.return_value = mock_doc_instance
        
        # Мокируем экстракторы
        nlp_pipeline.money_extractor.return_value = []
        nlp_pipeline.names_extractor.return_value = []
        
        entities = nlp_pipeline.extract_entities("Сбербанк растет")
        
        assert len(entities) == 1
        assert entities[0]['text'] == "Сбербанк"
        assert entities[0]['label'] == "ORG"
    
    def test_extract_financial_terms(self, nlp_pipeline):
        """Тест извлечения финансовых терминов."""
        tokens = ["акция", "растет", "прибыль", "собака"]
        lemmas = ["акция", "расти", "прибыль", "собака"]
        
        financial_terms = nlp_pipeline.extract_financial_terms(tokens, lemmas)
        
        assert "акция" in financial_terms
        assert "прибыль" in financial_terms
        assert "собака" not in financial_terms
        assert "растет" not in financial_terms
    
    def test_get_company_tickers(self, nlp_pipeline):
        """Тест извлечения тикеров компаний."""
        text = "Сбербанк и Газпром показали хорошие результаты"
        
        # Мокируем process_text
        nlp_pipeline.process_text = Mock(return_value=Mock())
        
        tickers = nlp_pipeline.get_company_tickers(text)
        
        assert "SBER" in tickers
        assert "GAZP" in tickers
    
    def test_process_text_integration(self, nlp_pipeline):
        """Интеграционный тест полной обработки текста."""
        # Мокируем все методы
        nlp_pipeline.clean_text = Mock(return_value="чистый текст")
        nlp_pipeline.tokenize_and_lemmatize = Mock(return_value=(["токен"], ["лемма"], ["NOUN"]))
        nlp_pipeline.extract_entities = Mock(return_value=[{"text": "сущность", "label": "ORG"}])
        nlp_pipeline.extract_financial_terms = Mock(return_value=["акция"])
        nlp_pipeline.extract_money_amounts = Mock(return_value=[{"amount": "1000", "currency": "RUB"}])
        
        result = nlp_pipeline.process_text("тестовый текст")
        
        assert isinstance(result, ProcessedText)
        assert result.original_text == "тестовый текст"
        assert result.cleaned_text == "чистый текст"
        assert result.tokens == ["токен"]
        assert result.lemmas == ["лемма"]
        assert result.pos_tags == ["NOUN"]
        assert len(result.entities) == 1
        assert len(result.financial_terms) == 1
        assert len(result.money_amounts) == 1
    
    def test_process_text_empty_input(self, nlp_pipeline):
        """Тест обработки пустого текста."""
        result = nlp_pipeline.process_text("")
        
        assert isinstance(result, ProcessedText)
        assert result.original_text == ""
        assert result.cleaned_text == ""
        assert result.tokens == []
        assert result.lemmas == []
        assert result.pos_tags == []
        assert result.entities == []
        assert result.financial_terms == []
        assert result.money_amounts == []


class TestRussianNLPIntegration:
    """Интеграционные тесты с реальными данными."""
    
    def test_financial_news_processing(self):
        """Тест обработки реальной финансовой новости."""
        # Этот тест требует реальных моделей, поэтому помечаем как интеграционный
        pytest.skip("Интеграционный тест - требует установленных моделей")
        
        news_text = """
        Акции Сбербанка выросли на 2.5% после публикации квартальных результатов.
        Чистая прибыль банка составила 150 миллиардов рублей, что превысило ожидания аналитиков.
        """
        
        pipeline = RussianNLPPipeline()
        result = pipeline.process_text(news_text)
        
        # Проверяем, что извлечены финансовые термины
        assert any("акция" in term.lower() for term in result.financial_terms)
        assert any("прибыль" in term.lower() for term in result.financial_terms)
        assert any("рубль" in term.lower() for term in result.financial_terms)
        
        # Проверяем извлечение денежных сумм
        assert len(result.money_amounts) > 0
        
        # Проверяем извлечение компаний
        tickers = pipeline.get_company_tickers(news_text)
        assert "SBER" in tickers


if __name__ == "__main__":
    pytest.main([__file__])