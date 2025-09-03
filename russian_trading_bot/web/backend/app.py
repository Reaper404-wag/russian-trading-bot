from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import os
from datetime import datetime, timedelta
import random

app = Flask(__name__, static_folder='../build', static_url_path='')
CORS(app)

# Mock data for demonstration
MOCK_PORTFOLIO = {
    'totalValue': 1250000,
    'cashBalance': 350000,
    'dailyPnL': 15000,
    'totalReturn': 8.5,
    'positions': [
        {
            'symbol': 'SBER',
            'name': 'Сбербанк',
            'quantity': 500,
            'avgPrice': 280.50,
            'currentPrice': 285.50,
            'marketValue': 142750,
            'unrealizedPnL': 2500,
            'change': 1.78
        },
        {
            'symbol': 'GAZP',
            'name': 'Газпром',
            'quantity': 300,
            'avgPrice': 180.20,
            'currentPrice': 178.20,
            'marketValue': 53460,
            'unrealizedPnL': -600,
            'change': -1.11
        },
        {
            'symbol': 'LKOH',
            'name': 'ЛУКОЙЛ',
            'quantity': 100,
            'avgPrice': 6850.00,
            'currentPrice': 7120.00,
            'marketValue': 712000,
            'unrealizedPnL': 27000,
            'change': 3.94
        }
    ]
}

MOCK_MARKET_DATA = {
    'marketStatus': 'open',
    'moexIndex': 2845.67,
    'rtsIndex': 1156.23,
    'moexChange': 1.2,
    'rtsChange': -0.8,
    'timestamp': datetime.now().isoformat()
}

@app.route('/')
def serve():
    """Serve the React app"""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/portfolio')
def get_portfolio():
    """Get portfolio data"""
    return jsonify(MOCK_PORTFOLIO)

@app.route('/api/market-data')
def get_market_data():
    """Get market data"""
    # Add some random variation to simulate real-time updates
    market_data = MOCK_MARKET_DATA.copy()
    market_data['moexIndex'] += random.uniform(-5, 5)
    market_data['rtsIndex'] += random.uniform(-3, 3)
    market_data['timestamp'] = datetime.now().isoformat()
    return jsonify(market_data)

@app.route('/api/trading-history')
def get_trading_history():
    """Get trading history"""
    history = [
        {
            'id': 1,
            'date': '2024-01-15',
            'time': '10:30:15',
            'symbol': 'SBER',
            'name': 'Сбербанк',
            'action': 'buy',
            'quantity': 100,
            'price': 280.50,
            'total': 28050,
            'status': 'executed',
            'reasoning': 'Технический анализ показывает пробой уровня сопротивления. RSI в зоне перепроданности.'
        },
        {
            'id': 2,
            'date': '2024-01-15',
            'time': '11:45:22',
            'symbol': 'GAZP',
            'name': 'Газпром',
            'action': 'sell',
            'quantity': 50,
            'price': 178.20,
            'total': 8910,
            'status': 'executed',
            'reasoning': 'Фиксация прибыли после достижения целевого уровня. Негативные новости по сектору.'
        }
    ]
    return jsonify(history)

@app.route('/api/dashboard-stats')
def get_dashboard_stats():
    """Get dashboard statistics"""
    stats = {
        'portfolioValue': MOCK_PORTFOLIO['totalValue'],
        'dailyPnL': MOCK_PORTFOLIO['dailyPnL'],
        'totalReturn': MOCK_PORTFOLIO['totalReturn'],
        'cashBalance': MOCK_PORTFOLIO['cashBalance'],
        'marketStatus': MOCK_MARKET_DATA['marketStatus'],
        'moexIndex': MOCK_MARKET_DATA['moexIndex'],
        'rtsIndex': MOCK_MARKET_DATA['rtsIndex'],
        'moexChange': MOCK_MARKET_DATA['moexChange'],
        'rtsChange': MOCK_MARKET_DATA['rtsChange']
    }
    return jsonify(stats)

@app.route('/api/real-time-data/<symbol>')
def get_real_time_data(symbol):
    """Get real-time stock data for charts"""
    # Generate mock real-time data
    base_prices = {
        'SBER': 285.50,
        'GAZP': 178.20,
        'LKOH': 7120.00,
        'ROSN': 550.80,
        'NVTK': 1890.00,
        'YNDX': 2450.00,
        'MGNT': 6800.00,
        'VTBR': 0.0285
    }
    
    base_price = base_prices.get(symbol, 100.0)
    current_price = base_price + random.uniform(-base_price * 0.02, base_price * 0.02)
    
    data = {
        'symbol': symbol,
        'price': round(current_price, 2),
        'change': round((current_price - base_price) / base_price * 100, 2),
        'volume': random.randint(10000, 100000),
        'timestamp': datetime.now().isoformat(),
        'high': round(current_price * 1.01, 2),
        'low': round(current_price * 0.99, 2),
        'open': round(base_price, 2)
    }
    return jsonify(data)

@app.route('/api/technical-indicators/<symbol>')
def get_technical_indicators(symbol):
    """Get technical indicators for a stock"""
    # Generate mock technical indicators
    rsi = random.uniform(20, 80)
    macd = random.uniform(-2, 2)
    
    indicators = {
        'symbol': symbol,
        'rsi': round(rsi, 2),
        'macd': round(macd, 3),
        'signal': 'buy' if rsi < 30 or macd > 0 else 'sell',
        'movingAverage20': round(285.50 + random.uniform(-10, 10), 2),
        'movingAverage50': round(285.50 + random.uniform(-20, 20), 2),
        'bollingerUpper': round(285.50 + random.uniform(5, 15), 2),
        'bollingerLower': round(285.50 - random.uniform(5, 15), 2),
        'timestamp': datetime.now().isoformat()
    }
    return jsonify(indicators)

@app.route('/api/russian-news')
def get_russian_news():
    """Get Russian financial news"""
    news_items = [
        {
            'id': 1,
            'title': 'Сбербанк увеличил прогноз по ключевой ставке ЦБ на конец года',
            'summary': 'Аналитики Сбербанка повысили прогноз по ключевой ставке ЦБ РФ на конец 2024 года до 18% с предыдущих 16%.',
            'source': 'РБК',
            'timestamp': (datetime.now() - timedelta(minutes=15)).isoformat(),
            'sentiment': 'negative',
            'impact': 'high',
            'relatedStocks': ['SBER', 'VTBR', 'GAZP'],
            'category': 'monetary_policy'
        },
        {
            'id': 2,
            'title': 'Газпром подписал новый контракт на поставку газа в Китай',
            'summary': 'Газпром заключил долгосрочный контракт на поставку природного газа в КНР объемом до 10 млрд кубометров в год.',
            'source': 'Ведомости',
            'timestamp': (datetime.now() - timedelta(minutes=45)).isoformat(),
            'sentiment': 'positive',
            'impact': 'high',
            'relatedStocks': ['GAZP', 'NVTK'],
            'category': 'energy'
        },
        {
            'id': 3,
            'title': 'ЛУКОЙЛ увеличил инвестиции в возобновляемую энергетику',
            'summary': 'Нефтяная компания ЛУКОЙЛ объявила о планах увеличить инвестиции в проекты возобновляемой энергетики на 25%.',
            'source': 'Коммерсантъ',
            'timestamp': (datetime.now() - timedelta(hours=1.5)).isoformat(),
            'sentiment': 'positive',
            'impact': 'medium',
            'relatedStocks': ['LKOH'],
            'category': 'energy'
        }
    ]
    return jsonify(news_items)

@app.route('/api/portfolio-performance')
def get_portfolio_performance():
    """Get portfolio performance data"""
    # Generate mock performance data for the last 30 days
    performance_data = []
    base_value = 1000000
    
    for i in range(30):
        date = datetime.now() - timedelta(days=29-i)
        daily_return = random.uniform(-0.02, 0.025)  # -2% to +2.5% daily return
        base_value *= (1 + daily_return)
        
        performance_data.append({
            'date': date.strftime('%Y-%m-%d'),
            'portfolioValue': round(base_value, 2),
            'dailyReturn': round(daily_return * 100, 2),
            'moexReturn': round(random.uniform(-0.015, 0.02) * 100, 2),
            'rtsReturn': round(random.uniform(-0.025, 0.03) * 100, 2)
        })
    
    return jsonify(performance_data)

@app.route('/api/trading-signals')
def get_trading_signals():
    """Get trading signals"""
    signals = [
        {
            'id': 1,
            'symbol': 'SBER',
            'name': 'Сбербанк',
            'action': 'buy',
            'confidence': 0.85,
            'targetPrice': 295.00,
            'currentPrice': 285.50,
            'stopLoss': 275.00,
            'reasoning': 'Технический анализ показывает пробой уровня сопротивления на 285 рублей. RSI находится в зоне 35, что указывает на перепроданность. MACD показывает бычий сигнал. Объем торгов увеличился на 25% по сравнению со средним.',
            'riskLevel': 'medium',
            'expectedReturn': 3.3,
            'timestamp': datetime.now().isoformat(),
            'status': 'pending'
        },
        {
            'id': 2,
            'symbol': 'GAZP',
            'name': 'Газпром',
            'action': 'sell',
            'confidence': 0.72,
            'targetPrice': 170.00,
            'currentPrice': 178.20,
            'stopLoss': 185.00,
            'reasoning': 'Негативные новости по энергетическому сектору. Цена достигла уровня сопротивления 180 рублей. RSI в зоне перекупленности (75). Геополитические риски увеличиваются.',
            'riskLevel': 'high',
            'expectedReturn': -4.6,
            'timestamp': (datetime.now() - timedelta(minutes=5)).isoformat(),
            'status': 'pending'
        },
        {
            'id': 3,
            'symbol': 'LKOH',
            'name': 'ЛУКОЙЛ',
            'action': 'hold',
            'confidence': 0.65,
            'targetPrice': 7200.00,
            'currentPrice': 7120.00,
            'stopLoss': 6900.00,
            'reasoning': 'Смешанные сигналы от технических индикаторов. Цена консолидируется в диапазоне 7000-7200. Ожидается публикация квартальных результатов через неделю.',
            'riskLevel': 'low',
            'expectedReturn': 1.1,
            'timestamp': (datetime.now() - timedelta(minutes=10)).isoformat(),
            'status': 'pending'
        }
    ]
    return jsonify(signals)

@app.route('/api/risk-assessment')
def get_risk_assessment():
    """Get risk assessment data"""
    risk_data = {
        'overallRiskScore': 65,
        'riskLevel': 'medium',
        'portfolioRisk': {
            'volatility': 18.5,
            'sharpeRatio': 1.2,
            'maxDrawdown': 12.3,
            'beta': 1.15,
            'var95': 45000
        },
        'marketRisk': {
            'moexVolatility': 22.1,
            'rubleVolatility': 15.8,
            'geopoliticalRisk': 'high',
            'sectorConcentration': 35.2,
            'liquidityRisk': 'low'
        },
        'riskFactors': [
            {
                'id': 1,
                'type': 'geopolitical',
                'severity': 'high',
                'title': 'Геополитические риски',
                'description': 'Повышенная неопределенность из-за международных санкций и геополитической напряженности',
                'impact': 'Может привести к резким колебаниям курса рубля и российских активов',
                'recommendation': 'Рекомендуется снизить размер позиций и увеличить долю защитных активов'
            },
            {
                'id': 2,
                'type': 'currency',
                'severity': 'medium',
                'title': 'Валютные риски',
                'description': 'Высокая волатильность рубля относительно основных валют',
                'impact': 'Влияет на стоимость экспортно-ориентированных компаний',
                'recommendation': 'Диверсификация по секторам с разной валютной чувствительностью'
            },
            {
                'id': 3,
                'type': 'sector',
                'severity': 'medium',
                'title': 'Секторальная концентрация',
                'description': 'Высокая концентрация в энергетическом и банковском секторах',
                'impact': 'Повышенная чувствительность к отраслевым рискам',
                'recommendation': 'Увеличить диверсификацию по секторам экономики'
            },
            {
                'id': 4,
                'type': 'liquidity',
                'severity': 'low',
                'title': 'Риски ликвидности',
                'description': 'Некоторые позиции имеют низкую ликвидность',
                'impact': 'Может затруднить быстрое закрытие позиций',
                'recommendation': 'Поддерживать достаточный уровень денежных средств'
            }
        ],
        'recommendations': [
            'Снизить общий размер позиций на 15-20% до улучшения рыночных условий',
            'Увеличить долю защитных активов (облигации, золото) до 25%',
            'Установить более жесткие стоп-лоссы для волатильных позиций',
            'Регулярно пересматривать портфель с учетом изменения рисков'
        ],
        'lastUpdated': datetime.now().isoformat()
    }
    return jsonify(risk_data)

@app.route('/api/notifications')
def get_notifications():
    """Get notifications and alerts"""
    notifications = [
        {
            'id': 1,
            'type': 'price',
            'severity': 'high',
            'title': 'Резкое падение цены SBER',
            'message': 'Цена акций Сбербанка упала на 5.2% за последние 30 минут. Текущая цена: 270.50 ₽',
            'symbol': 'SBER',
            'timestamp': datetime.now().isoformat(),
            'read': False,
            'actionRequired': True
        },
        {
            'id': 2,
            'type': 'risk',
            'severity': 'medium',
            'title': 'Превышен лимит риска по портфелю',
            'message': 'Общий риск портфеля превысил установленный лимит в 70%. Рекомендуется пересмотреть позиции.',
            'timestamp': (datetime.now() - timedelta(minutes=5)).isoformat(),
            'read': False,
            'actionRequired': True
        },
        {
            'id': 3,
            'type': 'news',
            'severity': 'high',
            'title': 'Важные новости по энергетическому сектору',
            'message': 'ЦБ РФ объявил о новых мерах поддержки энергетических компаний. Ожидается рост котировок.',
            'relatedStocks': ['GAZP', 'LKOH', 'ROSN'],
            'timestamp': (datetime.now() - timedelta(minutes=10)).isoformat(),
            'read': True,
            'actionRequired': False
        },
        {
            'id': 4,
            'type': 'signal',
            'severity': 'medium',
            'title': 'Новый торговый сигнал: GAZP',
            'message': 'Сгенерирован сигнал на покупку GAZP с уровнем уверенности 78%. Ожидаемая доходность: +3.2%',
            'symbol': 'GAZP',
            'timestamp': (datetime.now() - timedelta(minutes=15)).isoformat(),
            'read': True,
            'actionRequired': True
        },
        {
            'id': 5,
            'type': 'system',
            'severity': 'low',
            'title': 'Обновление системы завершено',
            'message': 'Система торгового бота успешно обновлена до версии 2.1.3. Добавлены новые функции анализа.',
            'timestamp': (datetime.now() - timedelta(hours=1)).isoformat(),
            'read': True,
            'actionRequired': False
        }
    ]
    return jsonify(notifications)

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors by serving the React app"""
    return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)