"""
Unit tests for market monitoring service
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from decimal import Decimal

from russian_trading_bot.models.market_data import MOEXMarketData
from russian_trading_bot.models.trading import Portfolio, Position
from russian_trading_bot.models.notifications import (
    NotificationPreferences, MarketAlert, GeopoliticalAlert, PortfolioAlert
)
from russian_trading_bot.services.market_monitor import MarketMonitor, VolatilityMetrics, MarketCondition
from russian_trading_bot.services.notification_service import NotificationService


class TestMarketMonitor:
    """Test market monitoring functionality"""
    
    @pytest.fixture
    def config(self):
        """Test configuration"""
        return {
            'volatility_threshold': 0.03,
            'volume_spike_threshold': 2.0,
            'price_movement_threshold': 0.05,
            'news_sources': [
                'https://test.rbc.ru/rss',
                'https://test.vedomosti.ru/rss'
            ]
        }
    
    @pytest.fixture
    def notification_service(self):
        """Mock notification service"""
        return Mock(spec=NotificationService)
    
    @pytest.fixture
    def market_monitor(self, notification_service, config):
        """Create market monitor instance"""
        return MarketMonitor(notification_service, config)
    
    @pytest.fixture
    def preferences(self):
        """Test notification preferences"""
        return NotificationPreferences(
            user_id="test_user",
            email="test@example.com",
            telegram_chat_id="123456789",
            market_volatility_threshold=0.03
        )
    
    @pytest.fixture
    def sample_market_data(self):
        """Sample market data for testing"""
        return [
            MOEXMarketData(
                symbol="SBER",
                price=Decimal("250.50"),
                volume=1000000,
                timestamp=datetime.now(),
                change_percent=0.08,  # 8% change - above threshold
                previous_close=Decimal("232.00")
            ),
            MOEXMarketData(
                symbol="GAZP",
                price=Decimal("180.75"),
                volume=500000,
                timestamp=datetime.now(),
                change_percent=0.02,  # 2% change - below threshold
                previous_close=Decimal("177.25")
            )
        ]
    
    def test_volatility_metrics_calculation(self, market_monitor):
        """Test volatility metrics calculation"""
        # Create test data
        test_data = MOEXMarketData(
            symbol="SBER",
            price=Decimal("250.50"),
            volume=1000000,
            timestamp=datetime.now(),
            change_percent=0.05,
            previous_close=Decimal("238.57")
        )
        
        # Add some historical data
        market_monitor.price_history["SBER"] = [
            (datetime.now() - timedelta(days=i), Decimal(str(250 + i)))
            for i in range(10)
        ]
        
        # Calculate volatility metrics
        volatility_metrics = asyncio.run(
            market_monitor._calculate_volatility_metrics(test_data)
        )
        
        # Verify metrics
        assert volatility_metrics.symbol == "SBER"
        assert volatility_metrics.current_volatility >= 0
        assert volatility_metrics.average_volatility >= 0
        assert 0 <= volatility_metrics.volatility_percentile <= 1
    
    @pytest.mark.asyncio
    async def test_monitor_market_volatility(self, market_monitor, sample_market_data, preferences):
        """Test market volatility monitoring"""
        # Mock notification service
        market_monitor.notification_service.send_market_alert = AsyncMock(
            return_value=[Mock()]
        )
        
        # Mock volatility calculation to return high volatility
        with patch.object(market_monitor, '_calculate_volatility_metrics') as mock_calc:
            mock_calc.return_value = VolatilityMetrics(
                symbol="SBER",
                current_volatility=0.05,  # Above threshold
                average_volatility=0.02,
                volatility_percentile=0.95,
                price_change_24h=0.08,
                volume_change_24h=0.0,
                is_high_volatility=True
            )
            
            # Monitor volatility
            alerts = await market_monitor.monitor_market_volatility(
                sample_market_data, preferences
            )
            
            # Verify alert was generated
            assert len(alerts) == 1
            assert alerts[0].alert_type == "ВЫСОКАЯ_ВОЛАТИЛЬНОСТЬ"
            assert alerts[0].symbol == "SBER"
            
            # Verify notification was sent
            market_monitor.notification_service.send_market_alert.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_monitor_volume_spikes(self, market_monitor, sample_market_data, preferences):
        """Test volume spike monitoring"""
        # Mock notification service
        market_monitor.notification_service.send_market_alert = AsyncMock(
            return_value=[Mock()]
        )
        
        # Mock average volume calculation
        with patch.object(market_monitor, '_get_average_volume') as mock_avg:
            mock_avg.return_value = 400000  # Average volume
            
            # Monitor volume spikes (current volume 1,000,000 vs average 400,000 = 2.5x)
            alerts = await market_monitor.monitor_volume_spikes(
                sample_market_data, preferences
            )
            
            # Verify alert was generated for SBER (volume spike)
            assert len(alerts) == 1
            assert alerts[0].alert_type == "ВСПЛЕСК_ОБЪЕМА"
            assert alerts[0].symbol == "SBER"
            
            # Verify notification was sent
            market_monitor.notification_service.send_market_alert.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_monitor_price_movements(self, market_monitor, sample_market_data, preferences):
        """Test price movement monitoring"""
        # Mock notification service
        market_monitor.notification_service.send_market_alert = AsyncMock(
            return_value=[Mock()]
        )
        
        # Monitor price movements (SBER has 8% change - above 5% threshold)
        alerts = await market_monitor.monitor_price_movements(
            sample_market_data, preferences
        )
        
        # Verify alert was generated for SBER
        assert len(alerts) == 1
        assert alerts[0].alert_type == "ЗНАЧИТЕЛЬНОЕ_РОСТ"
        assert alerts[0].symbol == "SBER"
        assert alerts[0].change_percent == 0.08
        
        # Verify notification was sent
        market_monitor.notification_service.send_market_alert.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_monitor_geopolitical_events(self, market_monitor, preferences):
        """Test geopolitical event monitoring"""
        # Mock notification service
        market_monitor.notification_service.send_geopolitical_alert = AsyncMock(
            return_value=[Mock()]
        )
        
        # Mock news fetching
        test_news = [
            {
                'title': 'Новые санкции против российских банков',
                'source': 'test.rbc.ru',
                'pub_date': datetime.now().isoformat()
            },
            {
                'title': 'ЦБ повысил ключевую ставку до 15%',
                'source': 'test.vedomosti.ru',
                'pub_date': datetime.now().isoformat()
            }
        ]
        
        with patch.object(market_monitor, '_fetch_russian_news') as mock_fetch:
            mock_fetch.return_value = test_news
            
            # Monitor geopolitical events
            alerts = await market_monitor.monitor_geopolitical_events(preferences)
            
            # Verify alerts were generated
            assert len(alerts) >= 1
            
            # Check for sanctions alert
            sanctions_alerts = [a for a in alerts if 'SANCTIONS' in a.event_type]
            if sanctions_alerts:
                assert sanctions_alerts[0].severity in ['КРИТИЧЕСКАЯ', 'ВЫСОКАЯ']
                assert 'БАНКИ' in sanctions_alerts[0].affected_sectors
    
    @pytest.mark.asyncio
    async def test_monitor_portfolio_risk_thresholds(self, market_monitor, preferences):
        """Test portfolio risk threshold monitoring"""
        # Create test portfolio with losses
        portfolio = Portfolio(
            positions={
                "SBER": Position(
                    symbol="SBER",
                    quantity=100,
                    average_price=Decimal("260.00"),
                    current_price=Decimal("230.00"),  # 11.5% loss
                    market_value=Decimal("23000.00"),
                    unrealized_pnl=Decimal("-3000.00")
                )
            },
            cash_balance=Decimal("50000.00"),
            total_value=Decimal("73000.00"),
            total_pnl=Decimal("-3000.00")  # About 4% loss
        )
        
        # Mock notification service
        market_monitor.notification_service.send_portfolio_alert = AsyncMock(
            return_value=[Mock()]
        )
        
        # Monitor portfolio risks
        alerts = await market_monitor.monitor_portfolio_risk_thresholds(
            portfolio, preferences
        )
        
        # Verify alerts were generated
        assert len(alerts) >= 1
        
        # Check for individual position loss alert
        position_alerts = [a for a in alerts if 'ПОЗИЦИИ' in a.alert_type]
        if position_alerts:
            assert 'SBER' in position_alerts[0].affected_positions
    
    def test_alert_cooldown_functionality(self, market_monitor):
        """Test alert cooldown to prevent spam"""
        alert_key = "test_alert_SBER"
        
        # Initially no cooldown
        assert not market_monitor._is_alert_on_cooldown(alert_key)
        
        # Set recent alert
        market_monitor.recent_alerts[alert_key] = datetime.now()
        
        # Should be on cooldown
        assert market_monitor._is_alert_on_cooldown(alert_key)
        
        # Set old alert (beyond cooldown period)
        market_monitor.recent_alerts[alert_key] = datetime.now() - timedelta(hours=1)
        
        # Should not be on cooldown
        assert not market_monitor._is_alert_on_cooldown(alert_key)
    
    def test_update_market_data(self, market_monitor):
        """Test updating market data for monitoring"""
        test_data = MOEXMarketData(
            symbol="SBER",
            price=Decimal("250.50"),
            volume=1000000,
            timestamp=datetime.now()
        )
        
        # Update market data
        market_monitor.update_market_data(test_data)
        
        # Verify data was stored
        assert "SBER" in market_monitor.price_history
        assert "SBER" in market_monitor.volume_history
        assert len(market_monitor.price_history["SBER"]) == 1
        assert len(market_monitor.volume_history["SBER"]) == 1
    
    def test_get_market_condition(self, market_monitor):
        """Test market condition assessment"""
        # Add some volatility data
        market_monitor.volatility_history = {
            "SBER": [0.02, 0.03, 0.04, 0.05],
            "GAZP": [0.01, 0.02, 0.03, 0.02]
        }
        
        # Get market condition
        condition = market_monitor.get_market_condition()
        
        # Verify condition
        assert isinstance(condition, MarketCondition)
        assert condition.market_phase in ["NORMAL", "VOLATILE", "CRISIS", "RECOVERY"]
        assert condition.volatility_index >= 0
        assert condition.timestamp is not None
    
    @pytest.mark.asyncio
    async def test_geopolitical_content_analysis(self, market_monitor):
        """Test geopolitical content analysis"""
        # Test news with sanctions content
        sanctions_news = {
            'title': 'США ввели новые санкции против российских банков',
            'source': 'test.rbc.ru'
        }
        
        analysis = await market_monitor._analyze_geopolitical_content(sanctions_news)
        
        # Verify analysis
        assert analysis['is_geopolitical'] is True
        assert 'SANCTIONS' in analysis['event_type']
        assert analysis['severity'] in ['КРИТИЧЕСКАЯ', 'ВЫСОКАЯ']
        assert 'БАНКИ' in analysis['affected_sectors']
        
        # Test news with monetary policy content
        policy_news = {
            'title': 'ЦБ РФ повысил ключевую ставку до 16%',
            'source': 'test.vedomosti.ru'
        }
        
        analysis = await market_monitor._analyze_geopolitical_content(policy_news)
        
        # Verify analysis
        assert analysis['is_geopolitical'] is True
        assert 'POLICY' in analysis['event_type']
        assert analysis['severity'] in ['ВЫСОКАЯ', 'СРЕДНЯЯ']
    
    def test_data_cleanup(self, market_monitor):
        """Test automatic cleanup of old data"""
        # Add old data (35 days ago)
        old_timestamp = datetime.now() - timedelta(days=35)
        recent_timestamp = datetime.now() - timedelta(days=5)
        
        market_monitor.price_history["SBER"] = [
            (old_timestamp, Decimal("240.00")),
            (recent_timestamp, Decimal("250.00"))
        ]
        
        market_monitor.volume_history["SBER"] = [
            (old_timestamp, 800000),
            (recent_timestamp, 1000000)
        ]
        
        # Update with new data (triggers cleanup)
        new_data = MOEXMarketData(
            symbol="SBER",
            price=Decimal("255.00"),
            volume=1200000,
            timestamp=datetime.now()
        )
        
        market_monitor.update_market_data(new_data)
        
        # Verify old data was cleaned up (only recent data remains)
        assert len(market_monitor.price_history["SBER"]) == 2  # Recent + new
        assert len(market_monitor.volume_history["SBER"]) == 2  # Recent + new
        
        # Verify old data is not present
        timestamps = [ts for ts, _ in market_monitor.price_history["SBER"]]
        assert old_timestamp not in timestamps
        assert recent_timestamp in timestamps


class TestVolatilityMetrics:
    """Test volatility metrics data class"""
    
    def test_volatility_metrics_creation(self):
        """Test creating volatility metrics"""
        metrics = VolatilityMetrics(
            symbol="SBER",
            current_volatility=0.05,
            average_volatility=0.03,
            volatility_percentile=0.8,
            price_change_24h=0.02,
            volume_change_24h=0.15,
            is_high_volatility=True
        )
        
        assert metrics.symbol == "SBER"
        assert metrics.current_volatility == 0.05
        assert metrics.is_high_volatility is True


class TestMarketCondition:
    """Test market condition data class"""
    
    def test_market_condition_creation(self):
        """Test creating market condition"""
        condition = MarketCondition(
            timestamp=datetime.now(),
            market_phase="VOLATILE",
            volatility_index=0.04,
            fear_greed_index=0.3,
            geopolitical_risk_score=0.7,
            affected_sectors=["БАНКИ", "ЭНЕРГЕТИКА"]
        )
        
        assert condition.market_phase == "VOLATILE"
        assert condition.volatility_index == 0.04
        assert "БАНКИ" in condition.affected_sectors
    
    def test_market_condition_defaults(self):
        """Test market condition with default values"""
        condition = MarketCondition(
            timestamp=datetime.now(),
            market_phase="NORMAL",
            volatility_index=0.02
        )
        
        assert condition.geopolitical_risk_score == 0.0
        assert condition.affected_sectors == []


if __name__ == "__main__":
    pytest.main([__file__])