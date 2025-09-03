import React, { useState } from 'react';
import { Row, Col, Tabs, Typography, Space, Button, Card } from 'antd';
import { useTranslation } from 'react-i18next';
import {
  SignalFilled,
  ShieldCheckOutlined,
  BellOutlined,
  BarChartOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import TradingSignals from '../../components/Trading/TradingSignals';
import RiskAssessment from '../../components/Trading/RiskAssessment';
import NotificationSystem from '../../components/Trading/NotificationSystem';
import './TradingDecisions.css';

const { Title, Text } = Typography;

const TradingDecisions = () => {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState('signals');
  const [refreshing, setRefreshing] = useState(false);

  const handleRefreshAll = async () => {
    setRefreshing(true);
    // Simulate refresh delay
    setTimeout(() => {
      setRefreshing(false);
    }, 1000);
  };

  const tabItems = [
    {
      key: 'signals',
      label: (
        <Space>
          <SignalFilled />
          {t('trading.decisions.tabs.signals')}
        </Space>
      ),
      children: <TradingSignals />
    },
    {
      key: 'risk',
      label: (
        <Space>
          <ShieldCheckOutlined />
          {t('trading.decisions.tabs.risk')}
        </Space>
      ),
      children: <RiskAssessment />
    },
    {
      key: 'notifications',
      label: (
        <Space>
          <BellOutlined />
          {t('trading.decisions.tabs.notifications')}
        </Space>
      ),
      children: <NotificationSystem />
    }
  ];

  return (
    <div className="trading-decisions-container">
      <div className="page-header">
        <Row justify="space-between" align="middle">
          <Col>
            <Space direction="vertical" size="small">
              <Title level={2} style={{ margin: 0 }}>
                {t('trading.decisions.title')}
              </Title>
              <Text type="secondary">
                {t('trading.decisions.subtitle')}
              </Text>
            </Space>
          </Col>
          <Col>
            <Button
              type="primary"
              icon={<ReloadOutlined />}
              loading={refreshing}
              onClick={handleRefreshAll}
            >
              {t('trading.decisions.refreshAll')}
            </Button>
          </Col>
        </Row>
      </div>

      {/* Quick Stats Overview */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={8}>
          <Card size="small" className="stat-card">
            <div className="stat-content">
              <div className="stat-icon signals">
                <SignalFilled />
              </div>
              <div className="stat-info">
                <Text type="secondary">{t('trading.decisions.stats.activeSignals')}</Text>
                <div className="stat-value">3</div>
              </div>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card size="small" className="stat-card">
            <div className="stat-content">
              <div className="stat-icon risk">
                <ShieldCheckOutlined />
              </div>
              <div className="stat-info">
                <Text type="secondary">{t('trading.decisions.stats.riskLevel')}</Text>
                <div className="stat-value risk-medium">
                  {t('risk.level.medium')}
                </div>
              </div>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card size="small" className="stat-card">
            <div className="stat-content">
              <div className="stat-icon notifications">
                <BellOutlined />
              </div>
              <div className="stat-info">
                <Text type="secondary">{t('trading.decisions.stats.unreadAlerts')}</Text>
                <div className="stat-value">2</div>
              </div>
            </div>
          </Card>
        </Col>
      </Row>

      {/* Main Content Tabs */}
      <Card className="main-content-card">
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          size="large"
          items={tabItems}
          className="trading-decisions-tabs"
        />
      </Card>
    </div>
  );
};

export default TradingDecisions;