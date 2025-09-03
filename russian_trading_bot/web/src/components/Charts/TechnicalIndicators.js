import React, { useEffect, useRef, useState } from 'react';
import { createChart } from 'lightweight-charts';
import { Card, Select, Space, Typography, Switch, Row, Col, Statistic } from 'antd';
import { useTranslation } from 'react-i18next';

const { Title, Text } = Typography;
const { Option } = Select;

const TechnicalIndicators = ({ symbol = 'SBER', height = 350 }) => {
  const { t } = useTranslation();
  const chartContainerRef = useRef();
  const chart = useRef();
  const priceSeries = useRef();
  const maSeries = useRef();
  const rsiSeries = useRef();
  const [indicators, setIndicators] = useState({
    ma: true,
    rsi: true,
    macd: false,
    bollinger: false
  });
  const [technicalData, setTechnicalData] = useState({
    rsi: 0,
    macd: 0,
    signal: '',
    trend: ''
  });

  useEffect(() => {
    if (!chartContainerRef.current) return;

    // Create main chart
    chart.current = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: height,
      layout: {
        background: { color: '#ffffff' },
        textColor: '#333',
      },
      grid: {
        vertLines: { color: '#f0f0f0' },
        horzLines: { color: '#f0f0f0' },
      },
      crosshair: {
        mode: 1,
      },
      rightPriceScale: {
        borderColor: '#cccccc',
      },
      timeScale: {
        borderColor: '#cccccc',
        timeVisible: true,
        secondsVisible: false,
      },
      localization: {
        locale: 'ru-RU',
        priceFormatter: (price) => `${price.toFixed(2)} ₽`,
      },
    });

    // Add price series (line chart)
    priceSeries.current = chart.current.addLineSeries({
      color: '#2962FF',
      lineWidth: 2,
    });

    // Add moving average series
    maSeries.current = chart.current.addLineSeries({
      color: '#FF6D00',
      lineWidth: 1,
      visible: indicators.ma,
    });

    // Add RSI series on separate pane
    rsiSeries.current = chart.current.addLineSeries({
      color: '#9C27B0',
      lineWidth: 2,
      priceScaleId: 'rsi',
      visible: indicators.rsi,
    });

    // Configure RSI scale
    chart.current.priceScale('rsi').applyOptions({
      scaleMargins: {
        top: 0.8,
        bottom: 0,
      },
      borderColor: '#cccccc',
    });

    // Handle resize
    const handleResize = () => {
      if (chart.current && chartContainerRef.current) {
        chart.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    // Load initial data
    loadTechnicalData();

    return () => {
      window.removeEventListener('resize', handleResize);
      if (chart.current) {
        chart.current.remove();
      }
    };
  }, [height]);

  useEffect(() => {
    // Update indicator visibility
    if (maSeries.current) {
      maSeries.current.applyOptions({ visible: indicators.ma });
    }
    if (rsiSeries.current) {
      rsiSeries.current.applyOptions({ visible: indicators.rsi });
    }
  }, [indicators]);

  const loadTechnicalData = () => {
    // Generate mock technical data
    const data = generateTechnicalData();
    
    if (priceSeries.current && maSeries.current && rsiSeries.current) {
      priceSeries.current.setData(data.prices);
      maSeries.current.setData(data.movingAverage);
      rsiSeries.current.setData(data.rsi);
      
      // Set current technical indicators
      const lastRsi = data.rsi[data.rsi.length - 1];
      const lastPrice = data.prices[data.prices.length - 1];
      const lastMA = data.movingAverage[data.movingAverage.length - 1];
      
      setTechnicalData({
        rsi: lastRsi.value,
        macd: (Math.random() - 0.5) * 2, // Mock MACD
        signal: lastPrice.value > lastMA.value ? 'Покупка' : 'Продажа',
        trend: lastPrice.value > lastMA.value ? 'Восходящий' : 'Нисходящий'
      });
    }
  };

  const generateTechnicalData = () => {
    const prices = [];
    const movingAverage = [];
    const rsi = [];
    const basePrice = 285.50;
    let currentPrice = basePrice;
    const priceHistory = [];
    
    for (let i = 0; i < 100; i++) {
      const time = Math.floor(Date.now() / 1000) - (100 - i) * 300; // 5-minute intervals
      
      // Generate price
      const change = (Math.random() - 0.5) * 0.02 * currentPrice;
      currentPrice += change;
      priceHistory.push(currentPrice);
      
      prices.push({
        time,
        value: parseFloat(currentPrice.toFixed(2)),
      });
      
      // Calculate moving average (20 periods)
      if (i >= 19) {
        const ma = priceHistory.slice(-20).reduce((sum, price) => sum + price, 0) / 20;
        movingAverage.push({
          time,
          value: parseFloat(ma.toFixed(2)),
        });
      }
      
      // Calculate RSI (simplified)
      if (i >= 14) {
        const gains = [];
        const losses = [];
        
        for (let j = 1; j <= 14; j++) {
          const change = priceHistory[priceHistory.length - j] - priceHistory[priceHistory.length - j - 1];
          if (change > 0) gains.push(change);
          else losses.push(Math.abs(change));
        }
        
        const avgGain = gains.length > 0 ? gains.reduce((sum, gain) => sum + gain, 0) / gains.length : 0;
        const avgLoss = losses.length > 0 ? losses.reduce((sum, loss) => sum + loss, 0) / losses.length : 0;
        
        const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
        const rsiValue = 100 - (100 / (1 + rs));
        
        rsi.push({
          time,
          value: parseFloat(rsiValue.toFixed(2)),
        });
      }
    }
    
    return { prices, movingAverage, rsi };
  };

  const toggleIndicator = (indicator) => {
    setIndicators(prev => ({
      ...prev,
      [indicator]: !prev[indicator]
    }));
  };

  const getRSIColor = (rsi) => {
    if (rsi > 70) return '#f5222d'; // Overbought - red
    if (rsi < 30) return '#52c41a'; // Oversold - green
    return '#1890ff'; // Neutral - blue
  };

  const getSignalColor = (signal) => {
    return signal === 'Покупка' ? '#52c41a' : '#f5222d';
  };

  return (
    <Card 
      title={
        <Title level={4} style={{ margin: 0 }}>
          {t('charts.technicalIndicators')}
        </Title>
      }
    >
      {/* Indicator Controls */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Space>
            <Text>MA(20):</Text>
            <Switch 
              checked={indicators.ma} 
              onChange={() => toggleIndicator('ma')}
              size="small"
            />
          </Space>
        </Col>
        <Col span={6}>
          <Space>
            <Text>RSI(14):</Text>
            <Switch 
              checked={indicators.rsi} 
              onChange={() => toggleIndicator('rsi')}
              size="small"
            />
          </Space>
        </Col>
        <Col span={6}>
          <Space>
            <Text>MACD:</Text>
            <Switch 
              checked={indicators.macd} 
              onChange={() => toggleIndicator('macd')}
              size="small"
              disabled
            />
          </Space>
        </Col>
        <Col span={6}>
          <Space>
            <Text>Bollinger:</Text>
            <Switch 
              checked={indicators.bollinger} 
              onChange={() => toggleIndicator('bollinger')}
              size="small"
              disabled
            />
          </Space>
        </Col>
      </Row>

      {/* Technical Indicators Summary */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Statistic
            title="RSI(14)"
            value={technicalData.rsi}
            precision={1}
            valueStyle={{ color: getRSIColor(technicalData.rsi) }}
          />
        </Col>
        <Col span={6}>
          <Statistic
            title="MACD"
            value={technicalData.macd}
            precision={3}
            valueStyle={{ color: technicalData.macd >= 0 ? '#52c41a' : '#f5222d' }}
          />
        </Col>
        <Col span={6}>
          <Statistic
            title={t('charts.signal')}
            value={technicalData.signal}
            valueStyle={{ color: getSignalColor(technicalData.signal) }}
          />
        </Col>
        <Col span={6}>
          <Statistic
            title={t('charts.trend')}
            value={technicalData.trend}
            valueStyle={{ color: technicalData.trend === 'Восходящий' ? '#52c41a' : '#f5222d' }}
          />
        </Col>
      </Row>

      {/* Chart */}
      <div ref={chartContainerRef} style={{ width: '100%', height: `${height}px` }} />
    </Card>
  );
};

export default TechnicalIndicators;