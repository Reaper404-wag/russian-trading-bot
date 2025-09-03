import React, { useState, useEffect } from 'react';
import { Card, Select, Space, Typography, Row, Col, Statistic, DatePicker } from 'antd';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, AreaChart, Area } from 'recharts';
import { useTranslation } from 'react-i18next';
import { ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';
import moment from 'moment';

const { Title, Text } = Typography;
const { Option } = Select;
const { RangePicker } = DatePicker;

const PortfolioPerformanceChart = ({ height = 400 }) => {
  const { t } = useTranslation();
  const [timeRange, setTimeRange] = useState('1M');
  const [chartType, setChartType] = useState('portfolio');
  const [performanceData, setPerformanceData] = useState([]);
  const [benchmarkData, setBenchmarkData] = useState([]);
  const [stats, setStats] = useState({
    totalReturn: 0,
    sharpeRatio: 0,
    maxDrawdown: 0,
    volatility: 0
  });

  useEffect(() => {
    generatePerformanceData();
  }, [timeRange]);

  const generatePerformanceData = () => {
    const periods = {
      '1D': { days: 1, interval: 'hour' },
      '1W': { days: 7, interval: 'day' },
      '1M': { days: 30, interval: 'day' },
      '3M': { days: 90, interval: 'day' },
      '6M': { days: 180, interval: 'day' },
      '1Y': { days: 365, interval: 'day' }
    };

    const period = periods[timeRange];
    const data = [];
    const benchmark = [];
    
    let portfolioValue = 1000000; // Starting value 1M RUB
    let moexValue = 2800; // Starting MOEX index
    let rtsValue = 1150; // Starting RTS index
    
    const portfolioVolatility = 0.015; // 1.5% daily volatility
    const moexVolatility = 0.012; // 1.2% daily volatility
    const rtsVolatility = 0.018; // 1.8% daily volatility
    
    for (let i = 0; i <= period.days; i++) {
      const date = moment().subtract(period.days - i, 'days');
      
      // Generate portfolio performance (slightly outperforming market)
      const portfolioChange = (Math.random() - 0.45) * portfolioVolatility; // Slight positive bias
      portfolioValue *= (1 + portfolioChange);
      
      // Generate MOEX performance
      const moexChange = (Math.random() - 0.5) * moexVolatility;
      moexValue *= (1 + moexChange);
      
      // Generate RTS performance (more volatile)
      const rtsChange = (Math.random() - 0.5) * rtsVolatility;
      rtsValue *= (1 + rtsChange);
      
      const dataPoint = {
        date: date.format('YYYY-MM-DD'),
        dateDisplay: date.format('DD.MM'),
        portfolio: Math.round(portfolioValue),
        portfolioReturn: ((portfolioValue - 1000000) / 1000000 * 100),
        moex: Math.round(moexValue * 100) / 100,
        moexReturn: ((moexValue - 2800) / 2800 * 100),
        rts: Math.round(rtsValue * 100) / 100,
        rtsReturn: ((rtsValue - 1150) / 1150 * 100),
        drawdown: Math.random() * -5, // Mock drawdown
        sharpe: 1.2 + Math.random() * 0.5 // Mock Sharpe ratio
      };
      
      data.push(dataPoint);
    }
    
    setPerformanceData(data);
    
    // Calculate statistics
    const finalData = data[data.length - 1];
    const initialData = data[0];
    
    setStats({
      totalReturn: finalData.portfolioReturn,
      sharpeRatio: 1.45,
      maxDrawdown: -3.2,
      volatility: 12.8
    });
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'RUB',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };

  const formatPercent = (value) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="custom-tooltip" style={{
          backgroundColor: 'white',
          padding: '10px',
          border: '1px solid #ccc',
          borderRadius: '4px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
        }}>
          <p style={{ margin: 0, fontWeight: 'bold' }}>{`Дата: ${label}`}</p>
          {payload.map((entry, index) => (
            <p key={index} style={{ margin: '4px 0', color: entry.color }}>
              {entry.name === 'portfolio' && `Портфель: ${formatCurrency(entry.value)}`}
              {entry.name === 'portfolioReturn' && `Доходность: ${formatPercent(entry.value)}`}
              {entry.name === 'moexReturn' && `MOEX: ${formatPercent(entry.value)}`}
              {entry.name === 'rtsReturn' && `RTS: ${formatPercent(entry.value)}`}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  const renderChart = () => {
    if (chartType === 'portfolio') {
      return (
        <ResponsiveContainer width="100%" height={height - 100}>
          <AreaChart data={performanceData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis 
              dataKey="dateDisplay" 
              tick={{ fontSize: 12 }}
            />
            <YAxis 
              tick={{ fontSize: 12 }}
              tickFormatter={formatCurrency}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend />
            <Area
              type="monotone"
              dataKey="portfolio"
              stroke="#1890ff"
              fill="#1890ff"
              fillOpacity={0.3}
              name="Стоимость портфеля"
            />
          </AreaChart>
        </ResponsiveContainer>
      );
    } else {
      return (
        <ResponsiveContainer width="100%" height={height - 100}>
          <LineChart data={performanceData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis 
              dataKey="dateDisplay" 
              tick={{ fontSize: 12 }}
            />
            <YAxis 
              tick={{ fontSize: 12 }}
              tickFormatter={(value) => `${value.toFixed(1)}%`}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend />
            <Line
              type="monotone"
              dataKey="portfolioReturn"
              stroke="#1890ff"
              strokeWidth={2}
              name="Портфель"
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="moexReturn"
              stroke="#52c41a"
              strokeWidth={2}
              name="MOEX"
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="rtsReturn"
              stroke="#fa8c16"
              strokeWidth={2}
              name="RTS"
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      );
    }
  };

  return (
    <Card
      title={
        <Title level={4} style={{ margin: 0 }}>
          {t('charts.portfolioPerformance')}
        </Title>
      }
      extra={
        <Space>
          <Select
            value={chartType}
            onChange={setChartType}
            style={{ width: 150 }}
            size="small"
          >
            <Option value="portfolio">{t('charts.portfolioValue')}</Option>
            <Option value="returns">{t('charts.returns')}</Option>
          </Select>
          <Select
            value={timeRange}
            onChange={setTimeRange}
            style={{ width: 80 }}
            size="small"
          >
            <Option value="1D">1Д</Option>
            <Option value="1W">1Н</Option>
            <Option value="1M">1М</Option>
            <Option value="3M">3М</Option>
            <Option value="6M">6М</Option>
            <Option value="1Y">1Г</Option>
          </Select>
        </Space>
      }
    >
      {/* Performance Statistics */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Statistic
            title={t('portfolio.totalReturn')}
            value={stats.totalReturn}
            precision={2}
            suffix="%"
            prefix={stats.totalReturn >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
            valueStyle={{ color: stats.totalReturn >= 0 ? '#3f8600' : '#cf1322' }}
          />
        </Col>
        <Col span={6}>
          <Statistic
            title={t('portfolio.sharpeRatio')}
            value={stats.sharpeRatio}
            precision={2}
            valueStyle={{ color: stats.sharpeRatio >= 1 ? '#3f8600' : '#faad14' }}
          />
        </Col>
        <Col span={6}>
          <Statistic
            title={t('portfolio.maxDrawdown')}
            value={stats.maxDrawdown}
            precision={2}
            suffix="%"
            valueStyle={{ color: '#cf1322' }}
          />
        </Col>
        <Col span={6}>
          <Statistic
            title={t('portfolio.volatility')}
            value={stats.volatility}
            precision={1}
            suffix="%"
            valueStyle={{ color: '#1890ff' }}
          />
        </Col>
      </Row>

      {/* Chart */}
      {renderChart()}
    </Card>
  );
};

export default PortfolioPerformanceChart;