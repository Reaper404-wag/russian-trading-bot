"""
Example usage of Russian tax reporting service
Demonstrates capital gains/losses calculation, dividend tracking, and tax report generation
"""

import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal
import json

# Add the parent directory to the path to import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from russian_trading_bot.services.russian_tax_reporter import (
    RussianTaxReporter, TaxCalculationMethod
)
from russian_trading_bot.services.transaction_logger import RussianTransactionLogger


def main():
    """Demonstrate Russian tax reporting functionality"""
    print("=== Демонстрация системы налогового учета для российских инвесторов ===\n")
    
    # Initialize services
    print("1. Инициализация сервисов...")
    transaction_logger = RussianTransactionLogger(
        log_directory="logs/tax_example",
        retention_days=2555  # 7 years as required by Russian law
    )
    
    tax_reporter = RussianTaxReporter(
        transaction_logger=transaction_logger,
        calculation_method=TaxCalculationMethod.FIFO
    )
    print("✓ Сервисы инициализированы\n")
    
    # Example 1: Record stock transactions
    print("2. Запись операций с акциями...")
    
    # Purchase SBER shares in January
    sber_purchase1 = tax_reporter.record_stock_purchase(
        symbol="SBER",
        quantity=100,
        price=Decimal('250.50'),
        commission=Decimal('15.00'),
        transaction_date=datetime(2024, 1, 15, 10, 30)
    )
    print(f"✓ Покупка SBER: 100 акций по 250.50 руб. (ID: {sber_purchase1})")
    
    # Purchase more SBER shares in March at different price
    sber_purchase2 = tax_reporter.record_stock_purchase(
        symbol="SBER",
        quantity=150,
        price=Decimal('275.25'),
        commission=Decimal('20.00'),
        transaction_date=datetime(2024, 3, 20, 14, 15)
    )
    print(f"✓ Покупка SBER: 150 акций по 275.25 руб. (ID: {sber_purchase2})")
    
    # Purchase GAZP shares
    gazp_purchase = tax_reporter.record_stock_purchase(
        symbol="GAZP",
        quantity=200,
        price=Decimal('180.75'),
        commission=Decimal('25.00'),
        transaction_date=datetime(2024, 2, 10, 11, 45)
    )
    print(f"✓ Покупка GAZP: 200 акций по 180.75 руб. (ID: {gazp_purchase})")
    
    # Sell some SBER shares (FIFO - will sell from first purchase first)
    sber_sale1 = tax_reporter.record_stock_sale(
        symbol="SBER",
        quantity=120,
        price=Decimal('290.00'),
        commission=Decimal('18.50'),
        transaction_date=datetime(2024, 6, 15, 13, 20)
    )
    print(f"✓ Продажа SBER: 120 акций по 290.00 руб. (ID: {sber_sale1})")
    
    # Sell GAZP shares at a loss
    gazp_sale = tax_reporter.record_stock_sale(
        symbol="GAZP",
        quantity=100,
        price=Decimal('165.50'),
        commission=Decimal('16.75'),
        transaction_date=datetime(2024, 8, 5, 15, 30)
    )
    print(f"✓ Продажа GAZP: 100 акций по 165.50 руб. (ID: {gazp_sale})")
    print()
    
    # Example 2: Record dividends
    print("3. Запись дивидендов...")
    
    # SBER dividend
    sber_dividend = tax_reporter.record_dividend(
        symbol="SBER",
        dividend_per_share=Decimal('18.70'),
        quantity=130,  # Remaining SBER shares after sale
        payment_date=datetime(2024, 7, 15, 12, 0),
        ex_dividend_date=datetime(2024, 6, 25)
    )
    print(f"✓ Дивиденды SBER: 18.70 руб. за акцию × 130 акций (ID: {sber_dividend})")
    
    # GAZP dividend
    gazp_dividend = tax_reporter.record_dividend(
        symbol="GAZP",
        dividend_per_share=Decimal('16.61'),
        quantity=100,  # Remaining GAZP shares after sale
        payment_date=datetime(2024, 9, 10, 12, 0)
    )
    print(f"✓ Дивиденды GAZP: 16.61 руб. за акцию × 100 акций (ID: {gazp_dividend})")
    print()
    
    # Example 3: Calculate capital gains/losses
    print("4. Расчет прибылей и убытков от реализации...")
    tax_year = 2024
    capital_gains = tax_reporter.calculate_capital_gains_losses(tax_year)
    
    print(f"Найдено {len(capital_gains)} операций реализации:")
    total_gains = Decimal('0')
    total_losses = Decimal('0')
    
    for i, cgl in enumerate(capital_gains, 1):
        print(f"\n  {i}. {cgl.symbol}:")
        print(f"     Дата покупки: {cgl.purchase_date.strftime('%d.%m.%Y')}")
        print(f"     Дата продажи: {cgl.sale_date.strftime('%d.%m.%Y')}")
        print(f"     Количество: {cgl.quantity} акций")
        print(f"     Цена покупки: {cgl.purchase_price:.2f} руб.")
        print(f"     Цена продажи: {cgl.sale_price:.2f} руб.")
        print(f"     Комиссии: {cgl.purchase_commission + cgl.sale_commission:.2f} руб.")
        print(f"     Результат: {cgl.gain_loss:.2f} руб.")
        print(f"     Период владения: {cgl.holding_period_days} дней")
        print(f"     Долгосрочная инвестиция: {'Да' if cgl.is_long_term else 'Нет'}")
        
        if cgl.gain_loss > 0:
            total_gains += cgl.gain_loss
        else:
            total_losses += abs(cgl.gain_loss)
    
    print(f"\nИтого прибыль: {total_gains:.2f} руб.")
    print(f"Итого убытки: {total_losses:.2f} руб.")
    print(f"Чистый результат: {total_gains - total_losses:.2f} руб.")
    print()
    
    # Example 4: Generate comprehensive tax report
    print("5. Формирование налогового отчета...")
    taxpayer_id = "123456789012"
    tax_report = tax_reporter.generate_tax_report(tax_year, taxpayer_id)
    
    print(f"Налоговый отчет за {tax_year} год:")
    print(f"Налогоплательщик: {tax_report.taxpayer_id}")
    print(f"Валюта: {tax_report.currency}")
    print(f"Дата формирования: {tax_report.generated_at.strftime('%d.%m.%Y %H:%M')}")
    print()
    
    print("Операции с ценными бумагами:")
    print(f"  Общая прибыль от реализации: {tax_report.total_capital_gains:.2f} руб.")
    print(f"  Общие убытки от реализации: {tax_report.total_capital_losses:.2f} руб.")
    print(f"  Чистый результат: {tax_report.net_capital_gains:.2f} руб.")
    print()
    
    print("Дивидендные доходы:")
    print(f"  Общая сумма дивидендов: {tax_report.total_dividend_income:.2f} руб.")
    print(f"  Удержанный налог: {tax_report.total_dividend_tax_withheld:.2f} руб.")
    print()
    
    print("Расходы:")
    print(f"  Брокерские комиссии: {tax_report.total_broker_commissions:.2f} руб.")
    print()
    
    print("Налоговые расчеты:")
    print(f"  Налогооблагаемый доход: {tax_report.taxable_income:.2f} руб.")
    print(f"  Ставка налога: {float(tax_report.tax_rate * 100):.0f}%")
    print(f"  Налог к доплате: {tax_report.estimated_tax_due:.2f} руб.")
    print()
    
    # Example 5: Export to different formats
    print("6. Экспорт отчета...")
    
    # Export to dictionary
    report_dict = tax_reporter.export_tax_report_to_dict(tax_report)
    print("✓ Экспорт в словарь Python")
    
    # Export Russian tax form data
    form_data = tax_reporter.generate_russian_tax_form_data(tax_report)
    print("✓ Экспорт данных для налоговой декларации")
    
    # Save to JSON file
    with open("tax_report_2024.json", "w", encoding="utf-8") as f:
        json.dump(report_dict, f, ensure_ascii=False, indent=2, default=str)
    print("✓ Сохранение в файл tax_report_2024.json")
    
    # Save Russian form data
    with open("tax_form_data_2024.json", "w", encoding="utf-8") as f:
        json.dump(form_data, f, ensure_ascii=False, indent=2, default=str)
    print("✓ Сохранение данных декларации в файл tax_form_data_2024.json")
    print()
    
    # Example 6: Tax optimization suggestions
    print("7. Рекомендации по налоговой оптимизации...")
    suggestions = tax_reporter.calculate_tax_optimization_suggestions(tax_report)
    
    if suggestions:
        for i, suggestion in enumerate(suggestions, 1):
            print(f"  {i}. {suggestion}")
    else:
        print("  Специальных рекомендаций не найдено.")
    print()
    
    # Example 7: Query historical data
    print("8. Запрос исторических данных...")
    
    # Get all tax events for the year
    tax_events = tax_reporter.get_tax_events_for_year(tax_year)
    print(f"Всего налоговых событий за {tax_year} год: {len(tax_events)}")
    
    # Get dividend records for the year
    dividend_records = tax_reporter.get_dividend_records_for_year(tax_year)
    print(f"Дивидендных выплат за {tax_year} год: {len(dividend_records)}")
    print()
    
    # Example 8: Display detailed breakdown
    print("9. Детальная разбивка по месяцам...")
    
    monthly_data = {}
    for event in tax_events:
        month_key = event.date.strftime('%Y-%m')
        if month_key not in monthly_data:
            monthly_data[month_key] = {
                'purchases': 0,
                'sales': 0,
                'dividends': 0,
                'purchase_amount': Decimal('0'),
                'sale_amount': Decimal('0'),
                'dividend_amount': Decimal('0')
            }
        
        if event.event_type.value == 'stock_purchase':
            monthly_data[month_key]['purchases'] += 1
            monthly_data[month_key]['purchase_amount'] += event.total_amount
        elif event.event_type.value == 'stock_sale':
            monthly_data[month_key]['sales'] += 1
            monthly_data[month_key]['sale_amount'] += event.total_amount
        elif event.event_type.value == 'dividend_received':
            monthly_data[month_key]['dividends'] += 1
            monthly_data[month_key]['dividend_amount'] += event.total_amount
    
    for month, data in sorted(monthly_data.items()):
        month_name = datetime.strptime(month, '%Y-%m').strftime('%B %Y')
        print(f"\n  {month_name}:")
        if data['purchases'] > 0:
            print(f"    Покупки: {data['purchases']} операций на сумму {data['purchase_amount']:.2f} руб.")
        if data['sales'] > 0:
            print(f"    Продажи: {data['sales']} операций на сумму {data['sale_amount']:.2f} руб.")
        if data['dividends'] > 0:
            print(f"    Дивиденды: {data['dividends']} выплат на сумму {data['dividend_amount']:.2f} руб.")
    
    print("\n=== Демонстрация завершена ===")
    print("\nФайлы созданы:")
    print("- tax_report_2024.json - полный налоговый отчет")
    print("- tax_form_data_2024.json - данные для налоговой декларации")
    print("- logs/tax_example/ - логи транзакций")


if __name__ == "__main__":
    main()