import React, { useState, useEffect } from 'react';
import { Card, Table, Typography, Row, Col, Statistic, Tag, Spin } from 'antd';
import { useTranslation } from 'react-i18next';
import {
  ArrowUpOutlined,
  ArrowDownOutlined
} from '@ant-design/icons';
import './Portfolio.css';

const { Title } = Typography;

const Portfolio = () => {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [portfolioData, setPortfolioData] = useState({
    totalValue: 1250000,
    cashBalance: 350000,
    dailyPnL: 15000,
    totalReturn: 8.5,
    positions: [
      {
        key: '1',
        symbol: 'SBER',
        name: 'Сбербанк',
        quantity: 500,
        avgPrice: 280.50,
        currentPrice: 285.50,
        marketValue: 142750,
        unrealizedPnL: 2500,
        change: 1.78
      },
      {
        key: '2',
        symbol: 'GAZP',
        name: 'Газпром',
        quantity: 300,
        avgPrice: 180.20,
        currentPrice: 178.20,
        marketValue: 53460,
        unrealizedPnL: -600,
        change: -1.11
      },
      {
        key: '3',
        symbol: 'LKOH',
        name: 'ЛУКОЙЛ',
        quantity: 100,
        avgPrice: 6850.00,
        currentPrice: 7120.00,
        marketValue: 712000,
        unrealizedPnL: 27000,
        change: 3.94
      },
      {
        key: '4',
        symbol: 'ROSN',
        name: 'Роснефть',
        quantity: 200,
        avgPrice: 520.30,
        currentPrice: 515.80,
        marketValue: 103160,
        unrealizedPnL: -900,
        change: -0.86
      }
    ]
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

  const formatPrice = (value) => {
    return new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'RUB',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value);
  };

  const columns = [
    {
      title: t('portfolio.symbol'),
      dataIndex: 'symbol',
      key: 'symbol',
      render: (text, record) => (
        <div>
          <div style={{ fontWeight: 'bold' }}>{text}</div>
          <div style={{ fontSize: '12px', color: '#666' }}>{record.name}</div>
        </div>
      ),
    },
    {
      title: t('portfolio.quantity'),
      dataIndex: 'quantity',
      key: 'quantity',
      align: 'right',
      render: (value) => new Intl.NumberFormat('ru-RU').format(value),
    },
    {
      title: t('portfolio.avgPrice'),
      dataIndex: 'avgPrice',
      key: 'avgPrice',
      align: 'right',
      render: (value) => formatPrice(value),
    },
    {
      title: t('portfolio.currentPrice'),
      dataIndex: 'currentPrice',
      key: 'currentPrice',
      align: 'right',
      render: (value, record) => (
        <div>
          <div>{formatPrice(value)}</div>
          <div style={{ fontSize: '12px' }}>
            <Tag color={record.change >= 0 ? 'green' : 'red'} size="small">
              {record.change >= 0 ? '+' : ''}{record.change.toFixed(2)}%
            </Tag>
          </div>
        </div>
      ),
    },
    {
      title: t('portfolio.marketValue'),
      dataIndex: 'marketValue',
      key: 'marketValue',
      align: 'right',
      render: (value) => formatCurrency(value),
    },
    {
      title: t('portfolio.unrealizedPnL'),
      dataIndex: 'unrealizedPnL',
      key: 'unrealizedPnL',
      align: 'right',
      render: (value) => (
        <span style={{ color: value >= 0 ? '#3f8600' : '#cf1322' }}>
          {value >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
          {' '}
          {formatCurrency(Math.abs(value))}
        </span>
      ),
    },
  ];

  if (loading) {
    return (
      <div className="loading-container">
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div className="portfolio-container">
      <Title level={2}>{t('portfolio.title')}</Title>
      
      {/* Portfolio Summary */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title={t('portfolio.totalValue')}
              value={portfolioData.totalValue}
              formatter={(value) => formatCurrency(value)}
              valueStyle={{ color: '#3f8600', fontSize: '24px' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title={t('portfolio.cashBalance')}
              value={portfolioData.cashBalance}
              formatter={(value) => formatCurrency(value)}
              valueStyle={{ color: '#1890ff', fontSize: '24px' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title={t('portfolio.dailyPnL')}
              value={portfolioData.dailyPnL}
              formatter={(value) => formatCurrency(value)}
              prefix={portfolioData.dailyPnL >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
              valueStyle={{ 
                color: portfolioData.dailyPnL >= 0 ? '#3f8600' : '#cf1322',
                fontSize: '24px'
              }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title={t('portfolio.totalReturn')}
              value={portfolioData.totalReturn}
              suffix="%"
              prefix={portfolioData.totalReturn >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
              valueStyle={{ 
                color: portfolioData.totalReturn >= 0 ? '#3f8600' : '#cf1322',
                fontSize: '24px'
              }}
            />
          </Card>
        </Col>
      </Row>

      {/* Positions Table */}
      <Card title={t('portfolio.positions')}>
        <Table
          columns={columns}
          dataSource={portfolioData.positions}
          pagination={false}
          scroll={{ x: 800 }}
          className="portfolio-table"
        />
      </Card>
    </div>
  );
};

export default Portfolio;