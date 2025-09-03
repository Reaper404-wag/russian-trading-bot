"""
Market monitoring service for Russian stock market
Monitors volatility, geopolitical events, and portfolio risk thresholds
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
import statistics
import pytz
import re
import requests
from dataclasses import dataclass

from ..models.market_data import RussianStock, MarketData, MOEXMarketData
from ..models.trading import Portfolio, Position
from ..models.notifications import (
    MarketAlert, GeopoliticalAlert, PortfolioAlert,
    NotificationPreferences, NotificationType
)
from .notification_service import NotificationService


@dataclass
class VolatilityMetrics:
    """Volatility metrics for market monitoring"""
    symbol: str
    current_volatility: float
    average_volatility: float
    volatility_percentile: float
    price_change_24h: float
    volume_change_24h: float
    is_high_volatility: bool


@dataclass
class MarketCondition:
    """Overall market condition assessment"""
    timestamp: datetime
    market_phase: str  # NORMAL, VOLATILE, CRISIS, RECOVERY
    volatility_index: float
    fear_greed_index: Optional[float] = None
    geopolitical_risk_score: float = 0.0
    affected_sectors: List[str] = None
    
    def __post_init__(self):
        if self.affected_sectors is None:
            self.affected_sectors = []


class MarketMonitor:
    """Service for monitoring Russian market conditions and alerts"""
    
    def __init__(self, notification_service: NotificationService, config: Dict[str, Any]):
        """Initialize market monitor"""
        self.notification_service = notification_service
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.moscow_tz = pytz.timezone('Europe/Moscow')
        
        # Monitoring thresholds
        self.volatility_threshold = config.get('volatility_threshold', 0.03)  # 3%
        self.volume_spike_threshold = config.get('volume_spike_threshold', 2.0)  # 2x average
        self.price_movement_threshold = config.get('price_movement_threshold', 0.05)  # 5%
        
        # Geopolitical monitoring
        self.news_sources = config.get('news_sources', [
            'https://www.rbc.ru/rss/rbcnews.rss',
            'https://www.vedomosti.ru/rss/news',
            'https://www.kommersant.ru/RSS/news.xml'
        ])
        
        # Keywords for geopolitical events
        self.geopolitical_keywords = {
            'sanctions': ['санкции', 'санкций', 'санкциями', 'ограничения'],
            'policy': ['политика', 'решение цб', 'ключевая ставка', 'регулирование'],
            'economic': ['экономика', 'инфляция', 'рецессия', 'кризис', 'рост ввп'],
            'energy': ['нефть', 'газ', 'энергетика', 'опек', 'экспорт'],
            'currency': ['рубль', 'доллар', 'евро', 'валюта', 'курс']
        }
        
        # Historical data storage
        self.price_history: Dict[str, List[Tuple[datetime, Decimal]]] = {}
        self.volume_history: Dict[str, List[Tuple[datetime, int]]] = {}
        self.volatility_history: Dict[str, List[float]] = {}
        
        # Alert tracking
        self.recent_alerts: Dict[str, datetime] = {}
        self.alert_cooldown = timedelta(minutes=30)  # Prevent spam
    
    async def monitor_market_volatility(
        self,
        market_data: List[MOEXMarketData],
        preferences: NotificationPreferences
    ) -> List[MarketAlert]:
        """Monitor market volatility and generate alerts"""
        alerts = []
        
        try:
            for data in market_data:
                # Calculate volatility metrics
                volatility_metrics = await self._calculate_volatility_metrics(data)
                
                # Check if volatility exceeds threshold
                if volatility_metrics.is_high_volatility:
                    alert_key = f"volatility_{data.symbol}"
                    
                    # Check cooldown
                    if self._is_alert_on_cooldown(alert_key):
                        continue
                    
                    # Create market alert
                    market_alert = MarketAlert(
                        alert_type="ВЫСОКАЯ_ВОЛАТИЛЬНОСТЬ",
                        symbol=data.symbol,
                        current_value=Decimal(str(volatility_metrics.current_volatility)),
                        threshold_value=Decimal(str(self.volatility_threshold)),
                        change_percent=volatility_metrics.price_change_24h,
                        market_condition="ВОЛАТИЛЬНЫЙ"
                    )
                    
                    # Send notification
                    notifications = await self.notification_service.send_market_alert(
                        market_alert, preferences
                    )
                    
                    if notifications:
                        alerts.append(market_alert)
                        self.recent_alerts[alert_key] = datetime.now()
                        self.logger.info(f"Volatility alert sent for {data.symbol}")
            
        except Exception as e:
            self.logger.error(f"Error monitoring market volatility: {e}")
        
        return alerts
    
    async def monitor_volume_spikes(
        self,
        market_data: List[MOEXMarketData],
        preferences: NotificationPreferences
    ) -> List[MarketAlert]:
        """Monitor unusual volume spikes"""
        alerts = []
        
        try:
            for data in market_data:
                # Calculate average volume
                avg_volume = await self._get_average_volume(data.symbol)
                
                if avg_volume and data.volume > 0:
                    volume_ratio = data.volume / avg_volume
                    
                    # Check for volume spike
                    if volume_ratio >= self.volume_spike_threshold:
                        alert_key = f"volume_{data.symbol}"
                        
                        # Check cooldown
                        if self._is_alert_on_cooldown(alert_key):
                            continue
                        
                        # Create market alert
                        market_alert = MarketAlert(
                            alert_type="ВСПЛЕСК_ОБЪЕМА",
                            symbol=data.symbol,
                            current_value=Decimal(str(data.volume)),
                            threshold_value=Decimal(str(avg_volume)),
                            change_percent=(volume_ratio - 1.0),
                            market_condition="АКТИВНАЯ_ТОРГОВЛЯ"
                        )
                        
                        # Send notification
                        notifications = await self.notification_service.send_market_alert(
                            market_alert, preferences
                        )
                        
                        if notifications:
                            alerts.append(market_alert)
                            self.recent_alerts[alert_key] = datetime.now()
                            self.logger.info(f"Volume spike alert sent for {data.symbol}")
            
        except Exception as e:
            self.logger.error(f"Error monitoring volume spikes: {e}")
        
        return alerts
    
    async def monitor_price_movements(
        self,
        market_data: List[MOEXMarketData],
        preferences: NotificationPreferences
    ) -> List[MarketAlert]:
        """Monitor significant price movements"""
        alerts = []
        
        try:
            for data in market_data:
                if data.previous_close and data.change_percent:
                    abs_change = abs(float(data.change_percent))
                    
                    # Check for significant price movement
                    if abs_change >= self.price_movement_threshold:
                        alert_key = f"price_{data.symbol}"
                        
                        # Check cooldown
                        if self._is_alert_on_cooldown(alert_key):
                            continue
                        
                        movement_type = "РОСТ" if data.change_percent > 0 else "ПАДЕНИЕ"
                        
                        # Create market alert
                        market_alert = MarketAlert(
                            alert_type=f"ЗНАЧИТЕЛЬНОЕ_{movement_type}",
                            symbol=data.symbol,
                            current_value=data.price,
                            threshold_value=data.previous_close,
                            change_percent=float(data.change_percent),
                            market_condition="АКТИВНОЕ_ДВИЖЕНИЕ"
                        )
                        
                        # Send notification
                        notifications = await self.notification_service.send_market_alert(
                            market_alert, preferences
                        )
                        
                        if notifications:
                            alerts.append(market_alert)
                            self.recent_alerts[alert_key] = datetime.now()
                            self.logger.info(f"Price movement alert sent for {data.symbol}")
            
        except Exception as e:
            self.logger.error(f"Error monitoring price movements: {e}")
        
        return alerts
    
    async def monitor_geopolitical_events(
        self,
        preferences: NotificationPreferences
    ) -> List[GeopoliticalAlert]:
        """Monitor geopolitical events from Russian news sources"""
        alerts = []
        
        try:
            # Fetch news from Russian sources
            news_items = await self._fetch_russian_news()
            
            for news_item in news_items:
                # Analyze news for geopolitical content
                geo_analysis = await self._analyze_geopolitical_content(news_item)
                
                if geo_analysis['is_geopolitical']:
                    alert_key = f"geo_{geo_analysis['event_type']}"
                    
                    # Check cooldown
                    if self._is_alert_on_cooldown(alert_key):
                        continue
                    
                    # Create geopolitical alert
                    geo_alert = GeopoliticalAlert(
                        event_type=geo_analysis['event_type'],
                        severity=geo_analysis['severity'],
                        description=news_item['title'],
                        affected_sectors=geo_analysis['affected_sectors'],
                        market_impact=geo_analysis['market_impact']
                    )
                    
                    # Send notification
                    notifications = await self.notification_service.send_geopolitical_alert(
                        geo_alert, preferences
                    )
                    
                    if notifications:
                        alerts.append(geo_alert)
                        self.recent_alerts[alert_key] = datetime.now()
                        self.logger.info(f"Geopolitical alert sent: {geo_analysis['event_type']}")
            
        except Exception as e:
            self.logger.error(f"Error monitoring geopolitical events: {e}")
        
        return alerts
    
    async def monitor_portfolio_risk_thresholds(
        self,
        portfolio: Portfolio,
        preferences: NotificationPreferences
    ) -> List[PortfolioAlert]:
        """Monitor portfolio risk thresholds"""
        alerts = []
        
        try:
            # Calculate portfolio metrics
            total_change_percent = 0.0
            if portfolio.total_pnl and portfolio.total_value:
                total_change_percent = float(portfolio.total_pnl / portfolio.total_value)
            
            # Check loss threshold
            if total_change_percent <= -preferences.portfolio_loss_threshold:
                alert_key = "portfolio_loss"
                
                if not self._is_alert_on_cooldown(alert_key):
                    portfolio_alert = PortfolioAlert(
                        alert_type="ПРЕВЫШЕН_ПОРОГ_УБЫТКОВ",
                        current_value=portfolio.total_value,
                        threshold_value=portfolio.total_value * Decimal(str(1 - preferences.portfolio_loss_threshold)),
                        change_amount=portfolio.total_pnl,
                        change_percent=total_change_percent,
                        affected_positions=list(portfolio.positions.keys())
                    )
                    
                    notifications = await self.notification_service.send_portfolio_alert(
                        portfolio_alert, preferences
                    )
                    
                    if notifications:
                        alerts.append(portfolio_alert)
                        self.recent_alerts[alert_key] = datetime.now()
            
            # Check gain threshold
            elif total_change_percent >= preferences.portfolio_gain_threshold:
                alert_key = "portfolio_gain"
                
                if not self._is_alert_on_cooldown(alert_key):
                    portfolio_alert = PortfolioAlert(
                        alert_type="ДОСТИГНУТ_ПОРОГ_ПРИБЫЛИ",
                        current_value=portfolio.total_value,
                        threshold_value=portfolio.total_value * Decimal(str(1 + preferences.portfolio_gain_threshold)),
                        change_amount=portfolio.total_pnl,
                        change_percent=total_change_percent,
                        affected_positions=list(portfolio.positions.keys())
                    )
                    
                    notifications = await self.notification_service.send_portfolio_alert(
                        portfolio_alert, preferences
                    )
                    
                    if notifications:
                        alerts.append(portfolio_alert)
                        self.recent_alerts[alert_key] = datetime.now()
            
            # Check individual position risks
            for symbol, position in portfolio.positions.items():
                if position.unrealized_pnl and position.market_value:
                    position_change = float(position.unrealized_pnl / position.market_value)
                    
                    # Large position loss
                    if position_change <= -0.10:  # 10% loss on individual position
                        alert_key = f"position_loss_{symbol}"
                        
                        if not self._is_alert_on_cooldown(alert_key):
                            portfolio_alert = PortfolioAlert(
                                alert_type="БОЛЬШИЕ_УБЫТКИ_ПО_ПОЗИЦИИ",
                                current_value=position.market_value,
                                change_amount=position.unrealized_pnl,
                                change_percent=position_change,
                                affected_positions=[symbol]
                            )
                            
                            notifications = await self.notification_service.send_portfolio_alert(
                                portfolio_alert, preferences
                            )
                            
                            if notifications:
                                alerts.append(portfolio_alert)
                                self.recent_alerts[alert_key] = datetime.now()
            
        except Exception as e:
            self.logger.error(f"Error monitoring portfolio risk thresholds: {e}")
        
        return alerts
    
    async def _calculate_volatility_metrics(self, data: MOEXMarketData) -> VolatilityMetrics:
        """Calculate volatility metrics for a stock"""
        # Store current price data
        if data.symbol not in self.price_history:
            self.price_history[data.symbol] = []
        
        self.price_history[data.symbol].append((data.timestamp, data.price))
        
        # Keep only last 30 days of data
        cutoff_date = datetime.now() - timedelta(days=30)
        self.price_history[data.symbol] = [
            (ts, price) for ts, price in self.price_history[data.symbol]
            if ts > cutoff_date
        ]
        
        # Calculate volatility
        prices = [float(price) for _, price in self.price_history[data.symbol]]
        
        if len(prices) < 2:
            return VolatilityMetrics(
                symbol=data.symbol,
                current_volatility=0.0,
                average_volatility=0.0,
                volatility_percentile=0.0,
                price_change_24h=0.0,
                volume_change_24h=0.0,
                is_high_volatility=False
            )
        
        # Calculate returns
        returns = []
        for i in range(1, len(prices)):
            ret = (prices[i] - prices[i-1]) / prices[i-1]
            returns.append(ret)
        
        current_volatility = statistics.stdev(returns[-10:]) if len(returns) >= 10 else statistics.stdev(returns)
        average_volatility = statistics.stdev(returns)
        
        # Calculate percentile
        volatility_percentile = 0.0
        if len(returns) > 10:
            sorted_vols = sorted([statistics.stdev(returns[i:i+10]) for i in range(len(returns)-9)])
            current_rank = sum(1 for vol in sorted_vols if vol <= current_volatility)
            volatility_percentile = current_rank / len(sorted_vols)
        
        # Price change 24h
        price_change_24h = 0.0
        if len(prices) >= 2:
            price_change_24h = (prices[-1] - prices[-2]) / prices[-2]
        
        # Volume change (simplified)
        volume_change_24h = 0.0
        
        # Determine if high volatility
        is_high_volatility = (
            current_volatility > self.volatility_threshold or
            volatility_percentile > 0.9 or
            abs(price_change_24h) > self.price_movement_threshold
        )
        
        return VolatilityMetrics(
            symbol=data.symbol,
            current_volatility=current_volatility,
            average_volatility=average_volatility,
            volatility_percentile=volatility_percentile,
            price_change_24h=price_change_24h,
            volume_change_24h=volume_change_24h,
            is_high_volatility=is_high_volatility
        )
    
    async def _get_average_volume(self, symbol: str, days: int = 20) -> Optional[float]:
        """Get average volume for a symbol"""
        if symbol not in self.volume_history:
            return None
        
        # Get recent volume data
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_volumes = [
            volume for ts, volume in self.volume_history[symbol]
            if ts > cutoff_date and volume > 0
        ]
        
        if not recent_volumes:
            return None
        
        return statistics.mean(recent_volumes)
    
    async def _fetch_russian_news(self) -> List[Dict[str, Any]]:
        """Fetch news from Russian sources"""
        news_items = []
        
        for source_url in self.news_sources:
            try:
                response = requests.get(source_url, timeout=10)
                response.raise_for_status()
                
                # Simple RSS parsing (in production, use proper XML parser)
                content = response.text
                
                # Extract titles (simplified)
                import xml.etree.ElementTree as ET
                root = ET.fromstring(content)
                
                for item in root.findall('.//item'):
                    title_elem = item.find('title')
                    pub_date_elem = item.find('pubDate')
                    
                    if title_elem is not None:
                        news_items.append({
                            'title': title_elem.text,
                            'source': source_url,
                            'pub_date': pub_date_elem.text if pub_date_elem is not None else None
                        })
                
            except Exception as e:
                self.logger.error(f"Error fetching news from {source_url}: {e}")
        
        return news_items
    
    async def _analyze_geopolitical_content(self, news_item: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze news content for geopolitical significance"""
        title = news_item.get('title', '').lower()
        
        # Check for geopolitical keywords
        event_types = []
        affected_sectors = []
        
        for event_type, keywords in self.geopolitical_keywords.items():
            if any(keyword in title for keyword in keywords):
                event_types.append(event_type.upper())
                
                # Map to affected sectors
                if event_type == 'energy':
                    affected_sectors.extend(['ЭНЕРГЕТИКА', 'НЕФТЕГАЗ'])
                elif event_type == 'sanctions':
                    affected_sectors.extend(['БАНКИ', 'ТЕХНОЛОГИИ', 'ЭНЕРГЕТИКА'])
                elif event_type == 'currency':
                    affected_sectors.extend(['БАНКИ', 'ЭКСПОРТ'])
        
        # Determine severity based on keywords
        severity = "НИЗКАЯ"
        critical_words = ['кризис', 'санкции', 'запрет', 'ограничения', 'падение']
        high_words = ['решение цб', 'ключевая ставка', 'инфляция']
        
        if any(word in title for word in critical_words):
            severity = "КРИТИЧЕСКАЯ"
        elif any(word in title for word in high_words):
            severity = "ВЫСОКАЯ"
        elif event_types:
            severity = "СРЕДНЯЯ"
        
        # Determine market impact
        market_impact = "НЕЙТРАЛЬНОЕ"
        if severity in ["КРИТИЧЕСКАЯ", "ВЫСОКАЯ"]:
            market_impact = "НЕГАТИВНОЕ" if any(word in title for word in critical_words) else "ЗНАЧИТЕЛЬНОЕ"
        
        return {
            'is_geopolitical': bool(event_types),
            'event_type': "_".join(event_types) if event_types else "ОБЩЕЕ",
            'severity': severity,
            'affected_sectors': list(set(affected_sectors)),
            'market_impact': market_impact
        }
    
    def _is_alert_on_cooldown(self, alert_key: str) -> bool:
        """Check if alert is on cooldown to prevent spam"""
        if alert_key not in self.recent_alerts:
            return False
        
        last_alert_time = self.recent_alerts[alert_key]
        return datetime.now() - last_alert_time < self.alert_cooldown
    
    def update_market_data(self, market_data: MOEXMarketData) -> None:
        """Update historical market data for monitoring"""
        # Update price history
        if market_data.symbol not in self.price_history:
            self.price_history[market_data.symbol] = []
        
        self.price_history[market_data.symbol].append(
            (market_data.timestamp, market_data.price)
        )
        
        # Update volume history
        if market_data.symbol not in self.volume_history:
            self.volume_history[market_data.symbol] = []
        
        self.volume_history[market_data.symbol].append(
            (market_data.timestamp, market_data.volume)
        )
        
        # Cleanup old data (keep 30 days)
        cutoff_date = datetime.now() - timedelta(days=30)
        
        self.price_history[market_data.symbol] = [
            (ts, price) for ts, price in self.price_history[market_data.symbol]
            if ts > cutoff_date
        ]
        
        self.volume_history[market_data.symbol] = [
            (ts, volume) for ts, volume in self.volume_history[market_data.symbol]
            if ts > cutoff_date
        ]
    
    def get_market_condition(self) -> MarketCondition:
        """Get overall market condition assessment"""
        # Calculate overall volatility index
        all_volatilities = []
        for symbol_history in self.volatility_history.values():
            if symbol_history:
                all_volatilities.extend(symbol_history[-10:])  # Last 10 readings
        
        volatility_index = statistics.mean(all_volatilities) if all_volatilities else 0.0
        
        # Determine market phase
        if volatility_index > 0.05:  # 5%
            market_phase = "CRISIS"
        elif volatility_index > 0.03:  # 3%
            market_phase = "VOLATILE"
        elif volatility_index < 0.01:  # 1%
            market_phase = "RECOVERY"
        else:
            market_phase = "NORMAL"
        
        return MarketCondition(
            timestamp=datetime.now(self.moscow_tz),
            market_phase=market_phase,
            volatility_index=volatility_index,
            geopolitical_risk_score=0.0  # Would be calculated from recent geo events
        )