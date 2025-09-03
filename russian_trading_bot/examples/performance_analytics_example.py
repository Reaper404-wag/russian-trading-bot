"""
Example usage of Russian market performance analytics service
"""

from datetime import datetime, timedelta
from decimal import Decimal
import random

from russian_trading_bot.services.performance_analytics import (
    PerformanceAnalyticsService,
    RussianIndex,
    RussianSector
)


def generate_sample_data():
    """Generate sample portfolio and benchmark data"""
    # Generate 90 days of sample data
    base_date = datetime(2024, 1, 1)
    timestamps = [base_date + timedelta(days=i) for i in range(90)]
    
    # Simulate portfolio returns with some volatility
    random.seed(42)  # For reproducible results
    portfolio_returns = []
    for i in range(90):
        # Add some trend and noise
        trend = 0.0005  # Slight positive trend
        noise = random.gauss(0, 0.015)  # 1.5% daily volatility
        portfolio_returns.append(trend + noise)
    
    # Generate portfolio values
    initial_value = 5000000.0  # 5M RUB
    portfolio_values = [initial_value]
    for ret in portfolio_returns:
        portfolio_values.append(portfolio_values[-1] * (1 + ret))
    
    # Generate MOEX returns (slightly less volatile)
    moex_returns = []
    for i in range(90):
        trend = 0.0003  # Slightly lower trend
        noise = random.gauss(0, 0.012)  # 1.2% daily volatility
        moex_returns.append(trend + noise)
    
    # Generate RTS returns (more volatile, USD-denominated)
    rts_returns = []
    for i in range(90):
        trend = 0.0004
        noise = random.gauss(0, 0.018)  # 1.8% daily volatility
        rts_returns.append(trend + noise)
    
    # Sample portfolio positions
    positions = {
        "SBER": 1500000.0,  # Banking - 30%
        "GAZP": 1000000.0,  # Oil & Gas - 20%
        "LKOH": 750000.0,   # Oil & Gas - 15%
        "GMKN": 500000.0,   # Metals & Mining - 10%
        "VTBR": 400000.0,   # Banking - 8%
        "YNDX": 350000.0,   # Technology - 7%
        "MTSS": 300000.0,   # Telecom - 6%
        "MGNT": 200000.0,   # Consumer - 4%
    }
    
    return {
        "portfolio_returns": portfolio_returns,
        "portfolio_values": portfolio_values,
        "positions": positions,
        "moex_returns": moex_returns,
        "rts_returns": rts_returns,
        "timestamps": timestamps
    }


def main():
    """Demonstrate performance analytics functionality"""
    print("=== ПРИМЕР ИСПОЛЬЗОВАНИЯ АНАЛИТИКИ ПРОИЗВОДИТЕЛЬНОСТИ ===\n")
    
    # Initialize the service
    analytics_service = PerformanceAnalyticsService()
    
    # Generate sample data
    print("Генерация примерных данных портфеля...")
    data = generate_sample_data()
    
    print(f"Период анализа: {len(data['timestamps'])} дней")
    print(f"Начальная стоимость портфеля: {data['portfolio_values'][0]:,.0f} ₽")
    print(f"Конечная стоимость портфеля: {data['portfolio_values'][-1]:,.0f} ₽")
    print(f"Количество позиций: {len(data['positions'])}")
    print()
    
    # Calculate comprehensive analytics
    print("Расчет комплексной аналитики производительности...")
    analytics = analytics_service.calculate_comprehensive_analytics(
        portfolio_returns=data["portfolio_returns"],
        portfolio_values=data["portfolio_values"],
        positions=data["positions"],
        moex_returns=data["moex_returns"],
        rts_returns=data["rts_returns"],
        timestamps=data["timestamps"]
    )
    
    # Generate and display the report
    print("\n" + "="*60)
    report = analytics_service.generate_performance_report(analytics)
    print(report)
    print("="*60)
    
    # Demonstrate individual metric access
    print("\n=== ДЕТАЛЬНЫЙ АНАЛИЗ МЕТРИК ===\n")
    
    print("ОСНОВНЫЕ ПОКАЗАТЕЛИ ЭФФЕКТИВНОСТИ:")
    print(f"  • Общая доходность: {analytics.total_return:.2%}")
    print(f"  • Годовая доходность: {analytics.annualized_return:.2%}")
    print(f"  • Волатильность (годовая): {analytics.volatility:.2%}")
    print(f"  • Коэффициент Шарпа: {analytics.sharpe_ratio:.3f}")
    print(f"  • Максимальная просадка: {analytics.max_drawdown:.2%}")
    print(f"  • Коэффициент Кальмара: {analytics.calmar_ratio:.3f}")
    print(f"  • Коэффициент Сортино: {analytics.sortino_ratio:.3f}")
    print(f"  • Доля прибыльных дней: {analytics.win_rate:.2%}")
    print(f"  • Фактор прибыли: {analytics.profit_factor:.3f}")
    print()
    
    print("СРАВНЕНИЕ С РОССИЙСКИМИ ИНДЕКСАМИ:")
    print("  MOEX Russia Index:")
    print(f"    - Альфа (превышение доходности): {analytics.moex_comparison.alpha:.2%}")
    print(f"    - Бета (чувствительность): {analytics.moex_comparison.beta:.3f}")
    print(f"    - Корреляция: {analytics.moex_comparison.correlation:.3f}")
    print(f"    - Ошибка отслеживания: {analytics.moex_comparison.tracking_error:.2%}")
    print(f"    - Коэффициент информации: {analytics.moex_comparison.information_ratio:.3f}")
    print()
    
    print("  RTS Index:")
    print(f"    - Альфа (превышение доходности): {analytics.rts_comparison.alpha:.2%}")
    print(f"    - Бета (чувствительность): {analytics.rts_comparison.beta:.3f}")
    print(f"    - Корреляция: {analytics.rts_comparison.correlation:.3f}")
    print(f"    - Ошибка отслеживания: {analytics.rts_comparison.tracking_error:.2%}")
    print(f"    - Коэффициент информации: {analytics.rts_comparison.information_ratio:.3f}")
    print()
    
    print("АНАЛИЗ ПО СЕКТОРАМ РОССИЙСКОГО РЫНКА:")
    for sector, perf in analytics.sector_performance.items():
        sector_name = sector.value.replace('_', ' ').title()
        print(f"  {sector_name}:")
        print(f"    - Доля в портфеле: {perf.weight_in_portfolio:.2%}")
        print(f"    - Общая доходность: {perf.total_return:.2%}")
        print(f"    - Дневная доходность: {perf.daily_return:.2%}")
        print(f"    - Волатильность: {perf.volatility:.2%}")
        print(f"    - Коэффициент Шарпа: {perf.sharpe_ratio:.3f}")
        print(f"    - Акции: {', '.join(perf.stocks)}")
        print()
    
    print("РИСК-МЕТРИКИ:")
    for metric, value in analytics.risk_adjusted_metrics.items():
        metric_name = metric.replace('_', ' ').title()
        if 'var' in metric.lower() or 'alpha' in metric.lower():
            print(f"  • {metric_name}: {value:.2%}")
        else:
            print(f"  • {metric_name}: {value:.3f}")
    print()
    
    # Demonstrate sector mappings
    print("=== МАППИНГ РОССИЙСКИХ АКЦИЙ ПО СЕКТОРАМ ===\n")
    sector_groups = {}
    for symbol, sector in analytics_service.sector_mappings.items():
        if sector not in sector_groups:
            sector_groups[sector] = []
        sector_groups[sector].append(symbol)
    
    for sector, symbols in sector_groups.items():
        sector_name = sector.value.replace('_', ' ').title()
        print(f"{sector_name}: {', '.join(sorted(symbols))}")
    print()
    
    # Performance interpretation
    print("=== ИНТЕРПРЕТАЦИЯ РЕЗУЛЬТАТОВ ===\n")
    
    if analytics.sharpe_ratio > 1.0:
        print("✅ ОТЛИЧНЫЙ коэффициент Шарпа (>1.0) - портфель показывает хорошую доходность с учетом риска")
    elif analytics.sharpe_ratio > 0.5:
        print("✅ ХОРОШИЙ коэффициент Шарпа (>0.5) - приемлемое соотношение доходности и риска")
    else:
        print("⚠️  НИЗКИЙ коэффициент Шарпа (<0.5) - стоит пересмотреть стратегию")
    
    if analytics.max_drawdown > -0.10:
        print("✅ УМЕРЕННАЯ максимальная просадка (<10%) - хороший контроль рисков")
    elif analytics.max_drawdown > -0.20:
        print("⚠️  ЗНАЧИТЕЛЬНАЯ максимальная просадка (10-20%) - стоит усилить риск-менеджмент")
    else:
        print("🚨 ВЫСОКАЯ максимальная просадка (>20%) - необходимо пересмотреть управление рисками")
    
    if analytics.moex_comparison.alpha > 0.02:
        print("✅ ПОЛОЖИТЕЛЬНАЯ альфа к MOEX (>2%) - портфель превосходит рынок")
    elif analytics.moex_comparison.alpha > 0:
        print("✅ НЕБОЛЬШАЯ положительная альфа к MOEX - портфель слегка превосходит рынок")
    else:
        print("⚠️  ОТРИЦАТЕЛЬНАЯ альфа к MOEX - портфель отстает от рынка")
    
    if analytics.win_rate > 0.6:
        print("✅ ВЫСОКАЯ доля прибыльных дней (>60%) - стабильная стратегия")
    elif analytics.win_rate > 0.5:
        print("✅ ХОРОШАЯ доля прибыльных дней (>50%) - сбалансированная стратегия")
    else:
        print("⚠️  НИЗКАЯ доля прибыльных дней (<50%) - стоит пересмотреть подход")
    
    print("\n=== РЕКОМЕНДАЦИИ ===\n")
    
    # Sector diversification analysis
    max_sector_weight = max(perf.weight_in_portfolio for perf in analytics.sector_performance.values())
    if max_sector_weight > 0.4:
        print("⚠️  КОНЦЕНТРАЦИЯ РИСКОВ: Один сектор занимает более 40% портфеля")
        print("   Рекомендация: Рассмотрите диверсификацию по другим секторам")
    
    # Volatility analysis
    if analytics.volatility > 0.25:
        print("⚠️  ВЫСОКАЯ ВОЛАТИЛЬНОСТЬ: Годовая волатильность превышает 25%")
        print("   Рекомендация: Рассмотрите добавление менее волатильных активов")
    
    # Beta analysis
    if analytics.moex_comparison.beta > 1.5:
        print("⚠️  ВЫСОКАЯ ЧУВСТВИТЕЛЬНОСТЬ К РЫНКУ: Бета превышает 1.5")
        print("   Рекомендация: Портфель очень чувствителен к движениям рынка")
    elif analytics.moex_comparison.beta < 0.5:
        print("ℹ️  НИЗКАЯ ЧУВСТВИТЕЛЬНОСТЬ К РЫНКУ: Бета менее 0.5")
        print("   Информация: Портфель слабо коррелирует с общим рынком")
    
    print("\n=== ЗАКЛЮЧЕНИЕ ===\n")
    print("Данный анализ производительности предоставляет комплексную оценку")
    print("эффективности торгового портфеля на российском рынке с учетом:")
    print("• Сравнения с основными российскими индексами (MOEX, RTS)")
    print("• Анализа по секторам российской экономики")
    print("• Риск-скорректированных метрик производительности")
    print("• Специфики российского рынка и валютных рисков")
    print("\nИспользуйте эти данные для принятия обоснованных инвестиционных решений!")


if __name__ == "__main__":
    main()