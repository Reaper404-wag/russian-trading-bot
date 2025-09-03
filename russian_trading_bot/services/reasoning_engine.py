"""
Russian Trading Decision Reasoning Engine

This module provides natural language generation capabilities for explaining
trading decisions in Russian. It creates detailed, human-readable explanations
of why specific trading decisions were made based on various analysis factors.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import re

from ..models.trading import TradingSignal, OrderAction
from ..models.market_data import RussianStock, MarketData
from ..models.news_data import NewsSentiment
from .technical_analyzer import TechnicalIndicators
from .ai_decision_engine import AnalysisFactor, AnalysisType, MarketConditions

logger = logging.getLogger(__name__)


class ExplanationLevel(Enum):
    """Levels of explanation detail"""
    BRIEF = "brief"           # Short summary
    DETAILED = "detailed"     # Comprehensive explanation
    TECHNICAL = "technical"   # Technical details for experts


@dataclass
class ReasoningTemplate:
    """Template for generating reasoning explanations"""
    template_id: str
    category: str
    condition: str
    positive_template: str
    negative_template: str
    neutral_template: str
    confidence_modifiers: Dict[str, str]


class RussianReasoningEngine:
    """
    Russian language reasoning engine for trading decisions.
    Generates natural language explanations in Russian.
    """
    
    def __init__(self):
        self.templates = self._initialize_templates()
        self.technical_terms = self._initialize_technical_terms()
        self.confidence_phrases = self._initialize_confidence_phrases()
        self.market_condition_phrases = self._initialize_market_condition_phrases()
        
        logger.info("Russian Reasoning Engine initialized")
    
    def _initialize_templates(self) -> Dict[str, ReasoningTemplate]:
        """Initialize reasoning templates for different scenarios"""
        templates = {}
        
        # RSI Templates
        templates['rsi_oversold'] = ReasoningTemplate(
            template_id='rsi_oversold',
            category='technical',
            condition='rsi < 30',
            positive_template="RSI составляет {rsi:.1f}, что указывает на перепроданность акции. Это создает возможность для покупки.",
            negative_template="RSI {rsi:.1f} показывает перепроданность, но другие факторы не поддерживают покупку.",
            neutral_template="RSI {rsi:.1f} в зоне перепроданности, требуется подтверждение другими индикаторами.",
            confidence_modifiers={
                'high': 'сильный сигнал',
                'medium': 'умеренный сигнал',
                'low': 'слабый сигнал'
            }
        )
        
        templates['rsi_overbought'] = ReasoningTemplate(
            template_id='rsi_overbought',
            category='technical',
            condition='rsi > 70',
            positive_template="RSI достиг {rsi:.1f}, что свидетельствует о перекупленности. Рекомендуется фиксация прибыли.",
            negative_template="RSI {rsi:.1f} показывает перекупленность, но тренд может продолжиться.",
            neutral_template="RSI {rsi:.1f} в зоне перекупленности, следует проявить осторожность.",
            confidence_modifiers={
                'high': 'четкий сигнал к продаже',
                'medium': 'сигнал к осторожности',
                'low': 'требует наблюдения'
            }
        )
        
        # MACD Templates
        templates['macd_bullish'] = ReasoningTemplate(
            template_id='macd_bullish',
            category='technical',
            condition='macd > signal',
            positive_template="MACD ({macd:.3f}) пересек сигнальную линию ({signal:.3f}) снизу вверх, формируя бычий сигнал.",
            negative_template="MACD показывает бычий сигнал, но слабый импульс не подтверждает покупку.",
            neutral_template="MACD в бычьей зоне, но сигнал требует подтверждения объемом.",
            confidence_modifiers={
                'high': 'сильный импульс роста',
                'medium': 'умеренный потенциал роста',
                'low': 'слабый сигнал роста'
            }
        )
        
        # Sentiment Templates
        templates['positive_sentiment'] = ReasoningTemplate(
            template_id='positive_sentiment',
            category='sentiment',
            condition='sentiment > 0.3',
            positive_template="Анализ новостей показывает позитивный настрой ({sentiment:.2f}). Ключевые слова: {keywords}.",
            negative_template="Несмотря на позитивные новости, технические факторы не поддерживают рост.",
            neutral_template="Позитивные новости создают благоприятный фон, но требуется техническое подтверждение.",
            confidence_modifiers={
                'high': 'очень позитивный информационный фон',
                'medium': 'умеренно позитивные новости',
                'low': 'слабо позитивный настрой'
            }
        )
        
        # Volume Templates
        templates['high_volume'] = ReasoningTemplate(
            template_id='high_volume',
            category='volume',
            condition='volume > average * 1.5',
            positive_template="Объем торгов превышает средний в {ratio:.1f} раза, подтверждая интерес инвесторов.",
            negative_template="Высокий объем может указывать на распродажу.",
            neutral_template="Повышенный объем требует анализа направления движения цены.",
            confidence_modifiers={
                'high': 'значительный интерес участников рынка',
                'medium': 'повышенная активность',
                'low': 'умеренное увеличение объемов'
            }
        )
        
        # Market Conditions Templates
        templates['bullish_market'] = ReasoningTemplate(
            template_id='bullish_market',
            category='market',
            condition='trend == BULLISH',
            positive_template="Общий тренд рынка восходящий, что поддерживает рост отдельных акций.",
            negative_template="Несмотря на бычий рынок, данная акция показывает слабость.",
            neutral_template="Бычий рынок создает благоприятные условия для роста.",
            confidence_modifiers={
                'high': 'сильный бычий тренд',
                'medium': 'умеренный рост рынка',
                'low': 'слабый восходящий тренд'
            }
        )
        
        return templates
    
    def _initialize_technical_terms(self) -> Dict[str, str]:
        """Initialize Russian technical analysis terms"""
        return {
            'rsi': 'Индекс относительной силы (RSI)',
            'macd': 'Схождение-расхождение скользящих средних (MACD)',
            'sma': 'Простая скользящая средняя (SMA)',
            'ema': 'Экспоненциальная скользящая средняя (EMA)',
            'bollinger_bands': 'Полосы Боллинджера',
            'volume': 'Объем торгов',
            'support': 'Уровень поддержки',
            'resistance': 'Уровень сопротивления',
            'trend': 'Тренд',
            'momentum': 'Моментум',
            'volatility': 'Волатильность',
            'oversold': 'Перепроданность',
            'overbought': 'Перекупленность'
        }
    
    def _initialize_confidence_phrases(self) -> Dict[str, List[str]]:
        """Initialize confidence level phrases"""
        return {
            'very_high': [
                'с очень высокой уверенностью',
                'с максимальной степенью уверенности',
                'практически гарантированно'
            ],
            'high': [
                'с высокой уверенностью',
                'с большой степенью уверенности',
                'весьма вероятно'
            ],
            'medium': [
                'с умеренной уверенностью',
                'с определенной степенью уверенности',
                'вероятно'
            ],
            'low': [
                'с низкой уверенностью',
                'с осторожностью',
                'возможно'
            ],
            'very_low': [
                'с очень низкой уверенностью',
                'крайне неопределенно',
                'маловероятно'
            ]
        }
    
    def _initialize_market_condition_phrases(self) -> Dict[str, Dict[str, str]]:
        """Initialize market condition descriptions"""
        return {
            'volatility': {
                'low': 'низкая волатильность создает стабильные условия для торговли',
                'medium': 'умеренная волатильность требует осторожности',
                'high': 'высокая волатильность увеличивает риски'
            },
            'geopolitical_risk': {
                'low': 'низкие геополитические риски поддерживают рынок',
                'medium': 'умеренные геополитические риски создают неопределенность',
                'high': 'высокие геополитические риски оказывают давление на рынок'
            },
            'ruble_volatility': {
                'low': 'стабильный курс рубля благоприятен для российских акций',
                'medium': 'умеренные колебания рубля влияют на настроения',
                'high': 'сильные колебания рубля создают дополнительные риски'
            }
        }
    
    def get_confidence_level(self, confidence: float) -> str:
        """Convert numeric confidence to text level"""
        if confidence >= 0.9:
            return 'very_high'
        elif confidence >= 0.7:
            return 'high'
        elif confidence >= 0.5:
            return 'medium'
        elif confidence >= 0.3:
            return 'low'
        else:
            return 'very_low'
    
    def get_confidence_phrase(self, confidence: float) -> str:
        """Get Russian phrase for confidence level"""
        level = self.get_confidence_level(confidence)
        phrases = self.confidence_phrases.get(level, ['неопределенно'])
        return phrases[0]  # Return first phrase for consistency
    
    def generate_technical_explanation(self, indicators: TechnicalIndicators,
                                     factors: List[AnalysisFactor],
                                     level: ExplanationLevel = ExplanationLevel.DETAILED) -> str:
        """Generate technical analysis explanation in Russian"""
        
        explanations = []
        
        # RSI Explanation
        if indicators.rsi is not None:
            if indicators.rsi < 30:
                template = self.templates['rsi_oversold']
                explanation = template.positive_template.format(rsi=indicators.rsi)
            elif indicators.rsi > 70:
                template = self.templates['rsi_overbought']
                explanation = template.positive_template.format(rsi=indicators.rsi)
            else:
                explanation = f"RSI составляет {indicators.rsi:.1f}, что находится в нейтральной зоне (30-70)."
            
            explanations.append(explanation)
        
        # MACD Explanation
        if indicators.macd is not None and indicators.macd_signal is not None:
            if indicators.macd > indicators.macd_signal:
                template = self.templates['macd_bullish']
                explanation = template.positive_template.format(
                    macd=indicators.macd, signal=indicators.macd_signal
                )
            else:
                explanation = f"MACD ({indicators.macd:.3f}) находится ниже сигнальной линии ({indicators.macd_signal:.3f}), что указывает на медвежий сигнал."
            
            explanations.append(explanation)
        
        # Moving Averages
        if indicators.sma_20 is not None and indicators.sma_50 is not None:
            if indicators.sma_20 > indicators.sma_50:
                explanation = f"SMA20 ({indicators.sma_20:.2f}) выше SMA50 ({indicators.sma_50:.2f}), подтверждая восходящий тренд."
            else:
                explanation = f"SMA20 ({indicators.sma_20:.2f}) ниже SMA50 ({indicators.sma_50:.2f}), указывая на нисходящий тренд."
            
            explanations.append(explanation)
        
        # Bollinger Bands
        if all([indicators.bollinger_upper, indicators.bollinger_lower, indicators.bollinger_middle]):
            explanation = f"Полосы Боллинджера: верхняя {indicators.bollinger_upper:.2f}, средняя {indicators.bollinger_middle:.2f}, нижняя {indicators.bollinger_lower:.2f}."
            
            if indicators.bollinger_width:
                if indicators.bollinger_width > 8:
                    explanation += " Широкие полосы указывают на высокую волатильность."
                elif indicators.bollinger_width < 4:
                    explanation += " Узкие полосы предвещают возможный прорыв."
                else:
                    explanation += " Ширина полос в нормальном диапазоне."
            
            explanations.append(explanation)
        
        # Stochastic
        if indicators.stochastic_k is not None:
            if indicators.stochastic_k < 20:
                explanation = f"Стохастический осциллятор ({indicators.stochastic_k:.1f}) в зоне перепроданности."
            elif indicators.stochastic_k > 80:
                explanation = f"Стохастический осциллятор ({indicators.stochastic_k:.1f}) в зоне перекупленности."
            else:
                explanation = f"Стохастический осциллятор ({indicators.stochastic_k:.1f}) в нейтральной зоне."
            
            explanations.append(explanation)
        
        if level == ExplanationLevel.BRIEF:
            return explanations[0] if explanations else "Технические индикаторы в нейтральной зоне."
        
        return " ".join(explanations) if explanations else "Недостаточно данных для технического анализа."
    
    def generate_sentiment_explanation(self, sentiments: List[NewsSentiment],
                                     symbol: str,
                                     level: ExplanationLevel = ExplanationLevel.DETAILED) -> str:
        """Generate sentiment analysis explanation in Russian"""
        
        if not sentiments:
            return "Новостной фон нейтральный, значимых новостей не обнаружено."
        
        # Filter relevant sentiments
        relevant_sentiments = [s for s in sentiments if 
                             symbol.upper() in str(s.positive_keywords + s.negative_keywords).upper()
                             or len(s.positive_keywords + s.negative_keywords) == 0]
        
        if not relevant_sentiments:
            relevant_sentiments = sentiments[-5:]  # Last 5 if none specific
        
        # Calculate overall sentiment
        avg_sentiment = sum(s.sentiment_score for s in relevant_sentiments) / len(relevant_sentiments)
        avg_confidence = sum(s.confidence for s in relevant_sentiments) / len(relevant_sentiments)
        
        # Collect keywords
        all_positive = []
        all_negative = []
        for s in relevant_sentiments:
            all_positive.extend(s.positive_keywords)
            all_negative.extend(s.negative_keywords)
        
        # Remove duplicates and take top keywords
        unique_positive = list(set(all_positive))[:5]
        unique_negative = list(set(all_negative))[:5]
        
        # Generate explanation
        explanation_parts = []
        
        if avg_sentiment > 0.3:
            explanation_parts.append(f"Анализ {len(relevant_sentiments)} новостных сообщений показывает позитивный настрой (оценка: {avg_sentiment:.2f}).")
            if unique_positive:
                explanation_parts.append(f"Ключевые позитивные темы: {', '.join(unique_positive)}.")
        elif avg_sentiment < -0.3:
            explanation_parts.append(f"Анализ {len(relevant_sentiments)} новостных сообщений выявил негативный настрой (оценка: {avg_sentiment:.2f}).")
            if unique_negative:
                explanation_parts.append(f"Основные негативные факторы: {', '.join(unique_negative)}.")
        else:
            explanation_parts.append(f"Новостной фон нейтральный (оценка: {avg_sentiment:.2f}) на основе {len(relevant_sentiments)} сообщений.")
        
        # Add confidence assessment
        confidence_phrase = self.get_confidence_phrase(avg_confidence)
        explanation_parts.append(f"Достоверность анализа новостей оценивается {confidence_phrase}.")
        
        if level == ExplanationLevel.BRIEF:
            return explanation_parts[0]
        
        return " ".join(explanation_parts)
    
    def generate_market_conditions_explanation(self, conditions: MarketConditions,
                                             level: ExplanationLevel = ExplanationLevel.DETAILED) -> str:
        """Generate market conditions explanation in Russian"""
        
        explanations = []
        
        # Market trend
        trend_phrases = {
            'BULLISH': 'восходящий тренд поддерживает рост акций',
            'BEARISH': 'нисходящий тренд создает давление на акции',
            'SIDEWAYS': 'боковой тренд указывает на неопределенность рынка'
        }
        
        trend_explanation = trend_phrases.get(conditions.market_trend, 'тренд рынка неопределен')
        explanations.append(f"Общий {trend_explanation}.")
        
        # Volatility
        if conditions.market_volatility < 0.3:
            vol_desc = self.market_condition_phrases['volatility']['low']
        elif conditions.market_volatility < 0.6:
            vol_desc = self.market_condition_phrases['volatility']['medium']
        else:
            vol_desc = self.market_condition_phrases['volatility']['high']
        
        explanations.append(f"Рыночная волатильность ({conditions.market_volatility:.2f}): {vol_desc}.")
        
        # Geopolitical risk
        if conditions.geopolitical_risk < 0.3:
            geo_desc = self.market_condition_phrases['geopolitical_risk']['low']
        elif conditions.geopolitical_risk < 0.6:
            geo_desc = self.market_condition_phrases['geopolitical_risk']['medium']
        else:
            geo_desc = self.market_condition_phrases['geopolitical_risk']['high']
        
        explanations.append(f"Геополитические риски ({conditions.geopolitical_risk:.2f}): {geo_desc}.")
        
        # Ruble volatility
        if conditions.ruble_volatility < 0.3:
            rub_desc = self.market_condition_phrases['ruble_volatility']['low']
        elif conditions.ruble_volatility < 0.6:
            rub_desc = self.market_condition_phrases['ruble_volatility']['medium']
        else:
            rub_desc = self.market_condition_phrases['ruble_volatility']['high']
        
        explanations.append(f"Волатильность рубля ({conditions.ruble_volatility:.2f}): {rub_desc}.")
        
        # Trading volume
        if conditions.trading_volume_ratio > 1.3:
            explanations.append(f"Объем торгов превышает средний в {conditions.trading_volume_ratio:.1f} раза, указывая на повышенный интерес.")
        elif conditions.trading_volume_ratio < 0.7:
            explanations.append(f"Объем торгов ниже среднего ({conditions.trading_volume_ratio:.1f}x), что может указывать на низкую активность.")
        
        if level == ExplanationLevel.BRIEF:
            return explanations[0]
        
        return " ".join(explanations)
    
    def generate_comprehensive_explanation(self, signal: TradingSignal,
                                         stock: RussianStock,
                                         technical_indicators: TechnicalIndicators,
                                         sentiments: List[NewsSentiment],
                                         market_conditions: MarketConditions,
                                         factors: List[AnalysisFactor],
                                         level: ExplanationLevel = ExplanationLevel.DETAILED) -> str:
        """Generate comprehensive trading decision explanation in Russian"""
        
        explanation_parts = []
        
        # Header with decision summary
        action_text = "ПОКУПКА" if signal.action == OrderAction.BUY else "ПРОДАЖА"
        confidence_phrase = self.get_confidence_phrase(signal.confidence)
        
        header = f"ТОРГОВОЕ РЕШЕНИЕ: {action_text} акций {stock.name} ({signal.symbol})"
        explanation_parts.append(header)
        explanation_parts.append("=" * len(header))
        
        # Decision summary
        summary = f"Рекомендация: {action_text} {confidence_phrase} (уверенность: {signal.confidence:.1%})"
        if signal.expected_return:
            summary += f", ожидаемая доходность: {signal.expected_return:.1%}"
        if signal.risk_score:
            summary += f", оценка риска: {signal.risk_score:.1%}"
        
        explanation_parts.append(summary)
        explanation_parts.append("")
        
        # Price targets
        if signal.target_price or signal.stop_loss:
            price_info = f"Текущая цена: {stock.symbol} - информация недоступна"
            if signal.target_price:
                price_info += f", целевая цена: {signal.target_price:.2f} руб."
            if signal.stop_loss:
                price_info += f", стоп-лосс: {signal.stop_loss:.2f} руб."
            explanation_parts.append(price_info)
            explanation_parts.append("")
        
        # Technical analysis
        if level != ExplanationLevel.BRIEF:
            explanation_parts.append("ТЕХНИЧЕСКИЙ АНАЛИЗ:")
            tech_explanation = self.generate_technical_explanation(technical_indicators, factors, level)
            explanation_parts.append(tech_explanation)
            explanation_parts.append("")
        
        # Sentiment analysis
        if sentiments and level != ExplanationLevel.BRIEF:
            explanation_parts.append("АНАЛИЗ НОВОСТЕЙ:")
            sentiment_explanation = self.generate_sentiment_explanation(sentiments, signal.symbol, level)
            explanation_parts.append(sentiment_explanation)
            explanation_parts.append("")
        
        # Market conditions
        if level == ExplanationLevel.DETAILED:
            explanation_parts.append("РЫНОЧНЫЕ УСЛОВИЯ:")
            market_explanation = self.generate_market_conditions_explanation(market_conditions, level)
            explanation_parts.append(market_explanation)
            explanation_parts.append("")
        
        # Factor analysis
        if factors and level == ExplanationLevel.DETAILED:
            explanation_parts.append("ДЕТАЛЬНЫЙ АНАЛИЗ ФАКТОРОВ:")
            
            # Group factors by type
            factor_groups = {}
            for factor in factors:
                if factor.factor_type not in factor_groups:
                    factor_groups[factor.factor_type] = []
                factor_groups[factor.factor_type].append(factor)
            
            type_names = {
                AnalysisType.TECHNICAL: "Технические индикаторы",
                AnalysisType.SENTIMENT: "Анализ настроений",
                AnalysisType.VOLUME: "Анализ объемов",
                AnalysisType.MARKET_CONDITIONS: "Рыночные условия",
                AnalysisType.FUNDAMENTAL: "Фундаментальный анализ"
            }
            
            for factor_type, type_factors in factor_groups.items():
                type_name = type_names.get(factor_type, str(factor_type))
                explanation_parts.append(f"{type_name}:")
                
                for factor in type_factors:
                    score_text = "положительный" if factor.score > 0 else "отрицательный" if factor.score < 0 else "нейтральный"
                    factor_line = f"  • {factor.name}: {score_text} сигнал (оценка: {factor.score:.2f}, уверенность: {factor.confidence:.1%})"
                    if factor.reasoning:
                        factor_line += f" - {factor.reasoning}"
                    explanation_parts.append(factor_line)
                
                explanation_parts.append("")
        
        # Risk assessment
        if level != ExplanationLevel.BRIEF:
            explanation_parts.append("ОЦЕНКА РИСКОВ:")
            risk_explanation = self._generate_risk_explanation(signal, stock, market_conditions)
            explanation_parts.append(risk_explanation)
            explanation_parts.append("")
        
        # Sector-specific considerations
        if stock.sector in ['OIL_GAS', 'BANKING'] and level == ExplanationLevel.DETAILED:
            explanation_parts.append("СЕКТОРАЛЬНЫЕ ОСОБЕННОСТИ:")
            sector_explanation = self._generate_sector_explanation(stock, market_conditions)
            explanation_parts.append(sector_explanation)
            explanation_parts.append("")
        
        # Conclusion
        conclusion = self._generate_conclusion(signal, stock, level)
        explanation_parts.append("ЗАКЛЮЧЕНИЕ:")
        explanation_parts.append(conclusion)
        
        return "\n".join(explanation_parts)
    
    def _generate_risk_explanation(self, signal: TradingSignal, stock: RussianStock,
                                 market_conditions: MarketConditions) -> str:
        """Generate risk assessment explanation"""
        risk_factors = []
        
        # Market volatility risk
        if market_conditions.market_volatility > 0.5:
            risk_factors.append(f"высокая рыночная волатильность ({market_conditions.market_volatility:.1%})")
        
        # Geopolitical risk
        if market_conditions.geopolitical_risk > 0.4:
            risk_factors.append(f"повышенные геополитические риски ({market_conditions.geopolitical_risk:.1%})")
        
        # Ruble volatility
        if market_conditions.ruble_volatility > 0.4:
            risk_factors.append(f"нестабильность рубля ({market_conditions.ruble_volatility:.1%})")
        
        # Confidence-based risk
        if signal.confidence < 0.6:
            risk_factors.append(f"низкая уверенность в сигнале ({signal.confidence:.1%})")
        
        if risk_factors:
            risk_text = f"Основные риски: {', '.join(risk_factors)}. "
        else:
            risk_text = "Уровень рисков умеренный. "
        
        # Risk mitigation advice
        if signal.action == OrderAction.BUY:
            risk_text += "Рекомендуется использовать стоп-лосс и не превышать 5-10% от портфеля."
        else:
            risk_text += "При продаже следует учитывать налоговые последствия."
        
        return risk_text
    
    def _generate_sector_explanation(self, stock: RussianStock, 
                                   market_conditions: MarketConditions) -> str:
        """Generate sector-specific explanation"""
        
        if stock.sector == 'OIL_GAS':
            explanation = "Нефтегазовый сектор характеризуется высокой волатильностью и зависимостью от цен на сырье. "
            
            if market_conditions.geopolitical_risk > 0.5:
                explanation += "Текущие геополитические риски особенно сильно влияют на нефтегазовые компании. "
            
            explanation += "Рекомендуется отслеживать динамику цен на нефть и газ, а также санкционные риски."
            
        elif stock.sector == 'BANKING':
            explanation = "Банковский сектор зависит от процентных ставок ЦБ РФ и общего состояния экономики. "
            
            if market_conditions.market_volatility < 0.3:
                explanation += "Текущая низкая волатильность благоприятна для банковских акций. "
            
            explanation += "Важно учитывать качество кредитного портфеля и регулятивные изменения."
            
        else:
            explanation = f"Сектор {stock.sector} имеет свои особенности, которые следует учитывать при принятии решений."
        
        return explanation
    
    def _generate_conclusion(self, signal: TradingSignal, stock: RussianStock,
                           level: ExplanationLevel) -> str:
        """Generate conclusion for the explanation"""
        
        action_text = "покупку" if signal.action == OrderAction.BUY else "продажу"
        confidence_phrase = self.get_confidence_phrase(signal.confidence)
        
        conclusion = f"На основе комплексного анализа рекомендуется {action_text} акций {stock.name} "
        conclusion += f"{confidence_phrase}. "
        
        if signal.confidence > 0.7:
            conclusion += "Сигнал подтверждается несколькими независимыми факторами."
        elif signal.confidence > 0.5:
            conclusion += "Сигнал имеет умеренную силу, требуется дополнительное наблюдение."
        else:
            conclusion += "Сигнал слабый, решение следует принимать с осторожностью."
        
        # Add timing advice
        if signal.action == OrderAction.BUY:
            conclusion += " Рекомендуется поэтапный вход в позицию."
        else:
            conclusion += " Рекомендуется постепенная фиксация позиции."
        
        return conclusion
    
    def format_for_telegram(self, explanation: str) -> str:
        """Format explanation for Telegram bot"""
        # Limit length for Telegram
        if len(explanation) > 4000:
            lines = explanation.split('\n')
            formatted_lines = []
            current_length = 0
            
            for line in lines:
                if current_length + len(line) > 3800:
                    formatted_lines.append("... (сокращено)")
                    break
                formatted_lines.append(line)
                current_length += len(line)
            
            explanation = '\n'.join(formatted_lines)
        
        # Add Telegram formatting
        explanation = re.sub(r'^([А-Я\s]+):$', r'*\1:*', explanation, flags=re.MULTILINE)
        explanation = re.sub(r'^([А-Я\s]+): ([А-Я]+)$', r'*\1: \2*', explanation, flags=re.MULTILINE)
        explanation = re.sub(r'^(=+)$', r'', explanation, flags=re.MULTILINE)
        
        return explanation
    
    def format_for_email(self, explanation: str) -> str:
        """Format explanation for email"""
        # Add HTML formatting
        explanation = explanation.replace('\n\n', '</p><p>')
        explanation = explanation.replace('\n', '<br>')
        explanation = f'<p>{explanation}</p>'
        
        # Bold headers
        explanation = re.sub(r'<p>([А-Я\s]+):</p>', r'<h3>\1:</h3>', explanation)
        explanation = re.sub(r'<p>([А-Я\s]+):<br>', r'<h3>\1:</h3><p>', explanation)
        
        return explanation