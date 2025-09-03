import React, { useState, useEffect } from 'react';
import { Row, Col, Card, Statistic, Typography, Space, Tag, Spin } from 'antd';
import { useTranslation } from 'react-i18next';
import {
  ArrowUpOutlined,
  ArrowDownOutlined,
  ClockCircleOutlined
} from '@ant-design/icons';
import RealTimeChart from '../../components/Charts/RealTimeChart';
import TechnicalIndicators from '../../components/Charts/TechnicalIndicators';
import RussianNewsFeed from '../../components/News/RussianNewsFeed';
import PortfolioPerformanceChart from '../../components/Charts/PortfolioPerformanceChart';
import './Dashboard.css';

const { Title, Text } = Typography;

const Dashboard = () => {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [marketData, setMarketData] = useState({
    portfolioValue: 1250000,
    dailyPnL: 15000,
    totalReturn: 8.5,
    marketStatus: 'open',
    moexIndex: 2845.67,
    rtsIndex: 1156.23,
    moexChange: 1.2,
    rtsChange: -0.8
  });

  useEffect(() => {
    // Simulate data loading
    const timer = setTimeout(() => {
      setLoading(false);
    }, 1000);

    return () => clearTimeout(timer);
  }, []);

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'RUB',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };

  const getMarketStatusTag = (status) => {
    const statusMap = {
      open: { color: 'green', text: t('dashboard.open') },
      closed: { color: 'red', text: t('dashboard.closed') },
      premarket: { color: 'orange', text: t('dashboard.premarket') },
      aftermarket: { color: 'blue', text: t('dashboard.aftermarket') }
    };
    
    const statusInfo = statusMap[status] || statusMap.closed;
    return <Tag color={statusInfo.color}>{statusInfo.text}</Tag>;
  };

  if (loading) {
    return (
      <div className="loading-container">
        <Spin size="large" />
        <Text style={{ marginTop: 16 }}>{t('common.loading')}</Text>
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      <Title level={2}>{t('dashboard.title')}</Title>
      
      {/* Market Status */}
      <Card className="market-status-card" style={{ marginBottom: 24 }}>
        <Space align="center">
          <ClockCircleOutlined style={{ fontSize: 20 }} />
          <Text strong>{t('dashboard.marketStatus')}:</Text>
          {getMarketStatusTag(marketData.marketStatus)}
          <Text type="secondary">
            {new Date().toLocaleTimeString('ru-RU', {
              hour: '2-digit',
              minute: '2-digit',
              timeZone: 'Europe/Moscow'
            })} МСК
          </Text>
        </Space>
      </Card>

      {/* Portfolio Overview */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title={t('portfolio.totalValue')}
              value={marketData.portfolioValue}
              formatter={(value) => formatCurrency(value)}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title={t('portfolio.dailyPnL')}
              value={marketData.dailyPnL}
              formatter={(value) => formatCurrency(value)}
              prefix={marketData.dailyPnL >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
              valueStyle={{ color: marketData.dailyPnL >= 0 ? '#3f8600' : '#cf1322' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title={t('portfolio.totalReturn')}
              value={marketData.totalReturn}
              suffix="%"
              prefix={marketData.totalReturn >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
              valueStyle={{ color: marketData.totalReturn >= 0 ? '#3f8600' : '#cf1322' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title={t('portfolio.cashBalance')}
              value={350000}
              formatter={(value) => formatCurrency(value)}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Market Indices */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={12}>
          <Card title={t('dashboard.indices')}>
            <Row gutter={16}>
              <Col span={12}>
                <Statistic
                  title={t('dashboard.moexIndex')}
                  value={marketData.moexIndex}
                  precision={2}
                  prefix={marketData.moexChange >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
                  suffix={`(${marketData.moexChange >= 0 ? '+' : ''}${marketData.moexChange}%)`}
                  valueStyle={{ 
                    color: marketData.moexChange >= 0 ? '#3f8600' : '#cf1322',
                    fontSize: '18px'
                  }}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title={t('dashboard.rtsIndex')}
                  value={marketData.rtsIndex}
                  precision={2}
                  prefix={marketData.rtsChange >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
                  suffix={`(${marketData.rtsChange >= 0 ? '+' : ''}${marketData.rtsChange}%)`}
                  valueStyle={{ 
                    color: marketData.rtsChange >= 0 ? '#3f8600' : '#cf1322',
                    fontSize: '18px'
                  }}
                />
              </Col>
            </Row>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title={t('dashboard.recentTrades')}>
            <div className="recent-trades">
              <div className="trade-item">
                <Space justify="space-between" style={{ width: '100%' }}>
                  <Space>
                    <Text strong>SBER</Text>
                    <Tag color="green">{t('trading.buy')}</Tag>
                  </Space>
                  <Text>100 × 285.50 ₽</Text>
                </Space>
                <Text type="secondary" style={{ fontSize: '12px' }}>
                  {new Date().toLocaleString('ru-RU')}
                </Text>
              </div>
              <div className="trade-item">
                <Space justify="space-between" style={{ width: '100%' }}>
                  <Space>
                    <Text strong>GAZP</Text>
                    <Tag color="red">{t('trading.sell')}</Tag>
                  </Space>
                  <Text>50 × 178.20 ₽</Text>
                </Space>
                <Text type="secondary" style={{ fontSize: '12px' }}>
                  {new Date(Date.now() - 3600000).toLocaleString('ru-RU')}
                </Text>
              </div>
            </div>
          </Card>
        </Col>
      </Row>

      {/* Real-time Charts Section */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} xl={16}>
          <RealTimeChart height={400} />
        </Col>
        <Col xs={24} xl={8}>
          <RussianNewsFeed height={400} />
        </Col>
      </Row>

      {/* Technical Analysis and Portfolio Performance */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} xl={12}>
          <TechnicalIndicators height={350} />
        </Col>
        <Col xs={24} xl={12}>
          <PortfolioPerformanceChart height={350} />
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;