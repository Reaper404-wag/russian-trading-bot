import React, { useState, useEffect } from 'react';
import { Card, List, Tag, Button, Space, Typography, Badge, Tooltip, Modal, Spin } from 'antd';
import { useTranslation } from 'react-i18next';
import {
  ArrowUpOutlined,
  ArrowDownOutlined,
  ExclamationCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  InfoCircleOutlined
} from '@ant-design/icons';
import './TradingSignals.css';

const { Title, Text, Paragraph } = Typography;

const TradingSignals = () => {
  const { t } = useTranslation();
  const [signals, setSignals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedSignal, setSelectedSignal] = useState(null);
  const [approvalModalVisible, setApprovalModalVisible] = useState(false);

  useEffect(() => {
    fetchTradingSignals();
    const interval = setInterval(fetchTradingSignals, 30000); // Update every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchTradingSignals = async () => {
    try {
      // Mock API call - replace with actual API endpoint
      const mockSignals = [
        {
          id: 1,
          symbol: 'SBER',
          name: 'Сбербанк',
          action: 'buy',
          confidence: 0.85,
          targetPrice: 295.00,
          currentPrice: 285.50,
          stopLoss: 275.00,
          reasoning: 'Технический анализ показывает пробой уровня сопротивления на 285 рублей. RSI находится в зоне 35, что указывает на перепроданность. MACD показывает бычий сигнал. Объем торгов увеличился на 25% по сравнению со средним.',
          riskLevel: 'medium',
          expectedReturn: 3.3,
          timestamp: new Date().toISOString(),
          status: 'pending'
        },
        {
          id: 2,
          symbol: 'GAZP',
          name: 'Газпром',
          action: 'sell',
          confidence: 0.72,
          targetPrice: 170.00,
          currentPrice: 178.20,
          stopLoss: 185.00,
          reasoning: 'Негативные новости по энергетическому сектору. Цена достигла уровня сопротивления 180 рублей. RSI в зоне перекупленности (75). Геополитические риски увеличиваются.',
          riskLevel: 'high',
          expectedReturn: -4.6,
          timestamp: new Date(Date.now() - 300000).toISOString(),
          status: 'pending'
        },
        {
          id: 3,
          symbol: 'LKOH',
          name: 'ЛУКОЙЛ',
          action: 'hold',
          confidence: 0.65,
          targetPrice: 7200.00,
          currentPrice: 7120.00,
          stopLoss: 6900.00,
          reasoning: 'Смешанные сигналы от технических индикаторов. Цена консолидируется в диапазоне 7000-7200. Ожидается публикация квартальных результатов через неделю.',
          riskLevel: 'low',
          expectedReturn: 1.1,
          timestamp: new Date(Date.now() - 600000).toISOString(),
          status: 'pending'
        }
      ];
      
      setSignals(mockSignals);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching trading signals:', error);
      setLoading(false);
    }
  };

  const getActionIcon = (action) => {
    switch (action) {
      case 'buy':
        return <ArrowUpOutlined style={{ color: '#52c41a' }} />;
      case 'sell':
        return <ArrowDownOutlined style={{ color: '#ff4d4f' }} />;
      default:
        return <InfoCircleOutlined style={{ color: '#1890ff' }} />;
    }
  };

  const getActionColor = (action) => {
    switch (action) {
      case 'buy':
        return 'success';
      case 'sell':
        return 'error';
      default:
        return 'default';
    }
  };

  const getRiskColor = (riskLevel) => {
    switch (riskLevel) {
      case 'low':
        return 'green';
      case 'medium':
        return 'orange';
      case 'high':
        return 'red';
      default:
        return 'default';
    }
  };

  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.8) return '#52c41a';
    if (confidence >= 0.6) return '#faad14';
    return '#ff4d4f';
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'RUB',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value);
  };

  const handleApproveSignal = (signal) => {
    setSelectedSignal(signal);
    setApprovalModalVisible(true);
  };

  const handleRejectSignal = (signalId) => {
    setSignals(signals.map(signal => 
      signal.id === signalId 
        ? { ...signal, status: 'rejected' }
        : signal
    ));
  };

  const confirmApproval = () => {
    if (selectedSignal) {
      setSignals(signals.map(signal => 
        signal.id === selectedSignal.id 
          ? { ...signal, status: 'approved' }
          : signal
      ));
      setApprovalModalVisible(false);
      setSelectedSignal(null);
    }
  };

  if (loading) {
    return (
      <Card title={t('trading.signals.title')}>
        <div style={{ textAlign: 'center', padding: '50px 0' }}>
          <Spin size="large" />
          <div style={{ marginTop: 16 }}>
            <Text>{t('common.loading')}</Text>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <div className="trading-signals">
      <Card 
        title={
          <Space>
            <Title level={4} style={{ margin: 0 }}>{t('trading.signals.title')}</Title>
            <Badge count={signals.filter(s => s.status === 'pending').length} />
          </Space>
        }
        extra={
          <Button onClick={fetchTradingSignals} loading={loading}>
            {t('common.refresh')}
          </Button>
        }
      >
        <List
          dataSource={signals}
          renderItem={(signal) => (
            <List.Item
              className={`signal-item signal-${signal.status}`}
              actions={signal.status === 'pending' ? [
                <Button
                  type="primary"
                  size="small"
                  icon={<CheckCircleOutlined />}
                  onClick={() => handleApproveSignal(signal)}
                >
                  {t('trading.signals.approve')}
                </Button>,
                <Button
                  danger
                  size="small"
                  icon={<CloseCircleOutlined />}
                  onClick={() => handleRejectSignal(signal.id)}
                >
                  {t('trading.signals.reject')}
                </Button>
              ] : []}
            >
              <List.Item.Meta
                avatar={
                  <div className="signal-avatar">
                    {getActionIcon(signal.action)}
                  </div>
                }
                title={
                  <Space>
                    <Text strong>{signal.symbol}</Text>
                    <Text type="secondary">({signal.name})</Text>
                    <Tag color={getActionColor(signal.action)}>
                      {t(`trading.signals.${signal.action}`)}
                    </Tag>
                    <Tag color={getRiskColor(signal.riskLevel)}>
                      {t(`trading.signals.risk.${signal.riskLevel}`)}
                    </Tag>
                  </Space>
                }
                description={
                  <div className="signal-details">
                    <div className="signal-prices">
                      <Space size="large">
                        <div>
                          <Text type="secondary">{t('trading.signals.currentPrice')}:</Text>
                          <br />
                          <Text strong>{formatCurrency(signal.currentPrice)}</Text>
                        </div>
                        <div>
                          <Text type="secondary">{t('trading.signals.targetPrice')}:</Text>
                          <br />
                          <Text strong>{formatCurrency(signal.targetPrice)}</Text>
                        </div>
                        <div>
                          <Text type="secondary">{t('trading.signals.stopLoss')}:</Text>
                          <br />
                          <Text strong>{formatCurrency(signal.stopLoss)}</Text>
                        </div>
                      </Space>
                    </div>
                    
                    <div className="signal-metrics">
                      <Space size="large">
                        <div>
                          <Text type="secondary">{t('trading.signals.confidence')}:</Text>
                          <br />
                          <Text 
                            strong 
                            style={{ color: getConfidenceColor(signal.confidence) }}
                          >
                            {Math.round(signal.confidence * 100)}%
                          </Text>
                        </div>
                        <div>
                          <Text type="secondary">{t('trading.signals.expectedReturn')}:</Text>
                          <br />
                          <Text 
                            strong 
                            style={{ color: signal.expectedReturn >= 0 ? '#52c41a' : '#ff4d4f' }}
                          >
                            {signal.expectedReturn >= 0 ? '+' : ''}{signal.expectedReturn.toFixed(1)}%
                          </Text>
                        </div>
                        <div>
                          <Text type="secondary">{t('trading.signals.time')}:</Text>
                          <br />
                          <Text>
                            {new Date(signal.timestamp).toLocaleTimeString('ru-RU', {
                              hour: '2-digit',
                              minute: '2-digit'
                            })}
                          </Text>
                        </div>
                      </Space>
                    </div>
                    
                    <div className="signal-reasoning">
                      <Paragraph 
                        ellipsis={{ rows: 2, expandable: true, symbol: t('common.showMore') }}
                        style={{ marginBottom: 0, marginTop: 8 }}
                      >
                        <Text type="secondary">{t('trading.signals.reasoning')}:</Text>
                        <br />
                        {signal.reasoning}
                      </Paragraph>
                    </div>
                  </div>
                }
              />
            </List.Item>
          )}
        />
      </Card>

      <Modal
        title={t('trading.signals.approvalModal.title')}
        open={approvalModalVisible}
        onOk={confirmApproval}
        onCancel={() => setApprovalModalVisible(false)}
        okText={t('trading.signals.approvalModal.confirm')}
        cancelText={t('common.cancel')}
        width={600}
      >
        {selectedSignal && (
          <div className="approval-modal-content">
            <div className="signal-summary">
              <Title level={5}>
                {t('trading.signals.approvalModal.summary')}
              </Title>
              <Space direction="vertical" size="small" style={{ width: '100%' }}>
                <div>
                  <Text strong>{selectedSignal.symbol}</Text> ({selectedSignal.name})
                  <Tag color={getActionColor(selectedSignal.action)} style={{ marginLeft: 8 }}>
                    {t(`trading.signals.${selectedSignal.action}`)}
                  </Tag>
                </div>
                <div>
                  <Text>{t('trading.signals.currentPrice')}: </Text>
                  <Text strong>{formatCurrency(selectedSignal.currentPrice)}</Text>
                </div>
                <div>
                  <Text>{t('trading.signals.targetPrice')}: </Text>
                  <Text strong>{formatCurrency(selectedSignal.targetPrice)}</Text>
                </div>
                <div>
                  <Text>{t('trading.signals.expectedReturn')}: </Text>
                  <Text 
                    strong 
                    style={{ color: selectedSignal.expectedReturn >= 0 ? '#52c41a' : '#ff4d4f' }}
                  >
                    {selectedSignal.expectedReturn >= 0 ? '+' : ''}{selectedSignal.expectedReturn.toFixed(1)}%
                  </Text>
                </div>
              </Space>
            </div>
            
            <div className="approval-warning">
              <Space align="start">
                <ExclamationCircleOutlined style={{ color: '#faad14', fontSize: 16 }} />
                <div>
                  <Text strong>{t('trading.signals.approvalModal.warning')}</Text>
                  <br />
                  <Text type="secondary">
                    {t('trading.signals.approvalModal.warningText')}
                  </Text>
                </div>
              </Space>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default TradingSignals;