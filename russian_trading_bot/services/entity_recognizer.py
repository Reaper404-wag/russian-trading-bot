"""
Entity recognition service for Russian companies and stock symbols.

This module provides comprehensive entity recognition capabilities specifically
designed for identifying Russian companies, their stock symbols, and linking
news mentions to MOEX tickers.
"""

import re
import json
import logging
from typing import List, Dict, Set, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from pathlib import Path

from .russian_nlp import RussianNLPPipeline

logger = logging.getLogger(__name__)


@dataclass
class CompanyEntity:
    """Сущность российской компании."""
    name: str
    ticker: str
    aliases: List[str]
    sector: str
    full_name: str
    confidence: float = 0.0
    start_pos: int = -1
    end_pos: int = -1


@dataclass
class EntityRecognitionResult:
    """Результат распознавания сущностей в тексте."""
    text: str
    companies: List[CompanyEntity]
    tickers_mentioned: List[str]
    confidence_score: float
    processing_time: float


class RussianCompanyDictionary:
    """Словарь российских компаний и их тикеров на MOEX."""
    
    def __init__(self):
        self.companies_data = self._build_companies_dictionary()
        self.ticker_to_company = self._build_ticker_mapping()
        self.alias_to_ticker = self._build_alias_mapping()
        
    def _build_companies_dictionary(self) -> Dict[str, Dict[str, Any]]:
        """Создает полный словарь российских компаний."""
        return {
            'SBER': {
                'name': 'Сбербанк',
                'full_name': 'ПАО Сбербанк России',
                'sector': 'Банки',
                'aliases': [
                    'сбер', 'сбербанк', 'сбербанка', 'сбербанку', 'сбербанком', 'сбербанке',
                    'сбера', 'сберу', 'сбером', 'сбере', 'пао сбербанк', 'sberbank',
                    'сбербанк россии', 'сбербанк рф'
                ]
            },
            'GAZP': {
                'name': 'Газпром',
                'full_name': 'ПАО Газпром',
                'sector': 'Нефть и газ',
                'aliases': [
                    'газпром', 'газпрома', 'газпрому', 'газпромом', 'газпроме',
                    'пао газпром', 'gazprom', 'газпром нефть'
                ]
            },
            'LKOH': {
                'name': 'Лукойл',
                'full_name': 'ПАО НК Лукойл',
                'sector': 'Нефть и газ',
                'aliases': [
                    'лукойл', 'лукойла', 'лукойлу', 'лукойлом', 'лукойле',
                    'пао нк лукойл', 'lukoil', 'нк лукойл'
                ]
            },
            'ROSN': {
                'name': 'Роснефть',
                'full_name': 'ПАО НК Роснефть',
                'sector': 'Нефть и газ',
                'aliases': [
                    'роснефть', 'роснефти', 'роснефтью', 'роснефтей',
                    'пао нк роснефть', 'rosneft', 'нк роснефть'
                ]
            },
            'NVTK': {
                'name': 'Новатэк',
                'full_name': 'ПАО Новатэк',
                'sector': 'Нефть и газ',
                'aliases': [
                    'новатэк', 'новатэка', 'новатэку', 'новатэком', 'новатэке',
                    'пао новатэк', 'novatek'
                ]
            },
            'TATN': {
                'name': 'Татнефть',
                'full_name': 'ПАО Татнефть',
                'sector': 'Нефть и газ',
                'aliases': [
                    'татнефть', 'татнефти', 'татнефтью', 'татнефтей',
                    'пао татнефть', 'tatneft'
                ]
            },
            'MGNT': {
                'name': 'Магнит',
                'full_name': 'ПАО Магнит',
                'sector': 'Ритейл',
                'aliases': [
                    'магнит', 'магнита', 'магниту', 'магнитом', 'магните',
                    'пао магнит', 'magnit'
                ]
            },
            'YNDX': {
                'name': 'Яндекс',
                'full_name': 'Яндекс НВ',
                'sector': 'Технологии',
                'aliases': [
                    'яндекс', 'яндекса', 'яндексу', 'яндексом', 'яндексе',
                    'yandex', 'яндекс нв'
                ]
            },
            'MTSS': {
                'name': 'МТС',
                'full_name': 'ПАО МТС',
                'sector': 'Телекоммуникации',
                'aliases': [
                    'мтс', 'мобильные телесистемы', 'пао мтс', 'mobile telesystems'
                ]
            },
            'MFON': {
                'name': 'МегаФон',
                'full_name': 'ПАО МегаФон',
                'sector': 'Телекоммуникации',
                'aliases': [
                    'мегафон', 'мегафона', 'мегафону', 'мегафоном', 'мегафоне',
                    'пао мегафон', 'megafon'
                ]
            },
            'GMKN': {
                'name': 'Норникель',
                'full_name': 'ПАО ГМК Норильский никель',
                'sector': 'Металлургия',
                'aliases': [
                    'норникель', 'норникеля', 'норникелю', 'норникелем', 'норникеле',
                    'норильский никель', 'гмк норильский никель', 'пао гмк норильский никель',
                    'norilsk nickel', 'nornickel'
                ]
            },
            'CHMF': {
                'name': 'Северсталь',
                'full_name': 'ПАО Северсталь',
                'sector': 'Металлургия',
                'aliases': [
                    'северсталь', 'северстали', 'северсталью', 'северсталей',
                    'пао северсталь', 'severstal'
                ]
            },
            'ALRS': {
                'name': 'АЛРОСА',
                'full_name': 'ПАО АЛРОСА',
                'sector': 'Добыча',
                'aliases': [
                    'алроса', 'алросы', 'алросе', 'алросой', 'алросу',
                    'пао алроса', 'alrosa'
                ]
            },
            'PLZL': {
                'name': 'Полюс',
                'full_name': 'ПАО Полюс',
                'sector': 'Добыча',
                'aliases': [
                    'полюс', 'полюса', 'полюсу', 'полюсом', 'полюсе',
                    'пао полюс', 'polyus'
                ]
            },
            'FIVE': {
                'name': 'X5 Retail Group',
                'full_name': 'X5 Retail Group',
                'sector': 'Ритейл',
                'aliases': [
                    'x5', 'икс5', 'пятерочка', 'карусель', 'перекресток',
                    'x5 retail group', 'x5 ритейл групп'
                ]
            },
            'TCS': {
                'name': 'Тинькофф',
                'full_name': 'Тинькофф Банк',
                'sector': 'Банки',
                'aliases': [
                    'тинькофф', 'тинькова', 'тинькову', 'тиньковым', 'тинькове',
                    'тинькофф банк', 'tinkoff', 'tcs group'
                ]
            },
            'VTBR': {
                'name': 'ВТБ',
                'full_name': 'Банк ВТБ',
                'sector': 'Банки',
                'aliases': [
                    'втб', 'банк втб', 'пао банк втб', 'vtb bank'
                ]
            },
            'AFLT': {
                'name': 'Аэрофлот',
                'full_name': 'ПАО Аэрофлот',
                'sector': 'Транспорт',
                'aliases': [
                    'аэрофлот', 'аэрофлота', 'аэрофлоту', 'аэрофлотом', 'аэрофлоте',
                    'пао аэрофлот', 'aeroflot'
                ]
            },
            'RTKM': {
                'name': 'Ростелеком',
                'full_name': 'ПАО Ростелеком',
                'sector': 'Телекоммуникации',
                'aliases': [
                    'ростелеком', 'ростелекома', 'ростелекому', 'ростелекомом', 'ростелекоме',
                    'пао ростелеком', 'rostelecom'
                ]
            },
            'SNGS': {
                'name': 'Сургутнефтегаз',
                'full_name': 'ПАО Сургутнефтегаз',
                'sector': 'Нефть и газ',
                'aliases': [
                    'сургутнефтегаз', 'сургутнефтегаза', 'сургутнефтегазу',
                    'пао сургутнефтегаз', 'surgutneftegas'
                ]
            }
        }
    
    def _build_ticker_mapping(self) -> Dict[str, Dict[str, Any]]:
        """Создает маппинг тикер -> данные компании."""
        return {ticker: data for ticker, data in self.companies_data.items()}
    
    def _build_alias_mapping(self) -> Dict[str, str]:
        """Создает маппинг алиас -> тикер."""
        alias_mapping = {}
        for ticker, data in self.companies_data.items():
            # Добавляем основное название
            alias_mapping[data['name'].lower()] = ticker
            alias_mapping[data['full_name'].lower()] = ticker
            
            # Добавляем все алиасы
            for alias in data['aliases']:
                alias_mapping[alias.lower()] = ticker
        
        return alias_mapping
    
    def get_ticker_by_alias(self, alias: str) -> Optional[str]:
        """Возвращает тикер по алиасу компании."""
        return self.alias_to_ticker.get(alias.lower())
    
    def get_company_data(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Возвращает данные компании по тикеру."""
        return self.ticker_to_company.get(ticker.upper())
    
    def get_all_tickers(self) -> List[str]:
        """Возвращает список всех тикеров."""
        return list(self.companies_data.keys())
    
    def get_companies_by_sector(self, sector: str) -> List[str]:
        """Возвращает список тикеров компаний по сектору."""
        return [
            ticker for ticker, data in self.companies_data.items()
            if data['sector'].lower() == sector.lower()
        ]


class RussianEntityRecognizer:
    """Основной класс для распознавания российских компаний в тексте."""
    
    def __init__(self):
        self.nlp_pipeline = RussianNLPPipeline()
        self.company_dict = RussianCompanyDictionary()
        self.confidence_threshold = 0.5  # Понижаем порог для лучшего распознавания
        
    def _calculate_confidence(self, match_text: str, alias: str, context: str) -> float:
        """Вычисляет уверенность в распознавании сущности."""
        confidence = 0.0
        
        # Базовая уверенность от точности совпадения
        if match_text.lower() == alias.lower():
            confidence += 0.6
        elif alias.lower() in match_text.lower():
            confidence += 0.4
        else:
            confidence += 0.2
        
        # Бонус за финансовый контекст
        financial_keywords = [
            'акции', 'акция', 'котировки', 'цена', 'рост', 'падение',
            'прибыль', 'убыток', 'выручка', 'дивиденды', 'капитализация',
            'торги', 'биржа', 'moex', 'московская биржа', 'отчетность',
            'результаты', 'квартал', 'компания', 'бумаги', 'инвестор'
        ]
        
        context_lower = context.lower()
        financial_context_bonus = 0
        for keyword in financial_keywords:
            if keyword in context_lower:
                financial_context_bonus += 0.05
        
        confidence += min(0.2, financial_context_bonus)  # Максимум 0.2 за финансовый контекст
        
        # Бонус за упоминание денежных сумм
        if any(word in context_lower for word in ['рубл', 'млрд', 'млн', 'тыс', '%', 'процент']):
            confidence += 0.1
        
        # Бонус за упоминание в новостном контексте
        news_keywords = ['сообщ', 'объяв', 'заяв', 'опублик', 'показ', 'продемонстр']
        if any(keyword in context_lower for keyword in news_keywords):
            confidence += 0.05
        
        # Штраф за слишком короткие совпадения только для коротких алиасов
        if len(alias) < 4 and len(match_text) < 3:
            confidence -= 0.1
        
        return min(1.0, max(0.0, confidence))
    
    def _extract_company_mentions(self, text: str) -> List[CompanyEntity]:
        """Извлекает упоминания компаний из текста."""
        companies = []
        text_lower = text.lower()
        
        # Ищем все возможные упоминания компаний
        for alias, ticker in self.company_dict.alias_to_ticker.items():
            # Используем регулярные выражения для поиска слов целиком
            pattern = r'\b' + re.escape(alias) + r'\b'
            matches = list(re.finditer(pattern, text_lower, re.IGNORECASE))
            
            for match in matches:
                start_pos = match.start()
                end_pos = match.end()
                match_text = text[start_pos:end_pos]
                
                # Получаем контекст вокруг упоминания (50 символов в каждую сторону)
                context_start = max(0, start_pos - 50)
                context_end = min(len(text), end_pos + 50)
                context = text[context_start:context_end]
                
                # Вычисляем уверенность
                confidence = self._calculate_confidence(match_text, alias, context)
                
                if confidence >= self.confidence_threshold:
                    company_data = self.company_dict.get_company_data(ticker)
                    if company_data:
                        company_entity = CompanyEntity(
                            name=company_data['name'],
                            ticker=ticker,
                            aliases=company_data['aliases'],
                            sector=company_data['sector'],
                            full_name=company_data['full_name'],
                            confidence=confidence,
                            start_pos=start_pos,
                            end_pos=end_pos
                        )
                        companies.append(company_entity)
        
        # Удаляем дубликаты и сортируем по позиции
        unique_companies = {}
        for company in companies:
            key = f"{company.ticker}_{company.start_pos}"
            if key not in unique_companies or company.confidence > unique_companies[key].confidence:
                unique_companies[key] = company
        
        return sorted(unique_companies.values(), key=lambda x: x.start_pos)
    
    def _extract_direct_tickers(self, text: str) -> List[str]:
        """Извлекает прямые упоминания тикеров из текста."""
        tickers = []
        
        # Паттерн для поиска тикеров (4-5 заглавных букв)
        ticker_pattern = r'\b[A-Z]{3,5}\b'
        matches = re.findall(ticker_pattern, text)
        
        for match in matches:
            if match in self.company_dict.get_all_tickers():
                tickers.append(match)
        
        return list(set(tickers))
    
    def recognize_entities(self, text: str) -> EntityRecognitionResult:
        """Распознает все сущности российских компаний в тексте."""
        import time
        start_time = time.time()
        
        if not text or not text.strip():
            return EntityRecognitionResult(
                text=text,
                companies=[],
                tickers_mentioned=[],
                confidence_score=0.0,
                processing_time=0.0
            )
        
        try:
            # Извлекаем упоминания компаний
            companies = self._extract_company_mentions(text)
            
            # Извлекаем прямые упоминания тикеров
            direct_tickers = self._extract_direct_tickers(text)
            
            # Собираем все упомянутые тикеры
            all_tickers = list(set([company.ticker for company in companies] + direct_tickers))
            
            # Вычисляем общую уверенность
            if companies:
                confidence_score = sum(company.confidence for company in companies) / len(companies)
            else:
                confidence_score = 0.8 if direct_tickers else 0.0
            
            processing_time = time.time() - start_time
            
            return EntityRecognitionResult(
                text=text,
                companies=companies,
                tickers_mentioned=all_tickers,
                confidence_score=confidence_score,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Ошибка при распознавании сущностей: {e}")
            processing_time = time.time() - start_time
            
            return EntityRecognitionResult(
                text=text,
                companies=[],
                tickers_mentioned=[],
                confidence_score=0.0,
                processing_time=processing_time
            )
    
    def link_news_to_stocks(self, news_text: str, news_title: str = "") -> Dict[str, Any]:
        """Связывает новость с упомянутыми в ней акциями."""
        full_text = f"{news_title} {news_text}".strip()
        
        # Распознаем сущности
        recognition_result = self.recognize_entities(full_text)
        
        # Группируем по секторам
        sectors = {}
        for company in recognition_result.companies:
            sector = company.sector
            if sector not in sectors:
                sectors[sector] = []
            sectors[sector].append({
                'ticker': company.ticker,
                'name': company.name,
                'confidence': company.confidence
            })
        
        return {
            'tickers': recognition_result.tickers_mentioned,
            'companies': [asdict(company) for company in recognition_result.companies],
            'sectors_affected': sectors,
            'overall_confidence': recognition_result.confidence_score,
            'processing_time': recognition_result.processing_time
        }
    
    def get_company_info(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Возвращает информацию о компании по тикеру."""
        return self.company_dict.get_company_data(ticker)
    
    def search_companies(self, query: str) -> List[Dict[str, Any]]:
        """Ищет компании по запросу."""
        results = []
        query_lower = query.lower()
        
        for ticker, data in self.company_dict.companies_data.items():
            # Проверяем название и алиасы
            if (query_lower in data['name'].lower() or 
                query_lower in data['full_name'].lower() or
                any(query_lower in alias.lower() for alias in data['aliases'])):
                
                results.append({
                    'ticker': ticker,
                    'name': data['name'],
                    'full_name': data['full_name'],
                    'sector': data['sector'],
                    'aliases': data['aliases']
                })
        
        return results
    
    def set_confidence_threshold(self, threshold: float):
        """Устанавливает порог уверенности для распознавания."""
        if 0.0 <= threshold <= 1.0:
            self.confidence_threshold = threshold
        else:
            raise ValueError("Порог уверенности должен быть между 0.0 и 1.0")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Возвращает статистику по словарю компаний."""
        sectors_count = {}
        total_aliases = 0
        
        for ticker, data in self.company_dict.companies_data.items():
            sector = data['sector']
            sectors_count[sector] = sectors_count.get(sector, 0) + 1
            total_aliases += len(data['aliases'])
        
        return {
            'total_companies': len(self.company_dict.companies_data),
            'total_aliases': total_aliases,
            'sectors': sectors_count,
            'average_aliases_per_company': total_aliases / len(self.company_dict.companies_data)
        }