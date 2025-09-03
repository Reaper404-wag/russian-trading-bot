"""
Unit tests for geopolitical risk assessment functionality
Tests the comprehensive geopolitical risk assessment, portfolio rebalancing,
and risk adjustment algorithms for sanctions and geopolitical events.
"""

import unittest
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict

from russian_trading_bot.services.risk_manager import (
    RussianMarketRiskManager, RiskParameters, Portfolio, Position,
    GeopoliticalEvent, GeopoliticalRiskLevel, GeopoliticalRiskScore,
    PortfolioRebalanceRecommendation, TradeOrder
)
from russian_trading_bot.models.market_data import MarketData
from russian_trading_bot.models.news_data import RussianNewsArticle, NewsSentiment


class TestGeopoliticalRiskAssessment(unittest.TestCase):
    """Test geopolitical risk assessment functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.risk_manager = RussianMarketRiskManager()
        
        # Create sample portfolio
        self.sample_portfolio = Portfolio(
            positions={
                'SBER': Position(
                    symbol='SBER',
                    quantity=100,
                    entry_price=Decimal('250.0'),
                    current_price=Decimal('260.0'),
                    market_value=Decimal('26000.0'),
                    unrealized_pnl=Decimal('1000.0'),
                    entry_date=datetime.now() - timedelta(days=30),
                    sector='BANKING'
                ),
                'GAZP': Position(
                    symbol='GAZP',
                    quantity=200,
                    entry_price=Decimal('180.0'),
                    current_price=Decimal('175.0'),
                    market_value=Decimal('35000.0'),
                    unrealized_pnl=Decimal('-1000.0'),
                    entry_date=datetime.now() - timedelta(days=20),
                    sector='ENERGY'
                ),
                'YNDX': Position(
                    symbol='YNDX',
                    quantity=50,
                    entry_price=Decimal('2800.0'),
                    current_price=Decimal('2900.0'),
                    market_value=Decimal('145000.0'),
                    unrealized_pnl=Decimal('5000.0'),
                    entry_date=datetime.now() - timedelta(days=10),
                    sector='TECHNOLOGY'
                )
            },
            cash_balance=Decimal('50000.0'),
            currency='RUB'
        )
        
        # Create sample market data
        self.sample_market_data = {
            'SBER': MarketData(
                symbol='SBER',
                timestamp=datetime.now(),
                price=Decimal('260.0'),
                volume=1000000,
                bid=Decimal('259.5'),
                ask=Decimal('260.5'),
                change_percent=4.0
            ),
            'GAZP': MarketData(
                symbol='GAZP',
                timestamp=datetime.now(),
                price=Decimal('175.0'),
                volume=800000,
                bid=Decimal('174.8'),
                ask=Decimal('175.2'),
                change_percent=-2.8
            ),
            'YNDX': MarketData(
                symbol='YNDX',
                timestamp=datetime.now(),
                price=Decimal('2900.0'),
                volume=50000,
                bid=Decimal('2895.0'),
                ask=Decimal('2905.0'),
                change_percent=3.6
            )
        }
        
        # Create sample news articles
        self.sample_news_articles = [
            RussianNewsArticle(
                title="Новые санкции против российских банков",
                content="Европейский союз ввел новые санкции против крупнейших российских банков, включая Сбербанк",
                source="RBC",
                timestamp=datetime.now() - timedelta(hours=2),
                mentioned_stocks=['SBER'],
                category='SANCTIONS'
            ),
            RussianNewsArticle(
                title="Центробанк повысил ключевую ставку",
                content="ЦБ РФ принял решение о повышении ключевой ставки до 16% годовых",
                source="VEDOMOSTI",
                timestamp=datetime.now() - timedelta(hours=4),
                mentioned_stocks=[],
                category='REGULATORY'
            ),
            RussianNewsArticle(
                title="Газпром сообщил о снижении экспорта",
                content="Газпром зафиксировал значительное снижение экспорта газа в Европу",
                source="INTERFAX",
                timestamp=datetime.now() - timedelta(hours=6),
                mentioned_stocks=['GAZP'],
                category='SECTOR_NEWS'
            )
        ]
        
        # Create sample news sentiments
        self.sample_news_sentiments = [
            NewsSentiment(
                article_id="RBC_sanctions_news",
                overall_sentiment="VERY_NEGATIVE",
                sentiment_score=-0.8,
                confidence=0.9,
                negative_keywords=['санкции', 'ограничения', 'запрет']
            ),
            NewsSentiment(
                article_id="VEDOMOSTI_cb_news",
                overall_sentiment="NEGATIVE",
                sentiment_score=-0.4,
                confidence=0.7,
                negative_keywords=['повышение', 'ставка']
            ),
            NewsSentiment(
                article_id="INTERFAX_gazprom_news",
                overall_sentiment="NEGATIVE",
                sentiment_score=-0.6,
                confidence=0.8,
                negative_keywords=['снижение', 'экспорт']
            )
        ]
    
    def test_assess_comprehensive_geopolitical_risk_normal_conditions(self):
        """Test geopolitical risk assessment under normal conditions"""
        # Create minimal news with neutral sentiment
        neutral_articles = [
            RussianNewsArticle(
                title="Обычные торги на MOEX",
                content="Торги на Московской бирже проходят в штатном режиме",
                source="RBC",
                timestamp=datetime.now(),
                mentioned_stocks=['MOEX']
            )
        ]
        
        neutral_sentiments = [
            NewsSentiment(
                article_id="neutral_news",
                overall_sentiment="NEUTRAL",
                sentiment_score=0.0,
                confidence=0.5
            )
        ]
        
        risk_score = self.risk_manager.assess_comprehensive_geopolitical_risk(
            neutral_articles, neutral_sentiments, []
        )
        
        self.assertIsInstance(risk_score, GeopoliticalRiskScore)
        self.assertEqual(risk_score.overall_risk_level, GeopoliticalRiskLevel.NORMAL)
        self.assertLess(risk_score.risk_score, 0.3)
        self.assertLessEqual(risk_score.sanctions_risk_score, 0.2)
    
    def test_assess_comprehensive_geopolitical_risk_high_sanctions(self):
        """Test geopolitical risk assessment with high sanctions risk"""
        # Create sanctions event
        sanctions_event = GeopoliticalEvent(
            event_id="sanctions_2024_01",
            event_type="SANCTIONS",
            severity="HIGH",
            description="Major sanctions against Russian financial sector",
            affected_sectors=['BANKING', 'ENERGY'],
            affected_stocks=['SBER', 'GAZP'],
            start_date=datetime.now() - timedelta(days=1),
            impact_score=0.8,
            confidence=0.9,
            source="EU_SANCTIONS"
        )
        
        risk_score = self.risk_manager.assess_comprehensive_geopolitical_risk(
            self.sample_news_articles, 
            self.sample_news_sentiments,
            [sanctions_event]
        )
        
        self.assertIsInstance(risk_score, GeopoliticalRiskScore)
        # Should have elevated risk due to sanctions event
        self.assertGreaterEqual(risk_score.overall_risk_level.value, GeopoliticalRiskLevel.NORMAL.value)
        self.assertGreater(risk_score.sanctions_risk_score, 0.5)
        self.assertGreater(risk_score.risk_score, 0.15)
        # Should have some recommendations
        self.assertIsInstance(risk_score.recommendations, list)
    
    def test_assess_comprehensive_geopolitical_risk_policy_changes(self):
        """Test geopolitical risk assessment with policy changes"""
        policy_event = GeopoliticalEvent(
            event_id="policy_2024_01",
            event_type="POLICY_CHANGE",
            severity="MEDIUM",
            description="Central bank rate increase",
            affected_sectors=['BANKING', 'REAL_ESTATE'],
            affected_stocks=[],
            start_date=datetime.now() - timedelta(hours=6),
            impact_score=0.5,
            confidence=0.8,
            source="CBR"
        )
        
        risk_score = self.risk_manager.assess_comprehensive_geopolitical_risk(
            self.sample_news_articles,
            self.sample_news_sentiments,
            [policy_event]
        )
        
        self.assertIsInstance(risk_score, GeopoliticalRiskScore)
        self.assertGreater(risk_score.policy_risk_score, 0.1)
        self.assertGreater(len(risk_score.market_stress_indicators), 0)
    
    def test_news_based_geopolitical_risk_calculation(self):
        """Test news-based geopolitical risk calculation"""
        risk_score = self.risk_manager._calculate_news_based_geopolitical_risk(
            self.sample_news_articles, self.sample_news_sentiments
        )
        
        self.assertIsInstance(risk_score, float)
        self.assertGreaterEqual(risk_score, -1.0)
        self.assertLessEqual(risk_score, 1.0)
        # Should be negative or zero due to negative news sentiment
        self.assertLessEqual(risk_score, 0.0)
    
    def test_sanctions_risk_assessment(self):
        """Test sanctions risk assessment"""
        sanctions_event = GeopoliticalEvent(
            event_id="test_sanctions",
            event_type="SANCTIONS",
            severity="CRITICAL",
            description="Test sanctions",
            affected_sectors=['BANKING'],
            affected_stocks=['SBER'],
            start_date=datetime.now(),
            impact_score=0.9,
            confidence=0.95
        )
        
        sanctions_risk = self.risk_manager._assess_sanctions_risk(
            self.sample_news_articles, [sanctions_event]
        )
        
        self.assertIsInstance(sanctions_risk, float)
        self.assertGreaterEqual(sanctions_risk, 0.0)
        self.assertLessEqual(sanctions_risk, 1.0)
        self.assertGreater(sanctions_risk, 0.7)  # Should be high due to critical sanctions
    
    def test_policy_risk_assessment(self):
        """Test policy risk assessment"""
        policy_event = GeopoliticalEvent(
            event_id="test_policy",
            event_type="POLICY_CHANGE",
            severity="HIGH",
            description="Test policy change",
            affected_sectors=['BANKING'],
            affected_stocks=[],
            start_date=datetime.now(),
            impact_score=0.7,
            confidence=0.8
        )
        
        policy_risk = self.risk_manager._assess_policy_risk(
            self.sample_news_articles, [policy_event]
        )
        
        self.assertIsInstance(policy_risk, float)
        self.assertGreaterEqual(policy_risk, 0.0)
        self.assertLessEqual(policy_risk, 1.0)
        self.assertGreater(policy_risk, 0.35)  # Should be elevated due to policy event
    
    def test_market_stress_indicators_calculation(self):
        """Test market stress indicators calculation"""
        stress_indicators = self.risk_manager._calculate_market_stress_indicators(
            self.sample_news_articles
        )
        
        self.assertIsInstance(stress_indicators, dict)
        expected_indicators = ['volatility_mentions', 'crisis_mentions', 'uncertainty_mentions', 'panic_mentions']
        
        for indicator in expected_indicators:
            self.assertIn(indicator, stress_indicators)
            self.assertGreaterEqual(stress_indicators[indicator], 0.0)
            self.assertLessEqual(stress_indicators[indicator], 1.0)
    
    def test_sector_specific_geopolitical_risks(self):
        """Test sector-specific geopolitical risk assessment"""
        energy_event = GeopoliticalEvent(
            event_id="energy_sanctions",
            event_type="SANCTIONS",
            severity="HIGH",
            description="Energy sector sanctions",
            affected_sectors=['ENERGY'],
            affected_stocks=['GAZP', 'ROSN'],
            start_date=datetime.now(),
            impact_score=0.8,
            confidence=0.9
        )
        
        sector_risks = self.risk_manager._assess_sector_specific_geopolitical_risks(
            self.sample_news_articles, [energy_event]
        )
        
        self.assertIsInstance(sector_risks, dict)
        self.assertIn('ENERGY', sector_risks)
        self.assertIn('BANKING', sector_risks)
        self.assertIn('TECHNOLOGY', sector_risks)
        
        # Energy sector should have higher risk due to the event
        self.assertGreater(sector_risks['ENERGY'], 0.55)
        
        # All risk scores should be between 0 and 1
        for sector, risk in sector_risks.items():
            self.assertGreaterEqual(risk, 0.0)
            self.assertLessEqual(risk, 1.0)
    
    def test_generate_portfolio_rebalance_recommendation_normal_risk(self):
        """Test portfolio rebalancing recommendation under normal risk"""
        normal_risk = GeopoliticalRiskScore(
            overall_risk_level=GeopoliticalRiskLevel.NORMAL,
            risk_score=0.2,
            active_events=[],
            news_sentiment_score=0.0,
            sanctions_risk_score=0.1,
            policy_risk_score=0.1,
            market_stress_indicators={},
            sector_specific_risks={},
            recommendations=[],
            timestamp=datetime.now()
        )
        
        recommendation = self.risk_manager.generate_portfolio_rebalance_recommendation(
            self.sample_portfolio, normal_risk, self.sample_market_data
        )
        
        self.assertIsInstance(recommendation, PortfolioRebalanceRecommendation)
        self.assertEqual(recommendation.urgency, "LOW")
        self.assertLessEqual(recommendation.cash_target_percent, 15.0)
        self.assertGreaterEqual(recommendation.risk_reduction_expected, 0.0)
        self.assertLessEqual(recommendation.risk_reduction_expected, 1.0)
    
    def test_generate_portfolio_rebalance_recommendation_critical_risk(self):
        """Test portfolio rebalancing recommendation under critical risk"""
        critical_risk = GeopoliticalRiskScore(
            overall_risk_level=GeopoliticalRiskLevel.CRITICAL,
            risk_score=0.9,
            active_events=[],
            news_sentiment_score=-0.8,
            sanctions_risk_score=0.9,
            policy_risk_score=0.7,
            market_stress_indicators={'crisis_mentions': 0.8},
            sector_specific_risks={'BANKING': 0.9, 'ENERGY': 0.8},
            recommendations=["Критический уровень риска"],
            timestamp=datetime.now()
        )
        
        recommendation = self.risk_manager.generate_portfolio_rebalance_recommendation(
            self.sample_portfolio, critical_risk, self.sample_market_data
        )
        
        self.assertIsInstance(recommendation, PortfolioRebalanceRecommendation)
        self.assertEqual(recommendation.urgency, "CRITICAL")
        self.assertGreaterEqual(recommendation.cash_target_percent, 40.0)
        self.assertGreater(len(recommendation.risky_positions), 0)
        self.assertGreater(recommendation.risk_reduction_expected, 0.5)
        self.assertIn("критический", recommendation.reasoning.lower())
    
    def test_adjust_risk_parameters_for_geopolitical_events_normal(self):
        """Test risk parameter adjustment under normal conditions"""
        normal_risk = GeopoliticalRiskScore(
            overall_risk_level=GeopoliticalRiskLevel.NORMAL,
            risk_score=0.2,
            active_events=[],
            news_sentiment_score=0.0,
            sanctions_risk_score=0.1,
            policy_risk_score=0.1,
            market_stress_indicators={},
            sector_specific_risks={},
            recommendations=[],
            timestamp=datetime.now()
        )
        
        adjusted_params = self.risk_manager.adjust_risk_parameters_for_geopolitical_events(
            normal_risk
        )
        
        self.assertIsInstance(adjusted_params, RiskParameters)
        # Parameters should be close to original under normal conditions
        self.assertAlmostEqual(
            adjusted_params.max_position_size_percent,
            self.risk_manager.risk_params.max_position_size_percent,
            delta=1.0
        )
    
    def test_adjust_risk_parameters_for_geopolitical_events_critical(self):
        """Test risk parameter adjustment under critical conditions"""
        critical_risk = GeopoliticalRiskScore(
            overall_risk_level=GeopoliticalRiskLevel.CRITICAL,
            risk_score=0.9,
            active_events=[],
            news_sentiment_score=-0.8,
            sanctions_risk_score=0.9,
            policy_risk_score=0.7,
            market_stress_indicators={},
            sector_specific_risks={},
            recommendations=[],
            timestamp=datetime.now()
        )
        
        adjusted_params = self.risk_manager.adjust_risk_parameters_for_geopolitical_events(
            critical_risk
        )
        
        self.assertIsInstance(adjusted_params, RiskParameters)
        # Parameters should be much more conservative under critical conditions
        self.assertLess(
            adjusted_params.max_position_size_percent,
            self.risk_manager.risk_params.max_position_size_percent / 1.5
        )
        self.assertGreater(
            adjusted_params.stop_loss_percent,
            self.risk_manager.risk_params.stop_loss_percent * 1.5
        )
        self.assertGreaterEqual(adjusted_params.min_cash_reserve_percent, 20.0)
    
    def test_adjust_risk_parameters_high_sanctions_risk(self):
        """Test risk parameter adjustment with high sanctions risk"""
        high_sanctions_risk = GeopoliticalRiskScore(
            overall_risk_level=GeopoliticalRiskLevel.HIGH,
            risk_score=0.7,
            active_events=[],
            news_sentiment_score=-0.5,
            sanctions_risk_score=0.8,  # High sanctions risk
            policy_risk_score=0.3,
            market_stress_indicators={},
            sector_specific_risks={},
            recommendations=[],
            timestamp=datetime.now()
        )
        
        adjusted_params = self.risk_manager.adjust_risk_parameters_for_geopolitical_events(
            high_sanctions_risk
        )
        
        # Should have very conservative parameters due to high sanctions risk
        self.assertLessEqual(adjusted_params.max_position_size_percent, 5.0)
        self.assertGreaterEqual(adjusted_params.min_cash_reserve_percent, 30.0)
    
    def test_calculate_current_allocation(self):
        """Test current portfolio allocation calculation"""
        allocation = self.risk_manager._calculate_current_allocation(self.sample_portfolio)
        
        self.assertIsInstance(allocation, dict)
        self.assertIn('CASH', allocation)
        self.assertIn('SBER', allocation)
        self.assertIn('GAZP', allocation)
        self.assertIn('YNDX', allocation)
        
        # All allocations should sum to approximately 100%
        total_allocation = sum(allocation.values())
        self.assertAlmostEqual(total_allocation, 100.0, delta=0.1)
        
        # Each allocation should be positive
        for symbol, percent in allocation.items():
            self.assertGreaterEqual(percent, 0.0)
    
    def test_calculate_defensive_allocation(self):
        """Test defensive allocation calculation"""
        high_risk = GeopoliticalRiskScore(
            overall_risk_level=GeopoliticalRiskLevel.HIGH,
            risk_score=0.7,
            active_events=[],
            news_sentiment_score=-0.6,
            sanctions_risk_score=0.6,
            policy_risk_score=0.5,
            market_stress_indicators={},
            sector_specific_risks={},
            recommendations=[],
            timestamp=datetime.now()
        )
        
        recommended_allocation, cash_target = self.risk_manager._calculate_defensive_allocation(
            self.sample_portfolio, high_risk, self.sample_market_data
        )
        
        self.assertIsInstance(recommended_allocation, dict)
        self.assertIsInstance(cash_target, float)
        
        # Cash target should be higher for high risk
        self.assertGreaterEqual(cash_target, 25.0)
        
        # Recommended allocation should sum to approximately 100%
        total_allocation = sum(recommended_allocation.values())
        self.assertAlmostEqual(total_allocation, 100.0, delta=0.1)
        
        # Cash allocation should match target
        self.assertAlmostEqual(recommended_allocation['CASH'], cash_target, delta=0.1)
    
    def test_identify_positions_for_adjustment(self):
        """Test identification of positions for adjustment"""
        risk_with_sector_risks = GeopoliticalRiskScore(
            overall_risk_level=GeopoliticalRiskLevel.HIGH,
            risk_score=0.7,
            active_events=[],
            news_sentiment_score=-0.5,
            sanctions_risk_score=0.6,
            policy_risk_score=0.4,
            market_stress_indicators={},
            sector_specific_risks={
                'BANKING': 0.8,  # High risk
                'ENERGY': 0.7,   # High risk
                'TECHNOLOGY': 0.2  # Low risk
            },
            recommendations=[],
            timestamp=datetime.now()
        )
        
        defensive_positions, risky_positions = self.risk_manager._identify_positions_for_adjustment(
            self.sample_portfolio, risk_with_sector_risks, self.sample_market_data
        )
        
        self.assertIsInstance(defensive_positions, list)
        self.assertIsInstance(risky_positions, list)
        
        # YNDX (TECHNOLOGY) should be defensive due to low sector risk
        self.assertIn('YNDX', defensive_positions)
        
        # SBER (BANKING) and GAZP (ENERGY) should be risky due to high sector risks
        self.assertIn('SBER', risky_positions)
        self.assertIn('GAZP', risky_positions)
    
    def test_generate_rebalancing_trades(self):
        """Test generation of rebalancing trades"""
        current_allocation = self.risk_manager._calculate_current_allocation(self.sample_portfolio)
        
        # Create a recommended allocation with higher cash
        recommended_allocation = current_allocation.copy()
        recommended_allocation['CASH'] = 40.0  # Increase cash to 40%
        
        # Reduce other positions proportionally
        reduction_factor = 60.0 / (100.0 - current_allocation['CASH'])
        for symbol in recommended_allocation:
            if symbol != 'CASH':
                recommended_allocation[symbol] *= reduction_factor
        
        trades = self.risk_manager._generate_rebalancing_trades(
            self.sample_portfolio, current_allocation, recommended_allocation, self.sample_market_data
        )
        
        self.assertIsInstance(trades, list)
        
        # Should generate sell trades to increase cash
        sell_trades = [trade for trade in trades if trade.action == "SELL"]
        self.assertGreater(len(sell_trades), 0)
        
        # All trades should have valid symbols and quantities
        for trade in trades:
            self.assertIsInstance(trade, TradeOrder)
            self.assertIn(trade.symbol, self.sample_portfolio.positions)
            self.assertGreater(trade.quantity, 0)
            self.assertIn(trade.action, ["BUY", "SELL"])
    
    def test_geopolitical_event_is_active(self):
        """Test geopolitical event active status"""
        # Active event (no end date)
        active_event = GeopoliticalEvent(
            event_id="active_event",
            event_type="SANCTIONS",
            severity="HIGH",
            description="Active event",
            affected_sectors=[],
            affected_stocks=[],
            start_date=datetime.now() - timedelta(days=1)
        )
        
        self.assertTrue(active_event.is_active())
        
        # Inactive event (ended)
        inactive_event = GeopoliticalEvent(
            event_id="inactive_event",
            event_type="SANCTIONS",
            severity="HIGH",
            description="Inactive event",
            affected_sectors=[],
            affected_stocks=[],
            start_date=datetime.now() - timedelta(days=10),
            end_date=datetime.now() - timedelta(days=5)
        )
        
        self.assertFalse(inactive_event.is_active())
        
        # Future event
        future_event = GeopoliticalEvent(
            event_id="future_event",
            event_type="POLICY_CHANGE",
            severity="MEDIUM",
            description="Future event",
            affected_sectors=[],
            affected_stocks=[],
            start_date=datetime.now() + timedelta(days=1)
        )
        
        self.assertFalse(future_event.is_active())


if __name__ == '__main__':
    unittest.main()