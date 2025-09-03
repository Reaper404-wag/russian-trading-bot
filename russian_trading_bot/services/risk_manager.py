"""
Risk management service for Russian market trading
Implements volatility-adjusted risk controls, geopolitical risk assessment,
and portfolio diversification rules specific to the Russian market.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal
import math
import statistics
from enum import Enum

from ..models.market_data import RussianStock, MarketData, MOEXMarketData
from ..models.news_data import RussianNewsArticle, NewsSentiment, NewsImpactScore


class RiskLevel(Enum):
    """Risk level enumeration"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class GeopoliticalRiskLevel(Enum):
    """Geopolitical risk level enumeration"""
    NORMAL = "NORMAL"
    ELEVATED = "ELEVATED"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class Position:
    """Portfolio position"""
    symbol: str
    quantity: int
    entry_price: Decimal
    current_price: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    entry_date: datetime
    sector: str
    
    @property
    def pnl_percent(self) -> float:
        """Calculate P&L percentage"""
        if self.entry_price == 0:
            return 0.0
        return float((self.current_price - self.entry_price) / self.entry_price * 100)


@dataclass
class Portfolio:
    """Portfolio representation"""
    positions: Dict[str, Position]
    cash_balance: Decimal
    currency: str = "RUB"
    
    @property
    def total_value(self) -> Decimal:
        """Calculate total portfolio value"""
        positions_value = sum(pos.market_value for pos in self.positions.values())
        return positions_value + self.cash_balance
    
    @property
    def total_unrealized_pnl(self) -> Decimal:
        """Calculate total unrealized P&L"""
        return sum(pos.unrealized_pnl for pos in self.positions.values())
    
    @property
    def sector_allocation(self) -> Dict[str, Decimal]:
        """Get sector allocation percentages"""
        total_value = self.total_value
        if total_value == 0:
            return {}
        
        sector_values = {}
        for position in self.positions.values():
            sector = position.sector
            if sector not in sector_values:
                sector_values[sector] = Decimal('0')
            sector_values[sector] += position.market_value
        
        return {
            sector: (value / total_value * 100) 
            for sector, value in sector_values.items()
        }


@dataclass
class RiskParameters:
    """Risk management parameters"""
    max_position_size_percent: float = 10.0  # Max position size as % of portfolio
    max_sector_allocation_percent: float = 30.0  # Max sector allocation
    stop_loss_percent: float = 5.0  # Default stop loss percentage
    max_portfolio_drawdown_percent: float = 15.0  # Max portfolio drawdown
    volatility_adjustment_factor: float = 1.5  # Volatility adjustment multiplier
    geopolitical_risk_multiplier: float = 2.0  # Risk multiplier during high geopolitical risk
    correlation_threshold: float = 0.7  # Max correlation between positions
    min_cash_reserve_percent: float = 10.0  # Minimum cash reserve
    
    # Russian market specific parameters
    ruble_volatility_threshold: float = 5.0  # Daily RUB volatility threshold
    sanctions_risk_multiplier: float = 3.0  # Risk multiplier during sanctions
    oil_price_correlation_factor: float = 0.8  # Oil price correlation adjustment


@dataclass
class RiskAssessment:
    """Risk assessment result"""
    overall_risk_level: RiskLevel
    portfolio_risk_score: float
    geopolitical_risk_level: GeopoliticalRiskLevel
    volatility_risk_score: float
    concentration_risk_score: float
    currency_risk_score: float
    recommendations: List[str]
    risk_factors: Dict[str, float]
    timestamp: datetime


@dataclass
class TradeOrder:
    """Trade order representation"""
    symbol: str
    action: str  # BUY, SELL
    quantity: int
    price: Optional[Decimal] = None
    order_type: str = "MARKET"  # MARKET, LIMIT
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None


@dataclass
class ValidationResult:
    """Trade validation result"""
    is_valid: bool
    risk_score: float
    warnings: List[str]
    errors: List[str]
    recommended_adjustments: Dict[str, Any]


@dataclass
class GeopoliticalEvent:
    """Geopolitical event that affects Russian market"""
    event_id: str
    event_type: str  # 'SANCTIONS', 'POLICY_CHANGE', 'CONFLICT', 'DIPLOMATIC', 'ECONOMIC'
    severity: str  # 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    description: str
    affected_sectors: List[str]
    affected_stocks: List[str]
    start_date: datetime
    end_date: Optional[datetime] = None
    impact_score: float = 0.0  # 0.0 to 1.0
    confidence: float = 0.0  # 0.0 to 1.0
    source: str = ""
    
    def is_active(self) -> bool:
        """Check if event is currently active"""
        now = datetime.now()
        if self.end_date:
            return self.start_date <= now <= self.end_date
        return self.start_date <= now


@dataclass
class GeopoliticalRiskScore:
    """Comprehensive geopolitical risk assessment"""
    overall_risk_level: GeopoliticalRiskLevel
    risk_score: float  # 0.0 to 1.0
    active_events: List[GeopoliticalEvent]
    news_sentiment_score: float  # -1.0 to 1.0
    sanctions_risk_score: float  # 0.0 to 1.0
    policy_risk_score: float  # 0.0 to 1.0
    market_stress_indicators: Dict[str, float]
    sector_specific_risks: Dict[str, float]  # sector -> risk score
    recommendations: List[str]
    timestamp: datetime


@dataclass
class PortfolioRebalanceRecommendation:
    """Portfolio rebalancing recommendation for high-risk periods"""
    current_allocation: Dict[str, float]  # symbol -> weight
    recommended_allocation: Dict[str, float]  # symbol -> weight
    trades_to_execute: List[TradeOrder]
    risk_reduction_expected: float  # Expected risk reduction (0.0 to 1.0)
    cash_target_percent: float
    defensive_positions: List[str]  # Symbols to increase
    risky_positions: List[str]  # Symbols to reduce/eliminate
    reasoning: str
    urgency: str  # 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    timestamp: datetime


class RussianMarketRiskManager:
    """
    Risk management service for Russian market trading
    Implements volatility-adjusted controls and geopolitical risk assessment
    """
    
    def __init__(self, risk_params: Optional[RiskParameters] = None):
        self.risk_params = risk_params or RiskParameters()
        self.historical_volatility_cache: Dict[str, List[float]] = {}
        self.correlation_matrix: Dict[Tuple[str, str], float] = {}
        self.geopolitical_events: List[Dict[str, Any]] = []
        
    def calculate_volatility_adjusted_stop_loss(
        self, 
        symbol: str, 
        entry_price: Decimal,
        historical_prices: List[Decimal],
        lookback_days: int = 20
    ) -> Decimal:
        """
        Calculate stop-loss price adjusted for Russian market volatility
        
        Args:
            symbol: Stock symbol
            entry_price: Entry price for the position
            historical_prices: List of historical prices
            lookback_days: Number of days to look back for volatility calculation
            
        Returns:
            Stop-loss price adjusted for volatility
        """
        if len(historical_prices) < 2:
            # Fallback to default stop loss
            stop_loss_percent = self.risk_params.stop_loss_percent / 100
            return entry_price * (Decimal('1') - Decimal(str(stop_loss_percent)))
        
        # Calculate historical volatility
        returns = []
        for i in range(1, min(len(historical_prices), lookback_days + 1)):
            daily_return = float(historical_prices[i] / historical_prices[i-1] - 1)
            returns.append(daily_return)
        
        if not returns:
            stop_loss_percent = self.risk_params.stop_loss_percent / 100
            return entry_price * (Decimal('1') - Decimal(str(stop_loss_percent)))
        
        # Calculate volatility (standard deviation of returns)
        volatility = statistics.stdev(returns) if len(returns) > 1 else 0.02
        
        # Adjust stop loss based on volatility
        base_stop_loss = self.risk_params.stop_loss_percent / 100
        volatility_adjustment = volatility * self.risk_params.volatility_adjustment_factor
        adjusted_stop_loss = base_stop_loss + volatility_adjustment
        
        # Cap the stop loss at reasonable levels
        adjusted_stop_loss = min(adjusted_stop_loss, 0.25)  # Max 25% stop loss
        adjusted_stop_loss = max(adjusted_stop_loss, 0.02)  # Min 2% stop loss
        
        return entry_price * (Decimal('1') - Decimal(str(adjusted_stop_loss)))
    
    def calculate_position_size(
        self,
        symbol: str,
        entry_price: Decimal,
        portfolio: Portfolio,
        volatility: Optional[float] = None,
        geopolitical_risk_level: GeopoliticalRiskLevel = GeopoliticalRiskLevel.NORMAL
    ) -> int:
        """
        Calculate optimal position size considering ruble volatility and risk factors
        
        Args:
            symbol: Stock symbol
            entry_price: Intended entry price
            portfolio: Current portfolio
            volatility: Stock volatility (optional)
            geopolitical_risk_level: Current geopolitical risk level
            
        Returns:
            Recommended position size in shares
        """
        total_portfolio_value = portfolio.total_value
        if total_portfolio_value <= 0:
            return 0
        
        # Base position size as percentage of portfolio
        base_position_percent = self.risk_params.max_position_size_percent / 100
        
        # Adjust for volatility
        if volatility:
            volatility_adjustment = 1 / (1 + volatility * 2)  # Reduce size for high volatility
            base_position_percent *= volatility_adjustment
        
        # Adjust for geopolitical risk
        geopolitical_multipliers = {
            GeopoliticalRiskLevel.NORMAL: 1.0,
            GeopoliticalRiskLevel.ELEVATED: 0.8,
            GeopoliticalRiskLevel.HIGH: 0.6,
            GeopoliticalRiskLevel.CRITICAL: 0.3
        }
        base_position_percent *= geopolitical_multipliers[geopolitical_risk_level]
        
        # Calculate position value and size
        position_value = total_portfolio_value * Decimal(str(base_position_percent))
        position_size = int(position_value / entry_price)
        
        return max(0, position_size)
    
    def assess_portfolio_risk(
        self,
        portfolio: Portfolio,
        market_data: Dict[str, MarketData],
        news_sentiment: Optional[Dict[str, float]] = None
    ) -> RiskAssessment:
        """
        Assess overall portfolio risk for Russian market conditions
        
        Args:
            portfolio: Current portfolio
            market_data: Current market data for all positions
            news_sentiment: News sentiment scores (optional)
            
        Returns:
            Comprehensive risk assessment
        """
        risk_factors = {}
        recommendations = []
        
        # 1. Concentration risk assessment
        concentration_risk = self._assess_concentration_risk(portfolio)
        risk_factors['concentration'] = concentration_risk
        
        if concentration_risk > 0.7:
            recommendations.append("Reduce position concentration - consider diversifying")
        
        # 2. Volatility risk assessment
        volatility_risk = self._assess_volatility_risk(portfolio, market_data)
        risk_factors['volatility'] = volatility_risk
        
        if volatility_risk > 0.8:
            recommendations.append("High volatility detected - consider reducing position sizes")
        
        # 3. Currency risk (RUB volatility)
        currency_risk = self._assess_currency_risk()
        risk_factors['currency'] = currency_risk
        
        if currency_risk > 0.6:
            recommendations.append("High ruble volatility - consider hedging currency exposure")
        
        # 4. Geopolitical risk assessment
        geopolitical_risk_level = self._assess_geopolitical_risk(news_sentiment)
        geopolitical_risk_score = self._geopolitical_risk_to_score(geopolitical_risk_level)
        risk_factors['geopolitical'] = geopolitical_risk_score
        
        if geopolitical_risk_level in [GeopoliticalRiskLevel.HIGH, GeopoliticalRiskLevel.CRITICAL]:
            recommendations.append("High geopolitical risk - consider defensive positioning")
        
        # 5. Sector concentration risk
        sector_risk = self._assess_sector_concentration_risk(portfolio)
        risk_factors['sector_concentration'] = sector_risk
        
        if sector_risk > 0.7:
            recommendations.append("High sector concentration - diversify across sectors")
        
        # Calculate overall risk score
        overall_risk_score = (
            concentration_risk * 0.25 +
            volatility_risk * 0.25 +
            currency_risk * 0.2 +
            geopolitical_risk_score * 0.2 +
            sector_risk * 0.1
        )
        
        # Determine overall risk level
        if overall_risk_score < 0.3:
            overall_risk_level = RiskLevel.LOW
        elif overall_risk_score < 0.6:
            overall_risk_level = RiskLevel.MEDIUM
        elif overall_risk_score < 0.8:
            overall_risk_level = RiskLevel.HIGH
        else:
            overall_risk_level = RiskLevel.CRITICAL
        
        return RiskAssessment(
            overall_risk_level=overall_risk_level,
            portfolio_risk_score=overall_risk_score,
            geopolitical_risk_level=geopolitical_risk_level,
            volatility_risk_score=volatility_risk,
            concentration_risk_score=concentration_risk,
            currency_risk_score=currency_risk,
            recommendations=recommendations,
            risk_factors=risk_factors,
            timestamp=datetime.now()
        )
    
    def validate_trade(
        self,
        order: TradeOrder,
        portfolio: Portfolio,
        market_data: Dict[str, MarketData],
        current_risk_assessment: Optional[RiskAssessment] = None
    ) -> ValidationResult:
        """
        Validate a trade order against risk management rules
        
        Args:
            order: Trade order to validate
            portfolio: Current portfolio
            market_data: Current market data
            current_risk_assessment: Current risk assessment (optional)
            
        Returns:
            Validation result with recommendations
        """
        warnings = []
        errors = []
        recommended_adjustments = {}
        
        # Get current market data for the symbol
        symbol_data = market_data.get(order.symbol)
        if not symbol_data:
            errors.append(f"No market data available for {order.symbol}")
            return ValidationResult(
                is_valid=False,
                risk_score=1.0,
                warnings=warnings,
                errors=errors,
                recommended_adjustments=recommended_adjustments
            )
        
        current_price = symbol_data.price
        
        # 1. Position size validation
        if order.action == "BUY":
            position_value = current_price * order.quantity
            portfolio_value = portfolio.total_value
            
            if portfolio_value > 0:
                position_percent = float(position_value / portfolio_value * 100)
                
                if position_percent > self.risk_params.max_position_size_percent:
                    errors.append(
                        f"Position size ({position_percent:.1f}%) exceeds maximum "
                        f"({self.risk_params.max_position_size_percent}%)"
                    )
                    # Recommend smaller position size
                    max_value = portfolio_value * Decimal(str(self.risk_params.max_position_size_percent / 100))
                    recommended_quantity = int(max_value / current_price)
                    recommended_adjustments['quantity'] = recommended_quantity
        
        # 2. Cash availability validation
        if order.action == "BUY":
            required_cash = current_price * order.quantity
            available_cash = portfolio.cash_balance
            
            if required_cash > available_cash:
                errors.append(f"Insufficient cash: need {required_cash} RUB, have {available_cash} RUB")
        
        # 3. Risk level validation
        if current_risk_assessment:
            if current_risk_assessment.overall_risk_level == RiskLevel.CRITICAL:
                if order.action == "BUY":
                    errors.append("Portfolio risk level is CRITICAL - new buy orders not recommended")
                else:
                    warnings.append("Consider reducing positions due to critical risk level")
        
        # 4. Sector concentration validation
        if order.action == "BUY":
            # This would require sector information - simplified for now
            sector_allocation = portfolio.sector_allocation
            # Assume we can get sector from symbol (would need lookup in real implementation)
            # For now, just warn if any sector is over-allocated
            max_sector_allocation = max(sector_allocation.values()) if sector_allocation else 0
            if max_sector_allocation > self.risk_params.max_sector_allocation_percent:
                warnings.append(f"High sector concentration detected ({max_sector_allocation:.1f}%)")
        
        # Calculate risk score for this trade
        risk_score = self._calculate_trade_risk_score(order, portfolio, symbol_data)
        
        # Determine if trade is valid
        is_valid = len(errors) == 0 and risk_score < 0.8
        
        return ValidationResult(
            is_valid=is_valid,
            risk_score=risk_score,
            warnings=warnings,
            errors=errors,
            recommended_adjustments=recommended_adjustments
        )
    
    def _assess_concentration_risk(self, portfolio: Portfolio) -> float:
        """Assess portfolio concentration risk"""
        if not portfolio.positions:
            return 0.0
        
        total_value = portfolio.total_value
        if total_value <= 0:
            return 0.0
        
        # Calculate position weights
        position_weights = [
            float(pos.market_value / total_value) 
            for pos in portfolio.positions.values()
        ]
        
        # Calculate Herfindahl-Hirschman Index (HHI) for concentration
        hhi = sum(weight ** 2 for weight in position_weights)
        
        # Normalize to 0-1 scale (1 = maximum concentration)
        # HHI ranges from 1/n (perfectly diversified) to 1 (fully concentrated)
        n_positions = len(position_weights)
        min_hhi = 1 / n_positions if n_positions > 0 else 1
        normalized_hhi = (hhi - min_hhi) / (1 - min_hhi) if min_hhi < 1 else 0
        
        return min(1.0, normalized_hhi)
    
    def _assess_volatility_risk(
        self, 
        portfolio: Portfolio, 
        market_data: Dict[str, MarketData]
    ) -> float:
        """Assess portfolio volatility risk"""
        if not portfolio.positions:
            return 0.0
        
        total_volatility_weighted = 0.0
        total_weight = 0.0
        
        for symbol, position in portfolio.positions.items():
            if symbol in market_data:
                # Get cached volatility or calculate simple proxy
                volatility = self._get_symbol_volatility(symbol, market_data[symbol])
                weight = float(position.market_value / portfolio.total_value)
                
                total_volatility_weighted += volatility * weight
                total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        portfolio_volatility = total_volatility_weighted / total_weight
        
        # Normalize to 0-1 scale (assuming 50% annual volatility as maximum)
        return min(1.0, portfolio_volatility / 0.5)
    
    def _assess_currency_risk(self) -> float:
        """Assess RUB currency risk based on recent volatility"""
        # This would typically use real USD/RUB exchange rate data
        # For now, return a moderate risk level as placeholder
        return 0.4
    
    def _assess_geopolitical_risk(
        self, 
        news_sentiment: Optional[Dict[str, float]] = None
    ) -> GeopoliticalRiskLevel:
        """Assess geopolitical risk level based on news and events"""
        # This would analyze news sentiment and geopolitical events
        # For now, return normal risk as placeholder
        if news_sentiment:
            avg_sentiment = sum(news_sentiment.values()) / len(news_sentiment)
            if avg_sentiment < -0.7:
                return GeopoliticalRiskLevel.CRITICAL
            elif avg_sentiment < -0.4:
                return GeopoliticalRiskLevel.HIGH
            elif avg_sentiment < -0.2:
                return GeopoliticalRiskLevel.ELEVATED
        
        return GeopoliticalRiskLevel.NORMAL
    
    def _assess_sector_concentration_risk(self, portfolio: Portfolio) -> float:
        """Assess sector concentration risk"""
        sector_allocation = portfolio.sector_allocation
        if not sector_allocation:
            return 0.0
        
        # Find maximum sector allocation
        max_allocation = max(sector_allocation.values())
        
        # Normalize to 0-1 scale
        return min(1.0, float(max_allocation) / 100.0)
    
    def _geopolitical_risk_to_score(self, risk_level: GeopoliticalRiskLevel) -> float:
        """Convert geopolitical risk level to numeric score"""
        mapping = {
            GeopoliticalRiskLevel.NORMAL: 0.2,
            GeopoliticalRiskLevel.ELEVATED: 0.4,
            GeopoliticalRiskLevel.HIGH: 0.7,
            GeopoliticalRiskLevel.CRITICAL: 1.0
        }
        return mapping[risk_level]
    
    def _get_symbol_volatility(self, symbol: str, market_data: MarketData) -> float:
        """Get or calculate symbol volatility"""
        # This would typically use historical price data
        # For now, return a placeholder based on price changes
        if hasattr(market_data, 'change_percent') and market_data.change_percent:
            return abs(float(market_data.change_percent)) / 100.0
        return 0.02  # Default 2% daily volatility
    
    def _calculate_trade_risk_score(
        self, 
        order: TradeOrder, 
        portfolio: Portfolio, 
        market_data: MarketData
    ) -> float:
        """Calculate risk score for a specific trade"""
        risk_score = 0.0
        
        # Position size risk
        if order.action == "BUY":
            position_value = market_data.price * order.quantity
            portfolio_value = portfolio.total_value
            
            if portfolio_value > 0:
                position_percent = float(position_value / portfolio_value)
                if position_percent > self.risk_params.max_position_size_percent / 100:
                    risk_score += 0.3
        
        # Volatility risk
        volatility = self._get_symbol_volatility(order.symbol, market_data)
        if volatility > 0.05:  # 5% daily volatility threshold
            risk_score += 0.2
        
        # Market timing risk (simplified)
        if hasattr(market_data, 'change_percent') and market_data.change_percent:
            daily_change = abs(float(market_data.change_percent))
            if daily_change > 5:  # High daily movement
                risk_score += 0.1
        
        return min(1.0, risk_score)
    
    def assess_comprehensive_geopolitical_risk(
        self,
        news_articles: List[RussianNewsArticle],
        news_sentiments: List[NewsSentiment],
        active_events: Optional[List[GeopoliticalEvent]] = None
    ) -> GeopoliticalRiskScore:
        """
        Comprehensive geopolitical risk assessment for Russian market
        
        Args:
            news_articles: Recent Russian news articles
            news_sentiments: Sentiment analysis results for news
            active_events: Currently active geopolitical events
            
        Returns:
            Comprehensive geopolitical risk assessment
        """
        if active_events is None:
            active_events = []
        
        # 1. Analyze news sentiment for geopolitical indicators
        news_sentiment_score = self._calculate_news_based_geopolitical_risk(
            news_articles, news_sentiments
        )
        
        # 2. Assess sanctions risk
        sanctions_risk_score = self._assess_sanctions_risk(news_articles, active_events)
        
        # 3. Assess policy risk
        policy_risk_score = self._assess_policy_risk(news_articles, active_events)
        
        # 4. Calculate market stress indicators
        market_stress_indicators = self._calculate_market_stress_indicators(news_articles)
        
        # 5. Assess sector-specific risks
        sector_specific_risks = self._assess_sector_specific_geopolitical_risks(
            news_articles, active_events
        )
        
        # 6. Calculate overall risk score
        overall_risk_score = (
            abs(news_sentiment_score) * 0.3 +  # News sentiment (absolute value)
            sanctions_risk_score * 0.35 +      # Sanctions risk (highest weight)
            policy_risk_score * 0.2 +          # Policy risk
            max(market_stress_indicators.values()) * 0.15 if market_stress_indicators else 0.0
        )
        
        # 7. Determine risk level
        if overall_risk_score < 0.25:
            risk_level = GeopoliticalRiskLevel.NORMAL
        elif overall_risk_score < 0.5:
            risk_level = GeopoliticalRiskLevel.ELEVATED
        elif overall_risk_score < 0.75:
            risk_level = GeopoliticalRiskLevel.HIGH
        else:
            risk_level = GeopoliticalRiskLevel.CRITICAL
        
        # 8. Generate recommendations
        recommendations = self._generate_geopolitical_risk_recommendations(
            risk_level, sanctions_risk_score, policy_risk_score, sector_specific_risks
        )
        
        return GeopoliticalRiskScore(
            overall_risk_level=risk_level,
            risk_score=overall_risk_score,
            active_events=active_events,
            news_sentiment_score=news_sentiment_score,
            sanctions_risk_score=sanctions_risk_score,
            policy_risk_score=policy_risk_score,
            market_stress_indicators=market_stress_indicators,
            sector_specific_risks=sector_specific_risks,
            recommendations=recommendations,
            timestamp=datetime.now()
        )
    
    def generate_portfolio_rebalance_recommendation(
        self,
        portfolio: Portfolio,
        geopolitical_risk: GeopoliticalRiskScore,
        market_data: Dict[str, MarketData]
    ) -> PortfolioRebalanceRecommendation:
        """
        Generate portfolio rebalancing recommendations for high-risk periods
        
        Args:
            portfolio: Current portfolio
            geopolitical_risk: Current geopolitical risk assessment
            market_data: Current market data
            
        Returns:
            Portfolio rebalancing recommendation
        """
        current_allocation = self._calculate_current_allocation(portfolio)
        
        # Determine urgency based on risk level
        urgency_mapping = {
            GeopoliticalRiskLevel.NORMAL: "LOW",
            GeopoliticalRiskLevel.ELEVATED: "MEDIUM", 
            GeopoliticalRiskLevel.HIGH: "HIGH",
            GeopoliticalRiskLevel.CRITICAL: "CRITICAL"
        }
        urgency = urgency_mapping[geopolitical_risk.overall_risk_level]
        
        # Calculate recommended allocation based on risk level
        recommended_allocation, cash_target = self._calculate_defensive_allocation(
            portfolio, geopolitical_risk, market_data
        )
        
        # Identify positions to adjust
        defensive_positions, risky_positions = self._identify_positions_for_adjustment(
            portfolio, geopolitical_risk, market_data
        )
        
        # Generate specific trades
        trades_to_execute = self._generate_rebalancing_trades(
            portfolio, current_allocation, recommended_allocation, market_data
        )
        
        # Calculate expected risk reduction
        risk_reduction_expected = self._calculate_expected_risk_reduction(
            geopolitical_risk, len(trades_to_execute)
        )
        
        # Generate reasoning
        reasoning = self._generate_rebalancing_reasoning(
            geopolitical_risk, defensive_positions, risky_positions, cash_target
        )
        
        return PortfolioRebalanceRecommendation(
            current_allocation=current_allocation,
            recommended_allocation=recommended_allocation,
            trades_to_execute=trades_to_execute,
            risk_reduction_expected=risk_reduction_expected,
            cash_target_percent=cash_target,
            defensive_positions=defensive_positions,
            risky_positions=risky_positions,
            reasoning=reasoning,
            urgency=urgency,
            timestamp=datetime.now()
        )
    
    def calculate_stock_correlation(
        self,
        symbol1: str,
        symbol2: str,
        price_history1: List[Decimal],
        price_history2: List[Decimal],
        min_periods: int = 20
    ) -> Optional[float]:
        """
        Calculate correlation coefficient between two Russian stocks
        
        Args:
            symbol1: First stock symbol
            symbol2: Second stock symbol
            price_history1: Price history for first stock
            price_history2: Price history for second stock
            min_periods: Minimum number of periods required
            
        Returns:
            Correlation coefficient (-1 to 1) or None if insufficient data
        """
        if len(price_history1) < min_periods or len(price_history2) < min_periods:
            return None
        
        if len(price_history1) != len(price_history2):
            # Align the arrays to the same length
            min_length = min(len(price_history1), len(price_history2))
            price_history1 = price_history1[-min_length:]
            price_history2 = price_history2[-min_length:]
        
        # Calculate returns
        returns1 = []
        returns2 = []
        
        for i in range(1, len(price_history1)):
            ret1 = float(price_history1[i] / price_history1[i-1] - 1)
            ret2 = float(price_history2[i] / price_history2[i-1] - 1)
            returns1.append(ret1)
            returns2.append(ret2)
        
        if len(returns1) < 2:
            return None
        
        # Calculate correlation coefficient
        mean1 = statistics.mean(returns1)
        mean2 = statistics.mean(returns2)
        
        numerator = sum((r1 - mean1) * (r2 - mean2) for r1, r2 in zip(returns1, returns2))
        
        sum_sq1 = sum((r1 - mean1) ** 2 for r1 in returns1)
        sum_sq2 = sum((r2 - mean2) ** 2 for r2 in returns2)
        
        if sum_sq1 == 0 or sum_sq2 == 0:
            return 0.0
        
        denominator = math.sqrt(sum_sq1 * sum_sq2)
        
        if denominator == 0:
            return 0.0
        
        correlation = numerator / denominator
        return max(-1.0, min(1.0, correlation))  # Clamp to [-1, 1]
    
    def build_correlation_matrix(
        self,
        symbols: List[str],
        price_histories: Dict[str, List[Decimal]]
    ) -> Dict[Tuple[str, str], float]:
        """
        Build correlation matrix for Russian stocks
        
        Args:
            symbols: List of stock symbols
            price_histories: Dictionary mapping symbols to price histories
            
        Returns:
            Dictionary mapping symbol pairs to correlation coefficients
        """
        correlation_matrix = {}
        
        for i, symbol1 in enumerate(symbols):
            for j, symbol2 in enumerate(symbols):
                if i <= j:  # Only calculate upper triangle and diagonal
                    if symbol1 == symbol2:
                        correlation_matrix[(symbol1, symbol2)] = 1.0
                    else:
                        if symbol1 in price_histories and symbol2 in price_histories:
                            correlation = self.calculate_stock_correlation(
                                symbol1, symbol2,
                                price_histories[symbol1],
                                price_histories[symbol2]
                            )
                            if correlation is not None:
                                correlation_matrix[(symbol1, symbol2)] = correlation
                                correlation_matrix[(symbol2, symbol1)] = correlation  # Symmetric
        
        return correlation_matrix
    
    def check_sector_diversification_rules(
        self,
        portfolio: Portfolio,
        stock_sectors: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Check sector diversification rules for Russian market
        
        Args:
            portfolio: Current portfolio
            stock_sectors: Dictionary mapping symbols to sectors
            
        Returns:
            Dictionary with diversification analysis results
        """
        total_value = portfolio.total_value
        if total_value <= 0:
            return {
                'is_compliant': True,
                'violations': [],
                'sector_allocations': {},
                'recommendations': []
            }
        
        # Calculate sector allocations
        sector_allocations = {}
        sector_values = {}
        
        for symbol, position in portfolio.positions.items():
            sector = stock_sectors.get(symbol, 'UNKNOWN')
            if sector not in sector_values:
                sector_values[sector] = Decimal('0')
            sector_values[sector] += position.market_value
        
        # Convert to percentages
        for sector, value in sector_values.items():
            sector_allocations[sector] = float(value / total_value * 100)
        
        # Check for violations
        violations = []
        recommendations = []
        
        # Russian market sector limits (more conservative for volatile market)
        sector_limits = {
            'OIL_GAS': 25.0,  # Oil & Gas - major Russian sector but volatile
            'BANKING': 20.0,  # Banking - significant but sanctions-sensitive
            'METALS_MINING': 20.0,  # Metals & Mining - important Russian sector
            'ENERGY': 25.0,  # Energy sector
            'FINANCIALS': 25.0,  # Financial services
            'MATERIALS': 20.0,  # Materials
            'INDUSTRIALS': 15.0,  # Industrials
            'CONSUMER_DISCRETIONARY': 15.0,  # Consumer discretionary
            'CONSUMER_STAPLES': 15.0,  # Consumer staples
            'INFORMATION_TECHNOLOGY': 10.0,  # IT - smaller in Russian market
            'COMMUNICATION_SERVICES': 15.0,  # Telecom
            'UTILITIES': 15.0,  # Utilities
            'REAL_ESTATE': 10.0,  # Real estate
            'HEALTH_CARE': 10.0,  # Healthcare
            'TELECOM': 15.0,  # Telecommunications
            'UNKNOWN': 5.0  # Unknown sectors - limit exposure
        }
        
        for sector, allocation in sector_allocations.items():
            limit = sector_limits.get(sector, 10.0)  # Default 10% for unlisted sectors
            if allocation > limit:
                violations.append({
                    'type': 'SECTOR_CONCENTRATION',
                    'sector': sector,
                    'current_allocation': allocation,
                    'limit': limit,
                    'excess': allocation - limit
                })
                recommendations.append(
                    f"Reduce {sector} sector allocation from {allocation:.1f}% to below {limit}%"
                )
        
        # Check for over-concentration in Russian-specific high-risk sectors
        high_risk_sectors = ['OIL_GAS', 'BANKING', 'METALS_MINING']
        high_risk_total = sum(
            sector_allocations.get(sector, 0) for sector in high_risk_sectors
        )
        
        if high_risk_total > 50.0:  # Max 50% in high-risk Russian sectors
            violations.append({
                'type': 'HIGH_RISK_SECTOR_CONCENTRATION',
                'sectors': high_risk_sectors,
                'total_allocation': high_risk_total,
                'limit': 50.0,
                'excess': high_risk_total - 50.0
            })
            recommendations.append(
                f"Reduce combined allocation in high-risk sectors (Oil/Gas, Banking, Metals) "
                f"from {high_risk_total:.1f}% to below 50%"
            )
        
        is_compliant = len(violations) == 0
        
        return {
            'is_compliant': is_compliant,
            'violations': violations,
            'sector_allocations': sector_allocations,
            'sector_limits': sector_limits,
            'high_risk_sectors_total': high_risk_total,
            'recommendations': recommendations
        }
    
    def check_position_size_limits(
        self,
        portfolio: Portfolio,
        individual_stock_limit_percent: float = 8.0,
        blue_chip_limit_percent: float = 12.0,
        blue_chip_symbols: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Check individual position size limits for Russian stocks
        
        Args:
            portfolio: Current portfolio
            individual_stock_limit_percent: Max allocation per individual stock
            blue_chip_limit_percent: Max allocation for blue-chip Russian stocks
            blue_chip_symbols: List of blue-chip Russian stock symbols
            
        Returns:
            Dictionary with position size analysis results
        """
        if blue_chip_symbols is None:
            # Major Russian blue-chip stocks
            blue_chip_symbols = [
                'SBER',  # Sberbank
                'GAZP',  # Gazprom
                'LKOH',  # Lukoil
                'ROSN',  # Rosneft
                'NVTK',  # Novatek
                'YNDX',  # Yandex
                'GMKN',  # Nornickel
                'MGNT',  # Magnit
                'MTSS',  # MTS
                'VTBR',  # VTB Bank
                'ALRS',  # Alrosa
                'SNGS',  # Surgutneftegas
                'TATN',  # Tatneft
                'NLMK',  # NLMK
                'MAGN'   # MMK
            ]
        
        total_value = portfolio.total_value
        if total_value <= 0:
            return {
                'is_compliant': True,
                'violations': [],
                'position_allocations': {},
                'recommendations': []
            }
        
        violations = []
        recommendations = []
        position_allocations = {}
        
        for symbol, position in portfolio.positions.items():
            allocation_percent = float(position.market_value / total_value * 100)
            position_allocations[symbol] = allocation_percent
            
            # Determine appropriate limit
            if symbol in blue_chip_symbols:
                limit = blue_chip_limit_percent
                stock_type = "blue-chip"
            else:
                limit = individual_stock_limit_percent
                stock_type = "individual"
            
            if allocation_percent > limit:
                violations.append({
                    'type': 'POSITION_SIZE_LIMIT',
                    'symbol': symbol,
                    'stock_type': stock_type,
                    'current_allocation': allocation_percent,
                    'limit': limit,
                    'excess': allocation_percent - limit,
                    'market_value': position.market_value
                })
                recommendations.append(
                    f"Reduce {symbol} position from {allocation_percent:.1f}% to below {limit}% "
                    f"({stock_type} stock limit)"
                )
        
        is_compliant = len(violations) == 0
        
        return {
            'is_compliant': is_compliant,
            'violations': violations,
            'position_allocations': position_allocations,
            'blue_chip_symbols': blue_chip_symbols,
            'limits': {
                'individual_stock': individual_stock_limit_percent,
                'blue_chip_stock': blue_chip_limit_percent
            },
            'recommendations': recommendations
        }
    
    def check_correlation_limits(
        self,
        portfolio: Portfolio,
        correlation_matrix: Dict[Tuple[str, str], float],
        max_correlation: float = 0.7,
        max_high_correlation_pairs: int = 3
    ) -> Dict[str, Any]:
        """
        Check correlation limits between Russian stocks in portfolio
        
        Args:
            portfolio: Current portfolio
            correlation_matrix: Correlation matrix for stocks
            max_correlation: Maximum allowed correlation between positions
            max_high_correlation_pairs: Maximum number of high-correlation pairs allowed
            
        Returns:
            Dictionary with correlation analysis results
        """
        violations = []
        recommendations = []
        high_correlation_pairs = []
        
        symbols = list(portfolio.positions.keys())
        
        # Check all pairs of positions
        for i, symbol1 in enumerate(symbols):
            for j, symbol2 in enumerate(symbols[i+1:], i+1):
                correlation = correlation_matrix.get((symbol1, symbol2))
                if correlation is None:
                    correlation = correlation_matrix.get((symbol2, symbol1))
                
                if correlation is not None and abs(correlation) > max_correlation:
                    pos1_value = portfolio.positions[symbol1].market_value
                    pos2_value = portfolio.positions[symbol2].market_value
                    total_value = portfolio.total_value
                    
                    combined_allocation = float((pos1_value + pos2_value) / total_value * 100)
                    
                    high_correlation_pairs.append({
                        'symbol1': symbol1,
                        'symbol2': symbol2,
                        'correlation': correlation,
                        'combined_allocation': combined_allocation,
                        'pos1_allocation': float(pos1_value / total_value * 100),
                        'pos2_allocation': float(pos2_value / total_value * 100)
                    })
        
        # Check if too many high-correlation pairs
        if len(high_correlation_pairs) > max_high_correlation_pairs:
            violations.append({
                'type': 'EXCESSIVE_CORRELATION',
                'high_correlation_pairs': len(high_correlation_pairs),
                'limit': max_high_correlation_pairs,
                'excess': len(high_correlation_pairs) - max_high_correlation_pairs
            })
            recommendations.append(
                f"Reduce number of highly correlated position pairs from "
                f"{len(high_correlation_pairs)} to {max_high_correlation_pairs} or fewer"
            )
        
        # Check individual high-correlation pairs with significant allocations
        for pair in high_correlation_pairs:
            if pair['combined_allocation'] > 20.0:  # Combined allocation > 20%
                violations.append({
                    'type': 'HIGH_CORRELATION_LARGE_POSITIONS',
                    'symbol1': pair['symbol1'],
                    'symbol2': pair['symbol2'],
                    'correlation': pair['correlation'],
                    'combined_allocation': pair['combined_allocation']
                })
                recommendations.append(
                    f"Reduce allocation in highly correlated stocks {pair['symbol1']} and "
                    f"{pair['symbol2']} (correlation: {pair['correlation']:.2f}, "
                    f"combined: {pair['combined_allocation']:.1f}%)"
                )
        
        is_compliant = len(violations) == 0
        
        return {
            'is_compliant': is_compliant,
            'violations': violations,
            'high_correlation_pairs': high_correlation_pairs,
            'correlation_threshold': max_correlation,
            'max_pairs_allowed': max_high_correlation_pairs,
            'recommendations': recommendations
        }
    
    def enforce_diversification_rules(
        self,
        portfolio: Portfolio,
        stock_sectors: Dict[str, str],
        price_histories: Dict[str, List[Decimal]],
        correlation_matrix: Optional[Dict[Tuple[str, str], float]] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive diversification rule enforcement for Russian market
        
        Args:
            portfolio: Current portfolio
            stock_sectors: Dictionary mapping symbols to sectors
            price_histories: Price histories for correlation calculation
            correlation_matrix: Pre-calculated correlation matrix (optional)
            
        Returns:
            Comprehensive diversification analysis and recommendations
        """
        # Build correlation matrix if not provided
        if correlation_matrix is None:
            symbols = list(portfolio.positions.keys())
            correlation_matrix = self.build_correlation_matrix(symbols, price_histories)
        
        # Run all diversification checks
        sector_check = self.check_sector_diversification_rules(portfolio, stock_sectors)
        position_check = self.check_position_size_limits(portfolio)
        correlation_check = self.check_correlation_limits(portfolio, correlation_matrix)
        
        # Combine results
        all_violations = (
            sector_check['violations'] + 
            position_check['violations'] + 
            correlation_check['violations']
        )
        
        all_recommendations = (
            sector_check['recommendations'] + 
            position_check['recommendations'] + 
            correlation_check['recommendations']
        )
        
        is_fully_compliant = (
            sector_check['is_compliant'] and 
            position_check['is_compliant'] and 
            correlation_check['is_compliant']
        )
        
        # Calculate overall diversification score (0-1, higher is better)
        diversification_score = self._calculate_diversification_score(
            sector_check, position_check, correlation_check
        )
        
        return {
            'is_fully_compliant': is_fully_compliant,
            'diversification_score': diversification_score,
            'total_violations': len(all_violations),
            'all_violations': all_violations,
            'all_recommendations': all_recommendations,
            'sector_analysis': sector_check,
            'position_analysis': position_check,
            'correlation_analysis': correlation_check,
            'correlation_matrix': correlation_matrix,
            'timestamp': datetime.now()
        }
    
    def _calculate_diversification_score(
        self,
        sector_check: Dict[str, Any],
        position_check: Dict[str, Any],
        correlation_check: Dict[str, Any]
    ) -> float:
        """
        Calculate overall diversification score (0-1, higher is better)
        
        Args:
            sector_check: Sector diversification check results
            position_check: Position size check results
            correlation_check: Correlation check results
            
        Returns:
            Diversification score between 0 and 1
        """
        # Start with perfect score
        score = 1.0
        
        # Penalize sector violations
        for violation in sector_check['violations']:
            if violation['type'] == 'SECTOR_CONCENTRATION':
                penalty = min(0.2, violation['excess'] / 100)  # Max 20% penalty
                score -= penalty
            elif violation['type'] == 'HIGH_RISK_SECTOR_CONCENTRATION':
                penalty = min(0.3, violation['excess'] / 100)  # Max 30% penalty
                score -= penalty
        
        # Penalize position size violations
        for violation in position_check['violations']:
            if violation['type'] == 'POSITION_SIZE_LIMIT':
                penalty = min(0.15, violation['excess'] / 100)  # Max 15% penalty
                score -= penalty
        
        # Penalize correlation violations
        for violation in correlation_check['violations']:
            if violation['type'] == 'EXCESSIVE_CORRELATION':
                score -= 0.1  # 10% penalty for too many correlated pairs
            elif violation['type'] == 'HIGH_CORRELATION_LARGE_POSITIONS':
                score -= 0.15  # 15% penalty for large correlated positions
        
        return max(0.0, score)  # Ensure score doesn't go below 0
    
    def adjust_risk_parameters_for_geopolitical_events(
        self,
        geopolitical_risk: GeopoliticalRiskScore
    ) -> RiskParameters:
        """
        Adjust risk parameters based on current geopolitical conditions
        
        Args:
            geopolitical_risk: Current geopolitical risk assessment
            
        Returns:
            Adjusted risk parameters
        """
        adjusted_params = RiskParameters(
            max_position_size_percent=self.risk_params.max_position_size_percent,
            max_sector_allocation_percent=self.risk_params.max_sector_allocation_percent,
            stop_loss_percent=self.risk_params.stop_loss_percent,
            max_portfolio_drawdown_percent=self.risk_params.max_portfolio_drawdown_percent,
            volatility_adjustment_factor=self.risk_params.volatility_adjustment_factor,
            geopolitical_risk_multiplier=self.risk_params.geopolitical_risk_multiplier,
            correlation_threshold=self.risk_params.correlation_threshold,
            min_cash_reserve_percent=self.risk_params.min_cash_reserve_percent,
            ruble_volatility_threshold=self.risk_params.ruble_volatility_threshold,
            sanctions_risk_multiplier=self.risk_params.sanctions_risk_multiplier,
            oil_price_correlation_factor=self.risk_params.oil_price_correlation_factor
        )
        
        # Adjust parameters based on risk level
        risk_multipliers = {
            GeopoliticalRiskLevel.NORMAL: 1.0,
            GeopoliticalRiskLevel.ELEVATED: 1.2,
            GeopoliticalRiskLevel.HIGH: 1.5,
            GeopoliticalRiskLevel.CRITICAL: 2.0
        }
        
        multiplier = risk_multipliers[geopolitical_risk.overall_risk_level]
        
        # Reduce position sizes during high risk
        adjusted_params.max_position_size_percent /= multiplier
        adjusted_params.max_sector_allocation_percent /= multiplier
        
        # Increase stop losses during high risk
        adjusted_params.stop_loss_percent *= multiplier
        
        # Increase cash reserves during high risk
        adjusted_params.min_cash_reserve_percent *= multiplier
        
        # Apply sanctions-specific adjustments
        if geopolitical_risk.sanctions_risk_score > 0.7:
            adjusted_params.max_position_size_percent *= 0.5  # Halve position sizes
            adjusted_params.min_cash_reserve_percent = max(
                adjusted_params.min_cash_reserve_percent, 30.0
            )  # Minimum 30% cash during high sanctions risk
        
        return adjusted_params
    
    def _calculate_news_based_geopolitical_risk(
        self,
        news_articles: List[RussianNewsArticle],
        news_sentiments: List[NewsSentiment]
    ) -> float:
        """Calculate geopolitical risk based on news sentiment analysis"""
        if not news_articles or not news_sentiments:
            return 0.0
        
        # Keywords that indicate geopolitical risk
        geopolitical_keywords = {
            'санкции', 'санкций', 'санкциями', 'embargo', 'эмбарго',
            'конфликт', 'война', 'военный', 'военные', 'военных',
            'политический', 'политика', 'политике', 'дипломатия',
            'международный', 'международные', 'международных',
            'запрет', 'ограничения', 'блокировка', 'заморозка',
            'отношения', 'переговоры', 'соглашение', 'договор',
            'кризис', 'напряженность', 'противостояние'
        }
        
        geopolitical_sentiment_scores = []
        
        # Create sentiment lookup
        sentiment_lookup = {s.article_id: s for s in news_sentiments}
        
        for article in news_articles:
            article_text = (article.title + " " + article.content).lower()
            
            # Check if article contains geopolitical keywords
            geopolitical_keyword_count = sum(
                1 for keyword in geopolitical_keywords 
                if keyword in article_text
            )
            
            if geopolitical_keyword_count >= 2:  # At least 2 geopolitical keywords
                # Get sentiment for this article
                article_id = f"{article.source}_{hash(article.title)}"
                if article_id in sentiment_lookup:
                    sentiment = sentiment_lookup[article_id]
                    # Weight by keyword count and confidence
                    weighted_score = (
                        sentiment.sentiment_score * 
                        sentiment.confidence * 
                        min(geopolitical_keyword_count / 5.0, 1.0)
                    )
                    geopolitical_sentiment_scores.append(weighted_score)
        
        if not geopolitical_sentiment_scores:
            return 0.0
        
        # Calculate weighted average sentiment
        avg_sentiment = sum(geopolitical_sentiment_scores) / len(geopolitical_sentiment_scores)
        
        return avg_sentiment  # Returns -1.0 to 1.0
    
    def _assess_sanctions_risk(
        self,
        news_articles: List[RussianNewsArticle],
        active_events: List[GeopoliticalEvent]
    ) -> float:
        """Assess sanctions-related risk"""
        sanctions_risk = 0.0
        
        # Check active sanctions events
        for event in active_events:
            if event.event_type == 'SANCTIONS' and event.is_active():
                severity_multipliers = {
                    'LOW': 0.2,
                    'MEDIUM': 0.5,
                    'HIGH': 0.8,
                    'CRITICAL': 1.0
                }
                event_risk = (
                    event.impact_score * 
                    severity_multipliers.get(event.severity, 0.5) * 
                    event.confidence
                )
                sanctions_risk = max(sanctions_risk, event_risk)
        
        # Analyze news for sanctions mentions
        sanctions_keywords = {
            'санкции', 'санкций', 'санкциями', 'санкционный',
            'ограничения', 'запрет', 'заморозка', 'блокировка',
            'embargo', 'эмбарго', 'blacklist', 'черный список'
        }
        
        sanctions_mentions = 0
        total_articles = len(news_articles)
        
        for article in news_articles:
            article_text = (article.title + " " + article.content).lower()
            if any(keyword in article_text for keyword in sanctions_keywords):
                sanctions_mentions += 1
        
        # Calculate news-based sanctions risk
        if total_articles > 0:
            news_sanctions_risk = min(sanctions_mentions / total_articles, 1.0)
            sanctions_risk = max(sanctions_risk, news_sanctions_risk * 0.7)
        
        return min(sanctions_risk, 1.0)
    
    def _assess_policy_risk(
        self,
        news_articles: List[RussianNewsArticle],
        active_events: List[GeopoliticalEvent]
    ) -> float:
        """Assess policy-related risk"""
        policy_risk = 0.0
        
        # Check active policy events
        for event in active_events:
            if event.event_type in ['POLICY_CHANGE', 'ECONOMIC'] and event.is_active():
                severity_multipliers = {
                    'LOW': 0.15,
                    'MEDIUM': 0.4,
                    'HIGH': 0.7,
                    'CRITICAL': 1.0
                }
                event_risk = (
                    event.impact_score * 
                    severity_multipliers.get(event.severity, 0.4) * 
                    event.confidence
                )
                policy_risk = max(policy_risk, event_risk)
        
        # Analyze news for policy-related mentions
        policy_keywords = {
            'центробанк', 'цб', 'ставка', 'процентная',
            'налог', 'налоги', 'налогов', 'налоговый',
            'регулирование', 'регулятор', 'закон', 'законы',
            'правительство', 'министерство', 'минфин',
            'политика', 'реформа', 'изменения', 'нововведения'
        }
        
        policy_mentions = 0
        negative_policy_mentions = 0
        
        for article in news_articles:
            article_text = (article.title + " " + article.content).lower()
            if any(keyword in article_text for keyword in policy_keywords):
                policy_mentions += 1
                
                # Check for negative context
                negative_indicators = {
                    'повышение', 'увеличение', 'ужесточение',
                    'ограничение', 'запрет', 'штраф', 'санкции'
                }
                if any(indicator in article_text for indicator in negative_indicators):
                    negative_policy_mentions += 1
        
        # Calculate policy risk based on negative mentions
        if policy_mentions > 0:
            negative_ratio = negative_policy_mentions / policy_mentions
            news_policy_risk = negative_ratio * 0.6
            policy_risk = max(policy_risk, news_policy_risk)
        
        return min(policy_risk, 1.0)
    
    def _calculate_market_stress_indicators(
        self,
        news_articles: List[RussianNewsArticle]
    ) -> Dict[str, float]:
        """Calculate various market stress indicators from news"""
        stress_indicators = {
            'volatility_mentions': 0.0,
            'crisis_mentions': 0.0,
            'uncertainty_mentions': 0.0,
            'panic_mentions': 0.0
        }
        
        if not news_articles:
            return stress_indicators
        
        # Keywords for different stress indicators
        stress_keywords = {
            'volatility_mentions': {
                'волатильность', 'колебания', 'нестабильность',
                'резкий', 'скачок', 'падение', 'рост'
            },
            'crisis_mentions': {
                'кризис', 'крах', 'обвал', 'коллапс',
                'катастрофа', 'провал', 'банкротство'
            },
            'uncertainty_mentions': {
                'неопределенность', 'неясность', 'сомнения',
                'риски', 'опасения', 'беспокойство'
            },
            'panic_mentions': {
                'паника', 'страх', 'тревога', 'массовый',
                'распродажа', 'бегство', 'отток'
            }
        }
        
        total_articles = len(news_articles)
        
        for indicator, keywords in stress_keywords.items():
            mentions = 0
            for article in news_articles:
                article_text = (article.title + " " + article.content).lower()
                if any(keyword in article_text for keyword in keywords):
                    mentions += 1
            
            stress_indicators[indicator] = mentions / total_articles if total_articles > 0 else 0.0
        
        return stress_indicators
    
    def _assess_sector_specific_geopolitical_risks(
        self,
        news_articles: List[RussianNewsArticle],
        active_events: List[GeopoliticalEvent]
    ) -> Dict[str, float]:
        """Assess geopolitical risks for specific sectors"""
        sector_risks = {
            'ENERGY': 0.0,
            'BANKING': 0.0,
            'TECHNOLOGY': 0.0,
            'METALS': 0.0,
            'TELECOMMUNICATIONS': 0.0,
            'RETAIL': 0.0,
            'TRANSPORTATION': 0.0
        }
        
        # Sector-specific keywords
        sector_keywords = {
            'ENERGY': {'нефть', 'газ', 'энергия', 'газпром', 'роснефть', 'новатэк'},
            'BANKING': {'банк', 'банки', 'сбербанк', 'втб', 'кредит', 'финансы'},
            'TECHNOLOGY': {'технологии', 'it', 'яндекс', 'интернет', 'софт'},
            'METALS': {'металл', 'сталь', 'алюминий', 'норникель', 'нлмк'},
            'TELECOMMUNICATIONS': {'связь', 'телеком', 'мтс', 'мегафон', 'билайн'},
            'RETAIL': {'ритейл', 'торговля', 'магнит', 'x5', 'лента'},
            'TRANSPORTATION': {'транспорт', 'авиация', 'аэрофлот', 'жд', 'логистика'}
        }
        
        # Check active events for sector-specific impacts
        for event in active_events:
            if event.is_active():
                for sector in event.affected_sectors:
                    if sector in sector_risks:
                        severity_multipliers = {
                            'LOW': 0.2,
                            'MEDIUM': 0.5,
                            'HIGH': 0.8,
                            'CRITICAL': 1.0
                        }
                        event_risk = (
                            event.impact_score * 
                            severity_multipliers.get(event.severity, 0.5) * 
                            event.confidence
                        )
                        sector_risks[sector] = max(sector_risks[sector], event_risk)
        
        # Analyze news for sector-specific mentions
        if news_articles:
            for sector, keywords in sector_keywords.items():
                negative_mentions = 0
                total_mentions = 0
                
                for article in news_articles:
                    article_text = (article.title + " " + article.content).lower()
                    
                    # Check if article mentions this sector
                    if any(keyword in article_text for keyword in keywords):
                        total_mentions += 1
                        
                        # Check for negative context
                        negative_indicators = {
                            'санкции', 'ограничения', 'запрет', 'проблемы',
                            'кризис', 'падение', 'убытки', 'штраф'
                        }
                        if any(indicator in article_text for indicator in negative_indicators):
                            negative_mentions += 1
                
                # Calculate sector risk from news
                if total_mentions > 0:
                    news_risk = (negative_mentions / total_mentions) * 0.6
                    sector_risks[sector] = max(sector_risks[sector], news_risk)
        
        return sector_risks
    
    def _generate_geopolitical_risk_recommendations(
        self,
        risk_level: GeopoliticalRiskLevel,
        sanctions_risk: float,
        policy_risk: float,
        sector_risks: Dict[str, float]
    ) -> List[str]:
        """Generate recommendations based on geopolitical risk assessment"""
        recommendations = []
        
        # General recommendations based on risk level
        if risk_level == GeopoliticalRiskLevel.CRITICAL:
            recommendations.extend([
                "КРИТИЧЕСКИЙ уровень геополитического риска - рассмотрите переход в защитные активы",
                "Увеличьте долю денежных средств до 40-50% портфеля",
                "Избегайте новых позиций в высокорисковых секторах"
            ])
        elif risk_level == GeopoliticalRiskLevel.HIGH:
            recommendations.extend([
                "ВЫСОКИЙ уровень геополитического риска - снизьте размеры позиций",
                "Увеличьте долю денежных средств до 25-30% портфеля",
                "Рассмотрите хеджирование валютных рисков"
            ])
        elif risk_level == GeopoliticalRiskLevel.ELEVATED:
            recommendations.extend([
                "ПОВЫШЕННЫЙ уровень геополитического риска - будьте осторожны",
                "Увеличьте долю денежных средств до 15-20% портфеля",
                "Мониторьте новости более внимательно"
            ])
        
        # Sanctions-specific recommendations
        if sanctions_risk > 0.7:
            recommendations.extend([
                "Высокий риск санкций - избегайте санкционных секторов",
                "Рассмотрите диверсификацию в менее подверженные санкциям активы",
                "Подготовьтесь к возможным ограничениям торговли"
            ])
        
        # Policy-specific recommendations
        if policy_risk > 0.6:
            recommendations.extend([
                "Высокий риск изменений политики - следите за решениями ЦБ и правительства",
                "Рассмотрите влияние возможных изменений налогового законодательства"
            ])
        
        # Sector-specific recommendations
        high_risk_sectors = [
            sector for sector, risk in sector_risks.items() 
            if risk > 0.7
        ]
        if high_risk_sectors:
            recommendations.append(
                f"Высокий риск в секторах: {', '.join(high_risk_sectors)} - "
                "рассмотрите снижение экспозиции"
            )
        
        return recommendations
    
    def _calculate_current_allocation(self, portfolio: Portfolio) -> Dict[str, float]:
        """Calculate current portfolio allocation as percentages"""
        total_value = portfolio.total_value
        if total_value <= 0:
            return {}
        
        allocation = {}
        for symbol, position in portfolio.positions.items():
            allocation[symbol] = float(position.market_value / total_value * 100)
        
        # Add cash allocation
        allocation['CASH'] = float(portfolio.cash_balance / total_value * 100)
        
        return allocation
    
    def _calculate_defensive_allocation(
        self,
        portfolio: Portfolio,
        geopolitical_risk: GeopoliticalRiskScore,
        market_data: Dict[str, MarketData]
    ) -> Tuple[Dict[str, float], float]:
        """Calculate recommended defensive allocation"""
        current_allocation = self._calculate_current_allocation(portfolio)
        
        # Determine target cash percentage based on risk level
        cash_targets = {
            GeopoliticalRiskLevel.NORMAL: 10.0,
            GeopoliticalRiskLevel.ELEVATED: 20.0,
            GeopoliticalRiskLevel.HIGH: 30.0,
            GeopoliticalRiskLevel.CRITICAL: 50.0
        }
        target_cash_percent = cash_targets[geopolitical_risk.overall_risk_level]
        
        # Calculate recommended allocation
        recommended_allocation = current_allocation.copy()
        
        # Increase cash allocation
        recommended_allocation['CASH'] = target_cash_percent
        
        # Reduce allocations proportionally for other positions
        remaining_percent = 100.0 - target_cash_percent
        current_positions_percent = 100.0 - current_allocation.get('CASH', 0.0)
        
        if current_positions_percent > 0:
            reduction_factor = remaining_percent / current_positions_percent
            
            for symbol in recommended_allocation:
                if symbol != 'CASH':
                    recommended_allocation[symbol] *= reduction_factor
        
        return recommended_allocation, target_cash_percent
    
    def _identify_positions_for_adjustment(
        self,
        portfolio: Portfolio,
        geopolitical_risk: GeopoliticalRiskScore,
        market_data: Dict[str, MarketData]
    ) -> Tuple[List[str], List[str]]:
        """Identify defensive and risky positions"""
        defensive_positions = []
        risky_positions = []
        
        # Define defensive sectors (less affected by geopolitical risk)
        defensive_sectors = {'UTILITIES', 'CONSUMER_STAPLES', 'HEALTHCARE'}
        
        # Define risky sectors (more affected by geopolitical risk)
        risky_sectors = {'ENERGY', 'BANKING', 'TECHNOLOGY', 'METALS'}
        
        for symbol, position in portfolio.positions.items():
            sector = position.sector
            
            # Check sector-specific risks
            sector_risk = geopolitical_risk.sector_specific_risks.get(sector, 0.0)
            
            if sector in defensive_sectors or sector_risk < 0.3:
                defensive_positions.append(symbol)
            elif sector in risky_sectors or sector_risk > 0.6:
                risky_positions.append(symbol)
        
        return defensive_positions, risky_positions
    
    def _generate_rebalancing_trades(
        self,
        portfolio: Portfolio,
        current_allocation: Dict[str, float],
        recommended_allocation: Dict[str, float],
        market_data: Dict[str, MarketData]
    ) -> List[TradeOrder]:
        """Generate specific trades for rebalancing"""
        trades = []
        total_value = portfolio.total_value
        
        for symbol in current_allocation:
            if symbol == 'CASH':
                continue
                
            current_percent = current_allocation.get(symbol, 0.0)
            recommended_percent = recommended_allocation.get(symbol, 0.0)
            
            difference_percent = recommended_percent - current_percent
            
            # Only generate trades for significant differences (>1%)
            if abs(difference_percent) > 1.0:
                difference_value = total_value * Decimal(str(difference_percent / 100))
                
                if symbol in market_data:
                    current_price = market_data[symbol].price
                    quantity = int(abs(difference_value) / current_price)
                    
                    if quantity > 0:
                        action = "BUY" if difference_percent > 0 else "SELL"
                        
                        trade = TradeOrder(
                            symbol=symbol,
                            action=action,
                            quantity=quantity,
                            price=current_price,
                            order_type="MARKET"
                        )
                        trades.append(trade)
        
        return trades
    
    def _calculate_expected_risk_reduction(
        self,
        geopolitical_risk: GeopoliticalRiskScore,
        num_trades: int
    ) -> float:
        """Calculate expected risk reduction from rebalancing"""
        base_reduction = 0.2  # 20% base risk reduction
        
        # More trades generally mean more risk reduction
        trade_factor = min(num_trades * 0.05, 0.3)  # Max 30% additional reduction
        
        # Higher initial risk allows for more reduction
        risk_factor = geopolitical_risk.risk_score * 0.4
        
        total_reduction = base_reduction + trade_factor + risk_factor
        
        return min(total_reduction, 0.8)  # Cap at 80% risk reduction
    
    def _generate_rebalancing_reasoning(
        self,
        geopolitical_risk: GeopoliticalRiskScore,
        defensive_positions: List[str],
        risky_positions: List[str],
        cash_target: float
    ) -> str:
        """Generate human-readable reasoning for rebalancing"""
        reasoning_parts = []
        
        # Risk level explanation
        risk_explanations = {
            GeopoliticalRiskLevel.NORMAL: "Нормальный уровень геополитического риска",
            GeopoliticalRiskLevel.ELEVATED: "Повышенный уровень геополитического риска",
            GeopoliticalRiskLevel.HIGH: "Высокий уровень геополитического риска",
            GeopoliticalRiskLevel.CRITICAL: "Критический уровень геополитического риска"
        }
        
        reasoning_parts.append(
            f"{risk_explanations[geopolitical_risk.overall_risk_level]} "
            f"(оценка: {geopolitical_risk.risk_score:.2f})"
        )
        
        # Cash target explanation
        reasoning_parts.append(
            f"Рекомендуется увеличить долю денежных средств до {cash_target:.1f}% "
            "для снижения рыночного риска"
        )
        
        # Sector-specific explanations
        if geopolitical_risk.sanctions_risk_score > 0.6:
            reasoning_parts.append(
                f"Высокий риск санкций ({geopolitical_risk.sanctions_risk_score:.2f}) - "
                "снижение экспозиции в подверженных санкциям секторах"
            )
        
        # Position adjustments
        if risky_positions:
            reasoning_parts.append(
                f"Снижение позиций в рисковых активах: {', '.join(risky_positions[:3])}"
            )
        
        if defensive_positions:
            reasoning_parts.append(
                f"Сохранение/увеличение защитных позиций: {', '.join(defensive_positions[:3])}"
            )
        
        return ". ".join(reasoning_parts)
    
    def validate_sector_diversification(
        self,
        portfolio: Portfolio,
        new_trade: Optional[TradeOrder] = None
    ) -> Tuple[bool, List[str], Dict[str, float]]:
        """
        Validate portfolio sector diversification rules for Russian market
        
        Args:
            portfolio: Current portfolio
            new_trade: Optional new trade to validate
            
        Returns:
            Tuple of (is_valid, warnings, sector_allocations)
        """
        warnings = []
        
        # Calculate current sector allocations
        sector_allocations = self._calculate_sector_allocations(portfolio, new_trade)
        
        # Russian market sector limits (adapted for local market characteristics)
        russian_sector_limits = {
            'ENERGY': 35.0,  # Higher limit due to dominance in Russian market
            'BANKING': 25.0,  # Major sector in Russian market
            'METALS': 20.0,   # Important sector for Russian economy
            'TECHNOLOGY': 15.0,
            'TELECOMMUNICATIONS': 15.0,
            'RETAIL': 15.0,
            'TRANSPORTATION': 10.0,
            'UTILITIES': 10.0,
            'HEALTHCARE': 10.0,
            'REAL_ESTATE': 10.0,
            'OTHER': 10.0
        }
        
        is_valid = True
        
        for sector, allocation in sector_allocations.items():
            limit = russian_sector_limits.get(sector, self.risk_params.max_sector_allocation_percent)
            
            if allocation > limit:
                is_valid = False
                warnings.append(
                    f"Превышен лимит сектора {sector}: {allocation:.1f}% > {limit:.1f}%"
                )
            elif allocation > limit * 0.8:  # Warning at 80% of limit
                warnings.append(
                    f"Приближение к лимиту сектора {sector}: {allocation:.1f}% (лимит {limit:.1f}%)"
                )
        
        return is_valid, warnings, sector_allocations
    
    def calculate_stock_correlations(
        self,
        symbols: List[str],
        historical_data: Dict[str, List[Decimal]],
        lookback_days: int = 60
    ) -> Dict[Tuple[str, str], float]:
        """
        Calculate correlation matrix for Russian stocks
        
        Args:
            symbols: List of stock symbols
            historical_data: Historical price data for each symbol
            lookback_days: Number of days to look back for correlation calculation
            
        Returns:
            Dictionary mapping symbol pairs to correlation coefficients
        """
        correlations = {}
        
        # Calculate returns for each symbol
        returns_data = {}
        for symbol in symbols:
            if symbol in historical_data and len(historical_data[symbol]) > 1:
                prices = historical_data[symbol][-lookback_days:]
                returns = []
                for i in range(1, len(prices)):
                    daily_return = float(prices[i] / prices[i-1] - 1)
                    returns.append(daily_return)
                returns_data[symbol] = returns
        
        # Calculate pairwise correlations
        for i, symbol1 in enumerate(symbols):
            for j, symbol2 in enumerate(symbols):
                if i >= j:  # Skip duplicate pairs and self-correlation
                    continue
                    
                if symbol1 in returns_data and symbol2 in returns_data:
                    returns1 = returns_data[symbol1]
                    returns2 = returns_data[symbol2]
                    
                    # Ensure same length
                    min_length = min(len(returns1), len(returns2))
                    if min_length < 10:  # Need at least 10 data points
                        continue
                        
                    returns1 = returns1[-min_length:]
                    returns2 = returns2[-min_length:]
                    
                    # Calculate correlation coefficient
                    correlation = self._calculate_correlation(returns1, returns2)
                    correlations[(symbol1, symbol2)] = correlation
                    correlations[(symbol2, symbol1)] = correlation  # Symmetric
        
        return correlations
    
    def validate_correlation_limits(
        self,
        portfolio: Portfolio,
        correlations: Dict[Tuple[str, str], float],
        new_trade: Optional[TradeOrder] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate portfolio correlation limits to ensure diversification
        
        Args:
            portfolio: Current portfolio
            correlations: Correlation matrix between stocks
            new_trade: Optional new trade to validate
            
        Returns:
            Tuple of (is_valid, warnings)
        """
        warnings = []
        is_valid = True
        
        # Get portfolio positions (including potential new trade)
        positions = portfolio.positions.copy()
        if new_trade and new_trade.action == "BUY":
            if new_trade.symbol in positions:
                # Increase existing position
                current_pos = positions[new_trade.symbol]
                new_quantity = current_pos.quantity + new_trade.quantity
                new_market_value = new_quantity * new_trade.price
                positions[new_trade.symbol] = Position(
                    symbol=new_trade.symbol,
                    quantity=new_quantity,
                    entry_price=current_pos.entry_price,
                    current_price=new_trade.price,
                    market_value=new_market_value,
                    unrealized_pnl=new_market_value - (current_pos.entry_price * new_quantity),
                    entry_date=current_pos.entry_date,
                    sector=current_pos.sector
                )
            else:
                # New position
                market_value = new_trade.quantity * new_trade.price
                positions[new_trade.symbol] = Position(
                    symbol=new_trade.symbol,
                    quantity=new_trade.quantity,
                    entry_price=new_trade.price,
                    current_price=new_trade.price,
                    market_value=market_value,
                    unrealized_pnl=Decimal('0'),
                    entry_date=datetime.now(),
                    sector="UNKNOWN"  # Would need sector lookup in real implementation
                )
        
        # Calculate position weights
        total_value = sum(pos.market_value for pos in positions.values()) + portfolio.cash_balance
        position_weights = {
            symbol: float(pos.market_value / total_value)
            for symbol, pos in positions.items()
        }
        
        # Check correlations between significant positions (>5% of portfolio)
        significant_positions = {
            symbol: weight for symbol, weight in position_weights.items()
            if weight > 0.05
        }
        
        high_correlation_pairs = []
        
        for symbol1 in significant_positions:
            for symbol2 in significant_positions:
                if symbol1 >= symbol2:  # Skip duplicates and self
                    continue
                    
                correlation_key = (symbol1, symbol2)
                if correlation_key in correlations:
                    correlation = correlations[correlation_key]
                    
                    if abs(correlation) > self.risk_params.correlation_threshold:
                        weight1 = position_weights[symbol1]
                        weight2 = position_weights[symbol2]
                        combined_weight = weight1 + weight2
                        
                        high_correlation_pairs.append((symbol1, symbol2, correlation, combined_weight))
                        
                        if combined_weight > 0.3:  # Combined weight > 30%
                            is_valid = False
                            warnings.append(
                                f"Высокая корреляция между {symbol1} и {symbol2}: "
                                f"{correlation:.2f} (общий вес {combined_weight:.1%})"
                            )
                        elif combined_weight > 0.2:  # Warning at 20%
                            warnings.append(
                                f"Внимание: корреляция {symbol1}-{symbol2}: "
                                f"{correlation:.2f} (общий вес {combined_weight:.1%})"
                            )
        
        return is_valid, warnings
    
    def validate_position_size_limits(
        self,
        portfolio: Portfolio,
        new_trade: Optional[TradeOrder] = None
    ) -> Tuple[bool, List[str], Dict[str, float]]:
        """
        Validate maximum position size limits for individual Russian stocks
        
        Args:
            portfolio: Current portfolio
            new_trade: Optional new trade to validate
            
        Returns:
            Tuple of (is_valid, warnings, position_sizes)
        """
        warnings = []
        is_valid = True
        
        # Calculate position sizes including potential new trade
        position_sizes = self._calculate_position_sizes(portfolio, new_trade)
        
        # Russian market position size limits (adapted for market liquidity)
        russian_position_limits = {
            # Blue chip stocks (higher liquidity) - can have larger positions
            'SBER': 15.0,    # Sberbank
            'GAZP': 15.0,    # Gazprom
            'LKOH': 12.0,    # Lukoil
            'ROSN': 12.0,    # Rosneft
            'NVTK': 10.0,    # Novatek
            'GMKN': 10.0,    # Nornickel
            'YNDX': 8.0,     # Yandex
            'MTSS': 8.0,     # MTS
            'MGNT': 8.0,     # Magnit
            'VTBR': 8.0,     # VTB
            
            # Default limits for other stocks based on market cap tiers
            'LARGE_CAP': 10.0,    # Large cap stocks
            'MID_CAP': 7.0,       # Mid cap stocks  
            'SMALL_CAP': 5.0,     # Small cap stocks
            'MICRO_CAP': 3.0      # Micro cap stocks
        }
        
        for symbol, size_percent in position_sizes.items():
            # Get specific limit or use default based on stock category
            limit = russian_position_limits.get(symbol)
            
            if limit is None:
                # Determine category based on symbol (simplified logic)
                if self._is_large_cap_stock(symbol):
                    limit = russian_position_limits['LARGE_CAP']
                elif self._is_mid_cap_stock(symbol):
                    limit = russian_position_limits['MID_CAP']
                elif self._is_small_cap_stock(symbol):
                    limit = russian_position_limits['SMALL_CAP']
                else:
                    limit = russian_position_limits['MICRO_CAP']
            
            if size_percent > limit:
                is_valid = False
                warnings.append(
                    f"Превышен лимит позиции {symbol}: {size_percent:.1f}% > {limit:.1f}%"
                )
            elif size_percent > limit * 0.8:  # Warning at 80% of limit
                warnings.append(
                    f"Приближение к лимиту позиции {symbol}: {size_percent:.1f}% (лимит {limit:.1f}%)"
                )
        
        return is_valid, warnings, position_sizes
    
    def enforce_diversification_rules(
        self,
        portfolio: Portfolio,
        new_trade: TradeOrder,
        historical_data: Dict[str, List[Decimal]]
    ) -> ValidationResult:
        """
        Comprehensive diversification rule enforcement for Russian market
        
        Args:
            portfolio: Current portfolio
            new_trade: Trade to validate
            historical_data: Historical price data for correlation analysis
            
        Returns:
            Validation result with diversification-specific checks
        """
        warnings = []
        errors = []
        recommended_adjustments = {}
        
        # 1. Validate sector diversification
        sector_valid, sector_warnings, sector_allocations = self.validate_sector_diversification(
            portfolio, new_trade
        )
        warnings.extend(sector_warnings)
        if not sector_valid:
            errors.extend([w for w in sector_warnings if "Превышен лимит" in w])
        
        # 2. Validate position size limits
        position_valid, position_warnings, position_sizes = self.validate_position_size_limits(
            portfolio, new_trade
        )
        warnings.extend(position_warnings)
        if not position_valid:
            errors.extend([w for w in position_warnings if "Превышен лимит" in w])
        
        # 3. Validate correlation limits
        if len(portfolio.positions) > 0:
            symbols = list(portfolio.positions.keys()) + [new_trade.symbol]
            correlations = self.calculate_stock_correlations(symbols, historical_data)
            
            correlation_valid, correlation_warnings = self.validate_correlation_limits(
                portfolio, correlations, new_trade
            )
            warnings.extend(correlation_warnings)
            if not correlation_valid:
                errors.extend([w for w in correlation_warnings if "Высокая корреляция" in w])
        
        # 4. Generate recommended adjustments
        if errors:
            # Suggest position size reduction if limits exceeded
            if new_trade.action == "BUY":
                current_position_size = position_sizes.get(new_trade.symbol, 0.0)
                if current_position_size > self.risk_params.max_position_size_percent:
                    # Calculate maximum allowed quantity
                    total_value = portfolio.total_value + (new_trade.quantity * new_trade.price)
                    max_position_value = total_value * Decimal(str(self.risk_params.max_position_size_percent / 100))
                    
                    current_position_value = portfolio.positions.get(new_trade.symbol)
                    if current_position_value:
                        max_additional_value = max_position_value - current_position_value.market_value
                    else:
                        max_additional_value = max_position_value
                    
                    if max_additional_value > 0 and new_trade.price:
                        max_quantity = int(max_additional_value / new_trade.price)
                        recommended_adjustments['quantity'] = max(0, max_quantity)
                    else:
                        recommended_adjustments['quantity'] = 0
        
        # Calculate overall diversification risk score
        diversification_risk_score = self._calculate_diversification_risk_score(
            sector_allocations, position_sizes, len(errors)
        )
        
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            risk_score=diversification_risk_score,
            warnings=warnings,
            errors=errors,
            recommended_adjustments=recommended_adjustments
        )
    
    def _calculate_sector_allocations(
        self,
        portfolio: Portfolio,
        new_trade: Optional[TradeOrder] = None
    ) -> Dict[str, float]:
        """Calculate sector allocations including potential new trade"""
        sector_values = {}
        total_value = portfolio.total_value
        
        # Add current positions
        for position in portfolio.positions.values():
            sector = position.sector
            if sector not in sector_values:
                sector_values[sector] = Decimal('0')
            sector_values[sector] += position.market_value
        
        # Add potential new trade
        if new_trade and new_trade.action == "BUY":
            trade_value = new_trade.quantity * new_trade.price
            total_value += trade_value
            
            # Would need sector lookup in real implementation
            trade_sector = "UNKNOWN"  # Placeholder
            if trade_sector not in sector_values:
                sector_values[trade_sector] = Decimal('0')
            sector_values[trade_sector] += trade_value
        
        # Convert to percentages
        if total_value > 0:
            return {
                sector: float(value / total_value * 100)
                for sector, value in sector_values.items()
            }
        return {}
    
    def _calculate_position_sizes(
        self,
        portfolio: Portfolio,
        new_trade: Optional[TradeOrder] = None
    ) -> Dict[str, float]:
        """Calculate position sizes as percentage of portfolio"""
        position_sizes = {}
        total_value = portfolio.total_value
        
        # Add current positions
        for symbol, position in portfolio.positions.items():
            position_sizes[symbol] = float(position.market_value / total_value * 100) if total_value > 0 else 0.0
        
        # Adjust for potential new trade
        if new_trade:
            trade_value = new_trade.quantity * new_trade.price
            
            if new_trade.action == "BUY":
                total_value += trade_value
                current_value = portfolio.positions.get(new_trade.symbol)
                if current_value:
                    new_position_value = current_value.market_value + trade_value
                else:
                    new_position_value = trade_value
                
                position_sizes[new_trade.symbol] = float(new_position_value / total_value * 100)
            
            elif new_trade.action == "SELL":
                if new_trade.symbol in portfolio.positions:
                    current_pos = portfolio.positions[new_trade.symbol]
                    remaining_quantity = max(0, current_pos.quantity - new_trade.quantity)
                    remaining_value = remaining_quantity * new_trade.price
                    
                    if remaining_quantity > 0:
                        position_sizes[new_trade.symbol] = float(remaining_value / total_value * 100)
                    else:
                        position_sizes[new_trade.symbol] = 0.0
        
        return position_sizes
    
    def _calculate_correlation(self, returns1: List[float], returns2: List[float]) -> float:
        """Calculate Pearson correlation coefficient between two return series"""
        if len(returns1) != len(returns2) or len(returns1) < 2:
            return 0.0
        
        n = len(returns1)
        
        # Calculate means
        mean1 = sum(returns1) / n
        mean2 = sum(returns2) / n
        
        # Calculate correlation components
        numerator = sum((returns1[i] - mean1) * (returns2[i] - mean2) for i in range(n))
        
        sum_sq1 = sum((returns1[i] - mean1) ** 2 for i in range(n))
        sum_sq2 = sum((returns2[i] - mean2) ** 2 for i in range(n))
        
        denominator = math.sqrt(sum_sq1 * sum_sq2)
        
        if denominator == 0:
            return 0.0
        
        correlation = numerator / denominator
        return max(-1.0, min(1.0, correlation))  # Clamp to [-1, 1]
    
    def _is_large_cap_stock(self, symbol: str) -> bool:
        """Check if stock is large cap (simplified logic)"""
        large_cap_stocks = {
            'SBER', 'GAZP', 'LKOH', 'ROSN', 'NVTK', 'GMKN', 'YNDX', 'MTSS', 'MGNT', 'VTBR',
            'TATN', 'SNGS', 'NLMK', 'ALRS', 'CHMF', 'MAGN', 'PLZL', 'RTKM', 'AFKS', 'MOEX'
        }
        return symbol in large_cap_stocks
    
    def _is_mid_cap_stock(self, symbol: str) -> bool:
        """Check if stock is mid cap (simplified logic)"""
        mid_cap_stocks = {
            'FEES', 'POLY', 'RUAL', 'PHOR', 'AFLT', 'FLOT', 'CBOM', 'TRNFP', 'PIKK', 'LSRG',
            'TCSG', 'OZON', 'FIXP', 'HHRU', 'MAIL', 'QIWI', 'DSKY', 'BSPB', 'UPRO', 'ETLN'
        }
        return symbol in mid_cap_stocks
    
    def _is_small_cap_stock(self, symbol: str) -> bool:
        """Check if stock is small cap (simplified logic)"""
        # Most other stocks would be considered small cap
        return not (self._is_large_cap_stock(symbol) or self._is_mid_cap_stock(symbol))
    
    def _calculate_diversification_risk_score(
        self,
        sector_allocations: Dict[str, float],
        position_sizes: Dict[str, float],
        num_violations: int
    ) -> float:
        """Calculate overall diversification risk score"""
        risk_score = 0.0
        
        # Sector concentration risk
        if sector_allocations:
            max_sector_allocation = max(sector_allocations.values())
            sector_risk = min(max_sector_allocation / 50.0, 1.0)  # Normalize to 50% max
            risk_score += sector_risk * 0.4
        
        # Position concentration risk
        if position_sizes:
            max_position_size = max(position_sizes.values())
            position_risk = min(max_position_size / 20.0, 1.0)  # Normalize to 20% max
            risk_score += position_risk * 0.4
        
        # Violation penalty
        violation_risk = min(num_violations * 0.1, 0.2)  # Max 20% penalty
        risk_score += violation_risk
        
        return min(risk_score, 1.0)


@dataclass
class DiversificationRules:
    """Portfolio diversification rules for Russian market"""
    # Sector diversification limits (percentage of portfolio)
    max_energy_sector: float = 25.0  # Oil, gas companies
    max_financial_sector: float = 20.0  # Banks, insurance
    max_materials_sector: float = 20.0  # Mining, metals
    max_technology_sector: float = 15.0  # Tech companies
    max_consumer_sector: float = 15.0  # Consumer goods/services
    max_utilities_sector: float = 10.0  # Utilities
    max_telecom_sector: float = 10.0  # Telecommunications
    max_healthcare_sector: float = 10.0  # Healthcare, pharma
    max_industrials_sector: float = 15.0  # Industrial companies
    max_real_estate_sector: float = 10.0  # Real estate
    
    # Individual position limits (percentage of portfolio)
    max_large_cap_position: float = 8.0  # Large cap stocks (SBER, GAZP, etc.)
    max_mid_cap_position: float = 5.0   # Mid cap stocks
    max_small_cap_position: float = 3.0  # Small cap stocks
    
    # Correlation limits
    max_correlation_threshold: float = 0.7  # Max correlation between positions
    max_correlated_positions: int = 3  # Max number of highly correlated positions
    
    # Minimum diversification requirements
    min_number_of_positions: int = 5  # Minimum positions for diversification
    min_number_of_sectors: int = 3   # Minimum sectors for diversification
    
    # Special Russian market rules
    max_state_owned_allocation: float = 30.0  # Max allocation to state-owned companies
    max_sanctions_sensitive_allocation: float = 20.0  # Max allocation to sanctions-sensitive stocks


@dataclass
class DiversificationViolation:
    """Represents a diversification rule violation"""
    rule_type: str  # 'SECTOR', 'POSITION_SIZE', 'CORRELATION', 'STATE_OWNED', etc.
    violation_description: str
    current_value: float
    limit_value: float
    severity: str  # 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    affected_symbols: List[str]
    recommended_action: str


@dataclass
class DiversificationAnalysis:
    """Complete diversification analysis result"""
    is_compliant: bool
    violations: List[DiversificationViolation]
    sector_allocations: Dict[str, float]
    position_sizes: Dict[str, float]
    correlation_matrix: Dict[Tuple[str, str], float]
    high_correlation_pairs: List[Tuple[str, str, float]]
    diversification_score: float  # 0.0 (poor) to 1.0 (excellent)
    recommendations: List[str]
    timestamp: datetime


class RussianMarketDiversificationManager:
    """
    Portfolio diversification manager for Russian market
    Implements sector diversification rules, correlation analysis, and position size limits
    """
    
    def __init__(self, rules: Optional[DiversificationRules] = None):
        self.rules = rules or DiversificationRules()
        self.sector_mapping = self._initialize_sector_mapping()
        self.state_owned_companies = self._initialize_state_owned_companies()
        self.sanctions_sensitive_stocks = self._initialize_sanctions_sensitive_stocks()
    
    def _initialize_sector_mapping(self) -> Dict[str, str]:
        """Initialize mapping of Russian stocks to sectors"""
        return {
            # Energy sector
            'GAZP': 'ENERGY', 'ROSN': 'ENERGY', 'LKOH': 'ENERGY', 'NVTK': 'ENERGY',
            'SNGS': 'ENERGY', 'TATN': 'ENERGY', 'TRNFP': 'ENERGY',
            
            # Financial sector
            'SBER': 'FINANCIAL', 'VTBR': 'FINANCIAL', 'TCSG': 'FINANCIAL', 'BSPB': 'FINANCIAL',
            'CBOM': 'FINANCIAL', 'AFKS': 'FINANCIAL',
            
            # Materials sector
            'GMKN': 'MATERIALS', 'NLMK': 'MATERIALS', 'MAGN': 'MATERIALS', 'CHMF': 'MATERIALS',
            'ALRS': 'MATERIALS', 'RUAL': 'MATERIALS', 'PHOR': 'MATERIALS', 'POLY': 'MATERIALS',
            
            # Technology sector
            'YNDX': 'TECHNOLOGY', 'MAIL': 'TECHNOLOGY', 'OZON': 'TECHNOLOGY', 'FIXP': 'TECHNOLOGY',
            'HHRU': 'TECHNOLOGY', 'DSKY': 'TECHNOLOGY', 'QIWI': 'TECHNOLOGY',
            
            # Consumer sector
            'MGNT': 'CONSUMER', 'FIVE': 'CONSUMER', 'LENT': 'CONSUMER', 'DIXY': 'CONSUMER',
            
            # Telecommunications
            'MTSS': 'TELECOM', 'RTKM': 'TELECOM', 'TTLK': 'TELECOM',
            
            # Utilities
            'FEES': 'UTILITIES', 'MSRS': 'UTILITIES', 'MRKZ': 'UTILITIES',
            
            # Healthcare
            'PHST': 'HEALTHCARE', 'GEMC': 'HEALTHCARE',
            
            # Industrials
            'AFLT': 'INDUSTRIALS', 'FLOT': 'INDUSTRIALS', 'BLNG': 'INDUSTRIALS',
            
            # Real Estate
            'PIKK': 'REAL_ESTATE', 'LSRG': 'REAL_ESTATE', 'ETLN': 'REAL_ESTATE'
        }
    
    def _initialize_state_owned_companies(self) -> set:
        """Initialize set of state-owned companies"""
        return {
            'GAZP', 'ROSN', 'SBER', 'VTBR', 'NVTK', 'SNGS', 'ALRS', 'AFLT',
            'RTKM', 'FEES', 'FLOT', 'TRNFP'
        }
    
    def _initialize_sanctions_sensitive_stocks(self) -> set:
        """Initialize set of sanctions-sensitive stocks"""
        return {
            'GAZP', 'ROSN', 'LKOH', 'NVTK', 'SNGS', 'TATN', 'SBER', 'VTBR',
            'GMKN', 'NLMK', 'MAGN', 'CHMF', 'ALRS', 'RUAL', 'AFLT'
        }
    
    def analyze_portfolio_diversification(
        self,
        portfolio: Portfolio,
        market_data: Dict[str, MarketData],
        historical_prices: Optional[Dict[str, List[Decimal]]] = None
    ) -> DiversificationAnalysis:
        """
        Analyze portfolio diversification and identify violations
        
        Args:
            portfolio: Current portfolio
            market_data: Current market data
            historical_prices: Historical price data for correlation analysis
            
        Returns:
            Complete diversification analysis
        """
        violations = []
        recommendations = []
        
        # 1. Calculate sector allocations
        sector_allocations = self._calculate_sector_allocations(portfolio)
        
        # 2. Calculate position sizes
        position_sizes = self._calculate_position_sizes(portfolio)
        
        # 3. Check sector diversification rules
        sector_violations = self._check_sector_diversification(sector_allocations)
        violations.extend(sector_violations)
        
        # 4. Check position size limits
        position_violations = self._check_position_size_limits(portfolio, position_sizes)
        violations.extend(position_violations)
        
        # 5. Calculate correlation matrix and check correlation limits
        correlation_matrix = {}
        high_correlation_pairs = []
        if historical_prices and len(portfolio.positions) > 1:
            correlation_matrix = self._calculate_correlation_matrix(
                list(portfolio.positions.keys()), historical_prices
            )
            correlation_violations, high_correlation_pairs = self._check_correlation_limits(
                correlation_matrix, portfolio
            )
            violations.extend(correlation_violations)
        
        # 6. Check minimum diversification requirements
        min_diversification_violations = self._check_minimum_diversification(
            portfolio, sector_allocations
        )
        violations.extend(min_diversification_violations)
        
        # 7. Check Russian market specific rules
        russian_market_violations = self._check_russian_market_rules(portfolio, position_sizes)
        violations.extend(russian_market_violations)
        
        # 8. Calculate diversification score
        diversification_score = self._calculate_diversification_score(
            portfolio, sector_allocations, position_sizes, violations
        )
        
        # 9. Generate recommendations
        recommendations = self._generate_diversification_recommendations(
            violations, sector_allocations, position_sizes
        )
        
        return DiversificationAnalysis(
            is_compliant=len(violations) == 0,
            violations=violations,
            sector_allocations=sector_allocations,
            position_sizes=position_sizes,
            correlation_matrix=correlation_matrix,
            high_correlation_pairs=high_correlation_pairs,
            diversification_score=diversification_score,
            recommendations=recommendations,
            timestamp=datetime.now()
        )
    
    def _calculate_sector_allocations(self, portfolio: Portfolio) -> Dict[str, float]:
        """Calculate sector allocation percentages"""
        sector_values = {}
        total_value = portfolio.total_value
        
        if total_value <= 0:
            return {}
        
        for symbol, position in portfolio.positions.items():
            sector = self.sector_mapping.get(symbol, 'OTHER')
            if sector not in sector_values:
                sector_values[sector] = Decimal('0')
            sector_values[sector] += position.market_value
        
        return {
            sector: float(value / total_value * 100)
            for sector, value in sector_values.items()
        }
    
    def _calculate_position_sizes(self, portfolio: Portfolio) -> Dict[str, float]:
        """Calculate individual position sizes as percentage of portfolio"""
        total_value = portfolio.total_value
        
        if total_value <= 0:
            return {}
        
        return {
            symbol: float(position.market_value / total_value * 100)
            for symbol, position in portfolio.positions.items()
        }
    
    def _check_sector_diversification(
        self, sector_allocations: Dict[str, float]
    ) -> List[DiversificationViolation]:
        """Check sector diversification rules"""
        violations = []
        
        sector_limits = {
            'ENERGY': self.rules.max_energy_sector,
            'FINANCIAL': self.rules.max_financial_sector,
            'MATERIALS': self.rules.max_materials_sector,
            'TECHNOLOGY': self.rules.max_technology_sector,
            'CONSUMER': self.rules.max_consumer_sector,
            'UTILITIES': self.rules.max_utilities_sector,
            'TELECOM': self.rules.max_telecom_sector,
            'HEALTHCARE': self.rules.max_healthcare_sector,
            'INDUSTRIALS': self.rules.max_industrials_sector,
            'REAL_ESTATE': self.rules.max_real_estate_sector
        }
        
        for sector, allocation in sector_allocations.items():
            limit = sector_limits.get(sector, 15.0)  # Default 15% for unknown sectors
            
            if allocation > limit:
                severity = self._determine_violation_severity(allocation, limit)
                violations.append(DiversificationViolation(
                    rule_type='SECTOR',
                    violation_description=f'Sector {sector} allocation ({allocation:.1f}%) exceeds limit ({limit:.1f}%)',
                    current_value=allocation,
                    limit_value=limit,
                    severity=severity,
                    affected_symbols=[],  # Would need reverse lookup
                    recommended_action=f'Reduce {sector} sector allocation to below {limit:.1f}%'
                ))
        
        return violations
    
    def _check_position_size_limits(
        self, portfolio: Portfolio, position_sizes: Dict[str, float]
    ) -> List[DiversificationViolation]:
        """Check individual position size limits"""
        violations = []
        
        for symbol, size in position_sizes.items():
            # Determine position limit based on market cap
            if self._is_large_cap_stock(symbol):
                limit = self.rules.max_large_cap_position
                cap_type = "large cap"
            elif self._is_mid_cap_stock(symbol):
                limit = self.rules.max_mid_cap_position
                cap_type = "mid cap"
            else:
                limit = self.rules.max_small_cap_position
                cap_type = "small cap"
            
            if size > limit:
                severity = self._determine_violation_severity(size, limit)
                violations.append(DiversificationViolation(
                    rule_type='POSITION_SIZE',
                    violation_description=f'{cap_type.title()} position {symbol} ({size:.1f}%) exceeds limit ({limit:.1f}%)',
                    current_value=size,
                    limit_value=limit,
                    severity=severity,
                    affected_symbols=[symbol],
                    recommended_action=f'Reduce {symbol} position to below {limit:.1f}%'
                ))
        
        return violations
    
    def _calculate_correlation_matrix(
        self, symbols: List[str], historical_prices: Dict[str, List[Decimal]]
    ) -> Dict[Tuple[str, str], float]:
        """Calculate correlation matrix for portfolio positions"""
        correlation_matrix = {}
        
        for i, symbol1 in enumerate(symbols):
            for j, symbol2 in enumerate(symbols):
                if i < j:  # Only calculate upper triangle
                    if symbol1 in historical_prices and symbol2 in historical_prices:
                        correlation = self._calculate_correlation(
                            historical_prices[symbol1], historical_prices[symbol2]
                        )
                        correlation_matrix[(symbol1, symbol2)] = correlation
        
        return correlation_matrix
    
    def _check_correlation_limits(
        self, correlation_matrix: Dict[Tuple[str, str], float], portfolio: Portfolio
    ) -> Tuple[List[DiversificationViolation], List[Tuple[str, str, float]]]:
        """Check correlation limits between positions"""
        violations = []
        high_correlation_pairs = []
        
        for (symbol1, symbol2), correlation in correlation_matrix.items():
            if abs(correlation) > self.rules.max_correlation_threshold:
                high_correlation_pairs.append((symbol1, symbol2, correlation))
                
                severity = 'HIGH' if abs(correlation) > 0.85 else 'MEDIUM'
                violations.append(DiversificationViolation(
                    rule_type='CORRELATION',
                    violation_description=f'High correlation ({correlation:.2f}) between {symbol1} and {symbol2}',
                    current_value=abs(correlation),
                    limit_value=self.rules.max_correlation_threshold,
                    severity=severity,
                    affected_symbols=[symbol1, symbol2],
                    recommended_action=f'Consider reducing exposure to one of {symbol1} or {symbol2}'
                ))
        
        # Check if too many highly correlated positions
        if len(high_correlation_pairs) > self.rules.max_correlated_positions:
            violations.append(DiversificationViolation(
                rule_type='CORRELATION',
                violation_description=f'Too many highly correlated positions ({len(high_correlation_pairs)})',
                current_value=len(high_correlation_pairs),
                limit_value=self.rules.max_correlated_positions,
                severity='HIGH',
                affected_symbols=[],
                recommended_action='Reduce number of highly correlated positions'
            ))
        
        return violations, high_correlation_pairs
    
    def _check_minimum_diversification(
        self, portfolio: Portfolio, sector_allocations: Dict[str, float]
    ) -> List[DiversificationViolation]:
        """Check minimum diversification requirements"""
        violations = []
        
        # Check minimum number of positions
        num_positions = len(portfolio.positions)
        if num_positions < self.rules.min_number_of_positions:
            violations.append(DiversificationViolation(
                rule_type='MIN_POSITIONS',
                violation_description=f'Insufficient diversification: only {num_positions} positions',
                current_value=num_positions,
                limit_value=self.rules.min_number_of_positions,
                severity='HIGH',
                affected_symbols=list(portfolio.positions.keys()),
                recommended_action=f'Add more positions to reach minimum of {self.rules.min_number_of_positions}'
            ))
        
        # Check minimum number of sectors
        num_sectors = len(sector_allocations)
        if num_sectors < self.rules.min_number_of_sectors:
            violations.append(DiversificationViolation(
                rule_type='MIN_SECTORS',
                violation_description=f'Insufficient sector diversification: only {num_sectors} sectors',
                current_value=num_sectors,
                limit_value=self.rules.min_number_of_sectors,
                severity='HIGH',
                affected_symbols=[],
                recommended_action=f'Diversify across minimum of {self.rules.min_number_of_sectors} sectors'
            ))
        
        return violations
    
    def _check_russian_market_rules(
        self, portfolio: Portfolio, position_sizes: Dict[str, float]
    ) -> List[DiversificationViolation]:
        """Check Russian market specific diversification rules"""
        violations = []
        
        # Check state-owned company allocation
        state_owned_allocation = sum(
            size for symbol, size in position_sizes.items()
            if symbol in self.state_owned_companies
        )
        
        if state_owned_allocation > self.rules.max_state_owned_allocation:
            severity = self._determine_violation_severity(
                state_owned_allocation, self.rules.max_state_owned_allocation
            )
            violations.append(DiversificationViolation(
                rule_type='STATE_OWNED',
                violation_description=f'State-owned allocation ({state_owned_allocation:.1f}%) exceeds limit ({self.rules.max_state_owned_allocation:.1f}%)',
                current_value=state_owned_allocation,
                limit_value=self.rules.max_state_owned_allocation,
                severity=severity,
                affected_symbols=[s for s in position_sizes.keys() if s in self.state_owned_companies],
                recommended_action=f'Reduce state-owned company allocation to below {self.rules.max_state_owned_allocation:.1f}%'
            ))
        
        # Check sanctions-sensitive allocation
        sanctions_sensitive_allocation = sum(
            size for symbol, size in position_sizes.items()
            if symbol in self.sanctions_sensitive_stocks
        )
        
        if sanctions_sensitive_allocation > self.rules.max_sanctions_sensitive_allocation:
            severity = self._determine_violation_severity(
                sanctions_sensitive_allocation, self.rules.max_sanctions_sensitive_allocation
            )
            violations.append(DiversificationViolation(
                rule_type='SANCTIONS_SENSITIVE',
                violation_description=f'Sanctions-sensitive allocation ({sanctions_sensitive_allocation:.1f}%) exceeds limit ({self.rules.max_sanctions_sensitive_allocation:.1f}%)',
                current_value=sanctions_sensitive_allocation,
                limit_value=self.rules.max_sanctions_sensitive_allocation,
                severity=severity,
                affected_symbols=[s for s in position_sizes.keys() if s in self.sanctions_sensitive_stocks],
                recommended_action=f'Reduce sanctions-sensitive allocation to below {self.rules.max_sanctions_sensitive_allocation:.1f}%'
            ))
        
        return violations
    
    def _determine_violation_severity(self, current: float, limit: float) -> str:
        """Determine severity of a violation based on how much it exceeds the limit"""
        excess_ratio = (current - limit) / limit
        
        if excess_ratio > 1.0:  # More than 100% over limit
            return 'CRITICAL'
        elif excess_ratio > 0.5:  # 50-100% over limit
            return 'HIGH'
        elif excess_ratio > 0.2:  # 20-50% over limit
            return 'MEDIUM'
        else:  # Less than 20% over limit
            return 'LOW'
    
    def _calculate_diversification_score(
        self,
        portfolio: Portfolio,
        sector_allocations: Dict[str, float],
        position_sizes: Dict[str, float],
        violations: List[DiversificationViolation]
    ) -> float:
        """Calculate overall diversification score (0.0 to 1.0)"""
        score = 1.0
        
        # Penalty for violations
        for violation in violations:
            if violation.severity == 'CRITICAL':
                score -= 0.3
            elif violation.severity == 'HIGH':
                score -= 0.2
            elif violation.severity == 'MEDIUM':
                score -= 0.1
            else:  # LOW
                score -= 0.05
        
        # Bonus for good diversification
        num_positions = len(portfolio.positions)
        num_sectors = len(sector_allocations)
        
        # Position diversity bonus
        if num_positions >= 10:
            score += 0.1
        elif num_positions >= 7:
            score += 0.05
        
        # Sector diversity bonus
        if num_sectors >= 5:
            score += 0.1
        elif num_sectors >= 4:
            score += 0.05
        
        # Even allocation bonus (lower concentration is better)
        if position_sizes:
            max_position = max(position_sizes.values())
            if max_position < 5.0:  # No position over 5%
                score += 0.1
            elif max_position < 8.0:  # No position over 8%
                score += 0.05
        
        return max(0.0, min(1.0, score))
    
    def _generate_diversification_recommendations(
        self,
        violations: List[DiversificationViolation],
        sector_allocations: Dict[str, float],
        position_sizes: Dict[str, float]
    ) -> List[str]:
        """Generate specific recommendations to improve diversification"""
        recommendations = []
        
        if not violations:
            recommendations.append("Portfolio diversification is compliant with all rules")
            return recommendations
        
        # Group violations by type
        violation_types = {}
        for violation in violations:
            if violation.rule_type not in violation_types:
                violation_types[violation.rule_type] = []
            violation_types[violation.rule_type].append(violation)
        
        # Generate recommendations by violation type
        if 'SECTOR' in violation_types:
            recommendations.append("Reduce overweight sector allocations and diversify across more sectors")
        
        if 'POSITION_SIZE' in violation_types:
            recommendations.append("Reduce individual position sizes to improve diversification")
        
        if 'CORRELATION' in violation_types:
            recommendations.append("Reduce exposure to highly correlated positions")
        
        if 'MIN_POSITIONS' in violation_types:
            recommendations.append("Add more positions to improve diversification")
        
        if 'MIN_SECTORS' in violation_types:
            recommendations.append("Diversify across more market sectors")
        
        if 'STATE_OWNED' in violation_types:
            recommendations.append("Reduce allocation to state-owned companies")
        
        if 'SANCTIONS_SENSITIVE' in violation_types:
            recommendations.append("Reduce exposure to sanctions-sensitive stocks")
        
        # Add specific sector recommendations
        overweight_sectors = [
            sector for sector, allocation in sector_allocations.items()
            if allocation > 20.0  # Arbitrary threshold for overweight
        ]
        
        if overweight_sectors:
            recommendations.append(f"Consider reducing exposure to overweight sectors: {', '.join(overweight_sectors)}")
        
        return recommendations
    
    def enforce_diversification_rules(
        self,
        proposed_trade: TradeOrder,
        portfolio: Portfolio,
        market_data: Dict[str, MarketData]
    ) -> Tuple[bool, List[str], Optional[TradeOrder]]:
        """
        Enforce diversification rules for a proposed trade
        
        Args:
            proposed_trade: The trade being proposed
            portfolio: Current portfolio
            market_data: Current market data
            
        Returns:
            Tuple of (is_allowed, warnings, modified_trade)
        """
        warnings = []
        
        # Simulate the trade to see the resulting portfolio
        simulated_portfolio = self._simulate_trade(proposed_trade, portfolio, market_data)
        
        # Analyze diversification of simulated portfolio
        analysis = self.analyze_portfolio_diversification(simulated_portfolio, market_data)
        
        # Check for critical violations
        critical_violations = [v for v in analysis.violations if v.severity == 'CRITICAL']
        high_violations = [v for v in analysis.violations if v.severity == 'HIGH']
        
        # If critical violations, reject the trade
        if critical_violations:
            return False, [v.violation_description for v in critical_violations], None
        
        # If high violations, suggest modifications
        if high_violations:
            warnings.extend([v.violation_description for v in high_violations])
            
            # Try to modify the trade to reduce violations
            modified_trade = self._suggest_trade_modification(
                proposed_trade, portfolio, market_data, high_violations
            )
            
            if modified_trade and modified_trade.quantity != proposed_trade.quantity:
                warnings.append(f"Suggested position size reduced from {proposed_trade.quantity} to {modified_trade.quantity}")
                return True, warnings, modified_trade
        
        # Add medium/low violations as warnings
        medium_low_violations = [v for v in analysis.violations if v.severity in ['MEDIUM', 'LOW']]
        if medium_low_violations:
            warnings.extend([v.violation_description for v in medium_low_violations])
        
        return True, warnings, None
    
    def _simulate_trade(
        self, trade: TradeOrder, portfolio: Portfolio, market_data: Dict[str, MarketData]
    ) -> Portfolio:
        """Simulate a trade and return the resulting portfolio"""
        # Create a copy of the portfolio
        simulated_positions = portfolio.positions.copy()
        simulated_cash = portfolio.cash_balance
        
        symbol_data = market_data.get(trade.symbol)
        if not symbol_data:
            return portfolio  # Can't simulate without market data
        
        current_price = symbol_data.price
        
        if trade.action == "BUY":
            # Add or increase position
            trade_value = current_price * trade.quantity
            
            if trade.symbol in simulated_positions:
                # Increase existing position
                existing_pos = simulated_positions[trade.symbol]
                new_quantity = existing_pos.quantity + trade.quantity
                new_entry_price = (
                    (existing_pos.entry_price * existing_pos.quantity + current_price * trade.quantity) /
                    new_quantity
                )
                
                simulated_positions[trade.symbol] = Position(
                    symbol=trade.symbol,
                    quantity=new_quantity,
                    entry_price=new_entry_price,
                    current_price=current_price,
                    market_value=current_price * new_quantity,
                    unrealized_pnl=(current_price - new_entry_price) * new_quantity,
                    entry_date=existing_pos.entry_date,
                    sector=existing_pos.sector
                )
            else:
                # New position
                sector = self.sector_mapping.get(trade.symbol, 'OTHER')
                simulated_positions[trade.symbol] = Position(
                    symbol=trade.symbol,
                    quantity=trade.quantity,
                    entry_price=current_price,
                    current_price=current_price,
                    market_value=current_price * trade.quantity,
                    unrealized_pnl=Decimal('0'),
                    entry_date=datetime.now(),
                    sector=sector
                )
            
            simulated_cash -= trade_value
            
        elif trade.action == "SELL":
            # Reduce or close position
            if trade.symbol in simulated_positions:
                existing_pos = simulated_positions[trade.symbol]
                
                if trade.quantity >= existing_pos.quantity:
                    # Close entire position
                    trade_value = current_price * existing_pos.quantity
                    del simulated_positions[trade.symbol]
                else:
                    # Partial sale
                    new_quantity = existing_pos.quantity - trade.quantity
                    trade_value = current_price * trade.quantity
                    
                    simulated_positions[trade.symbol] = Position(
                        symbol=trade.symbol,
                        quantity=new_quantity,
                        entry_price=existing_pos.entry_price,
                        current_price=current_price,
                        market_value=current_price * new_quantity,
                        unrealized_pnl=(current_price - existing_pos.entry_price) * new_quantity,
                        entry_date=existing_pos.entry_date,
                        sector=existing_pos.sector
                    )
                
                simulated_cash += trade_value
        
        return Portfolio(
            positions=simulated_positions,
            cash_balance=simulated_cash,
            currency=portfolio.currency
        )
    
    def _suggest_trade_modification(
        self,
        trade: TradeOrder,
        portfolio: Portfolio,
        market_data: Dict[str, MarketData],
        violations: List[DiversificationViolation]
    ) -> Optional[TradeOrder]:
        """Suggest modifications to a trade to reduce diversification violations"""
        if trade.action != "BUY":
            return None  # Only modify buy orders
        
        # Find position size violations
        position_violations = [v for v in violations if v.rule_type == 'POSITION_SIZE']
        if not position_violations:
            return None
        
        # Calculate maximum allowed position size
        symbol_data = market_data.get(trade.symbol)
        if not symbol_data:
            return None
        
        current_price = symbol_data.price
        portfolio_value = portfolio.total_value
        
        # Determine position limit based on stock type
        if self._is_large_cap_stock(trade.symbol):
            max_position_percent = self.rules.max_large_cap_position
        elif self._is_mid_cap_stock(trade.symbol):
            max_position_percent = self.rules.max_mid_cap_position
        else:
            max_position_percent = self.rules.max_small_cap_position
        
        max_position_value = portfolio_value * Decimal(str(max_position_percent / 100))
        
        # Account for existing position
        existing_value = Decimal('0')
        if trade.symbol in portfolio.positions:
            existing_value = portfolio.positions[trade.symbol].market_value
        
        max_additional_value = max_position_value - existing_value
        
        if max_additional_value <= 0:
            return None  # Can't buy any more of this stock
        
        max_additional_quantity = int(max_additional_value / current_price)
        
        if max_additional_quantity < trade.quantity:
            # Suggest reduced quantity
            modified_trade = TradeOrder(
                symbol=trade.symbol,
                action=trade.action,
                quantity=max_additional_quantity,
                price=trade.price,
                order_type=trade.order_type,
                stop_loss=trade.stop_loss,
                take_profit=trade.take_profit
            )
            return modified_trade
        
        return None

    # ===== DIVERSIFICATION RULES IMPLEMENTATION =====
    
    def check_sector_diversification_rules(
        self, 
        portfolio: Portfolio, 
        stock_sectors: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Check sector diversification rules for Russian market
        
        Args:
            portfolio: Current portfolio
            stock_sectors: Mapping of stock symbols to sectors
            
        Returns:
            Dictionary with compliance status and violations
        """
        violations = []
        sector_allocations = {}
        total_value = portfolio.total_value
        
        if total_value <= 0:
            return {
                'is_compliant': True,
                'violations': [],
                'sector_allocations': {}
            }
        
        # Calculate sector allocations
        sector_values = {}
        for symbol, position in portfolio.positions.items():
            sector = stock_sectors.get(symbol, 'OTHER')
            if sector not in sector_values:
                sector_values[sector] = Decimal('0')
            sector_values[sector] += position.market_value
        
        # Convert to percentages
        for sector, value in sector_values.items():
            sector_allocations[sector] = float(value / total_value * 100)
        
        # Russian market sector limits
        sector_limits = {
            'OIL_GAS': 25.0,  # Energy sector limit
            'BANKING': 20.0,  # Financial sector limit
            'METALS_MINING': 20.0,  # Materials sector limit
            'INFORMATION_TECHNOLOGY': 15.0,  # Technology sector limit
            'CONSUMER_STAPLES': 15.0,  # Consumer sector limit
            'UTILITIES': 10.0,  # Utilities sector limit
            'TELECOMMUNICATIONS': 10.0,  # Telecom sector limit
            'HEALTHCARE': 10.0,  # Healthcare sector limit
            'INDUSTRIALS': 15.0,  # Industrials sector limit
            'REAL_ESTATE': 10.0,  # Real estate sector limit
            'OTHER': 10.0  # Other sectors limit
        }
        
        # Check for violations
        for sector, allocation in sector_allocations.items():
            limit = sector_limits.get(sector, 10.0)  # Default 10% for unknown sectors
            
            if allocation > limit:
                violations.append({
                    'type': 'SECTOR_OVERALLOCATION',
                    'sector': sector,
                    'current_allocation': allocation,
                    'limit': limit,
                    'excess': allocation - limit,
                    'severity': self._get_violation_severity(allocation, limit)
                })
        
        return {
            'is_compliant': len(violations) == 0,
            'violations': violations,
            'sector_allocations': sector_allocations
        }
    
    def check_position_size_limits(self, portfolio: Portfolio) -> Dict[str, Any]:
        """
        Check individual position size limits for Russian stocks
        
        Args:
            portfolio: Current portfolio
            
        Returns:
            Dictionary with compliance status and violations
        """
        violations = []
        position_allocations = {}
        total_value = portfolio.total_value
        
        if total_value <= 0:
            return {
                'is_compliant': True,
                'violations': [],
                'position_allocations': {}
            }
        
        # Calculate position allocations
        for symbol, position in portfolio.positions.items():
            allocation = float(position.market_value / total_value * 100)
            position_allocations[symbol] = allocation
            
            # Determine position limit based on market cap (simplified classification)
            if self._is_large_cap_russian_stock(symbol):
                limit = 15.0  # Large cap limit
                cap_type = "large cap"
            elif self._is_mid_cap_russian_stock(symbol):
                limit = 10.0  # Mid cap limit
                cap_type = "mid cap"
            else:
                limit = 5.0   # Small cap limit
                cap_type = "small cap"
            
            if allocation > limit:
                violations.append({
                    'symbol': symbol,
                    'current_allocation': allocation,
                    'limit': limit,
                    'cap_type': cap_type,
                    'excess': allocation - limit,
                    'severity': self._get_violation_severity(allocation, limit)
                })
        
        return {
            'is_compliant': len(violations) == 0,
            'violations': violations,
            'position_allocations': position_allocations
        }
    
    def calculate_stock_correlation(
        self, 
        symbol1: str, 
        symbol2: str, 
        prices1: List[Decimal], 
        prices2: List[Decimal]
    ) -> Optional[float]:
        """
        Calculate correlation between two Russian stocks
        
        Args:
            symbol1: First stock symbol
            symbol2: Second stock symbol
            prices1: Price history for first stock
            prices2: Price history for second stock
            
        Returns:
            Correlation coefficient (-1 to 1) or None if insufficient data
        """
        if len(prices1) < 3 or len(prices2) < 3 or len(prices1) != len(prices2):
            return None
        
        # Calculate returns
        returns1 = []
        returns2 = []
        
        for i in range(1, len(prices1)):
            ret1 = float((prices1[i] - prices1[i-1]) / prices1[i-1])
            ret2 = float((prices2[i] - prices2[i-1]) / prices2[i-1])
            returns1.append(ret1)
            returns2.append(ret2)
        
        if len(returns1) < 2:
            return None
        
        # Calculate correlation coefficient
        n = len(returns1)
        mean1 = sum(returns1) / n
        mean2 = sum(returns2) / n
        
        numerator = sum((returns1[i] - mean1) * (returns2[i] - mean2) for i in range(n))
        
        sum_sq1 = sum((returns1[i] - mean1) ** 2 for i in range(n))
        sum_sq2 = sum((returns2[i] - mean2) ** 2 for i in range(n))
        
        denominator = (sum_sq1 * sum_sq2) ** 0.5
        
        if denominator == 0:
            return None
        
        correlation = numerator / denominator
        return max(-1.0, min(1.0, correlation))  # Clamp to [-1, 1]
    
    def build_correlation_matrix(
        self, 
        symbols: List[str], 
        price_histories: Dict[str, List[Decimal]]
    ) -> Dict[Tuple[str, str], float]:
        """
        Build correlation matrix for portfolio stocks
        
        Args:
            symbols: List of stock symbols
            price_histories: Historical prices for each symbol
            
        Returns:
            Dictionary mapping symbol pairs to correlation coefficients
        """
        correlation_matrix = {}
        
        for i, symbol1 in enumerate(symbols):
            for j, symbol2 in enumerate(symbols):
                if i < j:  # Only calculate upper triangle
                    if symbol1 in price_histories and symbol2 in price_histories:
                        correlation = self.calculate_stock_correlation(
                            symbol1, symbol2,
                            price_histories[symbol1],
                            price_histories[symbol2]
                        )
                        if correlation is not None:
                            correlation_matrix[(symbol1, symbol2)] = correlation
        
        return correlation_matrix
    
    def check_correlation_limits(
        self, 
        portfolio: Portfolio, 
        correlation_matrix: Dict[Tuple[str, str], float]
    ) -> Dict[str, Any]:
        """
        Check correlation limits between portfolio positions
        
        Args:
            portfolio: Current portfolio
            correlation_matrix: Correlation coefficients between stocks
            
        Returns:
            Dictionary with compliance status and high correlation pairs
        """
        high_correlation_pairs = []
        correlation_threshold = 0.7  # Maximum allowed correlation
        
        for (symbol1, symbol2), correlation in correlation_matrix.items():
            # Only check if both symbols are in portfolio
            if symbol1 in portfolio.positions and symbol2 in portfolio.positions:
                if abs(correlation) > correlation_threshold:
                    high_correlation_pairs.append({
                        'symbol1': symbol1,
                        'symbol2': symbol2,
                        'correlation': correlation,
                        'severity': 'HIGH' if abs(correlation) > 0.85 else 'MEDIUM'
                    })
        
        return {
            'is_compliant': len(high_correlation_pairs) == 0,
            'high_correlation_pairs': high_correlation_pairs,
            'correlation_threshold': correlation_threshold
        }
    
    def enforce_diversification_rules(
        self,
        portfolio: Portfolio,
        stock_sectors: Dict[str, str],
        price_histories: Dict[str, List[Decimal]]
    ) -> Dict[str, Any]:
        """
        Comprehensive diversification rule enforcement
        
        Args:
            portfolio: Current portfolio
            stock_sectors: Mapping of stock symbols to sectors
            price_histories: Historical prices for correlation analysis
            
        Returns:
            Comprehensive diversification analysis and recommendations
        """
        # 1. Check sector diversification
        sector_result = self.check_sector_diversification_rules(portfolio, stock_sectors)
        
        # 2. Check position size limits
        position_result = self.check_position_size_limits(portfolio)
        
        # 3. Build correlation matrix and check limits
        symbols = list(portfolio.positions.keys())
        correlation_matrix = self.build_correlation_matrix(symbols, price_histories)
        correlation_result = self.check_correlation_limits(portfolio, correlation_matrix)
        
        # 4. Calculate overall diversification score
        diversification_score = self._calculate_diversification_score(
            sector_result, position_result, correlation_result
        )
        
        # 5. Aggregate all violations
        all_violations = (
            sector_result['violations'] + 
            position_result['violations'] + 
            correlation_result['high_correlation_pairs']
        )
        
        # 6. Generate comprehensive recommendations
        all_recommendations = self._generate_comprehensive_recommendations(
            sector_result, position_result, correlation_result
        )
        
        return {
            'is_fully_compliant': (
                sector_result['is_compliant'] and 
                position_result['is_compliant'] and 
                correlation_result['is_compliant']
            ),
            'diversification_score': diversification_score,
            'total_violations': len(all_violations),
            'sector_analysis': sector_result,
            'position_analysis': position_result,
            'correlation_analysis': correlation_result,
            'all_recommendations': all_recommendations
        }
    
    def _is_large_cap_russian_stock(self, symbol: str) -> bool:
        """Check if stock is large cap Russian stock"""
        large_cap_stocks = {
            'SBER', 'GAZP', 'LKOH', 'GMKN', 'NVTK', 'ROSN', 'TATN', 'SNGS',
            'MGNT', 'FIVE', 'YNDX', 'OZON', 'VTBR', 'ALRS', 'NLMK', 'MAGN'
        }
        return symbol in large_cap_stocks
    
    def _is_mid_cap_russian_stock(self, symbol: str) -> bool:
        """Check if stock is mid cap Russian stock"""
        mid_cap_stocks = {
            'AFLT', 'CBOM', 'CHMF', 'DSKY', 'FEES', 'FIXP', 'FLOT', 'HYDR',
            'IRAO', 'LSRG', 'MOEX', 'MTSS', 'PHOR', 'PIKK', 'PLZL', 'POLY',
            'QIWI', 'RTKM', 'RUAL', 'SBERP', 'TCSG', 'TRNFP', 'UPRO', 'VKCO'
        }
        return symbol in mid_cap_stocks
    
    def _get_violation_severity(self, current: float, limit: float) -> str:
        """Determine severity of a violation"""
        excess_ratio = (current - limit) / limit
        
        if excess_ratio > 1.0:  # More than 100% over limit
            return 'CRITICAL'
        elif excess_ratio > 0.5:  # 50-100% over limit
            return 'HIGH'
        elif excess_ratio > 0.2:  # 20-50% over limit
            return 'MEDIUM'
        else:  # Less than 20% over limit
            return 'LOW'
    
    def _calculate_diversification_score(
        self,
        sector_result: Dict[str, Any],
        position_result: Dict[str, Any],
        correlation_result: Dict[str, Any]
    ) -> float:
        """Calculate overall diversification score (0.0 to 1.0)"""
        score = 1.0
        
        # Penalty for sector violations
        for violation in sector_result['violations']:
            if violation['severity'] == 'CRITICAL':
                score -= 0.3
            elif violation['severity'] == 'HIGH':
                score -= 0.2
            elif violation['severity'] == 'MEDIUM':
                score -= 0.1
            else:
                score -= 0.05
        
        # Penalty for position size violations
        for violation in position_result['violations']:
            if violation['severity'] == 'CRITICAL':
                score -= 0.25
            elif violation['severity'] == 'HIGH':
                score -= 0.15
            elif violation['severity'] == 'MEDIUM':
                score -= 0.08
            else:
                score -= 0.03
        
        # Penalty for high correlations
        for pair in correlation_result['high_correlation_pairs']:
            if pair['severity'] == 'HIGH':
                score -= 0.15
            else:
                score -= 0.08
        
        # Bonus for good diversification
        num_sectors = len(sector_result['sector_allocations'])
        if num_sectors >= 5:
            score += 0.1
        elif num_sectors >= 3:
            score += 0.05
        
        return max(0.0, min(1.0, score))
    
    def _generate_comprehensive_recommendations(
        self,
        sector_result: Dict[str, Any],
        position_result: Dict[str, Any],
        correlation_result: Dict[str, Any]
    ) -> List[str]:
        """Generate comprehensive diversification recommendations"""
        recommendations = []
        
        # Sector recommendations
        if sector_result['violations']:
            overweight_sectors = [v['sector'] for v in sector_result['violations']]
            recommendations.append(
                f"Reduce allocation in overweight sectors: {', '.join(overweight_sectors)}"
            )
        
        # Position size recommendations
        if position_result['violations']:
            large_positions = [v['symbol'] for v in position_result['violations']]
            recommendations.append(
                f"Reduce position sizes for: {', '.join(large_positions)}"
            )
        
        # Correlation recommendations
        if correlation_result['high_correlation_pairs']:
            correlated_pairs = [
                f"{pair['symbol1']}-{pair['symbol2']}" 
                for pair in correlation_result['high_correlation_pairs']
            ]
            recommendations.append(
                f"Reduce correlation risk between: {', '.join(correlated_pairs)}"
            )
        
        # General recommendations
        if len(sector_result['sector_allocations']) < 3:
            recommendations.append("Diversify across more sectors (minimum 3 recommended)")
        
        if len(position_result['position_allocations']) < 5:
            recommendations.append("Add more positions to improve diversification (minimum 5 recommended)")
        
        # Russian market specific recommendations
        oil_gas_allocation = sector_result['sector_allocations'].get('OIL_GAS', 0)
        if oil_gas_allocation > 20:
            recommendations.append(
                "Consider reducing oil & gas exposure due to geopolitical risks"
            )
        
        banking_allocation = sector_result['sector_allocations'].get('BANKING', 0)
        if banking_allocation > 15:
            recommendations.append(
                "Consider reducing banking sector exposure due to sanctions risks"
            )
        
        return recommendations