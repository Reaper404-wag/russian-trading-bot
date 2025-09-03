"""
Enhanced market condition monitoring for Russian stock market
Extends the base market monitor with additional monitoring capabilities
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
import statistics
import pytz
import requests
import json
from dataclasses import dataclass

from ..models.market_data import MOEXMarketData
from ..models.trading import Portfolio
from ..models.notifications import (
    MarketAlert, GeopoliticalAlert, PortfolioAlert, NotificationPreferences
)
from .market_monitor import MarketMonitor, MarketCondition, VolatilityMetrics
from .notification_service import NotificationService


@dataclass
class MarketSentiment:
    """Market sentiment analysis results"""
    timestamp: datetime
    overall_sentiment: str  # BULLISH, BEARISH, NEUTRAL
    sentiment_score: float  # -1.0 to 1.0
    confidence: float  # 0.0 to 1.0
    key_factors: List[str]
    sector_sentiments: Dict[str, float]


@dataclass
class RiskAssessment:
    """Comprehensive risk assessment"""
    timestamp: datetime
    overall_risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    risk_score: float  # 0.0 to 1.0
    volatility_risk: float
    geopolitical_risk: float
    liquidity_risk: float
    currency_risk: float  # RUB volatility
    recommendations: List[str]


@dataclass
class MarketRegimeChange:
    """Market regime change detection"""
    timestamp: datetime
    previous_regime: str
    current_regime: str
    confidence: float
    key_indicators: List[str]
    expected_duration: Optional[str] = None


class EnhancedMarketMonitor(MarketMonitor):
    """
    Enhanced market monitor with advanced monitoring capabilities
    """
    
    def __init__(self, notification_service: NotificationService, config: Dict[str, Any]):
        """Initialize enhanced market monitor"""
        super().__init__(notification_service, config)
        
        # Enhanced monitoring configuration
        self.sentiment_threshold = config.get('sentiment_threshold', 0.3)
        self.risk_escalation_threshold = config.get('risk_escalation_threshold', 0.7)
        self.regime_change_threshold = config.get('regime_change_threshold', 0.8)
        
        # Additional data storage
        self.sentiment_history: List[MarketSentiment] = []
        self.risk_assessments: List[RiskAssessment] = []
        self.regime_history: List[MarketRegimeChange] = []
        
        # Market indicators
        self.market_indicators: Dict[str, List[Tuple[datetime, float]]] = {}
        self.sector_performance: Dict[str, List[Tuple[datetime, float]]] = {}
        
        # Russian market specific indicators
        self.rub_usd_history: List[Tuple[datetime, Decimal]] = []
        self.oil_price_history: List[Tuple[datetime, Decimal]] = []
        self.cbr_rate_history: List[Tuple[datetime, float]] = []
        
        # Enhanced geopolitical monitoring
        self.geopolitical_events: List[Dict[str, Any]] = []
        self.sanctions_timeline: List[Dict[str, Any]] = []
    
    async def monitor_market_sentiment(
        self,
        market_data: List[MOEXMarketData],
        news_data: List[Dict[str, Any]]
    ) -> MarketSentiment:
        """Monitor and analyze market sentiment"""
        try:
            # Analyze price movements for sentiment
            price_sentiment = self._analyze_price_sentiment(market_data)
            
            # Analyze news sentiment
            news_sentiment = await self._analyze_news_sentiment(news_data)
            
            # Analyze volume patterns
            volume_sentiment = self._analyze_volume_sentiment(market_data)
            
            # Combine sentiments
            overall_score = (price_sentiment * 0.4 + news_sentiment * 0.4 + volume_sentiment * 0.2)
            
            # Determine sentiment category
            if overall_score > 0.3:
                sentiment_category = "BULLISH"
            elif overall_score < -0.3:
                sentiment_category = "BEARISH"
            else:
                sentiment_category = "NEUTRAL"
            
            # Calculate confidence based on consistency
            confidence = min(1.0, abs(overall_score) + 0.3)
            
            # Identify key factors
            key_factors = self._identify_sentiment_factors(
                price_sentiment, news_sentiment, volume_sentiment
            )
            
            # Analyze sector sentiments
            sector_sentiments = self._analyze_sector_sentiments(market_data)
            
            sentiment = MarketSentiment(
                timestamp=datetime.now(self.moscow_tz),
                overall_sentiment=sentiment_category,
                sentiment_score=overall_score,
                confidence=confidence,
                key_factors=key_factors,
                sector_sentiments=sector_sentiments
            )
            
            # Store sentiment history
            self.sentiment_history.append(sentiment)
            if len(self.sentiment_history) > 100:
                self.sentiment_history = self.sentiment_history[-100:]
            
            return sentiment
            
        except Exception as e:
            self.logger.error(f"Error monitoring market sentiment: {e}")
            return MarketSentiment(
                timestamp=datetime.now(self.moscow_tz),
                overall_sentiment="NEUTRAL",
                sentiment_score=0.0,
                confidence=0.0,
                key_factors=[],
                sector_sentiments={}
            )
    
    async def assess_comprehensive_risk(
        self,
        market_data: List[MOEXMarketData],
        portfolio: Optional[Portfolio] = None
    ) -> RiskAssessment:
        """Perform comprehensive risk assessment"""
        try:
            # Calculate volatility risk
            volatility_risk = await self._calculate_volatility_risk(market_data)
            
            # Assess geopolitical risk
            geopolitical_risk = await self._assess_geopolitical_risk()
            
            # Calculate liquidity risk
            liquidity_risk = self._calculate_liquidity_risk(market_data)
            
            # Assess currency risk (RUB volatility)
            currency_risk = await self._assess_currency_risk()
            
            # Calculate overall risk score
            overall_risk_score = (
                volatility_risk * 0.3 +
                geopolitical_risk * 0.3 +
                liquidity_risk * 0.2 +
                currency_risk * 0.2
            )
            
            # Determine risk level
            if overall_risk_score > 0.8:
                risk_level = "CRITICAL"
            elif overall_risk_score > 0.6:
                risk_level = "HIGH"
            elif overall_risk_score > 0.3:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"
            
            # Generate recommendations
            recommendations = self._generate_risk_recommendations(
                overall_risk_score, volatility_risk, geopolitical_risk,
                liquidity_risk, currency_risk, portfolio
            )
            
            risk_assessment = RiskAssessment(
                timestamp=datetime.now(self.moscow_tz),
                overall_risk_level=risk_level,
                risk_score=overall_risk_score,
                volatility_risk=volatility_risk,
                geopolitical_risk=geopolitical_risk,
                liquidity_risk=liquidity_risk,
                currency_risk=currency_risk,
                recommendations=recommendations
            )
            
            # Store risk assessment
            self.risk_assessments.append(risk_assessment)
            if len(self.risk_assessments) > 50:
                self.risk_assessments = self.risk_assessments[-50:]
            
            return risk_assessment
            
        except Exception as e:
            self.logger.error(f"Error assessing comprehensive risk: {e}")
            return RiskAssessment(
                timestamp=datetime.now(self.moscow_tz),
                overall_risk_level="MEDIUM",
                risk_score=0.5,
                volatility_risk=0.5,
                geopolitical_risk=0.5,
                liquidity_risk=0.5,
                currency_risk=0.5,
                recommendations=["Мониторинг рисков недоступен"]
            )
    
    async def detect_market_regime_changes(
        self,
        market_data: List[MOEXMarketData]
    ) -> Optional[MarketRegimeChange]:
        """Detect significant market regime changes"""
        try:
            # Get current market condition
            current_condition = self.get_market_condition()
            
            # Analyze recent regime history
            if not self.regime_history:
                # First assessment
                regime_change = MarketRegimeChange(
                    timestamp=datetime.now(self.moscow_tz),
                    previous_regime="UNKNOWN",
                    current_regime=current_condition.market_phase,
                    confidence=0.5,
                    key_indicators=["Initial assessment"]
                )
                self.regime_history.append(regime_change)
                return None
            
            # Get last regime
            last_regime = self.regime_history[-1]
            
            # Check if regime has changed
            if last_regime.current_regime != current_condition.market_phase:
                # Analyze confidence in regime change
                confidence = self._calculate_regime_change_confidence(
                    market_data, last_regime.current_regime, current_condition.market_phase
                )
                
                if confidence >= self.regime_change_threshold:
                    # Identify key indicators
                    key_indicators = self._identify_regime_change_indicators(
                        market_data, current_condition
                    )
                    
                    # Estimate duration
                    expected_duration = self._estimate_regime_duration(
                        current_condition.market_phase
                    )
                    
                    regime_change = MarketRegimeChange(
                        timestamp=datetime.now(self.moscow_tz),
                        previous_regime=last_regime.current_regime,
                        current_regime=current_condition.market_phase,
                        confidence=confidence,
                        key_indicators=key_indicators,
                        expected_duration=expected_duration
                    )
                    
                    self.regime_history.append(regime_change)
                    return regime_change
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error detecting market regime changes: {e}")
            return None
    
    async def monitor_russian_economic_indicators(self) -> Dict[str, Any]:
        """Monitor key Russian economic indicators"""
        try:
            indicators = {}
            
            # Monitor RUB/USD exchange rate
            rub_usd_rate = await self._fetch_rub_usd_rate()
            if rub_usd_rate:
                self.rub_usd_history.append((datetime.now(), rub_usd_rate))
                indicators['rub_usd_rate'] = float(rub_usd_rate)
                indicators['rub_volatility'] = self._calculate_rub_volatility()
            
            # Monitor oil prices (Brent)
            oil_price = await self._fetch_oil_price()
            if oil_price:
                self.oil_price_history.append((datetime.now(), oil_price))
                indicators['oil_price'] = float(oil_price)
                indicators['oil_change'] = self._calculate_oil_price_change()
            
            # Monitor CBR key rate
            cbr_rate = await self._fetch_cbr_rate()
            if cbr_rate:
                self.cbr_rate_history.append((datetime.now(), cbr_rate))
                indicators['cbr_rate'] = cbr_rate
                indicators['rate_trend'] = self._analyze_rate_trend()
            
            # Calculate economic stress index
            indicators['economic_stress_index'] = self._calculate_economic_stress_index()
            
            return indicators
            
        except Exception as e:
            self.logger.error(f"Error monitoring economic indicators: {e}")
            return {}
    
    async def send_enhanced_market_alerts(
        self,
        market_data: List[MOEXMarketData],
        preferences: NotificationPreferences
    ) -> List[Any]:
        """Send enhanced market condition alerts"""
        alerts = []
        
        try:
            # Monitor market sentiment
            sentiment = await self.monitor_market_sentiment(market_data, [])
            
            # Send sentiment alerts if significant
            if abs(sentiment.sentiment_score) > self.sentiment_threshold:
                sentiment_alert = MarketAlert(
                    alert_type=f"НАСТРОЕНИЕ_РЫНКА_{sentiment.overall_sentiment}",
                    symbol="MARKET",
                    current_value=Decimal(str(sentiment.sentiment_score)),
                    threshold_value=Decimal(str(self.sentiment_threshold)),
                    market_condition=f"Настроение: {sentiment.overall_sentiment}"
                )
                
                notifications = await self.notification_service.send_market_alert(
                    sentiment_alert, preferences
                )
                if notifications:
                    alerts.append(sentiment_alert)
            
            # Assess comprehensive risk
            risk_assessment = await self.assess_comprehensive_risk(market_data)
            
            # Send risk alerts if high
            if risk_assessment.risk_score > self.risk_escalation_threshold:
                risk_alert = MarketAlert(
                    alert_type=f"ВЫСОКИЙ_РИСК_{risk_assessment.overall_risk_level}",
                    symbol="MARKET",
                    current_value=Decimal(str(risk_assessment.risk_score)),
                    threshold_value=Decimal(str(self.risk_escalation_threshold)),
                    market_condition=f"Уровень риска: {risk_assessment.overall_risk_level}"
                )
                
                notifications = await self.notification_service.send_market_alert(
                    risk_alert, preferences
                )
                if notifications:
                    alerts.append(risk_alert)
            
            # Detect regime changes
            regime_change = await self.detect_market_regime_changes(market_data)
            if regime_change:
                regime_alert = MarketAlert(
                    alert_type="СМЕНА_РЕЖИМА_РЫНКА",
                    symbol="MARKET",
                    current_value=Decimal(str(regime_change.confidence)),
                    market_condition=f"Переход: {regime_change.previous_regime} → {regime_change.current_regime}"
                )
                
                notifications = await self.notification_service.send_market_alert(
                    regime_alert, preferences
                )
                if notifications:
                    alerts.append(regime_alert)
            
            # Monitor economic indicators
            economic_indicators = await self.monitor_russian_economic_indicators()
            
            # Send economic alerts if needed
            if economic_indicators.get('economic_stress_index', 0) > 0.7:
                economic_alert = MarketAlert(
                    alert_type="ЭКОНОМИЧЕСКИЙ_СТРЕСС",
                    symbol="ECONOMY",
                    current_value=Decimal(str(economic_indicators['economic_stress_index'])),
                    threshold_value=Decimal("0.7"),
                    market_condition="Высокий уровень экономического стресса"
                )
                
                notifications = await self.notification_service.send_market_alert(
                    economic_alert, preferences
                )
                if notifications:
                    alerts.append(economic_alert)
            
        except Exception as e:
            self.logger.error(f"Error sending enhanced market alerts: {e}")
        
        return alerts
    
    def _analyze_price_sentiment(self, market_data: List[MOEXMarketData]) -> float:
        """Analyze price movements for sentiment"""
        if not market_data:
            return 0.0
        
        # Calculate weighted sentiment based on price changes and volumes
        total_sentiment = 0.0
        total_weight = 0.0
        
        for data in market_data:
            if data.change_percent is not None and data.volume > 0:
                # Weight by volume
                weight = float(data.volume)
                sentiment = float(data.change_percent)
                
                total_sentiment += sentiment * weight
                total_weight += weight
        
        return total_sentiment / total_weight if total_weight > 0 else 0.0
    
    async def _analyze_news_sentiment(self, news_data: List[Dict[str, Any]]) -> float:
        """Analyze news sentiment (simplified implementation)"""
        if not news_data:
            return 0.0
        
        # Simplified sentiment analysis based on keywords
        positive_keywords = ['рост', 'прибыль', 'успех', 'развитие', 'инвестиции']
        negative_keywords = ['падение', 'убытки', 'кризис', 'санкции', 'проблемы']
        
        sentiment_scores = []
        
        for news in news_data:
            title = news.get('title', '').lower()
            
            positive_count = sum(1 for word in positive_keywords if word in title)
            negative_count = sum(1 for word in negative_keywords if word in title)
            
            if positive_count > 0 or negative_count > 0:
                score = (positive_count - negative_count) / (positive_count + negative_count)
                sentiment_scores.append(score)
        
        return statistics.mean(sentiment_scores) if sentiment_scores else 0.0
    
    def _analyze_volume_sentiment(self, market_data: List[MOEXMarketData]) -> float:
        """Analyze volume patterns for sentiment"""
        if not market_data:
            return 0.0
        
        # Analyze volume vs average volume
        volume_signals = []
        
        for data in market_data:
            avg_volume = asyncio.run(self._get_average_volume(data.symbol))
            if avg_volume and data.volume > 0:
                volume_ratio = data.volume / avg_volume
                
                # High volume with positive price change = bullish
                # High volume with negative price change = bearish
                if volume_ratio > 1.5:  # Significant volume
                    if data.change_percent and data.change_percent > 0:
                        volume_signals.append(0.5)  # Bullish
                    elif data.change_percent and data.change_percent < 0:
                        volume_signals.append(-0.5)  # Bearish
        
        return statistics.mean(volume_signals) if volume_signals else 0.0
    
    def _identify_sentiment_factors(
        self,
        price_sentiment: float,
        news_sentiment: float,
        volume_sentiment: float
    ) -> List[str]:
        """Identify key factors driving sentiment"""
        factors = []
        
        if abs(price_sentiment) > 0.3:
            direction = "положительная" if price_sentiment > 0 else "отрицательная"
            factors.append(f"Ценовая динамика ({direction})")
        
        if abs(news_sentiment) > 0.3:
            direction = "позитивные" if news_sentiment > 0 else "негативные"
            factors.append(f"Новостной фон ({direction})")
        
        if abs(volume_sentiment) > 0.3:
            direction = "активные покупки" if volume_sentiment > 0 else "активные продажи"
            factors.append(f"Объемы торгов ({direction})")
        
        return factors
    
    def _analyze_sector_sentiments(self, market_data: List[MOEXMarketData]) -> Dict[str, float]:
        """Analyze sentiment by sector"""
        # Simplified sector mapping
        sector_map = {
            'SBER': 'БАНКИ', 'VTB': 'БАНКИ',
            'GAZP': 'НЕФТЕГАЗ', 'LKOH': 'НЕФТЕГАЗ', 'ROSN': 'НЕФТЕГАЗ',
            'GMKN': 'МЕТАЛЛЫ', 'NLMK': 'МЕТАЛЛЫ', 'MAGN': 'МЕТАЛЛЫ'
        }
        
        sector_sentiments = {}
        sector_data = {}
        
        for data in market_data:
            sector = sector_map.get(data.symbol, 'ПРОЧИЕ')
            if sector not in sector_data:
                sector_data[sector] = []
            
            if data.change_percent is not None:
                sector_data[sector].append(float(data.change_percent))
        
        for sector, changes in sector_data.items():
            if changes:
                sector_sentiments[sector] = statistics.mean(changes)
        
        return sector_sentiments
    
    async def _calculate_volatility_risk(self, market_data: List[MOEXMarketData]) -> float:
        """Calculate volatility-based risk"""
        volatilities = []
        
        for data in market_data:
            metrics = await self._calculate_volatility_metrics(data)
            volatilities.append(metrics.current_volatility)
        
        if not volatilities:
            return 0.5
        
        avg_volatility = statistics.mean(volatilities)
        return min(1.0, avg_volatility / 0.1)  # Normalize to 0-1 scale
    
    async def _assess_geopolitical_risk(self) -> float:
        """Assess geopolitical risk level"""
        # Simplified implementation - would integrate with news analysis
        recent_events = len([
            event for event in self.geopolitical_events
            if event.get('timestamp', datetime.min) > datetime.now() - timedelta(days=7)
        ])
        
        # Scale based on recent events
        return min(1.0, recent_events / 10.0)
    
    def _calculate_liquidity_risk(self, market_data: List[MOEXMarketData]) -> float:
        """Calculate liquidity risk based on volume patterns"""
        if not market_data:
            return 0.5
        
        low_volume_count = 0
        total_count = len(market_data)
        
        for data in market_data:
            avg_volume = asyncio.run(self._get_average_volume(data.symbol))
            if avg_volume and data.volume < avg_volume * 0.5:  # Less than 50% of average
                low_volume_count += 1
        
        return low_volume_count / total_count if total_count > 0 else 0.5
    
    async def _assess_currency_risk(self) -> float:
        """Assess RUB volatility risk"""
        if len(self.rub_usd_history) < 10:
            return 0.5
        
        # Calculate RUB volatility
        recent_rates = [float(rate) for _, rate in self.rub_usd_history[-20:]]
        if len(recent_rates) < 2:
            return 0.5
        
        returns = []
        for i in range(1, len(recent_rates)):
            ret = (recent_rates[i] - recent_rates[i-1]) / recent_rates[i-1]
            returns.append(ret)
        
        volatility = statistics.stdev(returns) if len(returns) > 1 else 0.0
        return min(1.0, volatility / 0.05)  # Normalize to 0-1 scale
    
    def _generate_risk_recommendations(
        self,
        overall_risk: float,
        volatility_risk: float,
        geopolitical_risk: float,
        liquidity_risk: float,
        currency_risk: float,
        portfolio: Optional[Portfolio]
    ) -> List[str]:
        """Generate risk-based recommendations"""
        recommendations = []
        
        if overall_risk > 0.8:
            recommendations.append("Рассмотрите снижение размера позиций")
            recommendations.append("Увеличьте долю денежных средств в портфеле")
        
        if volatility_risk > 0.7:
            recommendations.append("Установите более жесткие стоп-лоссы")
            recommendations.append("Избегайте маржинальной торговли")
        
        if geopolitical_risk > 0.7:
            recommendations.append("Диверсифицируйте по секторам")
            recommendations.append("Мониторьте новости о санкциях")
        
        if liquidity_risk > 0.7:
            recommendations.append("Избегайте неликвидных акций")
            recommendations.append("Торгуйте только в основную сессию")
        
        if currency_risk > 0.7:
            recommendations.append("Рассмотрите валютное хеджирование")
            recommendations.append("Мониторьте курс рубля")
        
        return recommendations
    
    # Additional helper methods for economic indicators
    async def _fetch_rub_usd_rate(self) -> Optional[Decimal]:
        """Fetch current RUB/USD exchange rate"""
        try:
            # Simplified implementation - would use real API
            return Decimal("75.50")  # Mock rate
        except Exception:
            return None
    
    async def _fetch_oil_price(self) -> Optional[Decimal]:
        """Fetch current oil price"""
        try:
            # Simplified implementation - would use real API
            return Decimal("80.25")  # Mock price
        except Exception:
            return None
    
    async def _fetch_cbr_rate(self) -> Optional[float]:
        """Fetch current CBR key rate"""
        try:
            # Simplified implementation - would use real API
            return 16.0  # Mock rate
        except Exception:
            return None
    
    def _calculate_rub_volatility(self) -> float:
        """Calculate RUB volatility"""
        if len(self.rub_usd_history) < 10:
            return 0.0
        
        rates = [float(rate) for _, rate in self.rub_usd_history[-20:]]
        returns = [(rates[i] - rates[i-1]) / rates[i-1] for i in range(1, len(rates))]
        
        return statistics.stdev(returns) if len(returns) > 1 else 0.0
    
    def _calculate_oil_price_change(self) -> float:
        """Calculate oil price change"""
        if len(self.oil_price_history) < 2:
            return 0.0
        
        current = float(self.oil_price_history[-1][1])
        previous = float(self.oil_price_history[-2][1])
        
        return (current - previous) / previous
    
    def _analyze_rate_trend(self) -> str:
        """Analyze CBR rate trend"""
        if len(self.cbr_rate_history) < 3:
            return "STABLE"
        
        recent_rates = [rate for _, rate in self.cbr_rate_history[-3:]]
        
        if recent_rates[-1] > recent_rates[-2] > recent_rates[-3]:
            return "RISING"
        elif recent_rates[-1] < recent_rates[-2] < recent_rates[-3]:
            return "FALLING"
        else:
            return "STABLE"
    
    def _calculate_economic_stress_index(self) -> float:
        """Calculate economic stress index"""
        stress_factors = []
        
        # RUB volatility factor
        rub_vol = self._calculate_rub_volatility()
        stress_factors.append(min(1.0, rub_vol / 0.05))
        
        # Oil price volatility factor
        if len(self.oil_price_history) >= 10:
            oil_prices = [float(price) for _, price in self.oil_price_history[-10:]]
            oil_returns = [(oil_prices[i] - oil_prices[i-1]) / oil_prices[i-1] for i in range(1, len(oil_prices))]
            oil_vol = statistics.stdev(oil_returns) if len(oil_returns) > 1 else 0.0
            stress_factors.append(min(1.0, oil_vol / 0.1))
        
        # Interest rate factor
        if self.cbr_rate_history:
            current_rate = self.cbr_rate_history[-1][1]
            stress_factors.append(min(1.0, (current_rate - 5.0) / 15.0))  # Normalize around 5% base rate
        
        return statistics.mean(stress_factors) if stress_factors else 0.5
    
    def _calculate_regime_change_confidence(
        self,
        market_data: List[MOEXMarketData],
        old_regime: str,
        new_regime: str
    ) -> float:
        """Calculate confidence in regime change"""
        # Simplified implementation
        confidence_factors = []
        
        # Volatility consistency
        current_condition = self.get_market_condition()
        if current_condition.volatility_index > 0.05 and new_regime == "VOLATILE":
            confidence_factors.append(0.8)
        elif current_condition.volatility_index < 0.02 and new_regime == "NORMAL":
            confidence_factors.append(0.8)
        else:
            confidence_factors.append(0.5)
        
        # Duration in previous regime
        if len(self.regime_history) > 1:
            time_in_regime = datetime.now() - self.regime_history[-1].timestamp
            if time_in_regime > timedelta(days=7):  # Stable regime for a week
                confidence_factors.append(0.9)
            else:
                confidence_factors.append(0.6)
        
        return statistics.mean(confidence_factors)
    
    def _identify_regime_change_indicators(
        self,
        market_data: List[MOEXMarketData],
        condition: MarketCondition
    ) -> List[str]:
        """Identify key indicators of regime change"""
        indicators = []
        
        if condition.volatility_index > 0.05:
            indicators.append("Высокая волатильность")
        
        if condition.market_phase == "CRISIS":
            indicators.append("Кризисные условия")
        
        # Check for volume changes
        high_volume_count = sum(1 for data in market_data if data.volume > 1000000)
        if high_volume_count > len(market_data) * 0.7:
            indicators.append("Повышенные объемы торгов")
        
        return indicators
    
    def _estimate_regime_duration(self, regime: str) -> str:
        """Estimate expected duration of market regime"""
        duration_map = {
            "NORMAL": "2-4 недели",
            "VOLATILE": "1-2 недели",
            "CRISIS": "1-3 месяца",
            "RECOVERY": "3-6 недель"
        }
        
        return duration_map.get(regime, "Неопределенно")
    
    def get_enhanced_market_summary(self) -> Dict[str, Any]:
        """Get comprehensive market summary"""
        summary = {
            'timestamp': datetime.now(self.moscow_tz).isoformat(),
            'basic_condition': self.get_market_condition().__dict__,
            'sentiment': self.sentiment_history[-1].__dict__ if self.sentiment_history else None,
            'risk_assessment': self.risk_assessments[-1].__dict__ if self.risk_assessments else None,
            'recent_regime_changes': [r.__dict__ for r in self.regime_history[-3:]],
            'economic_indicators': {
                'rub_usd_rate': float(self.rub_usd_history[-1][1]) if self.rub_usd_history else None,
                'oil_price': float(self.oil_price_history[-1][1]) if self.oil_price_history else None,
                'cbr_rate': self.cbr_rate_history[-1][1] if self.cbr_rate_history else None,
                'economic_stress_index': self._calculate_economic_stress_index()
            }
        }
        
        return summary