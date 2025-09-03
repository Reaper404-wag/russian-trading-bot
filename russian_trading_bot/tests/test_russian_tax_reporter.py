"""
Unit tests for Russian tax reporting service
Tests capital gains/losses calculation, dividend tracking, and tax report generation
"""

import unittest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

from russian_trading_bot.services.russian_tax_reporter import (
    RussianTaxReporter, TaxEvent, TaxEventType, CapitalGainLoss, 
    DividendRecord, RussianTaxReport, TaxCalculationMethod
)
from russian_trading_bot.services.transaction_logger import RussianTransactionLogger


class TestRussianTaxReporter(unittest.TestCase):
    """Test cases for Russian tax reporter"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock transaction logger
        self.mock_logger = Mock(spec=RussianTransactionLogger)
        self.tax_reporter = RussianTaxReporter(
            transaction_logger=self.mock_logger,
            calculation_method=TaxCalculationMethod.FIFO
        )
        
        # Test data
        self.test_date = datetime(2024, 6, 15, 10, 30, 0)
        self.test_symbol = "SBER"
        self.test_quantity = 100
        self.test_price = Decimal('250.50')
        self.test_commission = Decimal('15.00')
    
    def test_record_stock_purchase(self):
        """Test recording stock purchase"""
        event_id = self.tax_reporter.record_stock_purchase(
            symbol=self.test_symbol,
            quantity=self.test_quantity,
            price=self.test_price,
            commission=self.test_commission,
            transaction_date=self.test_date
        )
        
        # Check event was created
        self.assertEqual(len(self.tax_reporter.tax_events), 1)
        
        event = self.tax_reporter.tax_events[0]
        self.assertEqual(event.event_id, event_id)
        self.assertEqual(event.event_type, TaxEventType.STOCK_PURCHASE)
        self.assertEqual(event.symbol, self.test_symbol)
        self.assertEqual(event.quantity, self.test_quantity)
        self.assertEqual(event.price, self.test_price)
        self.assertEqual(event.commission, self.test_commission)
        self.assertEqual(event.total_amount, self.test_price * self.test_quantity + self.test_commission)
        
        # Check transaction logger was called
        self.mock_logger.log_tax_event.assert_called_once()
    
    def test_record_stock_sale(self):
        """Test recording stock sale"""
        sale_price = Decimal('275.25')
        sale_commission = Decimal('18.50')
        
        event_id = self.tax_reporter.record_stock_sale(
            symbol=self.test_symbol,
            quantity=self.test_quantity,
            price=sale_price,
            commission=sale_commission,
            transaction_date=self.test_date
        )
        
        # Check event was created
        self.assertEqual(len(self.tax_reporter.tax_events), 1)
        
        event = self.tax_reporter.tax_events[0]
        self.assertEqual(event.event_type, TaxEventType.STOCK_SALE)
        self.assertEqual(event.symbol, self.test_symbol)
        self.assertEqual(event.quantity, self.test_quantity)
        self.assertEqual(event.price, sale_price)
        self.assertEqual(event.commission, sale_commission)
        self.assertEqual(event.total_amount, sale_price * self.test_quantity - sale_commission)
    
    def test_record_dividend(self):
        """Test recording dividend payment"""
        dividend_per_share = Decimal('12.50')
        quantity = 200
        payment_date = datetime(2024, 7, 15)
        
        event_id = self.tax_reporter.record_dividend(
            symbol=self.test_symbol,
            dividend_per_share=dividend_per_share,
            quantity=quantity,
            payment_date=payment_date
        )
        
        # Check dividend record was created
        self.assertEqual(len(self.tax_reporter.dividend_records), 1)
        
        dividend_record = self.tax_reporter.dividend_records[0]
        self.assertEqual(dividend_record.symbol, self.test_symbol)
        self.assertEqual(dividend_record.dividend_per_share, dividend_per_share)
        self.assertEqual(dividend_record.quantity, quantity)
        self.assertEqual(dividend_record.payment_date, payment_date)
        
        # Check tax calculations
        expected_gross = dividend_per_share * quantity
        expected_tax = expected_gross * Decimal('0.13')  # 13% Russian tax
        expected_net = expected_gross - expected_tax
        
        self.assertEqual(dividend_record.gross_dividend, expected_gross)
        self.assertEqual(dividend_record.tax_withheld, expected_tax)
        self.assertEqual(dividend_record.net_dividend, expected_net)
        
        # Check tax event was created
        self.assertEqual(len(self.tax_reporter.tax_events), 1)
        tax_event = self.tax_reporter.tax_events[0]
        self.assertEqual(tax_event.event_type, TaxEventType.DIVIDEND_RECEIVED)
    
    def test_calculate_capital_gains_losses_fifo(self):
        """Test capital gains/losses calculation using FIFO method"""
        tax_year = 2024
        
        # Record multiple purchases at different prices
        purchase_date1 = datetime(2024, 1, 15)
        purchase_date2 = datetime(2024, 2, 20)
        sale_date = datetime(2024, 6, 10)
        
        # First purchase: 100 shares at 200 RUB
        self.tax_reporter.record_stock_purchase(
            symbol=self.test_symbol,
            quantity=100,
            price=Decimal('200.00'),
            commission=Decimal('10.00'),
            transaction_date=purchase_date1
        )
        
        # Second purchase: 150 shares at 250 RUB
        self.tax_reporter.record_stock_purchase(
            symbol=self.test_symbol,
            quantity=150,
            price=Decimal('250.00'),
            commission=Decimal('15.00'),
            transaction_date=purchase_date2
        )
        
        # Sale: 120 shares at 300 RUB
        self.tax_reporter.record_stock_sale(
            symbol=self.test_symbol,
            quantity=120,
            price=Decimal('300.00'),
            commission=Decimal('20.00'),
            transaction_date=sale_date
        )
        
        # Calculate capital gains/losses
        capital_gains = self.tax_reporter.calculate_capital_gains_losses(tax_year)
        
        # Should have 2 records (100 from first purchase, 20 from second)
        self.assertEqual(len(capital_gains), 2)
        
        # First record: 100 shares from first purchase
        cgl1 = capital_gains[0]
        self.assertEqual(cgl1.symbol, self.test_symbol)
        self.assertEqual(cgl1.quantity, 100)
        self.assertEqual(cgl1.purchase_price, Decimal('200.00'))
        self.assertEqual(cgl1.sale_price, Decimal('300.00'))
        self.assertEqual(cgl1.purchase_date, purchase_date1)
        self.assertEqual(cgl1.sale_date, sale_date)
        
        # Calculate expected gain for first batch
        purchase_cost1 = Decimal('200.00') * 100 + Decimal('10.00')  # 20,010
        sale_proceeds1 = Decimal('300.00') * 100 - (Decimal('20.00') * 100 / 120)  # 30,000 - 16.67 = 29,983.33
        expected_gain1 = sale_proceeds1 - purchase_cost1
        self.assertAlmostEqual(float(cgl1.gain_loss), float(expected_gain1), places=2)
        
        # Second record: 20 shares from second purchase
        cgl2 = capital_gains[1]
        self.assertEqual(cgl2.quantity, 20)
        self.assertEqual(cgl2.purchase_price, Decimal('250.00'))
        self.assertEqual(cgl2.purchase_date, purchase_date2)
    
    def test_calculate_capital_gains_losses_long_term(self):
        """Test long-term capital gains calculation (>3 years)"""
        tax_year = 2024
        
        # Purchase more than 3 years ago
        purchase_date = datetime(2020, 1, 15)
        sale_date = datetime(2024, 6, 10)
        
        self.tax_reporter.record_stock_purchase(
            symbol=self.test_symbol,
            quantity=100,
            price=Decimal('150.00'),
            commission=Decimal('10.00'),
            transaction_date=purchase_date
        )
        
        self.tax_reporter.record_stock_sale(
            symbol=self.test_symbol,
            quantity=100,
            price=Decimal('300.00'),
            commission=Decimal('15.00'),
            transaction_date=sale_date
        )
        
        capital_gains = self.tax_reporter.calculate_capital_gains_losses(tax_year)
        
        self.assertEqual(len(capital_gains), 1)
        cgl = capital_gains[0]
        
        # Check long-term status
        self.assertTrue(cgl.is_long_term)
        self.assertGreater(cgl.holding_period_days, 3 * 365)
    
    def test_generate_tax_report(self):
        """Test comprehensive tax report generation"""
        tax_year = 2024
        taxpayer_id = "123456789012"
        
        # Add some transactions
        purchase_date = datetime(2024, 1, 15)
        sale_date = datetime(2024, 6, 10)
        dividend_date = datetime(2024, 7, 15)
        
        # Stock transactions
        self.tax_reporter.record_stock_purchase(
            symbol=self.test_symbol,
            quantity=100,
            price=Decimal('200.00'),
            commission=Decimal('10.00'),
            transaction_date=purchase_date
        )
        
        self.tax_reporter.record_stock_sale(
            symbol=self.test_symbol,
            quantity=100,
            price=Decimal('250.00'),
            commission=Decimal('12.00'),
            transaction_date=sale_date
        )
        
        # Dividend
        self.tax_reporter.record_dividend(
            symbol=self.test_symbol,
            dividend_per_share=Decimal('15.00'),
            quantity=50,
            payment_date=dividend_date
        )
        
        # Generate report
        tax_report = self.tax_reporter.generate_tax_report(tax_year, taxpayer_id)
        
        # Check report structure
        self.assertEqual(tax_report.tax_year, tax_year)
        self.assertEqual(tax_report.taxpayer_id, taxpayer_id)
        self.assertEqual(tax_report.currency, "RUB")
        
        # Check capital gains
        self.assertEqual(len(tax_report.capital_gains), 1)
        self.assertGreater(tax_report.total_capital_gains, 0)
        self.assertGreater(tax_report.net_capital_gains, 0)
        
        # Check dividends
        self.assertEqual(len(tax_report.dividend_records), 1)
        self.assertEqual(tax_report.total_dividend_income, Decimal('750.00'))  # 15 * 50
        
        # Check tax calculations
        self.assertGreater(tax_report.taxable_income, 0)
        self.assertGreaterEqual(tax_report.estimated_tax_due, 0)
        self.assertEqual(tax_report.tax_rate, Decimal('0.13'))
    
    def test_export_tax_report_to_dict(self):
        """Test tax report export to dictionary"""
        tax_year = 2024
        
        # Add minimal data
        self.tax_reporter.record_stock_purchase(
            symbol=self.test_symbol,
            quantity=100,
            price=Decimal('200.00'),
            commission=Decimal('10.00'),
            transaction_date=datetime(2024, 1, 15)
        )
        
        tax_report = self.tax_reporter.generate_tax_report(tax_year)
        report_dict = self.tax_reporter.export_tax_report_to_dict(tax_report)
        
        # Check structure
        self.assertIn("tax_year", report_dict)
        self.assertIn("summary", report_dict)
        self.assertIn("capital_gains_losses", report_dict)
        self.assertIn("dividends", report_dict)
        self.assertIn("tax_events_summary", report_dict)
        
        # Check summary values
        summary = report_dict["summary"]
        self.assertIn("total_capital_gains", summary)
        self.assertIn("total_capital_losses", summary)
        self.assertIn("net_capital_gains", summary)
        self.assertIn("taxable_income", summary)
        self.assertIn("estimated_tax_due", summary)
    
    def test_generate_russian_tax_form_data(self):
        """Test Russian tax form data generation"""
        tax_year = 2024
        
        # Add test data
        self.tax_reporter.record_stock_purchase(
            symbol=self.test_symbol,
            quantity=100,
            price=Decimal('200.00'),
            commission=Decimal('10.00'),
            transaction_date=datetime(2024, 1, 15)
        )
        
        self.tax_reporter.record_stock_sale(
            symbol=self.test_symbol,
            quantity=100,
            price=Decimal('250.00'),
            commission=Decimal('12.00'),
            transaction_date=datetime(2024, 6, 10)
        )
        
        tax_report = self.tax_reporter.generate_tax_report(tax_year)
        form_data = self.tax_reporter.generate_russian_tax_form_data(tax_report)
        
        # Check Russian form structure
        self.assertIn("Налоговый_период", form_data)
        self.assertIn("Операции_с_ценными_бумагами", form_data)
        self.assertIn("Дивидендные_доходы", form_data)
        self.assertIn("Итого", form_data)
        
        # Check securities section
        securities = form_data["Операции_с_ценными_бумагами"]
        self.assertIn("Доходы_от_реализации", securities)
        self.assertIn("Расходы_по_реализации", securities)
        self.assertIn("Финансовый_результат", securities)
        
        # Check summary section
        summary = form_data["Итого"]
        self.assertIn("Налогооблагаемый_доход", summary)
        self.assertIn("Налог_к_доплате", summary)
        self.assertIn("Ставка_налога", summary)
        self.assertEqual(summary["Ставка_налога"], "13%")
    
    def test_get_tax_events_for_year(self):
        """Test filtering tax events by year"""
        # Add events for different years
        self.tax_reporter.record_stock_purchase(
            symbol=self.test_symbol,
            quantity=100,
            price=Decimal('200.00'),
            commission=Decimal('10.00'),
            transaction_date=datetime(2023, 6, 15)
        )
        
        self.tax_reporter.record_stock_purchase(
            symbol=self.test_symbol,
            quantity=150,
            price=Decimal('250.00'),
            commission=Decimal('15.00'),
            transaction_date=datetime(2024, 3, 20)
        )
        
        # Get events for 2024
        events_2024 = self.tax_reporter.get_tax_events_for_year(2024)
        self.assertEqual(len(events_2024), 1)
        self.assertEqual(events_2024[0].date.year, 2024)
        
        # Get events for 2023
        events_2023 = self.tax_reporter.get_tax_events_for_year(2023)
        self.assertEqual(len(events_2023), 1)
        self.assertEqual(events_2023[0].date.year, 2023)
    
    def test_get_dividend_records_for_year(self):
        """Test filtering dividend records by year"""
        # Add dividends for different years
        self.tax_reporter.record_dividend(
            symbol=self.test_symbol,
            dividend_per_share=Decimal('10.00'),
            quantity=100,
            payment_date=datetime(2023, 7, 15)
        )
        
        self.tax_reporter.record_dividend(
            symbol=self.test_symbol,
            dividend_per_share=Decimal('12.00'),
            quantity=150,
            payment_date=datetime(2024, 7, 20)
        )
        
        # Get dividends for 2024
        dividends_2024 = self.tax_reporter.get_dividend_records_for_year(2024)
        self.assertEqual(len(dividends_2024), 1)
        self.assertEqual(dividends_2024[0].payment_date.year, 2024)
        
        # Get dividends for 2023
        dividends_2023 = self.tax_reporter.get_dividend_records_for_year(2023)
        self.assertEqual(len(dividends_2023), 1)
        self.assertEqual(dividends_2023[0].payment_date.year, 2023)
    
    def test_calculate_tax_optimization_suggestions(self):
        """Test tax optimization suggestions generation"""
        tax_year = 2024
        
        # Add long-term holding (>3 years)
        long_term_purchase = datetime(2020, 1, 15)
        long_term_sale = datetime(2024, 6, 10)
        
        self.tax_reporter.record_stock_purchase(
            symbol=self.test_symbol,
            quantity=100,
            price=Decimal('100.00'),
            commission=Decimal('5.00'),
            transaction_date=long_term_purchase
        )
        
        self.tax_reporter.record_stock_sale(
            symbol=self.test_symbol,
            quantity=100,
            price=Decimal('200.00'),
            commission=Decimal('8.00'),
            transaction_date=long_term_sale
        )
        
        # Add high dividend income
        self.tax_reporter.record_dividend(
            symbol=self.test_symbol,
            dividend_per_share=Decimal('50.00'),
            quantity=100,
            payment_date=datetime(2024, 7, 15)
        )
        
        tax_report = self.tax_reporter.generate_tax_report(tax_year)
        suggestions = self.tax_reporter.calculate_tax_optimization_suggestions(tax_report)
        
        # Should have suggestions
        self.assertGreater(len(suggestions), 0)
        
        # Check for long-term holding suggestion
        long_term_suggestion = any("долгосрочные инвестиции" in s for s in suggestions)
        self.assertTrue(long_term_suggestion)
        
        # Check for dividend optimization suggestion
        dividend_suggestion = any("дивидендов" in s for s in suggestions)
        self.assertTrue(dividend_suggestion)
    
    def test_capital_gain_loss_dataclass(self):
        """Test CapitalGainLoss dataclass calculations"""
        purchase_date = datetime(2020, 1, 15)
        sale_date = datetime(2024, 6, 10)
        
        cgl = CapitalGainLoss(
            symbol=self.test_symbol,
            sale_date=sale_date,
            purchase_date=purchase_date,
            quantity=100,
            purchase_price=Decimal('150.00'),
            sale_price=Decimal('250.00'),
            purchase_commission=Decimal('10.00'),
            sale_commission=Decimal('12.00'),
            gain_loss=Decimal('9978.00')  # Will be calculated
        )
        
        # Check holding period calculation
        expected_days = (sale_date - purchase_date).days
        self.assertEqual(cgl.holding_period_days, expected_days)
        
        # Check long-term status (>3 years)
        self.assertTrue(cgl.is_long_term)
        self.assertGreater(cgl.holding_period_days, 3 * 365)
    
    def test_dividend_record_dataclass(self):
        """Test DividendRecord dataclass calculations"""
        dividend_per_share = Decimal('15.50')
        quantity = 200
        tax_withheld = Decimal('403.00')  # 13% of gross
        
        dividend_record = DividendRecord(
            symbol=self.test_symbol,
            payment_date=datetime(2024, 7, 15),
            dividend_per_share=dividend_per_share,
            quantity=quantity,
            gross_dividend=None,  # Will be calculated
            tax_withheld=tax_withheld,
            net_dividend=None  # Will be calculated
        )
        
        # Check calculations
        expected_gross = dividend_per_share * quantity  # 3100
        expected_net = expected_gross - tax_withheld  # 2697
        
        self.assertEqual(dividend_record.gross_dividend, expected_gross)
        self.assertEqual(dividend_record.net_dividend, expected_net)
    
    def test_tax_event_dataclass(self):
        """Test TaxEvent dataclass calculations"""
        tax_event = TaxEvent(
            event_id="TEST_001",
            event_type=TaxEventType.STOCK_PURCHASE,
            date=self.test_date,
            symbol=self.test_symbol,
            quantity=self.test_quantity,
            price=self.test_price,
            commission=self.test_commission,
            total_amount=None  # Will be calculated
        )
        
        # Check total amount calculation
        expected_total = self.test_price * self.test_quantity + self.test_commission
        self.assertEqual(tax_event.total_amount, expected_total)
    
    def test_russian_tax_report_dataclass(self):
        """Test RussianTaxReport dataclass calculations"""
        # Create sample capital gains
        capital_gains = [
            CapitalGainLoss(
                symbol="SBER",
                sale_date=datetime(2024, 6, 10),
                purchase_date=datetime(2024, 1, 15),
                quantity=100,
                purchase_price=Decimal('200.00'),
                sale_price=Decimal('250.00'),
                purchase_commission=Decimal('10.00'),
                sale_commission=Decimal('12.00'),
                gain_loss=Decimal('4978.00')
            ),
            CapitalGainLoss(
                symbol="GAZP",
                sale_date=datetime(2024, 7, 15),
                purchase_date=datetime(2024, 2, 20),
                quantity=50,
                purchase_price=Decimal('300.00'),
                sale_price=Decimal('280.00'),
                purchase_commission=Decimal('8.00'),
                sale_commission=Decimal('7.00'),
                gain_loss=Decimal('-1015.00')
            )
        ]
        
        # Create sample dividend records
        dividend_records = [
            DividendRecord(
                symbol="SBER",
                payment_date=datetime(2024, 7, 15),
                dividend_per_share=Decimal('12.50'),
                quantity=100,
                gross_dividend=Decimal('1250.00'),
                tax_withheld=Decimal('162.50'),
                net_dividend=Decimal('1087.50')
            )
        ]
        
        tax_report = RussianTaxReport(
            tax_year=2024,
            taxpayer_id="123456789012",
            capital_gains=capital_gains,
            total_capital_gains=Decimal('0'),  # Will be calculated
            total_capital_losses=Decimal('0'),
            net_capital_gains=Decimal('0'),
            dividend_records=dividend_records,
            total_dividend_income=Decimal('0'),
            total_dividend_tax_withheld=Decimal('0'),
            total_broker_commissions=Decimal('37.00'),
            total_other_expenses=Decimal('0'),
            taxable_income=Decimal('0'),
            estimated_tax_due=Decimal('0')
        )
        
        # Check calculations
        self.assertEqual(tax_report.total_capital_gains, Decimal('4978.00'))
        self.assertEqual(tax_report.total_capital_losses, Decimal('1015.00'))
        self.assertEqual(tax_report.net_capital_gains, Decimal('3963.00'))
        self.assertEqual(tax_report.total_dividend_income, Decimal('1250.00'))
        self.assertEqual(tax_report.total_dividend_tax_withheld, Decimal('162.50'))
        
        # Taxable income = net capital gains + dividend income
        expected_taxable = Decimal('3963.00') + Decimal('1250.00')
        self.assertEqual(tax_report.taxable_income, expected_taxable)
        
        # Estimated tax = 13% of taxable income minus withheld tax
        expected_tax = expected_taxable * Decimal('0.13') - Decimal('162.50')
        self.assertEqual(tax_report.estimated_tax_due, expected_tax)


if __name__ == '__main__':
    unittest.main()