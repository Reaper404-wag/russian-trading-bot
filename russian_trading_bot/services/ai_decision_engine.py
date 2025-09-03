"""
AI Decision Engine for Russian Stock Market

This module implements a multi-factor decision making system that combines
technical analysis, sentiment analysis, and fundamental analysis to generate
trading signals for Russian stocks on MOEX.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import numpy as np

from ..models.trading import TradingSignal, OrderAction
from ..models.market_data import RussianStock, MarketData
from ..models.news_data import NewsSentiment
from .technical_analyzer import TechnicalIndicators

logger = logging.getLogger(__name__)


class AnalysisType(Enum):
    """Types of analysis factors"""
    TECHNICAL = "technical"
    SENTIMENT = "sentiment"
    FUNDAMENTAL = "fundamental"
    VOLUME = "volume"
    MARKET_CONDITIONS = "market_conditions"


@dataclass
class AnalysisFactor:
    """Individual analysis factor with weight and score"""
    factor_type: AnalysisType
    name: str
    score: float  # -1.0 to 1.0
    confidence: float  # 0.0 to 1.0
    weight: float  # Weight in final decision
    reasoning: str = ""  # Russian explanation


@dataclass
class DecisionWeights:
    """Configurable weights for different analysis factors"""
    technical_weight: float = 0.4
    sentiment_weight: float = 0.3
    fundamental_weight: float = 0.2
    volume_weight: float = 0.1
    market_conditions_weight: float = 0.1
    
    def __post_init__(self):
        """Normalize weights to sum to 1.0"""
        total = (self.technical_weight + self.sentiment_weight + 
                self.fundamental_weight + self.volume_weight + 
                self.market_conditions_weight)
        if total > 0:
            self.technical_weight /= total
            self.sentiment_weight /= total
            self.fundamental_weight /= total
            self.volume_weight /= total
            self.market_conditions_weight /= total


@dataclass
class MarketConditions:
    """Current market conditions affecting decisions"""
    market_volatility: float  # 0.0 to 1.0
    ruble_volatility: float   # 0.0 to 1.0
    geopolitical_risk: float  # 0.0 to 1.0
    market_trend: str         # "BULLISH", "BEARISH", "SIDEWAYS"
    trading_volume_ratio: float  # Current volume vs average
    
    def get_risk_adjustment(self) -> float:
        """Calculate risk adjustment factor based on conditions"""
        risk_factors = [
            self.market_volatility,
            self.ruble_volatility,
            self.geopolitical_risk
        ]
        avg_risk = np.mean(risk_factors)
        
        # Higher risk = lower position sizes
        return max(0.1, 1.0 - avg_risk * 0.5)


class AIDecisionEngine:
    """
    Multi-factor AI decision engine for Russian stock market.
    Combines technical, sentiment, and fundamental analysis.
    """
    
    def __init__(self, weights: Optional[DecisionWeights] = None):
        self.weights = weights or DecisionWeights()
        
        # Russian market specific parameters
        self.min_confidence_threshold = 0.6  # Minimum confidence for signals
        self.strong_signal_threshold = 0.8   # Threshold for strong signals
        self.russian_market_volatility_factor = 1.2  # Adjustment for Russian market
        
        # Sector-specific adjustments for Russian market
        self.sector_adjustments = {
            'OIL_GAS': {'volatility_factor': 1.5, 'geopolitical_sensitivity': 1.8},
            'BANKING': {'volatility_factor': 1.3, 'geopolitical_sensitivity': 1.6},
            'METALS_MINING': {'volatility_factor': 1.4, 'geopolitical_sensitivity': 1.4},
            'TELECOM': {'volatility_factor': 0.8, 'geopolitical_sensitivity': 1.2},
            'CONSUMER_STAPLES': {'volatility_factor': 0.9, 'geopolitical_sensitivity': 1.1}
        }
        
        logger.info("AI Decision Engine initialized for Russian market")
    
    def analyze_technical_factors(self, indicators: TechnicalIndicators) -> List[AnalysisFactor]:
        """Analyze technical indicators and return factors"""
        factors = []
        
        # RSI Analysis
        if indicators.rsi is not None:
            if indicators.rsi < 30:
                score = min((30 - indicators.rsi) / 30, 1.0)
                reasoning = f"RSI {indicators.rsi:.1f} указывает на перепроданность"
            elif indicators.rsi > 70:
                score = -min((indicators.rsi - 70) / 30, 1.0)
                reasoning = f"RSI {indicators.rsi:.1f} указывает на перекупленность"
            else:
                score = 0.0
                reasoning = f"RSI {indicators.rsi:.1f} в нейтральной зоне"
            
            factors.append(AnalysisFactor(
                factor_type=AnalysisType.TECHNICAL,
                name="RSI",
                score=score,
                confidence=0.8,
                weight=0.3,
                reasoning=reasoning
            ))
        
        # MACD Analysis
        if indicators.macd is not None and indicators.macd_signal is not None:
            macd_diff = indicators.macd - indicators.macd_signal
            score = np.tanh(macd_diff * 10)  # Normalize to -1, 1
            
            if macd_diff > 0:
                reasoning = f"MACD выше сигнальной линии (бычий сигнал)"
            else:
                reasoning = f"MACD ниже сигнальной линии (медвежий сигнал)"
            
            factors.append(AnalysisFactor(
                factor_type=AnalysisType.TECHNICAL,
                name="MACD",
                score=score,
                confidence=0.7,
                weight=0.25,
                reasoning=reasoning
            ))
        
        # Moving Average Analysis
        if indicators.sma_20 is not None and indicators.sma_50 is not None:
            ma_ratio = (indicators.sma_20 - indicators.sma_50) / indicators.sma_50
            score = np.tanh(ma_ratio * 20)  # Normalize
            
            if ma_ratio > 0:
                reasoning = f"SMA20 выше SMA50 (восходящий тренд)"
            else:
                reasoning = f"SMA20 ниже SMA50 (нисходящий тренд)"
            
            factors.append(AnalysisFactor(
                factor_type=AnalysisType.TECHNICAL,
                name="Moving_Averages",
                score=score,
                confidence=0.6,
                weight=0.2,
                reasoning=reasoning
            ))
        
        # Bollinger Bands Analysis
        if all([indicators.bollinger_upper, indicators.bollinger_lower, 
                indicators.bollinger_middle]):
            # Assume current price is middle band for now
            current_price = indicators.bollinger_middle
            band_width = indicators.bollinger_upper - indicators.bollinger_lower
            
            if current_price <= indicators.bollinger_lower:
                score = 0.7  # Oversold
                reasoning = "Цена у нижней полосы Боллинджера (возможна покупка)"
            elif current_price >= indicators.bollinger_upper:
                score = -0.7  # Overbought
                reasoning = "Цена у верхней полосы Боллинджера (возможна продажа)"
            else:
                score = 0.0
                reasoning = "Цена в пределах полос Боллинджера"
            
            factors.append(AnalysisFactor(
                factor_type=AnalysisType.TECHNICAL,
                name="Bollinger_Bands",
                score=score,
                confidence=0.6,
                weight=0.15,
                reasoning=reasoning
            ))
        
        # Stochastic Analysis
        if indicators.stochastic_k is not None:
            if indicators.stochastic_k < 20:
                score = (20 - indicators.stochastic_k) / 20
                reasoning = f"Стохастик {indicators.stochastic_k:.1f} в зоне перепроданности"
            elif indicators.stochastic_k > 80:
                score = -(indicators.stochastic_k - 80) / 20
                reasoning = f"Стохастик {indicators.stochastic_k:.1f} в зоне перекупленности"
            else:
                score = 0.0
                reasoning = f"Стохастик {indicators.stochastic_k:.1f} в нейтральной зоне"
            
            factors.append(AnalysisFactor(
                factor_type=AnalysisType.TECHNICAL,
                name="Stochastic",
                score=score,
                confidence=0.5,
                weight=0.1,
                reasoning=reasoning
            ))
        
        return factors
    
    def analyze_sentiment_factors(self, sentiments: List[NewsSentiment], 
                                symbol: str) -> List[AnalysisFactor]:
        """Analyze news sentiment factors"""
        factors = []
        
        if not sentiments:
            return factors
        
        # Filter sentiments for the specific symbol or general market news
        relevant_sentiments = [s for s in sentiments if 
                             symbol.upper() in str(s.positive_keywords + s.negative_keywords).upper()
                             or len(s.positive_keywords + s.negative_keywords) == 0]
        
        if not relevant_sentiments:
            relevant_sentiments = sentiments  # Use all if none specific
        
        # Calculate weighted sentiment score
        total_weight = 0
        weighted_score = 0
        
        for sentiment in relevant_sentiments[-10:]:  # Last 10 news items
            weight = sentiment.confidence
            score = sentiment.sentiment_score
            
            weighted_score += score * weight
            total_weight += weight
        
        if total_weight > 0:
            avg_sentiment = weighted_score / total_weight
            confidence = min(total_weight / 5.0, 1.0)  # More news = higher confidence
            
            if avg_sentiment > 0.3:
                reasoning = "Позитивные новости поддерживают рост акции"
            elif avg_sentiment < -0.3:
                reasoning = "Негативные новости создают давление на акцию"
            else:
                reasoning = "Нейтральный новостной фон"
            
            factors.append(AnalysisFactor(
                factor_type=AnalysisType.SENTIMENT,
                name="News_Sentiment",
                score=avg_sentiment,
                confidence=confidence,
                weight=1.0,
                reasoning=reasoning
            ))
        
        return factors
    
    def analyze_volume_factors(self, market_data: MarketData, 
                             historical_volume: List[int]) -> List[AnalysisFactor]:
        """Analyze volume-based factors"""
        factors = []
        
        if not historical_volume or len(historical_volume) < 20:
            return factors
        
        current_volume = market_data.volume
        avg_volume = np.mean(historical_volume[-20:])  # 20-day average
        
        if avg_volume > 0:
            volume_ratio = current_volume / avg_volume
            
            if volume_ratio > 2.0:
                score = min((volume_ratio - 1) / 3, 1.0)
                reasoning = f"Объем торгов в {volume_ratio:.1f} раз выше среднего (сильный интерес)"
            elif volume_ratio > 1.5:
                score = 0.5
                reasoning = f"Повышенный объем торгов ({volume_ratio:.1f}x от среднего)"
            elif volume_ratio < 0.5:
                score = -0.3
                reasoning = f"Низкий объем торгов ({volume_ratio:.1f}x от среднего)"
            else:
                score = 0.0
                reasoning = f"Обычный объем торгов ({volume_ratio:.1f}x от среднего)"
            
            factors.append(AnalysisFactor(
                factor_type=AnalysisType.VOLUME,
                name="Volume_Analysis",
                score=score,
                confidence=0.6,
                weight=1.0,
                reasoning=reasoning
            ))
        
        return factors
    
    def analyze_market_conditions(self, conditions: MarketConditions) -> List[AnalysisFactor]:
        """Analyze overall market conditions"""
        factors = []
        
        # Market trend factor
        trend_score = 0.0
        if conditions.market_trend == "BULLISH":
            trend_score = 0.5
            trend_reasoning = "Общий тренд рынка восходящий"
        elif conditions.market_trend == "BEARISH":
            trend_score = -0.5
            trend_reasoning = "Общий тренд рынка нисходящий"
        else:
            trend_reasoning = "Рынок в боковом тренде"
        
        factors.append(AnalysisFactor(
            factor_type=AnalysisType.MARKET_CONDITIONS,
            name="Market_Trend",
            score=trend_score,
            confidence=0.7,
            weight=0.4,
            reasoning=trend_reasoning
        ))
        
        # Volatility factor
        volatility_score = -conditions.market_volatility * 0.5  # High volatility = negative
        volatility_reasoning = f"Волатильность рынка: {conditions.market_volatility:.1f}"
        
        factors.append(AnalysisFactor(
            factor_type=AnalysisType.MARKET_CONDITIONS,
            name="Market_Volatility",
            score=volatility_score,
            confidence=0.6,
            weight=0.3,
            reasoning=volatility_reasoning
        ))
        
        # Geopolitical risk factor
        geopolitical_score = -conditions.geopolitical_risk * 0.7
        geopolitical_reasoning = f"Геополитические риски: {conditions.geopolitical_risk:.1f}"
        
        factors.append(AnalysisFactor(
            factor_type=AnalysisType.MARKET_CONDITIONS,
            name="Geopolitical_Risk",
            score=geopolitical_score,
            confidence=0.8,
            weight=0.3,
            reasoning=geopolitical_reasoning
        ))
        
        return factors
    
    def calculate_confidence_score(self, factors: List[AnalysisFactor]) -> float:
        """Calculate overall confidence based on factor confidences and agreement"""
        if not factors:
            return 0.0
        
        # Weighted average of individual confidences
        total_weight = sum(f.confidence * f.weight for f in factors)
        total_confidence_weight = sum(f.weight for f in factors)
        
        if total_confidence_weight == 0:
            return 0.0
        
        base_confidence = total_weight / total_confidence_weight
        
        # Agreement bonus: factors pointing in same direction increase confidence
        positive_factors = [f for f in factors if f.score > 0.1]
        negative_factors = [f for f in factors if f.score < -0.1]
        neutral_factors = [f for f in factors if abs(f.score) <= 0.1]
        
        total_factors = len(factors)
        if total_factors > 0:
            agreement_ratio = max(len(positive_factors), len(negative_factors)) / total_factors
            agreement_bonus = (agreement_ratio - 0.5) * 0.3  # Up to 15% bonus
            base_confidence += max(0, agreement_bonus)
        
        return min(base_confidence, 1.0)
    
    def generate_trading_signal(self, symbol: str, stock: RussianStock,
                              market_data: MarketData,
                              technical_indicators: TechnicalIndicators,
                              sentiments: List[NewsSentiment],
                              market_conditions: MarketConditions,
                              historical_volume: Optional[List[int]] = None) -> TradingSignal:
        """
        Generate comprehensive trading signal based on all factors.
        
        Args:
            symbol: Stock symbol
            stock: Russian stock information
            market_data: Current market data
            technical_indicators: Technical analysis results
            sentiments: Recent news sentiments
            market_conditions: Current market conditions
            historical_volume: Historical volume data
            
        Returns:
            TradingSignal with recommendation and reasoning
        """
        try:
            all_factors = []
            
            # Collect all analysis factors
            technical_factors = self.analyze_technical_factors(technical_indicators)
            sentiment_factors = self.analyze_sentiment_factors(sentiments, symbol)
            volume_factors = self.analyze_volume_factors(market_data, historical_volume or [])
            market_factors = self.analyze_market_conditions(market_conditions)
            
            all_factors.extend(technical_factors)
            all_factors.extend(sentiment_factors)
            all_factors.extend(volume_factors)
            all_factors.extend(market_factors)
            
            if not all_factors:
                logger.warning(f"No analysis factors available for {symbol}")
                return self._create_neutral_signal(symbol, "Недостаточно данных для анализа")
            
            # Calculate weighted score
            weighted_score = 0.0
            total_weight = 0.0
            
            for factor in all_factors:
                factor_weight = self._get_factor_weight(factor.factor_type) * factor.weight
                weighted_score += factor.score * factor.confidence * factor_weight
                total_weight += factor.confidence * factor_weight
            
            if total_weight == 0:
                return self._create_neutral_signal(symbol, "Нулевой общий вес факторов")
            
            final_score = weighted_score / total_weight
            
            # Apply sector-specific adjustments
            sector_adjustment = self.sector_adjustments.get(stock.sector, {})
            if sector_adjustment:
                volatility_factor = sector_adjustment.get('volatility_factor', 1.0)
                geopolitical_sensitivity = sector_adjustment.get('geopolitical_sensitivity', 1.0)
                
                # Adjust for sector volatility and geopolitical sensitivity
                risk_adjustment = (volatility_factor * market_conditions.market_volatility + 
                                 geopolitical_sensitivity * market_conditions.geopolitical_risk) / 2
                final_score *= (1.0 - risk_adjustment * 0.3)  # Reduce signal strength for risky conditions
            
            # Calculate confidence
            confidence = self.calculate_confidence_score(all_factors)
            
            # Apply Russian market volatility adjustment
            confidence *= (1.0 / self.russian_market_volatility_factor)
            final_score *= market_conditions.get_risk_adjustment()
            
            # Determine action and target prices
            action, target_price, stop_loss = self._determine_action_and_prices(
                final_score, confidence, market_data.price
            )
            
            # Generate reasoning in Russian
            reasoning = self._generate_reasoning(all_factors, final_score, confidence, action)
            
            return TradingSignal(
                symbol=symbol,
                action=action,
                confidence=confidence,
                target_price=target_price,
                stop_loss=stop_loss,
                reasoning=reasoning,
                timestamp=datetime.now(),
                expected_return=abs(final_score) * 0.1,  # Rough estimate
                risk_score=1.0 - confidence
            )
            
        except Exception as e:
            logger.error(f"Error generating trading signal for {symbol}: {e}")
            return self._create_neutral_signal(symbol, f"Ошибка анализа: {str(e)}")
    
    def _get_factor_weight(self, factor_type: AnalysisType) -> float:
        """Get weight for factor type from configuration"""
        weight_map = {
            AnalysisType.TECHNICAL: self.weights.technical_weight,
            AnalysisType.SENTIMENT: self.weights.sentiment_weight,
            AnalysisType.FUNDAMENTAL: self.weights.fundamental_weight,
            AnalysisType.VOLUME: self.weights.volume_weight,
            AnalysisType.MARKET_CONDITIONS: self.weights.market_conditions_weight
        }
        return weight_map.get(factor_type, 0.1)
    
    def _determine_action_and_prices(self, score: float, confidence: float, 
                                   current_price: float) -> Tuple[OrderAction, float, float]:
        """Determine trading action and price targets"""
        if confidence < self.min_confidence_threshold:
            return OrderAction.SELL if score < 0 else OrderAction.BUY, None, None
        
        if score > 0.3 and confidence > self.min_confidence_threshold:
            action = OrderAction.BUY
            # Conservative target: 5-15% based on score and confidence
            target_multiplier = 1 + (score * confidence * 0.15)
            target_price = current_price * target_multiplier
            # Stop loss: 3-8% below current price
            stop_loss_multiplier = 1 - (0.03 + score * confidence * 0.05)
            stop_loss = current_price * stop_loss_multiplier
        elif score < -0.3 and confidence > self.min_confidence_threshold:
            action = OrderAction.SELL
            # For sell signals, we don't set target/stop loss the same way
            target_price = None
            stop_loss = None
        else:
            action = OrderAction.BUY if score > 0 else OrderAction.SELL
            target_price = None
            stop_loss = None
        
        return action, target_price, stop_loss
    
    def _generate_reasoning(self, factors: List[AnalysisFactor], score: float, 
                          confidence: float, action: OrderAction) -> str:
        """Generate Russian language reasoning for the decision"""
        reasoning_parts = []
        
        # Overall assessment
        if action == OrderAction.BUY:
            reasoning_parts.append(f"Рекомендация: ПОКУПКА (оценка: {score:.2f}, уверенность: {confidence:.2f})")
        else:
            reasoning_parts.append(f"Рекомендация: ПРОДАЖА (оценка: {score:.2f}, уверенность: {confidence:.2f})")
        
        # Group factors by type
        factor_groups = {}
        for factor in factors:
            if factor.factor_type not in factor_groups:
                factor_groups[factor.factor_type] = []
            factor_groups[factor.factor_type].append(factor)
        
        # Add reasoning for each factor type
        type_names = {
            AnalysisType.TECHNICAL: "Технический анализ",
            AnalysisType.SENTIMENT: "Анализ новостей",
            AnalysisType.VOLUME: "Анализ объемов",
            AnalysisType.MARKET_CONDITIONS: "Рыночные условия",
            AnalysisType.FUNDAMENTAL: "Фундаментальный анализ"
        }
        
        for factor_type, type_factors in factor_groups.items():
            if type_factors:
                type_name = type_names.get(factor_type, str(factor_type))
                reasoning_parts.append(f"\n{type_name}:")
                
                for factor in type_factors:
                    if factor.reasoning:
                        reasoning_parts.append(f"  • {factor.reasoning}")
        
        return " ".join(reasoning_parts)
    
    def _create_neutral_signal(self, symbol: str, reason: str) -> TradingSignal:
        """Create a neutral trading signal"""
        return TradingSignal(
            symbol=symbol,
            action=OrderAction.BUY,  # Default action
            confidence=0.0,
            reasoning=f"Нейтральный сигнал: {reason}",
            timestamp=datetime.now(),
            expected_return=0.0,
            risk_score=1.0
        )
    
    def update_weights(self, new_weights: DecisionWeights):
        """Update decision weights"""
        self.weights = new_weights
        logger.info("Decision weights updated")
    
    def get_factor_analysis(self, symbol: str, **kwargs) -> Dict[str, List[AnalysisFactor]]:
        """Get detailed factor analysis for debugging/explanation"""
        factors = {}
        
        if 'technical_indicators' in kwargs:
            factors['technical'] = self.analyze_technical_factors(kwargs['technical_indicators'])
        
        if 'sentiments' in kwargs:
            factors['sentiment'] = self.analyze_sentiment_factors(kwargs['sentiments'], symbol)
        
        if 'market_data' in kwargs and 'historical_volume' in kwargs:
            factors['volume'] = self.analyze_volume_factors(
                kwargs['market_data'], kwargs['historical_volume']
            )
        
        if 'market_conditions' in kwargs:
            factors['market_conditions'] = self.analyze_market_conditions(kwargs['market_conditions'])
        
        return factors