"""
Russian tax reporting service for individual investors
Handles capital gains/losses calculation, dividend tracking, and tax report generation
according to Russian tax legislation
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
import logging
from collections import defaultdict

from ..models.trading import Portfolio, Position, ExecutionResult, OrderAction
from .transaction_logger import RussianTransactionLogger, TransactionType, RussianTaxEvent


logger = logging.getLogger(__name__)


class TaxEventType(Enum):
    """Types of tax events for Russian reporting"""
    STOCK_PURCHASE = "stock_purchase"
    STOCK_SALE = "stock_sale"
    DIVIDEND_RECEIVED = "dividend_received"
    COUPON_RECEIVED = "coupon_received"
    BROKER_COMMISSION = "broker_commission"


class TaxCalculationMethod(Enum):
    """Methods for calculating capital gains in Russia"""
    FIFO = "fifo"  # First In, First Out (default for Russian tax)
    AVERAGE_COST = "average_cost"  # Alternative method


@dataclass
class TaxEvent:
    """Individual tax event record"""
    event_id: str
    event_type: TaxEventType
    date: datetime
    symbol: str
    quantity: int
    price: Decimal
    commission: Decimal
    total_amount: Decimal
    currency: str = "RUB"
    description: str = ""
    
    def __post_init__(self):
        """Calculate total amount if not provided"""
        if self.total_amount is None:
            if self.event_type in [TaxEventType.STOCK_PURCHASE, TaxEventType.STOCK_SALE]:
                self.total_amount = self.price * self.quantity + self.commission
            else:
                self.total_amount = self.price * self.quantity


@dataclass
class CapitalGainLoss:
    """Capital gain/loss calculation result"""
    symbol: str
    sale_date: datetime
    purchase_date: datetime
    quantity: int
    purchase_price: Decimal
    sale_price: Decimal
    purchase_commission: Decimal
    sale_commission: Decimal
    gain_loss: Decimal
    currency: str = "RUB"
    holding_period_days: Optional[int] = None
    is_long_term: Optional[bool] = None
    
    def __post_init__(self):
        """Calculate derived values"""
        if self.holding_period_days is None:
            self.holding_period_days = (self.sale_date - self.purchase_date).days
        if self.is_long_term is None:
            self.is_long_term = self.holding_period_days > (3 * 365)  # 3 years for Russian tax benefits


@dataclass
class DividendRecord:
    """Dividend payment record"""
    symbol: str
    payment_date: datetime
    dividend_per_share: Decimal
    quantity: int
    tax_withheld: Decimal
    ex_dividend_date: Optional[datetime] = None
    gross_dividend: Optional[Decimal] = None
    net_dividend: Optional[Decimal] = None
    currency: str = "RUB"
    source_country: str = "RU"
    
    def __post_init__(self):
        """Calculate derived values"""
        if self.gross_dividend is None:
            self.gross_dividend = self.dividend_per_share * self.quantity
        if self.net_dividend is None:
            self.net_dividend = self.gross_dividend - self.tax_withheld


@dataclass
class RussianTaxReport:
    """Comprehensive Russian tax report for individual investors"""
    tax_year: int
    taxpayer_id: Optional[str]
    
    # Capital gains/losses
    capital_gains: List[CapitalGainLoss]
    total_capital_gains: Decimal
    total_capital_losses: Decimal
    net_capital_gains: Decimal
    
    # Dividends
    dividend_records: List[DividendRecord]
    total_dividend_income: Decimal
    total_dividend_tax_withheld: Decimal
    
    # Commissions and expenses
    total_broker_commissions: Decimal
    total_other_expenses: Decimal
    
    # Tax calculations
    taxable_income: Decimal
    estimated_tax_due: Decimal
    tax_rate: Decimal = Decimal('0.13')  # 13% for Russian residents
    
    # Report metadata
    generated_at: datetime = field(default_factory=datetime.now)
    currency: str = "RUB"
    
    def __post_init__(self):
        """Calculate summary values"""
        # Capital gains summary
        self.total_capital_gains = sum(
            cgl.gain_loss for cgl in self.capital_gains if cgl.gain_loss > 0
        )
        self.total_capital_losses = sum(
            abs(cgl.gain_loss) for cgl in self.capital_gains if cgl.gain_loss < 0
        )
        self.net_capital_gains = self.total_capital_gains - self.total_capital_losses
        
        # Dividend summary
        self.total_dividend_income = sum(dr.gross_dividend for dr in self.dividend_records)
        self.total_dividend_tax_withheld = sum(dr.tax_withheld for dr in self.dividend_records)
        
        # Taxable income (capital gains + dividends)
        self.taxable_income = max(Decimal('0'), self.net_capital_gains) + self.total_dividend_income
        
        # Estimated tax (13% for residents, minus withheld tax)
        gross_tax = self.taxable_income * self.tax_rate
        self.estimated_tax_due = max(Decimal('0'), gross_tax - self.total_dividend_tax_withheld)


class RussianTaxReporter:
    """Russian tax reporting service for individual investors"""
    
    def __init__(self, 
                 transaction_logger: RussianTransactionLogger,
                 calculation_method: TaxCalculationMethod = TaxCalculationMethod.FIFO):
        """
        Initialize Russian tax reporter
        
        Args:
            transaction_logger: Transaction logger instance
            calculation_method: Method for calculating capital gains
        """
        self.transaction_logger = transaction_logger
        self.calculation_method = calculation_method
        self.tax_events: List[TaxEvent] = []
        self.dividend_records: List[DividendRecord] = []
        
        logger.info(f"Russian tax reporter initialized with {calculation_method.value} method")
    
    def record_stock_purchase(self, 
                            symbol: str, 
                            quantity: int, 
                            price: Decimal, 
                            commission: Decimal,
                            transaction_date: Optional[datetime] = None) -> str:
        """
        Record stock purchase for tax purposes
        
        Args:
            symbol: Stock symbol
            quantity: Number of shares
            price: Purchase price per share
            commission: Broker commission
            transaction_date: Transaction date (defaults to now)
            
        Returns:
            Event ID
        """
        if transaction_date is None:
            transaction_date = datetime.now()
        
        event_id = f"PUR_{symbol}_{transaction_date.strftime('%Y%m%d_%H%M%S')}"
        
        tax_event = TaxEvent(
            event_id=event_id,
            event_type=TaxEventType.STOCK_PURCHASE,
            date=transaction_date,
            symbol=symbol,
            quantity=quantity,
            price=price,
            commission=commission,
            total_amount=price * quantity + commission,
            description=f"Покупка {quantity} акций {symbol} по цене {price} руб."
        )
        
        self.tax_events.append(tax_event)
        
        # Log to transaction logger
        self.transaction_logger.log_tax_event(
            RussianTaxEvent.STOCK_PURCHASE,
            symbol,
            quantity,
            price,
            commission
        )
        
        logger.info(f"Recorded stock purchase: {quantity} {symbol} at {price} RUB")
        return event_id
    
    def record_stock_sale(self, 
                         symbol: str, 
                         quantity: int, 
                         price: Decimal, 
                         commission: Decimal,
                         transaction_date: Optional[datetime] = None) -> str:
        """
        Record stock sale for tax purposes
        
        Args:
            symbol: Stock symbol
            quantity: Number of shares sold
            price: Sale price per share
            commission: Broker commission
            transaction_date: Transaction date (defaults to now)
            
        Returns:
            Event ID
        """
        if transaction_date is None:
            transaction_date = datetime.now()
        
        event_id = f"SAL_{symbol}_{transaction_date.strftime('%Y%m%d_%H%M%S')}"
        
        tax_event = TaxEvent(
            event_id=event_id,
            event_type=TaxEventType.STOCK_SALE,
            date=transaction_date,
            symbol=symbol,
            quantity=quantity,
            price=price,
            commission=commission,
            total_amount=price * quantity - commission,
            description=f"Продажа {quantity} акций {symbol} по цене {price} руб."
        )
        
        self.tax_events.append(tax_event)
        
        # Log to transaction logger
        self.transaction_logger.log_tax_event(
            RussianTaxEvent.STOCK_SALE,
            symbol,
            quantity,
            price,
            commission
        )
        
        logger.info(f"Recorded stock sale: {quantity} {symbol} at {price} RUB")
        return event_id
    
    def record_dividend(self, 
                       symbol: str, 
                       dividend_per_share: Decimal, 
                       quantity: int,
                       payment_date: Optional[datetime] = None,
                       tax_withheld: Optional[Decimal] = None,
                       ex_dividend_date: Optional[datetime] = None) -> str:
        """
        Record dividend payment for tax purposes
        
        Args:
            symbol: Stock symbol
            dividend_per_share: Dividend amount per share
            quantity: Number of shares
            payment_date: Dividend payment date
            tax_withheld: Tax withheld at source
            ex_dividend_date: Ex-dividend date
            
        Returns:
            Record ID
        """
        if payment_date is None:
            payment_date = datetime.now()
        
        if tax_withheld is None:
            # Default Russian dividend tax withholding (13% for residents)
            gross_dividend = dividend_per_share * quantity
            tax_withheld = gross_dividend * Decimal('0.13')
        
        dividend_record = DividendRecord(
            symbol=symbol,
            payment_date=payment_date,
            ex_dividend_date=ex_dividend_date,
            dividend_per_share=dividend_per_share,
            quantity=quantity,
            gross_dividend=dividend_per_share * quantity,
            tax_withheld=tax_withheld,
            net_dividend=(dividend_per_share * quantity) - tax_withheld
        )
        
        self.dividend_records.append(dividend_record)
        
        # Create tax event
        event_id = f"DIV_{symbol}_{payment_date.strftime('%Y%m%d_%H%M%S')}"
        tax_event = TaxEvent(
            event_id=event_id,
            event_type=TaxEventType.DIVIDEND_RECEIVED,
            date=payment_date,
            symbol=symbol,
            quantity=quantity,
            price=dividend_per_share,
            commission=Decimal('0'),
            total_amount=dividend_per_share * quantity,
            description=f"Дивиденды по {quantity} акциям {symbol}: {dividend_per_share} руб. за акцию"
        )
        
        self.tax_events.append(tax_event)
        
        logger.info(f"Recorded dividend: {quantity} {symbol} at {dividend_per_share} RUB per share")
        return event_id
    
    def calculate_capital_gains_losses(self, tax_year: int) -> List[CapitalGainLoss]:
        """
        Calculate capital gains and losses for a specific tax year
        
        Args:
            tax_year: Tax year to calculate for
            
        Returns:
            List of capital gain/loss records
        """
        # Get all purchases (from any year) and sales for the tax year
        purchases = defaultdict(list)  # symbol -> list of purchases
        sales = []
        
        for event in self.tax_events:
            if event.event_type == TaxEventType.STOCK_PURCHASE:
                purchases[event.symbol].append(event)
            elif event.event_type == TaxEventType.STOCK_SALE and event.date.year == tax_year:
                sales.append(event)
        
        # Sort purchases by date (for FIFO)
        for symbol in purchases:
            purchases[symbol].sort(key=lambda x: x.date)
        
        capital_gains_losses = []
        
        # Process each sale
        for sale in sales:
            symbol = sale.symbol
            remaining_quantity = sale.quantity
            
            if symbol not in purchases or not purchases[symbol]:
                logger.warning(f"No purchase records found for sale of {symbol}")
                continue
            
            # Match sales with purchases using FIFO method
            while remaining_quantity > 0 and purchases[symbol]:
                purchase = purchases[symbol][0]
                
                # Determine quantity to match
                match_quantity = min(remaining_quantity, purchase.quantity)
                
                # Store original quantities for commission calculation
                original_purchase_quantity = purchase.quantity
                original_sale_quantity = sale.quantity
                
                # Calculate proportional commissions (avoid division by zero)
                purchase_commission_portion = (
                    purchase.commission * match_quantity / original_purchase_quantity
                    if original_purchase_quantity > 0 else Decimal('0')
                )
                sale_commission_portion = (
                    sale.commission * match_quantity / original_sale_quantity
                    if original_sale_quantity > 0 else Decimal('0')
                )
                
                # Calculate gain/loss
                purchase_cost = purchase.price * match_quantity + purchase_commission_portion
                sale_proceeds = sale.price * match_quantity - sale_commission_portion
                gain_loss = sale_proceeds - purchase_cost
                
                # Create capital gain/loss record
                cgl = CapitalGainLoss(
                    symbol=symbol,
                    sale_date=sale.date,
                    purchase_date=purchase.date,
                    quantity=match_quantity,
                    purchase_price=purchase.price,
                    sale_price=sale.price,
                    purchase_commission=purchase_commission_portion,
                    sale_commission=sale_commission_portion,
                    gain_loss=gain_loss
                )
                
                capital_gains_losses.append(cgl)
                
                # Update remaining quantities
                remaining_quantity -= match_quantity
                purchase.quantity -= match_quantity
                
                # Remove purchase if fully consumed
                if purchase.quantity <= 0:
                    purchases[symbol].pop(0)
        
        logger.info(f"Calculated {len(capital_gains_losses)} capital gain/loss records for {tax_year}")
        return capital_gains_losses
    
    def generate_tax_report(self, tax_year: int, taxpayer_id: Optional[str] = None) -> RussianTaxReport:
        """
        Generate comprehensive Russian tax report
        
        Args:
            tax_year: Tax year to generate report for
            taxpayer_id: Optional taxpayer identifier
            
        Returns:
            Complete tax report
        """
        logger.info(f"Generating Russian tax report for year {tax_year}")
        
        # Calculate capital gains/losses
        capital_gains = self.calculate_capital_gains_losses(tax_year)
        
        # Get dividend records for the year
        year_dividends = [
            dr for dr in self.dividend_records 
            if dr.payment_date.year == tax_year
        ]
        
        # Calculate total commissions
        total_commissions = sum(
            event.commission for event in self.tax_events
            if event.date.year == tax_year and event.event_type in [
                TaxEventType.STOCK_PURCHASE, TaxEventType.STOCK_SALE
            ]
        )
        
        # Create tax report
        tax_report = RussianTaxReport(
            tax_year=tax_year,
            taxpayer_id=taxpayer_id,
            capital_gains=capital_gains,
            total_capital_gains=Decimal('0'),  # Will be calculated in __post_init__
            total_capital_losses=Decimal('0'),
            net_capital_gains=Decimal('0'),
            dividend_records=year_dividends,
            total_dividend_income=Decimal('0'),
            total_dividend_tax_withheld=Decimal('0'),
            total_broker_commissions=total_commissions,
            total_other_expenses=Decimal('0'),
            taxable_income=Decimal('0'),
            estimated_tax_due=Decimal('0')
        )
        
        logger.info(f"Generated tax report: {tax_report.net_capital_gains} RUB net capital gains, "
                   f"{tax_report.total_dividend_income} RUB dividend income")
        
        return tax_report
    
    def export_tax_report_to_dict(self, tax_report: RussianTaxReport) -> Dict[str, Any]:
        """
        Export tax report to dictionary format
        
        Args:
            tax_report: Tax report to export
            
        Returns:
            Dictionary representation of tax report
        """
        return {
            "tax_year": tax_report.tax_year,
            "taxpayer_id": tax_report.taxpayer_id,
            "generated_at": tax_report.generated_at.isoformat(),
            "currency": tax_report.currency,
            
            "summary": {
                "total_capital_gains": float(tax_report.total_capital_gains),
                "total_capital_losses": float(tax_report.total_capital_losses),
                "net_capital_gains": float(tax_report.net_capital_gains),
                "total_dividend_income": float(tax_report.total_dividend_income),
                "total_dividend_tax_withheld": float(tax_report.total_dividend_tax_withheld),
                "total_broker_commissions": float(tax_report.total_broker_commissions),
                "taxable_income": float(tax_report.taxable_income),
                "estimated_tax_due": float(tax_report.estimated_tax_due),
                "tax_rate": float(tax_report.tax_rate)
            },
            
            "capital_gains_losses": [
                {
                    "symbol": cgl.symbol,
                    "sale_date": cgl.sale_date.isoformat(),
                    "purchase_date": cgl.purchase_date.isoformat(),
                    "quantity": cgl.quantity,
                    "purchase_price": float(cgl.purchase_price),
                    "sale_price": float(cgl.sale_price),
                    "purchase_commission": float(cgl.purchase_commission),
                    "sale_commission": float(cgl.sale_commission),
                    "gain_loss": float(cgl.gain_loss),
                    "holding_period_days": cgl.holding_period_days,
                    "is_long_term": cgl.is_long_term
                }
                for cgl in tax_report.capital_gains
            ],
            
            "dividends": [
                {
                    "symbol": dr.symbol,
                    "payment_date": dr.payment_date.isoformat(),
                    "ex_dividend_date": dr.ex_dividend_date.isoformat() if dr.ex_dividend_date else None,
                    "dividend_per_share": float(dr.dividend_per_share),
                    "quantity": dr.quantity,
                    "gross_dividend": float(dr.gross_dividend),
                    "tax_withheld": float(dr.tax_withheld),
                    "net_dividend": float(dr.net_dividend)
                }
                for dr in tax_report.dividend_records
            ],
            
            "tax_events_summary": {
                "total_events": len([e for e in self.tax_events if e.date.year == tax_report.tax_year]),
                "purchases": len([e for e in self.tax_events 
                               if e.date.year == tax_report.tax_year and e.event_type == TaxEventType.STOCK_PURCHASE]),
                "sales": len([e for e in self.tax_events 
                            if e.date.year == tax_report.tax_year and e.event_type == TaxEventType.STOCK_SALE]),
                "dividends": len([e for e in self.tax_events 
                                if e.date.year == tax_report.tax_year and e.event_type == TaxEventType.DIVIDEND_RECEIVED])
            }
        }
    
    def generate_russian_tax_form_data(self, tax_report: RussianTaxReport) -> Dict[str, Any]:
        """
        Generate data formatted for Russian tax forms (декларация)
        
        Args:
            tax_report: Tax report to format
            
        Returns:
            Dictionary with Russian tax form data
        """
        # Russian tax form sections
        return {
            "Налоговый_период": tax_report.tax_year,
            "Налогоплательщик": tax_report.taxpayer_id or "Не указан",
            
            # Section for securities transactions (Раздел по ценным бумагам)
            "Операции_с_ценными_бумагами": {
                "Доходы_от_реализации": float(tax_report.total_capital_gains),
                "Расходы_по_реализации": float(tax_report.total_capital_losses + tax_report.total_broker_commissions),
                "Финансовый_результат": float(tax_report.net_capital_gains),
                "Количество_операций": len(tax_report.capital_gains)
            },
            
            # Section for dividend income (Раздел по дивидендам)
            "Дивидендные_доходы": {
                "Общая_сумма_дивидендов": float(tax_report.total_dividend_income),
                "Удержанный_налог": float(tax_report.total_dividend_tax_withheld),
                "К_доплате": float(max(Decimal('0'), 
                                     tax_report.total_dividend_income * tax_report.tax_rate - tax_report.total_dividend_tax_withheld))
            },
            
            # Summary section (Итоговые суммы)
            "Итого": {
                "Налогооблагаемый_доход": float(tax_report.taxable_income),
                "Налог_к_доплате": float(tax_report.estimated_tax_due),
                "Ставка_налога": f"{float(tax_report.tax_rate * 100):.0f}%"
            },
            
            # Metadata
            "Дата_формирования": tax_report.generated_at.strftime("%d.%m.%Y"),
            "Валюта": tax_report.currency
        }
    
    def get_tax_events_for_year(self, tax_year: int) -> List[TaxEvent]:
        """
        Get all tax events for a specific year
        
        Args:
            tax_year: Year to filter by
            
        Returns:
            List of tax events for the year
        """
        return [event for event in self.tax_events if event.date.year == tax_year]
    
    def get_dividend_records_for_year(self, tax_year: int) -> List[DividendRecord]:
        """
        Get all dividend records for a specific year
        
        Args:
            tax_year: Year to filter by
            
        Returns:
            List of dividend records for the year
        """
        return [record for record in self.dividend_records if record.payment_date.year == tax_year]
    
    def calculate_tax_optimization_suggestions(self, tax_report: RussianTaxReport) -> List[str]:
        """
        Generate tax optimization suggestions for Russian investors
        
        Args:
            tax_report: Tax report to analyze
            
        Returns:
            List of optimization suggestions in Russian
        """
        suggestions = []
        
        # Check for long-term holdings (3+ years for Russian tax benefits)
        long_term_gains = [cgl for cgl in tax_report.capital_gains if cgl.is_long_term and cgl.gain_loss > 0]
        if long_term_gains:
            total_long_term = sum(cgl.gain_loss for cgl in long_term_gains)
            suggestions.append(
                f"У вас есть долгосрочные инвестиции (более 3 лет) с прибылью {total_long_term:.2f} руб. "
                "Рассмотрите возможность применения льготы по долгосрочному владению ценными бумагами."
            )
        
        # Check for tax loss harvesting opportunities
        unrealized_losses = sum(cgl.gain_loss for cgl in tax_report.capital_gains if cgl.gain_loss < 0)
        if unrealized_losses < 0 and tax_report.net_capital_gains > 0:
            suggestions.append(
                f"Вы можете зачесть убытки {abs(unrealized_losses):.2f} руб. против прибыли "
                f"{tax_report.total_capital_gains:.2f} руб. для снижения налогооблагаемой базы."
            )
        
        # Check dividend tax optimization
        if tax_report.total_dividend_income > 0:
            potential_savings = tax_report.total_dividend_income * Decimal('0.05')  # 5% vs 13%
            suggestions.append(
                f"При доходе от дивидендов {tax_report.total_dividend_income:.2f} руб. "
                f"рассмотрите возможность получения статуса квалифицированного инвестора "
                f"для снижения налоговой ставки с 13% до 5%."
            )
        
        # Check IIA (Individual Investment Account) benefits
        if tax_report.taxable_income > 400000:  # 400k RUB threshold
            suggestions.append(
                "При доходах свыше 400,000 руб. рассмотрите возможность открытия ИИС "
                "для получения налоговых льгот до 52,000 руб. в год."
            )
        
        return suggestions