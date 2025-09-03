import React, { useState, useEffect } from 'react';
import { Card, List, Typography, Tag, Space, Avatar, Button, Spin, Badge } from 'antd';
import { useTranslation } from 'react-i18next';
import {
  ArrowUpOutlined,
  ArrowDownOutlined,
  ClockCircleOutlined,
  ReloadOutlined,
  GlobalOutlined
} from '@ant-design/icons';
import moment from 'moment';

const { Title, Text, Paragraph } = Typography;

const RussianNewsFeed = ({ height = 400 }) => {
  const { t } = useTranslation();
  const [news, setNews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadNews();
    
    // Set up auto-refresh every 5 minutes
    const interval = setInterval(loadNews, 5 * 60 * 1000);
    
    return () => clearInterval(interval);
  }, []);

  const loadNews = async () => {
    setLoading(true);
    try {
      // Generate mock Russian financial news
      const mockNews = generateMockNews();
      setNews(mockNews);
    } catch (error) {
      console.error('Error loading news:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const refreshNews = () => {
    setRefreshing(true);
    loadNews();
  };

  const generateMockNews = () => {
    const sources = [
      { name: 'РБК', icon: '🏢', color: '#1890ff' },
      { name: 'Ведомости', icon: '📰', color: '#52c41a' },
      { name: 'Коммерсантъ', icon: '💼', color: '#722ed1' },
      { name: 'Интерфакс', icon: '📡', color: '#fa8c16' },
      { name: 'Финам', icon: '📊', color: '#eb2f96' }
    ];

    const newsItems = [
      {
        id: 1,
        title: 'Сбербанк увеличил прогноз по ключевой ставке ЦБ на конец года',
        summary: 'Аналитики Сбербанка повысили прогноз по ключевой ставке ЦБ РФ на конец 2024 года до 18% с предыдущих 16%. Решение связано с ускорением инфляции.',
        source: sources[0],
        timestamp: new Date(Date.now() - 15 * 60 * 1000), // 15 minutes ago
        sentiment: 'negative',
        impact: 'high',
        relatedStocks: ['SBER', 'VTBR', 'GAZP'],
        category: 'monetary_policy'
      },
      {
        id: 2,
        title: 'Газпром подписал новый контракт на поставку газа в Китай',
        summary: 'Газпром заключил долгосрочный контракт на поставку природного газа в КНР объемом до 10 млрд кубометров в год. Контракт рассчитан на 30 лет.',
        source: sources[1],
        timestamp: new Date(Date.now() - 45 * 60 * 1000), // 45 minutes ago
        sentiment: 'positive',
        impact: 'high',
        relatedStocks: ['GAZP', 'NVTK'],
        category: 'energy'
      },
      {
        id: 3,
        title: 'ЛУКОЙЛ увеличил инвестиции в возобновляемую энергетику',
        summary: 'Нефтяная компания ЛУКОЙЛ объявила о планах увеличить инвестиции в проекты возобновляемой энергетики на 25% в следующем году.',
        source: sources[2],
        timestamp: new Date(Date.now() - 1.5 * 60 * 60 * 1000), // 1.5 hours ago
        sentiment: 'positive',
        impact: 'medium',
        relatedStocks: ['LKOH'],
        category: 'energy'
      },
      {
        id: 4,
        title: 'Яндекс представил новую версию поисковой системы с ИИ',
        summary: 'Компания Яндекс анонсировала обновленную версию поисковой системы с интегрированным искусственным интеллектом, что может укрепить позиции на рынке.',
        source: sources[3],
        timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000), // 2 hours ago
        sentiment: 'positive',
        impact: 'medium',
        relatedStocks: ['YNDX'],
        category: 'technology'
      },
      {
        id: 5,
        title: 'Магнит отчитался о росте выручки на 12% в третьем квартале',
        summary: 'Розничная сеть Магнит опубликовала финансовые результаты за третий квартал, показав рост выручки на 12% год к году благодаря расширению сети.',
        source: sources[4],
        timestamp: new Date(Date.now() - 3 * 60 * 60 * 1000), // 3 hours ago
        sentiment: 'positive',
        impact: 'medium',
        relatedStocks: ['MGNT'],
        category: 'retail'
      },
      {
        id: 6,
        title: 'ЦБ РФ сохранил ключевую ставку на уровне 16%',
        summary: 'Банк России принял решение сохранить ключевую ставку на уровне 16% годовых, что соответствует ожиданиям большинства аналитиков.',
        source: sources[0],
        timestamp: new Date(Date.now() - 4 * 60 * 60 * 1000), // 4 hours ago
        sentiment: 'neutral',
        impact: 'high',
        relatedStocks: ['SBER', 'VTBR', 'GAZP', 'LKOH'],
        category: 'monetary_policy'
      }
    ];

    return newsItems.sort((a, b) => b.timestamp - a.timestamp);
  };

  const getSentimentIcon = (sentiment) => {
    switch (sentiment) {
      case 'positive':
        return <ArrowUpOutlined style={{ color: '#52c41a' }} />;
      case 'negative':
        return <ArrowDownOutlined style={{ color: '#f5222d' }} />;
      default:
        return <ClockCircleOutlined style={{ color: '#faad14' }} />;
    }
  };

  const getSentimentColor = (sentiment) => {
    switch (sentiment) {
      case 'positive':
        return 'green';
      case 'negative':
        return 'red';
      default:
        return 'orange';
    }
  };

  const getImpactColor = (impact) => {
    switch (impact) {
      case 'high':
        return 'red';
      case 'medium':
        return 'orange';
      default:
        return 'blue';
    }
  };

  const getCategoryColor = (category) => {
    const colors = {
      monetary_policy: 'purple',
      energy: 'green',
      technology: 'blue',
      retail: 'orange',
      banking: 'cyan'
    };
    return colors[category] || 'default';
  };

  const formatTimeAgo = (timestamp) => {
    moment.locale('ru');
    return moment(timestamp).fromNow();
  };

  return (
    <Card
      title={
        <Space>
          <GlobalOutlined />
          <Title level={4} style={{ margin: 0 }}>
            {t('news.russianFinancialNews')}
          </Title>
          <Badge count={news.length} showZero color="#52c41a" />
        </Space>
      }
      extra={
        <Button
          icon={<ReloadOutlined spin={refreshing} />}
          onClick={refreshNews}
          loading={refreshing}
          size="small"
        >
          {t('common.refresh')}
        </Button>
      }
      style={{ height: height + 50 }}
    >
      {loading ? (
        <div style={{ textAlign: 'center', padding: '50px' }}>
          <Spin size="large" />
          <div style={{ marginTop: 16 }}>
            <Text>{t('common.loading')}</Text>
          </div>
        </div>
      ) : (
        <List
          dataSource={news}
          style={{ height: height, overflowY: 'auto' }}
          renderItem={(item) => (
            <List.Item key={item.id}>
              <List.Item.Meta
                avatar={
                  <Avatar 
                    style={{ backgroundColor: item.source.color }}
                    size="large"
                  >
                    {item.source.icon}
                  </Avatar>
                }
                title={
                  <Space direction="vertical" size="small" style={{ width: '100%' }}>
                    <Space wrap>
                      <Text strong style={{ fontSize: '14px' }}>
                        {item.title}
                      </Text>
                      {getSentimentIcon(item.sentiment)}
                    </Space>
                    <Space wrap>
                      <Tag color={item.source.color} size="small">
                        {item.source.name}
                      </Tag>
                      <Tag color={getSentimentColor(item.sentiment)} size="small">
                        {t(`news.sentiment.${item.sentiment}`)}
                      </Tag>
                      <Tag color={getImpactColor(item.impact)} size="small">
                        {t(`news.impact.${item.impact}`)}
                      </Tag>
                      <Tag color={getCategoryColor(item.category)} size="small">
                        {t(`news.category.${item.category}`)}
                      </Tag>
                    </Space>
                  </Space>
                }
                description={
                  <Space direction="vertical" size="small" style={{ width: '100%' }}>
                    <Paragraph 
                      style={{ margin: 0, fontSize: '13px' }}
                      ellipsis={{ rows: 2, expandable: true, symbol: 'показать больше' }}
                    >
                      {item.summary}
                    </Paragraph>
                    <Space wrap>
                      <Text type="secondary" style={{ fontSize: '12px' }}>
                        <ClockCircleOutlined /> {formatTimeAgo(item.timestamp)}
                      </Text>
                      {item.relatedStocks.length > 0 && (
                        <Space size="small">
                          <Text type="secondary" style={{ fontSize: '12px' }}>
                            Акции:
                          </Text>
                          {item.relatedStocks.map(stock => (
                            <Tag key={stock} size="small" color="blue">
                              {stock}
                            </Tag>
                          ))}
                        </Space>
                      )}
                    </Space>
                  </Space>
                }
              />
            </List.Item>
          )}
        />
      )}
    </Card>
  );
};

export default RussianNewsFeed;