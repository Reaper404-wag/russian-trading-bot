import React, { useState, useEffect } from 'react';
import { Card, Progress, Row, Col, Statistic, Alert, Space, Typography, Tag, Tooltip } from 'antd';
import { useTranslation } from 'react-i18next';
import {
  ExclamationTriangleOutlined,
  ShieldCheckOutlined,
  WarningOutlined,
  InfoCircleOutlined,
  TrendingUpOutlined,
  TrendingDownOutlined
} from '@ant-design/icons';
import './RiskAssessment.css';

const { Title, Text, Paragraph } = Typography;

const RiskAssessment = () => {
  const { t } = useTranslation();
  const [riskData, setRiskData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRiskAssessment();
    const interval = setInterval(fetchRiskAssessment, 60000); // Update every minute
    return () => clearInterval(interval);
  }, []);

  const fetchRiskAssessment = async () => {
    try {
      // Mock API call - replace with actual API endpoint
      const mockRiskData = {
        overallRiskScore: 65, // 0-100 scale
        riskLevel: 'medium',
        portfolioRisk: {
          volatility: 18.5,
          sharpeRatio: 1.2,
          maxDrawdown: 12.3,
          beta: 1.15,
          var95: 45000 // Value at Risk 95%
        },
        marketRisk: {
          moexVolatility: 22.1,
          rubleVolatility: 15.8,
          geopoliticalRisk: 'high',
          sectorConcentration: 35.2,
          liquidityRisk: 'low'
        },
        riskFactors: [
          {
            id: 1,
            type: 'geopolitical',
            severity: 'high',
            title: 'Геополитические риски',
            description: 'Повышенная неопределенность из-за международных санкций и геополитической напряженности',
            impact: 'Может привести к резким колебаниям курса рубля и российских активов',
            recommendation: 'Рекомендуется снизить размер позиций и увеличить долю защитных активов'
          },
          {
            id: 2,
            type: 'currency',
            severity: 'medium',
            title: 'Валютные риски',
            description: 'Высокая волатильность рубля относительно основных валют',
            impact: 'Влияет на стоимость экспортно-ориентированных компаний',
            recommendation: 'Диверсификация по секторам с разной валютной чувствительностью'
          },
          {
            id: 3,
            type: 'sector',
            severity: 'medium',
            title: 'Секторальная концентрация',
            description: 'Высокая концентрация в энергетическом и банковском секторах',
            impact: 'Повышенная чувствительность к отраслевым рискам',
            recommendation: 'Увеличить диверсификацию по секторам экономики'
          },
          {
            id: 4,
            type: 'liquidity',
            severity: 'low',
            title: 'Риски ликвидности',
            description: 'Некоторые позиции имеют низкую ликвидность',
            impact: 'Может затруднить быстрое закрытие позиций',
            recommendation: 'Поддерживать достаточный уровень денежных средств'
          }
        ],
        recommendations: [
          'Снизить общий размер позиций на 15-20% до улучшения рыночных условий',
          'Увеличить долю защитных активов (облигации, золото) до 25%',
          'Установить более жесткие стоп-лоссы для волатильных позиций',
          'Регулярно пересматривать портфель с учетом изменения рисков'
        ],
        lastUpdated: new Date().toISOString()
      };
      
      setRiskData(mockRiskData);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching risk assessment:', error);
      setLoading(false);
    }
  };

  const getRiskColor = (level) => {
    switch (level) {
      case 'low':
        return '#52c41a';
      case 'medium':
        return '#faad14';
      case 'high':
        return '#ff4d4f';
      default:
        return '#d9d9d9';
    }
  };

  const getRiskIcon = (severity) => {
    switch (severity) {
      case 'high':
        return <ExclamationTriangleOutlined style={{ color: '#ff4d4f' }} />;
      case 'medium':
        return <WarningOutlined style={{ color: '#faad14' }} />;
      case 'low':
        return <InfoCircleOutlined style={{ color: '#52c41a' }} />;
      default:
        return <ShieldCheckOutlined style={{ color: '#d9d9d9' }} />;
    }
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'RUB',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };

  if (loading || !riskData) {
    return (
      <Card title={t('risk.assessment.title')} loading={loading}>
        <div style={{ height: 400 }} />
      </Card>
    );
  }

  return (
    <div className="risk-assessment">
      <Card 
        title={
          <Space>
            <Title level={4} style={{ margin: 0 }}>{t('risk.assessment.title')}</Title>
            <Tag color={getRiskColor(riskData.riskLevel)}>
              {t(`risk.level.${riskData.riskLevel}`)}
            </Tag>
          </Space>
        }
        extra={
          <Text type="secondary">
            {t('risk.lastUpdated')}: {new Date(riskData.lastUpdated).toLocaleTimeString('ru-RU')}
          </Text>
        }
      >
        {/* Overall Risk Score */}
        <div className="overall-risk-section">
          <Row gutter={[16, 16]} align="middle">
            <Col xs={24} sm={12}>
              <div className="risk-score-container">
                <Progress
                  type="circle"
                  percent={riskData.overallRiskScore}
                  strokeColor={getRiskColor(riskData.riskLevel)}
                  format={(percent) => (
                    <div className="risk-score-text">
                      <div className="score">{percent}</div>
                      <div className="label">{t('risk.score')}</div>
                    </div>
                  )}
                  size={120}
                />
              </div>
            </Col>
            <Col xs={24} sm={12}>
              <Space direction="vertical" size="small">
                <Text strong style={{ fontSize: 16 }}>
                  {t('risk.currentLevel')}: {t(`risk.level.${riskData.riskLevel}`)}
                </Text>
                <Text type="secondary">
                  {t('risk.assessment.description')}
                </Text>
              </Space>
            </Col>
          </Row>
        </div>

        {/* Portfolio Risk Metrics */}
        <Card 
          title={t('risk.portfolio.title')} 
          size="small" 
          style={{ marginTop: 16, marginBottom: 16 }}
        >
          <Row gutter={[16, 16]}>
            <Col xs={12} sm={8} lg={4}>
              <Statistic
                title={t('risk.portfolio.volatility')}
                value={riskData.portfolioRisk.volatility}
                suffix="%"
                precision={1}
                valueStyle={{ fontSize: 16 }}
              />
            </Col>
            <Col xs={12} sm={8} lg={4}>
              <Statistic
                title={t('risk.portfolio.sharpeRatio')}
                value={riskData.portfolioRisk.sharpeRatio}
                precision={2}
                valueStyle={{ fontSize: 16 }}
              />
            </Col>
            <Col xs={12} sm={8} lg={4}>
              <Statistic
                title={t('risk.portfolio.maxDrawdown')}
                value={riskData.portfolioRisk.maxDrawdown}
                suffix="%"
                precision={1}
                valueStyle={{ fontSize: 16, color: '#ff4d4f' }}
              />
            </Col>
            <Col xs={12} sm={8} lg={4}>
              <Statistic
                title={t('risk.portfolio.beta')}
                value={riskData.portfolioRisk.beta}
                precision={2}
                valueStyle={{ fontSize: 16 }}
              />
            </Col>
            <Col xs={12} sm={8} lg={4}>
              <Tooltip title={t('risk.portfolio.varTooltip')}>
                <Statistic
                  title={t('risk.portfolio.var95')}
                  value={riskData.portfolioRisk.var95}
                  formatter={(value) => formatCurrency(value)}
                  valueStyle={{ fontSize: 16, color: '#ff4d4f' }}
                />
              </Tooltip>
            </Col>
          </Row>
        </Card>

        {/* Market Risk Factors */}
        <Card 
          title={t('risk.market.title')} 
          size="small" 
          style={{ marginBottom: 16 }}
        >
          <Row gutter={[16, 16]}>
            <Col xs={12} sm={6}>
              <Statistic
                title={t('risk.market.moexVolatility')}
                value={riskData.marketRisk.moexVolatility}
                suffix="%"
                precision={1}
                prefix={<TrendingUpOutlined />}
                valueStyle={{ fontSize: 16 }}
              />
            </Col>
            <Col xs={12} sm={6}>
              <Statistic
                title={t('risk.market.rubleVolatility')}
                value={riskData.marketRisk.rubleVolatility}
                suffix="%"
                precision={1}
                prefix={<TrendingDownOutlined />}
                valueStyle={{ fontSize: 16 }}
              />
            </Col>
            <Col xs={12} sm={6}>
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {t('risk.market.geopoliticalRisk')}
                </Text>
                <br />
                <Tag color={getRiskColor(riskData.marketRisk.geopoliticalRisk)}>
                  {t(`risk.level.${riskData.marketRisk.geopoliticalRisk}`)}
                </Tag>
              </div>
            </Col>
            <Col xs={12} sm={6}>
              <Statistic
                title={t('risk.market.sectorConcentration')}
                value={riskData.marketRisk.sectorConcentration}
                suffix="%"
                precision={1}
                valueStyle={{ fontSize: 16 }}
              />
            </Col>
          </Row>
        </Card>

        {/* Risk Factors */}
        <Card title={t('risk.factors.title')} size="small" style={{ marginBottom: 16 }}>
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            {riskData.riskFactors.map((factor) => (
              <Alert
                key={factor.id}
                type={factor.severity === 'high' ? 'error' : factor.severity === 'medium' ? 'warning' : 'info'}
                showIcon
                icon={getRiskIcon(factor.severity)}
                message={
                  <Space>
                    <Text strong>{factor.title}</Text>
                    <Tag color={getRiskColor(factor.severity)} size="small">
                      {t(`risk.severity.${factor.severity}`)}
                    </Tag>
                  </Space>
                }
                description={
                  <div className="risk-factor-details">
                    <Paragraph style={{ marginBottom: 8 }}>
                      <Text>{factor.description}</Text>
                    </Paragraph>
                    <Paragraph style={{ marginBottom: 8 }}>
                      <Text strong>{t('risk.factors.impact')}: </Text>
                      <Text>{factor.impact}</Text>
                    </Paragraph>
                    <Paragraph style={{ marginBottom: 0 }}>
                      <Text strong>{t('risk.factors.recommendation')}: </Text>
                      <Text>{factor.recommendation}</Text>
                    </Paragraph>
                  </div>
                }
              />
            ))}
          </Space>
        </Card>

        {/* Recommendations */}
        <Card title={t('risk.recommendations.title')} size="small">
          <Space direction="vertical" size="small" style={{ width: '100%' }}>
            {riskData.recommendations.map((recommendation, index) => (
              <div key={index} className="recommendation-item">
                <Space align="start">
                  <ShieldCheckOutlined style={{ color: '#1890ff', marginTop: 4 }} />
                  <Text>{recommendation}</Text>
                </Space>
              </div>
            ))}
          </Space>
        </Card>
      </Card>
    </div>
  );
};

export default RiskAssessment;