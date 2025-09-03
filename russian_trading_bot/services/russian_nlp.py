"""
Russian NLP processing pipeline for financial news analysis.

This module provides comprehensive Russian language processing capabilities
specifically designed for financial news and market analysis.
"""

import re
import logging
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

import spacy
from natasha import (
    Segmenter, MorphVocab, NewsEmbedding, NewsMorphTagger,
    NewsNERTagger, NewsSyntaxParser, Doc
)
from natasha.extractors import MoneyExtractor, NamesExtractor
import pymorphy2

logger = logging.getLogger(__name__)


@dataclass
class ProcessedText:
    """Результат обработки русского текста."""
    original_text: str
    cleaned_text: str
    tokens: List[str]
    lemmas: List[str]
    pos_tags: List[str]
    entities: List[Dict[str, str]]
    financial_terms: List[str]
    money_amounts: List[Dict[str, str]]


class RussianFinancialTerms:
    """Словарь русской финансовой терминологии."""
    
    def __init__(self):
        self.financial_terms = {
            # Основные финансовые термины
            'акция', 'акции', 'акций', 'акциями', 'акциях',
            'облигация', 'облигации', 'облигаций', 'облигациями',
            'дивиденд', 'дивиденды', 'дивидендов', 'дивидендами',
            'прибыль', 'прибыли', 'прибылью', 'убыток', 'убытки', 'убытков',
            'выручка', 'выручки', 'выручкой', 'доход', 'доходы', 'доходов',
            'капитализация', 'капитализации', 'капитализацией',
            'котировка', 'котировки', 'котировок', 'котировками',
            'индекс', 'индексы', 'индексов', 'индексами',
            
            # Рыночные термины
            'рост', 'росте', 'ростом', 'падение', 'падении', 'падением',
            'волатильность', 'волатильности', 'волатильностью',
            'ликвидность', 'ликвидности', 'ликвидностью',
            'торги', 'торгов', 'торгами', 'сделка', 'сделки', 'сделок',
            'объем', 'объемы', 'объемов', 'объемами',
            
            # Компании и секторы
            'банк', 'банки', 'банков', 'банками', 'банковский',
            'нефть', 'нефти', 'нефтью', 'нефтяной', 'газ', 'газа', 'газом', 'газовый',
            'металлургия', 'металлургии', 'металлургией', 'металлургический',
            'телеком', 'телекома', 'телекоммуникации', 'телекоммуникаций',
            'ритейл', 'ритейла', 'ритейлом', 'розничный',
            
            # Валюты
            'рубль', 'рубли', 'рублей', 'рублями', 'рублях',
            'доллар', 'доллары', 'долларов', 'долларами', 'долларах',
            'евро', 'валюта', 'валюты', 'валют', 'валютой',
            
            # Регулирование
            'цб', 'центробанк', 'банк россии', 'регулятор', 'регулятора',
            'ставка', 'ставки', 'ставок', 'ставкой', 'ключевая ставка',
            'санкции', 'санкций', 'санкциями', 'ограничения', 'ограничений'
        }
        
        # Компании MOEX
        self.moex_companies = {
            'сбер': 'SBER', 'сбербанк': 'SBER',
            'газпром': 'GAZP', 'газпрома': 'GAZP',
            'лукойл': 'LKOH', 'лукойла': 'LKOH',
            'роснефть': 'ROSN', 'роснефти': 'ROSN',
            'новатэк': 'NVTK', 'новатэка': 'NVTK',
            'татнефть': 'TATN', 'татнефти': 'TATN',
            'магнит': 'MGNT', 'магнита': 'MGNT',
            'яндекс': 'YNDX', 'яндекса': 'YNDX',
            'мтс': 'MTSS', 'мегафон': 'MFON',
            'норникель': 'GMKN', 'норникеля': 'GMKN',
            'северсталь': 'CHMF', 'северстали': 'CHMF',
            'алроса': 'ALRS', 'алросы': 'ALRS',
            'полюс': 'PLZL', 'полюса': 'PLZL',
            'x5': 'FIVE', 'пятерочка': 'FIVE',
            'тинькофф': 'TCS', 'тинькова': 'TCS',
            'втб': 'VTBR', 'вэб': 'VEB'
        }
    
    def is_financial_term(self, word: str) -> bool:
        """Проверяет, является ли слово финансовым термином."""
        return word.lower() in self.financial_terms
    
    def get_ticker_by_company(self, company_name: str) -> Optional[str]:
        """Возвращает тикер по названию компании."""
        return self.moex_companies.get(company_name.lower())


class RussianNLPPipeline:
    """Основной класс для обработки русского текста в финансовом контексте."""
    
    def __init__(self):
        self.segmenter = None
        self.morph_vocab = None
        self.emb = None
        self.morph_tagger = None
        self.ner_tagger = None
        self.syntax_parser = None
        self.pymorphy = None
        self.spacy_nlp = None
        self.financial_terms = RussianFinancialTerms()
        self.money_extractor = None
        self.names_extractor = None
        
        self._initialize_models()
    
    def _initialize_models(self):
        """Инициализирует все NLP модели."""
        try:
            logger.info("Инициализация русских NLP моделей...")
            
            # Natasha компоненты
            self.segmenter = Segmenter()
            self.morph_vocab = MorphVocab()
            self.emb = NewsEmbedding()
            self.morph_tagger = NewsMorphTagger(self.emb)
            self.ner_tagger = NewsNERTagger(self.emb)
            self.syntax_parser = NewsSyntaxParser(self.emb)
            
            # PyMorphy2 для морфологического анализа
            self.pymorphy = pymorphy2.MorphAnalyzer()
            
            # Инициализируем экстракторы с морфологическим анализатором
            self.money_extractor = MoneyExtractor(self.pymorphy)
            self.names_extractor = NamesExtractor(self.pymorphy)
            
            # Попытка загрузить spaCy модель для русского языка
            try:
                self.spacy_nlp = spacy.load("ru_core_news_sm")
                logger.info("SpaCy модель ru_core_news_sm загружена")
            except OSError:
                logger.warning("SpaCy модель ru_core_news_sm не найдена. Используем только Natasha и PyMorphy2")
                self.spacy_nlp = None
            
            logger.info("Русские NLP модели успешно инициализированы")
            
        except Exception as e:
            logger.error(f"Ошибка при инициализации NLP моделей: {e}")
            raise
    
    def clean_text(self, text: str) -> str:
        """Очищает текст от лишних символов и нормализует."""
        if not text:
            return ""
        
        # Удаляем лишние пробелы и переносы строк
        text = re.sub(r'\s+', ' ', text)
        
        # Удаляем HTML теги если есть
        text = re.sub(r'<[^>]+>', '', text)
        
        # Удаляем URL
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', ' ', text)
        
        # Удаляем email адреса
        text = re.sub(r'\S+@\S+', ' ', text)
        
        # Нормализуем кавычки
        text = re.sub(r'[«»""„"]', '"', text)
        
        # Удаляем лишние знаки препинания
        text = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)\"\'№%]', '', text)
        
        # Финальная нормализация пробелов
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def tokenize_and_lemmatize(self, text: str) -> Tuple[List[str], List[str], List[str]]:
        """Токенизирует текст и возвращает токены, леммы и части речи."""
        if not text:
            return [], [], []
        
        try:
            # Используем Natasha для токенизации и морфологического анализа
            doc = Doc(text)
            doc.segment(self.segmenter)
            doc.tag_morph(self.morph_tagger)
            
            tokens = []
            lemmas = []
            pos_tags = []
            
            for token in doc.tokens:
                if token.text.strip() and len(token.text) > 1:
                    tokens.append(token.text)
                    
                    # Получаем лемму через PyMorphy2 для лучшего качества
                    parsed = self.pymorphy.parse(token.text)[0]
                    lemmas.append(parsed.normal_form)
                    pos_tags.append(parsed.tag.POS or 'UNKN')
            
            return tokens, lemmas, pos_tags
            
        except Exception as e:
            logger.error(f"Ошибка при токенизации: {e}")
            # Fallback к простой токенизации
            tokens = text.split()
            lemmas = [self.pymorphy.parse(token)[0].normal_form for token in tokens]
            pos_tags = ['UNKN'] * len(tokens)
            return tokens, lemmas, pos_tags
    
    def extract_entities(self, text: str) -> List[Dict[str, str]]:
        """Извлекает именованные сущности из текста."""
        entities = []
        
        try:
            # Используем Natasha NER
            doc = Doc(text)
            doc.segment(self.segmenter)
            doc.tag_ner(self.ner_tagger)
            
            for span in doc.spans:
                entities.append({
                    'text': span.text,
                    'label': span.type,
                    'start': span.start,
                    'end': span.stop
                })
            
            # Дополнительно извлекаем персон и деньги
            money_matches = list(self.money_extractor(text))
            for match in money_matches:
                entities.append({
                    'text': match.fact.amount,
                    'label': 'MONEY',
                    'start': match.start,
                    'end': match.stop,
                    'currency': getattr(match.fact, 'currency', 'RUB')
                })
            
            names_matches = list(self.names_extractor(text))
            for match in names_matches:
                first_name = getattr(match.fact, 'first', '') or ''
                last_name = getattr(match.fact, 'last', '') or ''
                full_name = (first_name + ' ' + last_name).strip() if last_name else first_name
                if full_name:
                    entities.append({
                        'text': full_name,
                        'label': 'PERSON',
                        'start': match.start,
                        'end': match.stop
                    })
            
        except Exception as e:
            logger.error(f"Ошибка при извлечении сущностей: {e}")
        
        return entities
    
    def extract_financial_terms(self, tokens: List[str], lemmas: List[str]) -> List[str]:
        """Извлекает финансовые термины из токенов."""
        financial_terms = []
        
        # Проверяем токены
        for token in tokens:
            if self.financial_terms.is_financial_term(token):
                financial_terms.append(token)
        
        # Проверяем леммы
        for lemma in lemmas:
            if self.financial_terms.is_financial_term(lemma):
                financial_terms.append(lemma)
        
        return list(set(financial_terms))  # Убираем дубликаты
    
    def extract_money_amounts(self, text: str) -> List[Dict[str, str]]:
        """Извлекает денежные суммы из текста."""
        money_amounts = []
        
        try:
            matches = list(self.money_extractor(text))
            for match in matches:
                money_amounts.append({
                    'amount': str(match.fact.amount),
                    'currency': getattr(match.fact, 'currency', 'RUB'),
                    'text': text[match.start:match.stop],
                    'start': match.start,
                    'end': match.stop
                })
        except Exception as e:
            logger.error(f"Ошибка при извлечении денежных сумм: {e}")
        
        return money_amounts
    
    def process_text(self, text: str) -> ProcessedText:
        """Полная обработка русского текста."""
        if not text:
            return ProcessedText(
                original_text="",
                cleaned_text="",
                tokens=[],
                lemmas=[],
                pos_tags=[],
                entities=[],
                financial_terms=[],
                money_amounts=[]
            )
        
        try:
            # Очищаем текст
            cleaned_text = self.clean_text(text)
            
            # Токенизируем и лемматизируем
            tokens, lemmas, pos_tags = self.tokenize_and_lemmatize(cleaned_text)
            
            # Извлекаем сущности
            entities = self.extract_entities(cleaned_text)
            
            # Извлекаем финансовые термины
            financial_terms = self.extract_financial_terms(tokens, lemmas)
            
            # Извлекаем денежные суммы
            money_amounts = self.extract_money_amounts(cleaned_text)
            
            return ProcessedText(
                original_text=text,
                cleaned_text=cleaned_text,
                tokens=tokens,
                lemmas=lemmas,
                pos_tags=pos_tags,
                entities=entities,
                financial_terms=financial_terms,
                money_amounts=money_amounts
            )
            
        except Exception as e:
            logger.error(f"Ошибка при обработке текста: {e}")
            return ProcessedText(
                original_text=text,
                cleaned_text=text,
                tokens=[],
                lemmas=[],
                pos_tags=[],
                entities=[],
                financial_terms=[],
                money_amounts=[]
            )
    
    def get_company_tickers(self, text: str) -> List[str]:
        """Извлекает тикеры компаний из текста."""
        tickers = []
        processed = self.process_text(text)
        
        # Ищем упоминания компаний в тексте
        text_lower = text.lower()
        for company, ticker in self.financial_terms.moex_companies.items():
            if company in text_lower:
                tickers.append(ticker)
        
        return list(set(tickers))