"""
Example demonstrating geopolitical risk assessment functionality
Shows how to assess geopolitical risks and generate portfolio rebalancing recommendations
"""

from datetime import datetime, timedelta
from decimal import Decimal

from russian_trading_bot.services.risk_manager import (
    RussianMarketRiskManager, Portfolio, Position, GeopoliticalEvent
)
from russian_trading_bot.models.market_data import MarketData
from russian_trading_bot.models.news_data import RussianNewsArticle, NewsSentiment


def create_sample_portfolio():
    """Create a sample portfolio for demonstration"""
    return Portfolio(
        positions={
            'SBER': Position(
                symbol='SBER',
                quantity=100,
                entry_price=Decimal('250.0'),
                current_price=Decimal('240.0'),
                market_value=Decimal('24000.0'),
                unrealized_pnl=Decimal('-1000.0'),
                entry_date=datetime.now() - timedelta(days=30),
                sector='BANKING'
            ),
            'GAZP': Position(
                symbol='GAZP',
                quantity=200,
                entry_price=Decimal('180.0'),
                current_price=Decimal('170.0'),
                market_value=Decimal('34000.0'),
                unrealized_pnl=Decimal('-2000.0'),
                entry_date=datetime.now() - timedelta(days=20),
                sector='ENERGY'
            ),
            'YNDX': Position(
                symbol='YNDX',
                quantity=50,
                entry_price=Decimal('2800.0'),
                current_price=Decimal('2750.0'),
                market_value=Decimal('137500.0'),
                unrealized_pnl=Decimal('-2500.0'),
                entry_date=datetime.now() - timedelta(days=10),
                sector='TECHNOLOGY'
            )
        },
        cash_balance=Decimal('50000.0'),
        currency='RUB'
    )


def create_sample_market_data():
    """Create sample market data"""
    return {
        'SBER': MarketData(
            symbol='SBER',
            timestamp=datetime.now(),
            price=Decimal('240.0'),
            volume=1200000,
            bid=Decimal('239.5'),
            ask=Decimal('240.5'),
            change_percent=-4.0
        ),
        'GAZP': MarketData(
            symbol='GAZP',
            timestamp=datetime.now(),
            price=Decimal('170.0'),
            volume=900000,
            bid=Decimal('169.8'),
            ask=Decimal('170.2'),
            change_percent=-5.6
        ),
        'YNDX': MarketData(
            symbol='YNDX',
            timestamp=datetime.now(),
            price=Decimal('2750.0'),
            volume=60000,
            bid=Decimal('2745.0'),
            ask=Decimal('2755.0'),
            change_percent=-1.8
        )
    }


def create_sample_news_and_sentiments():
    """Create sample news articles and sentiments"""
    news_articles = [
        RussianNewsArticle(
            title="Новые санкции ЕС против российских банков",
            content="Европейский союз ввел новые санкции против крупнейших российских банков, включая ограничения на международные операции",
            source="RBC",
            timestamp=datetime.now() - timedelta(hours=2),
            mentioned_stocks=['SBER'],
            category='SANCTIONS'
        ),
        RussianNewsArticle(
            title="Центробанк повысил ключевую ставку до 17%",
            content="ЦБ РФ принял решение о повышении ключевой ставки до 17% годовых в связи с ростом инфляционных рисков",
            source="VEDOMOSTI",
            timestamp=datetime.now() - timedelta(hours=4),
            mentioned_stocks=[],
            category='REGULATORY'
        ),
        RussianNewsArticle(
            title="Газпром сократил поставки газа в Европу",
            content="Газпром объявил о значительном сокращении поставок газа в европейские страны из-за технических проблем",
            source="INTERFAX",
            timestamp=datetime.now() - timedelta(hours=6),
            mentioned_stocks=['GAZP'],
            category='SECTOR_NEWS'
        ),
        RussianNewsArticle(
            title="Яндекс рассматривает продажу зарубежных активов",
            content="Яндекс объявил о планах продажи зарубежных активов в связи с санкционными ограничениями",
            source="RBC",
            timestamp=datetime.now() - timedelta(hours=8),
            mentioned_stocks=['YNDX'],
            category='SECTOR_NEWS'
        )
    ]
    
    news_sentiments = [
        NewsSentiment(
            article_id="RBC_sanctions_news",
            overall_sentiment="VERY_NEGATIVE",
            sentiment_score=-0.85,
            confidence=0.92,
            negative_keywords=['санкции', 'ограничения', 'запрет']
        ),
        NewsSentiment(
            article_id="VEDOMOSTI_cb_news",
            overall_sentiment="NEGATIVE",
            sentiment_score=-0.45,
            confidence=0.78,
            negative_keywords=['повышение', 'ставка', 'инфляция']
        ),
        NewsSentiment(
            article_id="INTERFAX_gazprom_news",
            overall_sentiment="NEGATIVE",
            sentiment_score=-0.65,
            confidence=0.83,
            negative_keywords=['сократил', 'проблемы']
        ),
        NewsSentiment(
            article_id="RBC_yandex_news",
            overall_sentiment="NEGATIVE",
            sentiment_score=-0.55,
            confidence=0.75,
            negative_keywords=['продажа', 'санкции']
        )
    ]
    
    return news_articles, news_sentiments


def create_sample_geopolitical_events():
    """Create sample geopolitical events"""
    return [
        GeopoliticalEvent(
            event_id="sanctions_2024_banking",
            event_type="SANCTIONS",
            severity="HIGH",
            description="Major EU sanctions against Russian banking sector",
            affected_sectors=['BANKING'],
            affected_stocks=['SBER', 'VTBR'],
            start_date=datetime.now() - timedelta(days=2),
            impact_score=0.8,
            confidence=0.9,
            source="EU_SANCTIONS"
        ),
        GeopoliticalEvent(
            event_id="energy_restrictions_2024",
            event_type="SANCTIONS",
            severity="MEDIUM",
            description="Energy sector export restrictions",
            affected_sectors=['ENERGY'],
            affected_stocks=['GAZP', 'ROSN'],
            start_date=datetime.now() - timedelta(days=5),
            impact_score=0.6,
            confidence=0.8,
            source="INTERNATIONAL_RESTRICTIONS"
        )
    ]


def main():
    """Main demonstration function"""
    print("=== Geopolitical Risk Assessment Example ===\n")
    
    # Initialize risk manager
    risk_manager = RussianMarketRiskManager()
    
    # Create sample data
    portfolio = create_sample_portfolio()
    market_data = create_sample_market_data()
    news_articles, news_sentiments = create_sample_news_and_sentiments()
    geopolitical_events = create_sample_geopolitical_events()
    
    print("1. Portfolio Overview:")
    print(f"   Total Value: {portfolio.total_value:,.0f} RUB")
    print(f"   Cash Balance: {portfolio.cash_balance:,.0f} RUB")
    print(f"   Total P&L: {portfolio.total_unrealized_pnl:,.0f} RUB")
    print(f"   Positions: {len(portfolio.positions)}")
    
    for symbol, position in portfolio.positions.items():
        print(f"     {symbol}: {position.quantity} shares, "
              f"{position.market_value:,.0f} RUB, "
              f"P&L: {position.unrealized_pnl:,.0f} RUB ({position.pnl_percent:.1f}%)")
    
    print(f"\n2. News Analysis:")
    print(f"   Total Articles: {len(news_articles)}")
    for i, article in enumerate(news_articles):
        sentiment = news_sentiments[i]
        print(f"     {article.source}: {article.title[:50]}...")
        print(f"       Sentiment: {sentiment.overall_sentiment} ({sentiment.sentiment_score:.2f})")
        print(f"       Mentioned Stocks: {article.mentioned_stocks}")
    
    print(f"\n3. Active Geopolitical Events:")
    for event in geopolitical_events:
        print(f"     {event.event_id}: {event.description}")
        print(f"       Type: {event.event_type}, Severity: {event.severity}")
        print(f"       Affected Sectors: {event.affected_sectors}")
        print(f"       Impact Score: {event.impact_score:.2f}")
    
    # Assess comprehensive geopolitical risk
    print(f"\n4. Comprehensive Geopolitical Risk Assessment:")
    geopolitical_risk = risk_manager.assess_comprehensive_geopolitical_risk(
        news_articles, news_sentiments, geopolitical_events
    )
    
    print(f"   Overall Risk Level: {geopolitical_risk.overall_risk_level.value}")
    print(f"   Risk Score: {geopolitical_risk.risk_score:.3f}")
    print(f"   News Sentiment Score: {geopolitical_risk.news_sentiment_score:.3f}")
    print(f"   Sanctions Risk Score: {geopolitical_risk.sanctions_risk_score:.3f}")
    print(f"   Policy Risk Score: {geopolitical_risk.policy_risk_score:.3f}")
    
    print(f"\n   Market Stress Indicators:")
    for indicator, value in geopolitical_risk.market_stress_indicators.items():
        print(f"     {indicator}: {value:.3f}")
    
    print(f"\n   Sector-Specific Risks:")
    for sector, risk in geopolitical_risk.sector_specific_risks.items():
        if risk > 0:
            print(f"     {sector}: {risk:.3f}")
    
    print(f"\n   Recommendations:")
    for recommendation in geopolitical_risk.recommendations:
        print(f"     • {recommendation}")
    
    # Generate portfolio rebalancing recommendation
    print(f"\n5. Portfolio Rebalancing Recommendation:")
    rebalance_rec = risk_manager.generate_portfolio_rebalance_recommendation(
        portfolio, geopolitical_risk, market_data
    )
    
    print(f"   Urgency: {rebalance_rec.urgency}")
    print(f"   Target Cash: {rebalance_rec.cash_target_percent:.1f}%")
    print(f"   Expected Risk Reduction: {rebalance_rec.risk_reduction_expected:.1f}%")
    
    print(f"\n   Current Allocation:")
    for symbol, percent in rebalance_rec.current_allocation.items():
        print(f"     {symbol}: {percent:.1f}%")
    
    print(f"\n   Recommended Allocation:")
    for symbol, percent in rebalance_rec.recommended_allocation.items():
        print(f"     {symbol}: {percent:.1f}%")
    
    print(f"\n   Defensive Positions: {rebalance_rec.defensive_positions}")
    print(f"   Risky Positions: {rebalance_rec.risky_positions}")
    
    print(f"\n   Trades to Execute:")
    for trade in rebalance_rec.trades_to_execute:
        print(f"     {trade.action} {trade.quantity} shares of {trade.symbol} at {trade.price} RUB")
    
    print(f"\n   Reasoning: {rebalance_rec.reasoning}")
    
    # Adjust risk parameters
    print(f"\n6. Risk Parameter Adjustments:")
    original_params = risk_manager.risk_params
    adjusted_params = risk_manager.adjust_risk_parameters_for_geopolitical_events(geopolitical_risk)
    
    print(f"   Max Position Size: {original_params.max_position_size_percent:.1f}% → {adjusted_params.max_position_size_percent:.1f}%")
    print(f"   Stop Loss: {original_params.stop_loss_percent:.1f}% → {adjusted_params.stop_loss_percent:.1f}%")
    print(f"   Min Cash Reserve: {original_params.min_cash_reserve_percent:.1f}% → {adjusted_params.min_cash_reserve_percent:.1f}%")
    
    print(f"\n=== End of Geopolitical Risk Assessment ===")


if __name__ == "__main__":
    main()