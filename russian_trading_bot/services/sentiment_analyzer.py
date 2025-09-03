"""
Russian Financial News Sentiment Analysis Service

This module provides sentiment analysis capabilities specifically designed
for Russian financial news content, with support for financial terminology
and market-specific sentiment patterns.
"""

import logging
import re
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass
from datetime import datetime
import pickle
import os
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import joblib

from ..models.news_data import RussianNewsArticle, NewsSentiment, SENTIMENT_LEVELS
from .russian_nlp import RussianNLPPipeline, ProcessedText

logger = logging.getLogger(__name__)


@dataclass
class SentimentFeatures:
    """Признаки для анализа настроений."""
    tfidf_features: np.ndarray
    financial_term_count: int
    positive_word_count: int
    negative_word_count: int
    exclamation_count: int
    question_count: int
    capital_ratio: float
    sentence_count: int
    avg_sentence_length: float


class RussianFinancialSentimentLexicon:
    """Словарь русских финансовых терминов с эмоциональной окраской."""
    
    def __init__(self):
        # Позитивные финансовые термины
        self.positive_terms = {
            'рост', 'растет', 'выросли', 'увеличение', 'прибыль', 'доходы',
            'успех', 'успешный', 'прорыв', 'достижение', 'рекорд', 'максимум',
            'подъем', 'восстановление', 'улучшение', 'оптимизм', 'позитивный',
            'стабильность', 'укрепление', 'развитие', 'расширение', 'инновации',
            'дивиденды', 'выплаты', 'бонус', 'премия', 'награда', 'победа',
            'лидер', 'лидирует', 'превышение', 'превзошел', 'опережение',
            'эффективность', 'результативность', 'производительность',
            'конкурентоспособность', 'перспективы', 'потенциал', 'возможности'
        }
        
        # Негативные финансовые термины
        self.negative_terms = {
            'падение', 'снижение', 'упал', 'сократился', 'убыток', 'потери',
            'кризис', 'проблемы', 'трудности', 'риски', 'угроза', 'опасность',
            'минимум', 'дно', 'обвал', 'крах', 'банкротство', 'долги',
            'задолженность', 'штраф', 'санкции', 'ограничения', 'запрет',
            'остановка', 'приостановка', 'закрытие', 'сокращение', 'увольнение',
            'неопределенность', 'нестабильность', 'волатильность', 'спад',
            'рецессия', 'стагнация', 'инфляция', 'девальвация', 'обесценение',
            'дефицит', 'нехватка', 'недостаток', 'провал', 'неудача'
        }
        
        # Нейтральные финансовые термины
        self.neutral_terms = {
            'акции', 'облигации', 'капитализация', 'котировки', 'индекс',
            'торги', 'сделка', 'объем', 'цена', 'стоимость', 'курс',
            'рубль', 'доллар', 'евро', 'валюта', 'биржа', 'рынок',
            'инвестиции', 'портфель', 'активы', 'пассивы', 'баланс',
            'отчет', 'квартал', 'год', 'период', 'данные', 'показатели',
            'анализ', 'прогноз', 'оценка', 'рейтинг', 'рекомендация'
        }
        
        # Усилители (модификаторы интенсивности)
        self.intensifiers = {
            'очень': 1.5, 'крайне': 1.8, 'чрезвычайно': 2.0, 'исключительно': 1.7,
            'значительно': 1.4, 'существенно': 1.4, 'серьезно': 1.3,
            'резко': 1.6, 'стремительно': 1.7, 'кардинально': 1.8,
            'немного': 0.7, 'слегка': 0.6, 'незначительно': 0.5,
            'практически': 0.9, 'почти': 0.8, 'едва': 0.4
        }
        
        # Отрицания
        self.negations = {
            'не', 'нет', 'ни', 'без', 'отсутствие', 'недостаток',
            'невозможно', 'нельзя', 'запрещено', 'исключено'
        }
    
    def get_term_sentiment(self, term: str) -> float:
        """Возвращает эмоциональную окраску термина (-1.0 до 1.0)."""
        term_lower = term.lower()
        
        if term_lower in self.positive_terms:
            return 1.0
        elif term_lower in self.negative_terms:
            return -1.0
        elif term_lower in self.neutral_terms:
            return 0.0
        else:
            return 0.0
    
    def get_intensifier_weight(self, word: str) -> float:
        """Возвращает вес усилителя."""
        return self.intensifiers.get(word.lower(), 1.0)
    
    def is_negation(self, word: str) -> bool:
        """Проверяет, является ли слово отрицанием."""
        return word.lower() in self.negations


class RussianSentimentAnalyzer:
    """Анализатор настроений для русских финансовых новостей."""
    
    def __init__(self, model_path: Optional[str] = None):
        self.nlp_pipeline = RussianNLPPipeline()
        self.lexicon = RussianFinancialSentimentLexicon()
        self.vectorizer = None
        self.model = None
        self.model_path = model_path or "models/russian_sentiment_model.pkl"
        
        # Создаем директорию для моделей если не существует
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        
        # Пытаемся загрузить предобученную модель
        self._load_model()
        
        # Если модель не загружена, создаем базовую
        if self.model is None:
            self._initialize_basic_model()
    
    def _load_model(self) -> bool:
        """Загружает предобученную модель."""
        try:
            if os.path.exists(self.model_path):
                with open(self.model_path, 'rb') as f:
                    model_data = pickle.load(f)
                    self.vectorizer = model_data['vectorizer']
                    self.model = model_data['model']
                logger.info(f"Модель загружена из {self.model_path}")
                return True
        except Exception as e:
            logger.warning(f"Не удалось загрузить модель: {e}")
        return False
    
    def _save_model(self):
        """Сохраняет модель."""
        try:
            model_data = {
                'vectorizer': self.vectorizer,
                'model': self.model
            }
            with open(self.model_path, 'wb') as f:
                pickle.dump(model_data, f)
            logger.info(f"Модель сохранена в {self.model_path}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении модели: {e}")
    
    def _initialize_basic_model(self):
        """Инициализирует базовую модель с синтетическими данными."""
        logger.info("Инициализация базовой модели анализа настроений...")
        
        # Создаем синтетические данные для обучения
        synthetic_data = self._create_synthetic_training_data()
        
        if synthetic_data:
            texts, labels = zip(*synthetic_data)
            self._train_model(list(texts), list(labels))
        else:
            # Создаем минимальную модель
            self.vectorizer = TfidfVectorizer(
                max_features=1000,
                ngram_range=(1, 2),
                stop_words=None
            )
            self.model = LogisticRegression(random_state=42)
            logger.warning("Создана минимальная модель без обучения")
    
    def _create_synthetic_training_data(self) -> List[Tuple[str, str]]:
        """Создает синтетические данные для обучения."""
        synthetic_data = []
        
        # Позитивные примеры
        positive_templates = [
            "Акции {company} выросли на {percent}% после публикации отличных результатов",
            "Прибыль {company} превзошла ожидания аналитиков",
            "Успешное развитие бизнеса {company} радует инвесторов",
            "Рекордные показатели {company} укрепляют позиции на рынке",
            "Дивиденды {company} увеличились благодаря росту прибыли"
        ]
        
        # Негативные примеры
        negative_templates = [
            "Акции {company} упали на {percent}% из-за плохих новостей",
            "Убытки {company} разочаровали инвесторов",
            "Кризис в {company} вызывает серьезные опасения",
            "Санкции негативно повлияли на деятельность {company}",
            "Проблемы {company} могут привести к дальнейшему падению"
        ]
        
        # Нейтральные примеры
        neutral_templates = [
            "Компания {company} опубликовала квартальный отчет",
            "Торги акциями {company} проходят в обычном режиме",
            "Аналитики дали прогноз по акциям {company}",
            "Капитализация {company} составляет {amount} рублей",
            "Индекс MOEX включает акции {company}"
        ]
        
        companies = ["Сбербанк", "Газпром", "Лукойл", "Роснефть", "Яндекс"]
        percentages = ["5", "10", "15", "20"]
        amounts = ["1 трлн", "500 млрд", "2 трлн"]
        
        # Генерируем позитивные примеры
        for template in positive_templates:
            for company in companies:
                for percent in percentages:
                    for amount in amounts:
                        text = template.format(company=company, percent=percent, amount=amount)
                        synthetic_data.append((text, "POSITIVE"))
        
        # Генерируем негативные примеры
        for template in negative_templates:
            for company in companies:
                for percent in percentages:
                    text = template.format(company=company, percent=percent)
                    synthetic_data.append((text, "NEGATIVE"))
        
        # Генерируем нейтральные примеры
        for template in neutral_templates:
            for company in companies:
                for amount in amounts:
                    text = template.format(company=company, amount=amount)
                    synthetic_data.append((text, "NEUTRAL"))
        
        return synthetic_data
    
    def _extract_features(self, processed_text: ProcessedText) -> SentimentFeatures:
        """Извлекает признаки для анализа настроений."""
        text = processed_text.cleaned_text
        tokens = processed_text.tokens
        lemmas = processed_text.lemmas
        
        # TF-IDF признаки (будут заполнены позже)
        tfidf_features = np.array([])
        
        # Подсчет финансовых терминов
        financial_term_count = len(processed_text.financial_terms)
        
        # Подсчет позитивных и негативных слов
        positive_count = sum(1 for lemma in lemmas 
                           if self.lexicon.get_term_sentiment(lemma) > 0)
        negative_count = sum(1 for lemma in lemmas 
                           if self.lexicon.get_term_sentiment(lemma) < 0)
        
        # Подсчет знаков препинания
        exclamation_count = text.count('!')
        question_count = text.count('?')
        
        # Соотношение заглавных букв
        if len(text) > 0:
            capital_ratio = sum(1 for c in text if c.isupper()) / len(text)
        else:
            capital_ratio = 0.0
        
        # Статистика предложений
        sentences = re.split(r'[.!?]+', text)
        sentence_count = len([s for s in sentences if s.strip()])
        avg_sentence_length = np.mean([len(s.split()) for s in sentences if s.strip()]) if sentences else 0
        
        return SentimentFeatures(
            tfidf_features=tfidf_features,
            financial_term_count=financial_term_count,
            positive_word_count=positive_count,
            negative_word_count=negative_count,
            exclamation_count=exclamation_count,
            question_count=question_count,
            capital_ratio=capital_ratio,
            sentence_count=sentence_count,
            avg_sentence_length=avg_sentence_length
        )
    
    def _calculate_lexicon_sentiment(self, processed_text: ProcessedText) -> Tuple[float, float]:
        """Вычисляет настроение на основе словаря."""
        lemmas = processed_text.lemmas
        tokens = processed_text.tokens
        
        sentiment_scores = []
        
        for i, lemma in enumerate(lemmas):
            base_sentiment = self.lexicon.get_term_sentiment(lemma)
            
            if base_sentiment != 0:
                # Проверяем усилители в окрестности
                intensifier = 1.0
                negation = False
                
                # Проверяем предыдущие 2 слова
                for j in range(max(0, i-2), i):
                    if j < len(tokens):
                        word = tokens[j]
                        if self.lexicon.is_negation(word):
                            negation = True
                        intensifier *= self.lexicon.get_intensifier_weight(word)
                
                # Применяем модификаторы
                final_sentiment = base_sentiment * intensifier
                if negation:
                    final_sentiment *= -1
                
                sentiment_scores.append(final_sentiment)
        
        if sentiment_scores:
            avg_sentiment = np.mean(sentiment_scores)
            confidence = min(len(sentiment_scores) / 10.0, 1.0)  # Больше терминов = больше уверенности
        else:
            avg_sentiment = 0.0
            confidence = 0.0
        
        return avg_sentiment, confidence
    
    def _train_model(self, texts: List[str], labels: List[str]):
        """Обучает модель машинного обучения."""
        try:
            logger.info(f"Обучение модели на {len(texts)} примерах...")
            
            # Подготавливаем тексты
            processed_texts = []
            for text in texts:
                processed = self.nlp_pipeline.process_text(text)
                processed_texts.append(' '.join(processed.lemmas))
            
            # Создаем TF-IDF векторизатор
            self.vectorizer = TfidfVectorizer(
                max_features=5000,
                ngram_range=(1, 3),
                min_df=2,
                max_df=0.8,
                stop_words=None
            )
            
            # Векторизуем тексты
            X = self.vectorizer.fit_transform(processed_texts)
            
            # Разделяем на обучающую и тестовую выборки
            X_train, X_test, y_train, y_test = train_test_split(
                X, labels, test_size=0.2, random_state=42, stratify=labels
            )
            
            # Обучаем модель
            self.model = LogisticRegression(
                random_state=42,
                max_iter=1000,
                class_weight='balanced'
            )
            self.model.fit(X_train, y_train)
            
            # Оцениваем качество
            y_pred = self.model.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            
            logger.info(f"Точность модели: {accuracy:.3f}")
            logger.info("Отчет по классификации:")
            logger.info(classification_report(y_test, y_pred))
            
            # Сохраняем модель
            self._save_model()
            
        except Exception as e:
            logger.error(f"Ошибка при обучении модели: {e}")
            raise
    
    def analyze_sentiment(self, article: RussianNewsArticle) -> NewsSentiment:
        """Анализирует настроение новостной статьи."""
        try:
            # Обрабатываем текст
            full_text = f"{article.title} {article.content}"
            processed_text = self.nlp_pipeline.process_text(full_text)
            
            # Извлекаем признаки
            features = self._extract_features(processed_text)
            
            # Анализ на основе словаря
            lexicon_sentiment, lexicon_confidence = self._calculate_lexicon_sentiment(processed_text)
            
            # Анализ с помощью ML модели (если доступна)
            ml_sentiment = 0.0
            ml_confidence = 0.0
            
            if self.model is not None and self.vectorizer is not None:
                try:
                    # Подготавливаем текст для модели
                    processed_for_ml = ' '.join(processed_text.lemmas)
                    X = self.vectorizer.transform([processed_for_ml])
                    
                    # Получаем предсказание
                    prediction = self.model.predict(X)[0]
                    probabilities = self.model.predict_proba(X)[0]
                    
                    # Конвертируем в числовое значение
                    if prediction == "POSITIVE":
                        ml_sentiment = 0.7
                    elif prediction == "NEGATIVE":
                        ml_sentiment = -0.7
                    else:
                        ml_sentiment = 0.0
                    
                    ml_confidence = max(probabilities)
                    
                except Exception as e:
                    logger.warning(f"Ошибка ML анализа: {e}")
            
            # Комбинируем результаты
            if lexicon_confidence > 0 and ml_confidence > 0:
                # Взвешенное среднее
                total_confidence = lexicon_confidence + ml_confidence
                final_sentiment = (lexicon_sentiment * lexicon_confidence + 
                                 ml_sentiment * ml_confidence) / total_confidence
                final_confidence = min((lexicon_confidence + ml_confidence) / 2, 1.0)
            elif lexicon_confidence > 0:
                final_sentiment = lexicon_sentiment
                final_confidence = lexicon_confidence
            elif ml_confidence > 0:
                final_sentiment = ml_sentiment
                final_confidence = ml_confidence
            else:
                final_sentiment = 0.0
                final_confidence = 0.1  # Минимальная уверенность
            
            # Определяем категорию настроения
            if final_sentiment >= 0.5:
                overall_sentiment = "VERY_POSITIVE"
            elif final_sentiment >= 0.1:
                overall_sentiment = "POSITIVE"
            elif final_sentiment <= -0.5:
                overall_sentiment = "VERY_NEGATIVE"
            elif final_sentiment <= -0.1:
                overall_sentiment = "NEGATIVE"
            else:
                overall_sentiment = "NEUTRAL"
            
            # Извлекаем ключевые слова по категориям
            positive_keywords = [lemma for lemma in processed_text.lemmas 
                               if self.lexicon.get_term_sentiment(lemma) > 0]
            negative_keywords = [lemma for lemma in processed_text.lemmas 
                               if self.lexicon.get_term_sentiment(lemma) < 0]
            neutral_keywords = [lemma for lemma in processed_text.lemmas 
                              if self.lexicon.get_term_sentiment(lemma) == 0 and 
                              lemma in self.lexicon.neutral_terms]
            
            return NewsSentiment(
                article_id=f"{article.source}_{hash(article.title)}_{int(article.timestamp.timestamp())}",
                overall_sentiment=overall_sentiment,
                sentiment_score=final_sentiment,
                confidence=final_confidence,
                positive_keywords=positive_keywords[:10],  # Топ-10
                negative_keywords=negative_keywords[:10],  # Топ-10
                neutral_keywords=neutral_keywords[:10],   # Топ-10
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Ошибка при анализе настроения: {e}")
            # Возвращаем нейтральный результат в случае ошибки
            return NewsSentiment(
                article_id=f"error_{int(datetime.now().timestamp())}",
                overall_sentiment="NEUTRAL",
                sentiment_score=0.0,
                confidence=0.0,
                timestamp=datetime.now()
            )
    
    def batch_analyze_sentiment(self, articles: List[RussianNewsArticle]) -> List[NewsSentiment]:
        """Анализирует настроение для списка статей."""
        results = []
        
        for i, article in enumerate(articles):
            try:
                sentiment = self.analyze_sentiment(article)
                results.append(sentiment)
                
                if (i + 1) % 10 == 0:
                    logger.info(f"Обработано {i + 1}/{len(articles)} статей")
                    
            except Exception as e:
                logger.error(f"Ошибка при обработке статьи {i}: {e}")
                # Добавляем нейтральный результат
                results.append(NewsSentiment(
                    article_id=f"error_{i}_{int(datetime.now().timestamp())}",
                    overall_sentiment="NEUTRAL",
                    sentiment_score=0.0,
                    confidence=0.0,
                    timestamp=datetime.now()
                ))
        
        return results
    
    def train_on_labeled_data(self, labeled_articles: List[Tuple[RussianNewsArticle, str]]):
        """Обучает модель на размеченных данных."""
        if not labeled_articles:
            logger.warning("Нет данных для обучения")
            return
        
        texts = []
        labels = []
        
        for article, label in labeled_articles:
            full_text = f"{article.title} {article.content}"
            texts.append(full_text)
            labels.append(label)
        
        self._train_model(texts, labels)
        logger.info(f"Модель обучена на {len(labeled_articles)} примерах")
    
    def get_sentiment_statistics(self, sentiments: List[NewsSentiment]) -> Dict[str, float]:
        """Возвращает статистику по настроениям."""
        if not sentiments:
            return {}
        
        # Подсчитываем распределение
        sentiment_counts = {}
        total_score = 0.0
        total_confidence = 0.0
        
        for sentiment in sentiments:
            sentiment_counts[sentiment.overall_sentiment] = sentiment_counts.get(
                sentiment.overall_sentiment, 0
            ) + 1
            total_score += sentiment.sentiment_score
            total_confidence += sentiment.confidence
        
        total_count = len(sentiments)
        
        # Вычисляем статистики
        stats = {
            'total_articles': total_count,
            'average_sentiment_score': total_score / total_count,
            'average_confidence': total_confidence / total_count,
            'positive_ratio': (sentiment_counts.get('POSITIVE', 0) + 
                             sentiment_counts.get('VERY_POSITIVE', 0)) / total_count,
            'negative_ratio': (sentiment_counts.get('NEGATIVE', 0) + 
                             sentiment_counts.get('VERY_NEGATIVE', 0)) / total_count,
            'neutral_ratio': sentiment_counts.get('NEUTRAL', 0) / total_count
        }
        
        # Добавляем детальное распределение
        for sentiment_type, count in sentiment_counts.items():
            stats[f'{sentiment_type.lower()}_count'] = count
            stats[f'{sentiment_type.lower()}_ratio'] = count / total_count
        
        return stats