import React, { useEffect, useRef, useState } from 'react';
import { createChart } from 'lightweight-charts';
import { Card, Select, Space, Typography, Tag, Spin } from 'antd';
import { useTranslation } from 'react-i18next';
import axios from 'axios';

const { Title, Text } = Typography;
const { Option } = Select;

const RealTimeChart = ({ symbol = 'SBER', height = 400 }) => {
  const { t } = useTranslation();
  const chartContainerRef = useRef();
  const chart = useRef();
  const candlestickSeries = useRef();
  const volumeSeries = useRef();
  const [loading, setLoading] = useState(true);
  const [selectedSymbol, setSelectedSymbol] = useState(symbol);
  const [currentPrice, setCurrentPrice] = useState(null);
  const [priceChange, setPriceChange] = useState(null);

  // Russian stocks list
  const russianStocks = [
    { symbol: 'SBER', name: 'Сбербанк' },
    { symbol: 'GAZP', name: 'Газпром' },
    { symbol: 'LKOH', name: 'ЛУКОЙЛ' },
    { symbol: 'ROSN', name: 'Роснефть' },
    { symbol: 'NVTK', name: 'НОВАТЭК' },
    { symbol: 'YNDX', name: 'Яндекс' },
    { symbol: 'MGNT', name: 'Магнит' },
    { symbol: 'VTBR', name: 'ВТБ' }
  ];

  useEffect(() => {
    if (!chartContainerRef.current) return;

    // Create chart
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

    // Add candlestick series
    candlestickSeries.current = chart.current.addCandlestickSeries({
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderVisible: false,
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
    });

    // Add volume series
    volumeSeries.current = chart.current.addHistogramSeries({
      color: '#26a69a',
      priceFormat: {
        type: 'volume',
      },
      priceScaleId: '',
      scaleMargins: {
        top: 0.8,
        bottom: 0,
      },
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

    return () => {
      window.removeEventListener('resize', handleResize);
      if (chart.current) {
        chart.current.remove();
      }
    };
  }, [height]);

  useEffect(() => {
    loadChartData(selectedSymbol);
  }, [selectedSymbol]);

  const loadChartData = async (symbol) => {
    setLoading(true);
    try {
      // Generate mock historical data for the chart
      const data = generateMockData(symbol);
      
      if (candlestickSeries.current && volumeSeries.current) {
        candlestickSeries.current.setData(data.candlesticks);
        volumeSeries.current.setData(data.volumes);
        
        // Set current price from last candle
        const lastCandle = data.candlesticks[data.candlesticks.length - 1];
        setCurrentPrice(lastCandle.close);
        setPriceChange(((lastCandle.close - lastCandle.open) / lastCandle.open * 100));
      }
      
      setLoading(false);
    } catch (error) {
      console.error('Error loading chart data:', error);
      setLoading(false);
    }
  };

  const generateMockData = (symbol) => {
    const candlesticks = [];
    const volumes = [];
    const basePrice = getBasePrice(symbol);
    let currentPrice = basePrice;
    
    // Generate 100 data points for the last 100 minutes
    for (let i = 0; i < 100; i++) {
      const time = Math.floor(Date.now() / 1000) - (100 - i) * 60; // 1 minute intervals
      
      const open = currentPrice;
      const volatility = 0.02; // 2% volatility
      const change = (Math.random() - 0.5) * volatility * currentPrice;
      const close = open + change;
      const high = Math.max(open, close) + Math.random() * 0.01 * currentPrice;
      const low = Math.min(open, close) - Math.random() * 0.01 * currentPrice;
      const volume = Math.floor(Math.random() * 10000) + 1000;
      
      candlesticks.push({
        time,
        open: parseFloat(open.toFixed(2)),
        high: parseFloat(high.toFixed(2)),
        low: parseFloat(low.toFixed(2)),
        close: parseFloat(close.toFixed(2)),
      });
      
      volumes.push({
        time,
        value: volume,
        color: close >= open ? '#26a69a' : '#ef5350',
      });
      
      currentPrice = close;
    }
    
    return { candlesticks, volumes };
  };

  const getBasePrice = (symbol) => {
    const basePrices = {
      'SBER': 285.50,
      'GAZP': 178.20,
      'LKOH': 7120.00,
      'ROSN': 550.80,
      'NVTK': 1890.00,
      'YNDX': 2450.00,
      'MGNT': 6800.00,
      'VTBR': 0.0285
    };
    return basePrices[symbol] || 100;
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'RUB',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value);
  };

  return (
    <Card 
      title={
        <Space>
          <Title level={4} style={{ margin: 0 }}>
            {t('charts.realTimePrice')}
          </Title>
          <Select
            value={selectedSymbol}
            onChange={setSelectedSymbol}
            style={{ width: 200 }}
          >
            {russianStocks.map(stock => (
              <Option key={stock.symbol} value={stock.symbol}>
                {stock.symbol} - {stock.name}
              </Option>
            ))}
          </Select>
        </Space>
      }
      extra={
        currentPrice && (
          <Space>
            <Text strong style={{ fontSize: '16px' }}>
              {formatCurrency(currentPrice)}
            </Text>
            <Tag color={priceChange >= 0 ? 'green' : 'red'}>
              {priceChange >= 0 ? '+' : ''}{priceChange?.toFixed(2)}%
            </Tag>
          </Space>
        )
      }
    >
      {loading ? (
        <div style={{ textAlign: 'center', padding: '50px' }}>
          <Spin size="large" />
          <div style={{ marginTop: 16 }}>
            <Text>{t('common.loading')}</Text>
          </div>
        </div>
      ) : (
        <div ref={chartContainerRef} style={{ width: '100%', height: `${height}px` }} />
      )}
    </Card>
  );
};

export default RealTimeChart;