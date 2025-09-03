"""
Russian Market-Specific Trading Strategies

This module implements trading strategies adapted for the Russian stock market,
including momentum strategies, mean reversion strategies, and sector-specific
strategies for Russian oil/gas and banking sectors.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import numpy as np
from abc import ABC, abstractmethod

from ..models.trading import TradingSignal, OrderAction
from ..models.market_data import RussianStock, MarketData
from ..models.news_data import NewsSentiment
from .technical_analyzer import TechnicalIndicators
from .ai_decision_engine import MarketConditions, AnalysisFactor, AnalysisType

logger = logging.getLogger(__name__)


class StrategyType(Enum):
    """Types of trading strategies"""
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    SECTOR_SPECIFIC = "sector_specific"
    VOLATILITY_BREAKOUT = "volatility_breakout"
    NEWS_DRIVEN = "news_driven"


@dataclass
class StrategyParameters:
    """Parameters for trading strategies"""
    lookback_period: int = 20
    volatility_threshold: float = 0.02
    momentum_threshold: float = 0.05
    mean_reversion_threshold: float = 0.15
    volume_multiplier: float = 1.5
    confidence_threshold: float = 0.6
    max_position_size: float = 0.1  # 10% of portfolio
    stop_loss_pct: float = 0.05     # 5% stop loss
    take_profit_pct: float = 0.15   # 15% take profit


class TradingStrategy(ABC):
    """Abstract base class for trading strategies"""
    
    def __init__(self, name: str, strategy_type: StrategyType, 
                 parameters: Optional[StrategyParameters] = None):
        self.name = name
        self.strategy_type = strategy_type
        self.parameters = parameters or StrategyParameters()
        
        # Russian market specific adjustments
        self.russian_market_multiplier = 1.2  # Higher volatility adjustment
        self.geopolitical_risk_factor = 0.8   # Reduce signals during high risk
        
    @abstractmethod
    def generate_signal(self, symbol: str, stock: RussianStock, 
                       market_data: MarketData, technical_indicators: TechnicalIndicators,
                       historical_data: List[MarketData], sentiments: List[NewsSentiment],
                       market_conditions: MarketConditions) -> TradingSignal:
        """Generate trading signal based on strategy logic"""
        pass
    
    def _calculate_volatility(self, prices: List[float], period: int = 20) -> float:
        """Calculate price volatility"""
        if len(prices) < period:
            return 0.0
        
        returns = np.diff(np.log(prices[-period:]))
        return np.std(returns) * np.sqrt(252)  # Annualized volatility
    
    def _calculate_momentum(self, prices: List[float], period: int = 20) -> float:
        """Calculate price momentum"""
        if len(prices) < period + 1:
            return 0.0
        
        return (prices[-1] - prices[-period-1]) / prices[-period-1]
    
    def _is_high_volume(self, current_volume: int, historical_volumes: List[int]) -> bool:
        """Check if current volume is significantly higher than average"""
        if len(historical_volumes) < 10:
            return False
        
        avg_volume = np.mean(historical_volumes[-20:])
        return current_volume > avg_volume * self.parameters.volume_multiplier
    
    def _adjust_for_russian_market(self, base_signal: TradingSignal, 
                                 market_conditions: MarketConditions) -> TradingSignal:
        """Apply Russian market specific adjustments"""
        # Adjust confidence based on geopolitical risk
        geopolitical_adjustment = 1.0 - (market_conditions.geopolitical_risk * 0.3)
        adjusted_confidence = base_signal.confidence * geopolitical_adjustment
        
        # Adjust for ruble volatility
        ruble_adjustment = 1.0 - (market_conditions.ruble_volatility * 0.2)
        adjusted_confidence *= ruble_adjustment
        
        # Create adjusted signal
        adjusted_signal = TradingSignal(
            symbol=base_signal.symbol,
            action=base_signal.action,
            confidence=max(0.0, min(1.0, adjusted_confidence)),
            target_price=base_signal.target_price,
            stop_loss=base_signal.stop_loss,
            reasoning=base_signal.reasoning + f" (Скорректировано для российского рынка)",
            timestamp=base_signal.timestamp,
            expected_return=base_signal.expected_return,
            risk_score=base_signal.risk_score
        )
        
        return adjusted_signal


class MomentumStrategy(TradingStrategy):
    """Momentum strategy adapted for Russian market volatility"""
    
    def __init__(self, parameters: Optional[StrategyParameters] = None):
        super().__init__("Russian Momentum", StrategyType.MOMENTUM, parameters)
        
        # Russian market specific momentum parameters
        self.momentum_periods = [10, 20, 50]  # Multiple timeframes
        self.volume_confirmation_required = True
        self.news_sentiment_weight = 0.3
    
    def generate_signal(self, symbol: str, stock: RussianStock, 
                       market_data: MarketData, technical_indicators: TechnicalIndicators,
                       historical_data: List[MarketData], sentiments: List[NewsSentiment],
                       market_conditions: MarketConditions) -> TradingSignal:
        """Generate momentum-based trading signal"""
        
        if len(historical_data) < max(self.momentum_periods) + 1:
            return self._create_neutral_signal(symbol, "Недостаточно исторических данных")
        
        prices = [float(data.price) for data in historical_data]
        volumes = [data.volume for data in historical_data]
        
        # Calculate momentum for different periods
        momentum_scores = []
        for period in self.momentum_periods:
            momentum = self._calculate_momentum(prices, period)
            momentum_scores.append(momentum)
        
        # Weighted average momentum (shorter periods have higher weight)
        weights = [0.5, 0.3, 0.2]
        weighted_momentum = sum(m * w for m, w in zip(momentum_scores, weights))
        
        # Volume confirmation
        volume_confirmed = self._is_high_volume(market_data.volume, volumes)
        
        # News sentiment factor
        sentiment_score = 0.0
        if sentiments:
            recent_sentiments = [s for s in sentiments if 
                               (datetime.now() - s.timestamp).days <= 3]
            if recent_sentiments:
                sentiment_score = np.mean([s.sentiment_score for s in recent_sentiments])
        
        # Generate signal
        base_confidence = 0.5
        
        if weighted_momentum > self.parameters.momentum_threshold:
            action = OrderAction.BUY
            confidence = min(0.9, base_confidence + abs(weighted_momentum) * 2)
            
            if volume_confirmed:
                confidence += 0.1
            if sentiment_score > 0.2:
                confidence += sentiment_score * self.news_sentiment_weight
                
            reasoning = f"Моментум стратегия: положительный моментум {weighted_momentum:.3f}"
            if volume_confirmed:
                reasoning += ", подтвержден объемом"
            if sentiment_score > 0.2:
                reasoning += f", поддержан позитивными новостями ({sentiment_score:.2f})"
                
        elif weighted_momentum < -self.parameters.momentum_threshold:
            action = OrderAction.SELL
            confidence = min(0.9, base_confidence + abs(weighted_momentum) * 2)
            
            if volume_confirmed:
                confidence += 0.1
            if sentiment_score < -0.2:
                confidence += abs(sentiment_score) * self.news_sentiment_weight
                
            reasoning = f"Моментум стратегия: отрицательный моментум {weighted_momentum:.3f}"
            if volume_confirmed:
                reasoning += ", подтвержден объемом"
            if sentiment_score < -0.2:
                reasoning += f", усилен негативными новостями ({sentiment_score:.2f})"
        else:
            return self._create_neutral_signal(symbol, f"Слабый моментум: {weighted_momentum:.3f}")
        
        # Calculate target and stop loss
        current_price = float(market_data.price)
        if action == OrderAction.BUY:
            target_price = current_price * (1 + self.parameters.take_profit_pct)
            stop_loss = current_price * (1 - self.parameters.stop_loss_pct)
        else:
            target_price = None
            stop_loss = None
        
        base_signal = TradingSignal(
            symbol=symbol,
            action=action,
            confidence=confidence,
            target_price=target_price,
            stop_loss=stop_loss,
            reasoning=reasoning,
            timestamp=datetime.now(),
            expected_return=abs(weighted_momentum) * 0.5,
            risk_score=1.0 - confidence
        )
        
        return self._adjust_for_russian_market(base_signal, market_conditions)
    
    def _create_neutral_signal(self, symbol: str, reason: str) -> TradingSignal:
        """Create neutral signal"""
        return TradingSignal(
            symbol=symbol,
            action=OrderAction.BUY,
            confidence=0.0,
            reasoning=f"Нейтральный сигнал: {reason}",
            timestamp=datetime.now(),
            expected_return=0.0,
            risk_score=1.0
        )


class MeanReversionStrategy(TradingStrategy):
    """Mean reversion strategy for Russian blue-chip stocks"""
    
    def __init__(self, parameters: Optional[StrategyParameters] = None):
        super().__init__("Russian Mean Reversion", StrategyType.MEAN_REVERSION, parameters)
        
        # Russian blue-chip stocks that tend to mean revert
        self.blue_chip_symbols = {
            'SBER', 'GAZP', 'LKOH', 'ROSN', 'NVTK', 'GMKN', 'MAGN', 'TATN'
        }
        
        # Mean reversion parameters
        self.bollinger_period = 20
        self.bollinger_std = 2.0
        self.rsi_oversold = 30
        self.rsi_overbought = 70
    
    def generate_signal(self, symbol: str, stock: RussianStock, 
                       market_data: MarketData, technical_indicators: TechnicalIndicators,
                       historical_data: List[MarketData], sentiments: List[NewsSentiment],
                       market_conditions: MarketConditions) -> TradingSignal:
        """Generate mean reversion signal"""
        
        # Check if this is a blue-chip stock suitable for mean reversion
        if symbol not in self.blue_chip_symbols:
            return self._create_neutral_signal(symbol, "Не подходит для стратегии возврата к среднему")
        
        if len(historical_data) < self.bollinger_period:
            return self._create_neutral_signal(symbol, "Недостаточно данных для расчета")
        
        prices = [float(data.price) for data in historical_data]
        current_price = float(market_data.price)
        
        # Calculate Bollinger Bands
        sma = np.mean(prices[-self.bollinger_period:])
        std = np.std(prices[-self.bollinger_period:])
        upper_band = sma + (std * self.bollinger_std)
        lower_band = sma - (std * self.bollinger_std)
        
        # Calculate distance from mean
        distance_from_mean = abs(current_price - sma) / sma
        
        # RSI confirmation
        rsi = technical_indicators.rsi if technical_indicators.rsi else 50
        
        # Generate signal based on mean reversion logic
        if current_price <= lower_band and rsi <= self.rsi_oversold:
            action = OrderAction.BUY
            confidence = min(0.9, 0.6 + distance_from_mean * 2)
            reasoning = f"Возврат к среднему: цена {current_price:.2f} ниже нижней полосы {lower_band:.2f}, RSI {rsi:.1f}"
            
            target_price = sma  # Target is the mean
            stop_loss = current_price * (1 - self.parameters.stop_loss_pct)
            
        elif current_price >= upper_band and rsi >= self.rsi_overbought:
            action = OrderAction.SELL
            confidence = min(0.9, 0.6 + distance_from_mean * 2)
            reasoning = f"Возврат к среднему: цена {current_price:.2f} выше верхней полосы {upper_band:.2f}, RSI {rsi:.1f}"
            
            target_price = None
            stop_loss = None
            
        else:
            return self._create_neutral_signal(symbol, f"Цена близко к среднему: {current_price:.2f} vs {sma:.2f}")
        
        # Check market conditions - mean reversion works better in stable markets
        if market_conditions.market_volatility > 0.6:
            confidence *= 0.7  # Reduce confidence in highly volatile markets
            reasoning += " (снижена уверенность из-за высокой волатильности)"
        
        base_signal = TradingSignal(
            symbol=symbol,
            action=action,
            confidence=confidence,
            target_price=target_price,
            stop_loss=stop_loss,
            reasoning=reasoning,
            timestamp=datetime.now(),
            expected_return=distance_from_mean * 0.3,
            risk_score=1.0 - confidence
        )
        
        return self._adjust_for_russian_market(base_signal, market_conditions)
    
    def _create_neutral_signal(self, symbol: str, reason: str) -> TradingSignal:
        """Create neutral signal"""
        return TradingSignal(
            symbol=symbol,
            action=OrderAction.BUY,
            confidence=0.0,
            reasoning=f"Нейтральный сигнал: {reason}",
            timestamp=datetime.now(),
            expected_return=0.0,
            risk_score=1.0
        )


class SectorSpecificStrategy(TradingStrategy):
    """Sector-specific strategies for Russian oil/gas and banking sectors"""
    
    def __init__(self, parameters: Optional[StrategyParameters] = None):
        super().__init__("Russian Sector Specific", StrategyType.SECTOR_SPECIFIC, parameters)
        
        # Sector definitions
        self.oil_gas_symbols = {'GAZP', 'LKOH', 'ROSN', 'NVTK', 'TATN', 'SNGS'}
        self.banking_symbols = {'SBER', 'VTBR', 'TCSB', 'RUAL'}
        
        # Sector-specific parameters
        self.oil_gas_params = {
            'oil_price_correlation': 0.8,
            'geopolitical_sensitivity': 1.5,
            'volatility_multiplier': 1.3
        }
        
        self.banking_params = {
            'interest_rate_sensitivity': 1.2,
            'economic_indicator_weight': 1.4,
            'regulatory_risk_factor': 1.1
        }
    
    def generate_signal(self, symbol: str, stock: RussianStock, 
                       market_data: MarketData, technical_indicators: TechnicalIndicators,
                       historical_data: List[MarketData], sentiments: List[NewsSentiment],
                       market_conditions: MarketConditions) -> TradingSignal:
        """Generate sector-specific trading signal"""
        
        if symbol in self.oil_gas_symbols:
            return self._generate_oil_gas_signal(
                symbol, stock, market_data, technical_indicators, 
                historical_data, sentiments, market_conditions
            )
        elif symbol in self.banking_symbols:
            return self._generate_banking_signal(
                symbol, stock, market_data, technical_indicators,
                historical_data, sentiments, market_conditions
            )
        else:
            return self._create_neutral_signal(symbol, "Сектор не поддерживается данной стратегией")
    
    def _generate_oil_gas_signal(self, symbol: str, stock: RussianStock,
                               market_data: MarketData, technical_indicators: TechnicalIndicators,
                               historical_data: List[MarketData], sentiments: List[NewsSentiment],
                               market_conditions: MarketConditions) -> TradingSignal:
        """Generate signal for oil/gas sector"""
        
        if len(historical_data) < 20:
            return self._create_neutral_signal(symbol, "Недостаточно данных")
        
        prices = [float(data.price) for data in historical_data]
        current_price = float(market_data.price)
        
        # Calculate sector-specific factors
        price_momentum = self._calculate_momentum(prices, 10)
        volatility = self._calculate_volatility(prices)
        
        # Geopolitical risk adjustment (oil/gas is highly sensitive)
        geopolitical_impact = market_conditions.geopolitical_risk * self.oil_gas_params['geopolitical_sensitivity']
        
        # News sentiment analysis (focus on oil/gas related news)
        sector_sentiment = 0.0
        if sentiments:
            oil_gas_keywords = ['нефть', 'газ', 'энергия', 'санкции', 'экспорт']
            relevant_sentiments = []
            
            for sentiment in sentiments:
                keywords = sentiment.positive_keywords + sentiment.negative_keywords + sentiment.neutral_keywords
                if any(keyword.lower() in oil_gas_keywords for keyword in keywords):
                    relevant_sentiments.append(sentiment)
            
            if relevant_sentiments:
                sector_sentiment = np.mean([s.sentiment_score for s in relevant_sentiments])
        
        # Generate signal
        base_confidence = 0.5
        
        # Positive momentum + low geopolitical risk + positive sentiment
        if (price_momentum > 0.03 and geopolitical_impact < 0.5 and sector_sentiment > 0.2):
            action = OrderAction.BUY
            confidence = min(0.9, base_confidence + price_momentum * 3 + sector_sentiment * 0.5)
            reasoning = f"Нефтегазовый сектор: моментум {price_momentum:.3f}, низкие геополитические риски, позитивные новости"
            
            target_price = current_price * (1 + self.parameters.take_profit_pct * 1.2)  # Higher target for oil/gas
            stop_loss = current_price * (1 - self.parameters.stop_loss_pct * 1.1)      # Wider stop loss
            
        # Negative conditions
        elif (price_momentum < -0.03 or geopolitical_impact > 0.7 or sector_sentiment < -0.3):
            action = OrderAction.SELL
            confidence = min(0.9, base_confidence + abs(price_momentum) * 2 + abs(sector_sentiment) * 0.5)
            reasoning = f"Нефтегазовый сектор: негативные условия - моментум {price_momentum:.3f}, геориски {geopolitical_impact:.2f}"
            
            target_price = None
            stop_loss = None
            
        else:
            return self._create_neutral_signal(symbol, "Нейтральные условия для нефтегазового сектора")
        
        # Adjust for high volatility in oil/gas sector
        if volatility > 0.4:
            confidence *= 0.8
            reasoning += f" (высокая волатильность {volatility:.2f})"
        
        base_signal = TradingSignal(
            symbol=symbol,
            action=action,
            confidence=confidence,
            target_price=target_price,
            stop_loss=stop_loss,
            reasoning=reasoning,
            timestamp=datetime.now(),
            expected_return=abs(price_momentum) * 0.6,
            risk_score=1.0 - confidence + geopolitical_impact * 0.3
        )
        
        return self._adjust_for_russian_market(base_signal, market_conditions)
    
    def _generate_banking_signal(self, symbol: str, stock: RussianStock,
                               market_data: MarketData, technical_indicators: TechnicalIndicators,
                               historical_data: List[MarketData], sentiments: List[NewsSentiment],
                               market_conditions: MarketConditions) -> TradingSignal:
        """Generate signal for banking sector"""
        
        if len(historical_data) < 20:
            return self._create_neutral_signal(symbol, "Недостаточно данных")
        
        prices = [float(data.price) for data in historical_data]
        current_price = float(market_data.price)
        
        # Banking sector specific analysis
        price_momentum = self._calculate_momentum(prices, 15)  # Slightly longer period for banks
        
        # Interest rate environment (proxy through market conditions)
        interest_rate_factor = 1.0 - market_conditions.market_volatility  # Stable markets = better for banks
        
        # Banking sector sentiment
        banking_sentiment = 0.0
        if sentiments:
            banking_keywords = ['банк', 'кредит', 'процент', 'ставка', 'регулирование']
            relevant_sentiments = []
            
            for sentiment in sentiments:
                keywords = sentiment.positive_keywords + sentiment.negative_keywords + sentiment.neutral_keywords
                if any(keyword.lower() in banking_keywords for keyword in keywords):
                    relevant_sentiments.append(sentiment)
            
            if relevant_sentiments:
                banking_sentiment = np.mean([s.sentiment_score for s in relevant_sentiments])
        
        # Technical indicators weight (banks are more technical-driven)
        technical_score = 0.0
        if technical_indicators.rsi:
            if technical_indicators.rsi < 40:
                technical_score += 0.3
            elif technical_indicators.rsi > 60:
                technical_score -= 0.3
        
        if technical_indicators.macd and technical_indicators.macd_signal:
            if technical_indicators.macd > technical_indicators.macd_signal:
                technical_score += 0.2
            else:
                technical_score -= 0.2
        
        # Generate signal
        combined_score = (price_momentum * 0.4 + banking_sentiment * 0.3 + 
                         technical_score * 0.3) * interest_rate_factor
        
        base_confidence = 0.5
        
        if combined_score > 0.15:
            action = OrderAction.BUY
            confidence = min(0.9, base_confidence + combined_score * 2)
            reasoning = f"Банковский сектор: комбинированная оценка {combined_score:.3f}, стабильная процентная среда"
            
            target_price = current_price * (1 + self.parameters.take_profit_pct)
            stop_loss = current_price * (1 - self.parameters.stop_loss_pct)
            
        elif combined_score < -0.15:
            action = OrderAction.SELL
            confidence = min(0.9, base_confidence + abs(combined_score) * 2)
            reasoning = f"Банковский сектор: негативная оценка {combined_score:.3f}"
            
            target_price = None
            stop_loss = None
            
        else:
            return self._create_neutral_signal(symbol, f"Нейтральная оценка банковского сектора: {combined_score:.3f}")
        
        base_signal = TradingSignal(
            symbol=symbol,
            action=action,
            confidence=confidence,
            target_price=target_price,
            stop_loss=stop_loss,
            reasoning=reasoning,
            timestamp=datetime.now(),
            expected_return=abs(combined_score) * 0.4,
            risk_score=1.0 - confidence
        )
        
        return self._adjust_for_russian_market(base_signal, market_conditions)
    
    def _create_neutral_signal(self, symbol: str, reason: str) -> TradingSignal:
        """Create neutral signal"""
        return TradingSignal(
            symbol=symbol,
            action=OrderAction.BUY,
            confidence=0.0,
            reasoning=f"Нейтральный сигнал: {reason}",
            timestamp=datetime.now(),
            expected_return=0.0,
            risk_score=1.0
        )


class StrategyManager:
    """Manager for multiple trading strategies"""
    
    def __init__(self):
        self.strategies: Dict[str, TradingStrategy] = {}
        self.strategy_weights: Dict[str, float] = {}
        
        # Initialize default strategies
        self._initialize_default_strategies()
    
    def _initialize_default_strategies(self):
        """Initialize default Russian market strategies"""
        # Create default strategies
        momentum_strategy = MomentumStrategy()
        mean_reversion_strategy = MeanReversionStrategy()
        sector_strategy = SectorSpecificStrategy()
        
        # Add strategies with weights
        self.add_strategy("momentum", momentum_strategy, 0.4)
        self.add_strategy("mean_reversion", mean_reversion_strategy, 0.3)
        self.add_strategy("sector_specific", sector_strategy, 0.3)
    
    def add_strategy(self, name: str, strategy: TradingStrategy, weight: float):
        """Add a trading strategy with weight"""
        self.strategies[name] = strategy
        self.strategy_weights[name] = weight
        
        # Normalize weights
        total_weight = sum(self.strategy_weights.values())
        if total_weight > 0:
            for strategy_name in self.strategy_weights:
                self.strategy_weights[strategy_name] /= total_weight
    
    def remove_strategy(self, name: str):
        """Remove a trading strategy"""
        if name in self.strategies:
            del self.strategies[name]
            del self.strategy_weights[name]
    
    def generate_combined_signal(self, symbol: str, stock: RussianStock,
                                market_data: MarketData, technical_indicators: TechnicalIndicators,
                                historical_data: List[MarketData], sentiments: List[NewsSentiment],
                                market_conditions: MarketConditions) -> TradingSignal:
        """Generate combined signal from all strategies"""
        
        if not self.strategies:
            return self._create_neutral_signal(symbol, "Нет доступных стратегий")
        
        strategy_signals = []
        
        # Get signals from all strategies
        for strategy_name, strategy in self.strategies.items():
            try:
                signal = strategy.generate_signal(
                    symbol, stock, market_data, technical_indicators,
                    historical_data, sentiments, market_conditions
                )
                
                if signal.confidence > 0.1:  # Only consider signals with some confidence
                    strategy_signals.append((strategy_name, signal, self.strategy_weights[strategy_name]))
                    
            except Exception as e:
                logger.warning(f"Strategy {strategy_name} failed for {symbol}: {e}")
        
        if not strategy_signals:
            return self._create_neutral_signal(symbol, "Все стратегии дали нейтральные сигналы")
        
        # Combine signals
        return self._combine_signals(symbol, strategy_signals)
    
    def _combine_signals(self, symbol: str, strategy_signals: List[Tuple[str, TradingSignal, float]]) -> TradingSignal:
        """Combine multiple strategy signals into one"""
        
        buy_weight = 0.0
        sell_weight = 0.0
        total_confidence = 0.0
        total_weight = 0.0
        reasoning_parts = []
        
        expected_returns = []
        risk_scores = []
        
        for strategy_name, signal, weight in strategy_signals:
            weighted_confidence = signal.confidence * weight
            
            if signal.action == OrderAction.BUY:
                buy_weight += weighted_confidence
            else:
                sell_weight += weighted_confidence
            
            total_confidence += weighted_confidence
            total_weight += weight
            
            expected_returns.append(signal.expected_return or 0.0)
            risk_scores.append(signal.risk_score or 0.5)
            
            reasoning_parts.append(f"{strategy_name}: {signal.reasoning[:100]}...")
        
        # Determine final action
        if buy_weight > sell_weight:
            final_action = OrderAction.BUY
            final_confidence = buy_weight
        else:
            final_action = OrderAction.SELL
            final_confidence = sell_weight
        
        # Normalize confidence
        if total_weight > 0:
            final_confidence = min(1.0, final_confidence / total_weight)
        
        # Calculate combined metrics
        avg_expected_return = np.mean(expected_returns) if expected_returns else 0.0
        avg_risk_score = np.mean(risk_scores) if risk_scores else 0.5
        
        # Generate combined reasoning
        combined_reasoning = f"Комбинированный сигнал ({len(strategy_signals)} стратегий): "
        combined_reasoning += f"{'ПОКУПКА' if final_action == OrderAction.BUY else 'ПРОДАЖА'} "
        combined_reasoning += f"(уверенность: {final_confidence:.2f})\n"
        combined_reasoning += "\n".join(reasoning_parts)
        
        return TradingSignal(
            symbol=symbol,
            action=final_action,
            confidence=final_confidence,
            target_price=None,  # Will be set by risk management
            stop_loss=None,     # Will be set by risk management
            reasoning=combined_reasoning,
            timestamp=datetime.now(),
            expected_return=avg_expected_return,
            risk_score=avg_risk_score
        )
    
    def _create_neutral_signal(self, symbol: str, reason: str) -> TradingSignal:
        """Create neutral signal"""
        return TradingSignal(
            symbol=symbol,
            action=OrderAction.BUY,
            confidence=0.0,
            reasoning=f"Нейтральный сигнал: {reason}",
            timestamp=datetime.now(),
            expected_return=0.0,
            risk_score=1.0
        )
    
    def get_strategy_performance(self) -> Dict[str, Dict[str, Any]]:
        """Get performance metrics for each strategy"""
        # This would be implemented with historical performance tracking
        # For now, return basic info
        performance = {}
        
        for name, strategy in self.strategies.items():
            performance[name] = {
                'name': strategy.name,
                'type': strategy.strategy_type.value,
                'weight': self.strategy_weights[name],
                'parameters': strategy.parameters.__dict__
            }
        
        return performance