import React, { useState, useEffect } from 'react';
import { Card, List, Badge, Button, Space, Typography, Tag, Switch, Modal, Form, Select, InputNumber, notification } from 'antd';
import { useTranslation } from 'react-i18next';
import {
  BellOutlined,
  WarningOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  SettingOutlined,
  DeleteOutlined,
  PlusOutlined
} from '@ant-design/icons';
import './NotificationSystem.css';

const { Title, Text } = Typography;
const { Option } = Select;

const NotificationSystem = () => {
  const { t } = useTranslation();
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [settingsVisible, setSettingsVisible] = useState(false);
  const [notificationSettings, setNotificationSettings] = useState({
    enabled: true,
    priceAlerts: true,
    riskAlerts: true,
    newsAlerts: true,
    tradingSignals: true,
    emailNotifications: false,
    telegramNotifications: false
  });
  const [form] = Form.useForm();

  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 30000); // Update every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchAlerts = async () => {
    try {
      // Mock API call - replace with actual API endpoint
      const mockAlerts = [
        {
          id: 1,
          type: 'price',
          severity: 'high',
          title: 'Резкое падение цены SBER',
          message: 'Цена акций Сбербанка упала на 5.2% за последние 30 минут. Текущая цена: 270.50 ₽',
          symbol: 'SBER',
          timestamp: new Date().toISOString(),
          read: false,
          actionRequired: true
        },
        {
          id: 2,
          type: 'risk',
          severity: 'medium',
          title: 'Превышен лимит риска по портфелю',
          message: 'Общий риск портфеля превысил установленный лимит в 70%. Рекомендуется пересмотреть позиции.',
          timestamp: new Date(Date.now() - 300000).toISOString(),
          read: false,
          actionRequired: true
        },
        {
          id: 3,
          type: 'news',
          severity: 'high',
          title: 'Важные новости по энергетическому сектору',
          message: 'ЦБ РФ объявил о новых мерах поддержки энергетических компаний. Ожидается рост котировок.',
          relatedStocks: ['GAZP', 'LKOH', 'ROSN'],
          timestamp: new Date(Date.now() - 600000).toISOString(),
          read: true,
          actionRequired: false
        },
        {
          id: 4,
          type: 'signal',
          severity: 'medium',
          title: 'Новый торговый сигнал: GAZP',
          message: 'Сгенерирован сигнал на покупку GAZP с уровнем уверенности 78%. Ожидаемая доходность: +3.2%',
          symbol: 'GAZP',
          timestamp: new Date(Date.now() - 900000).toISOString(),
          read: true,
          actionRequired: true
        },
        {
          id: 5,
          type: 'system',
          severity: 'low',
          title: 'Обновление системы завершено',
          message: 'Система торгового бота успешно обновлена до версии 2.1.3. Добавлены новые функции анализа.',
          timestamp: new Date(Date.now() - 3600000).toISOString(),
          read: true,
          actionRequired: false
        }
      ];
      
      setAlerts(mockAlerts);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching alerts:', error);
      setLoading(false);
    }
  };

  const getAlertIcon = (type, severity) => {
    const iconStyle = { fontSize: 16 };
    
    switch (severity) {
      case 'high':
        iconStyle.color = '#ff4d4f';
        break;
      case 'medium':
        iconStyle.color = '#faad14';
        break;
      case 'low':
        iconStyle.color = '#52c41a';
        break;
      default:
        iconStyle.color = '#1890ff';
    }

    switch (type) {
      case 'price':
        return <ExclamationCircleOutlined style={iconStyle} />;
      case 'risk':
        return <WarningOutlined style={iconStyle} />;
      case 'news':
        return <InfoCircleOutlined style={iconStyle} />;
      case 'signal':
        return <CheckCircleOutlined style={iconStyle} />;
      default:
        return <BellOutlined style={iconStyle} />;
    }
  };

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'high':
        return 'red';
      case 'medium':
        return 'orange';
      case 'low':
        return 'green';
      default:
        return 'blue';
    }
  };

  const markAsRead = (alertId) => {
    setAlerts(alerts.map(alert => 
      alert.id === alertId ? { ...alert, read: true } : alert
    ));
  };

  const deleteAlert = (alertId) => {
    setAlerts(alerts.filter(alert => alert.id !== alertId));
  };

  const markAllAsRead = () => {
    setAlerts(alerts.map(alert => ({ ...alert, read: true })));
  };

  const clearAllAlerts = () => {
    Modal.confirm({
      title: t('notifications.clearAll.title'),
      content: t('notifications.clearAll.content'),
      okText: t('common.confirm'),
      cancelText: t('common.cancel'),
      onOk: () => {
        setAlerts([]);
        notification.success({
          message: t('notifications.clearAll.success')
        });
      }
    });
  };

  const handleSettingsChange = (key, value) => {
    setNotificationSettings(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const saveSettings = () => {
    // Mock API call to save settings
    notification.success({
      message: t('notifications.settings.saved')
    });
    setSettingsVisible(false);
  };

  const unreadCount = alerts.filter(alert => !alert.read).length;

  return (
    <div className="notification-system">
      <Card 
        title={
          <Space>
            <Title level={4} style={{ margin: 0 }}>{t('notifications.title')}</Title>
            <Badge count={unreadCount} />
          </Space>
        }
        extra={
          <Space>
            <Button 
              size="small" 
              onClick={markAllAsRead}
              disabled={unreadCount === 0}
            >
              {t('notifications.markAllRead')}
            </Button>
            <Button 
              size="small" 
              onClick={clearAllAlerts}
              disabled={alerts.length === 0}
            >
              {t('notifications.clearAll.button')}
            </Button>
            <Button 
              size="small" 
              icon={<SettingOutlined />}
              onClick={() => setSettingsVisible(true)}
            >
              {t('notifications.settings.button')}
            </Button>
          </Space>
        }
      >
        <List
          loading={loading}
          dataSource={alerts}
          locale={{ emptyText: t('notifications.empty') }}
          renderItem={(alert) => (
            <List.Item
              className={`alert-item ${alert.read ? 'read' : 'unread'}`}
              actions={[
                !alert.read && (
                  <Button 
                    type="link" 
                    size="small"
                    onClick={() => markAsRead(alert.id)}
                  >
                    {t('notifications.markRead')}
                  </Button>
                ),
                <Button 
                  type="link" 
                  size="small" 
                  danger
                  icon={<DeleteOutlined />}
                  onClick={() => deleteAlert(alert.id)}
                />
              ].filter(Boolean)}
            >
              <List.Item.Meta
                avatar={getAlertIcon(alert.type, alert.severity)}
                title={
                  <Space>
                    <Text strong={!alert.read}>{alert.title}</Text>
                    <Tag color={getSeverityColor(alert.severity)} size="small">
                      {t(`notifications.severity.${alert.severity}`)}
                    </Tag>
                    <Tag color="blue" size="small">
                      {t(`notifications.type.${alert.type}`)}
                    </Tag>
                    {alert.actionRequired && (
                      <Tag color="red" size="small">
                        {t('notifications.actionRequired')}
                      </Tag>
                    )}
                  </Space>
                }
                description={
                  <div className="alert-content">
                    <Text type={alert.read ? 'secondary' : undefined}>
                      {alert.message}
                    </Text>
                    {alert.symbol && (
                      <div className="alert-symbol">
                        <Text strong>{alert.symbol}</Text>
                      </div>
                    )}
                    {alert.relatedStocks && (
                      <div className="alert-stocks">
                        <Text type="secondary">{t('notifications.relatedStocks')}: </Text>
                        {alert.relatedStocks.map(stock => (
                          <Tag key={stock} size="small">{stock}</Tag>
                        ))}
                      </div>
                    )}
                    <div className="alert-time">
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {new Date(alert.timestamp).toLocaleString('ru-RU')}
                      </Text>
                    </div>
                  </div>
                }
              />
            </List.Item>
          )}
        />
      </Card>

      <Modal
        title={t('notifications.settings.title')}
        open={settingsVisible}
        onOk={saveSettings}
        onCancel={() => setSettingsVisible(false)}
        okText={t('common.save')}
        cancelText={t('common.cancel')}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={notificationSettings}
        >
          <Form.Item>
            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
              <div className="setting-item">
                <Space justify="space-between" style={{ width: '100%' }}>
                  <div>
                    <Text strong>{t('notifications.settings.enabled')}</Text>
                    <br />
                    <Text type="secondary">{t('notifications.settings.enabledDesc')}</Text>
                  </div>
                  <Switch
                    checked={notificationSettings.enabled}
                    onChange={(checked) => handleSettingsChange('enabled', checked)}
                  />
                </Space>
              </div>

              <div className="setting-item">
                <Space justify="space-between" style={{ width: '100%' }}>
                  <div>
                    <Text strong>{t('notifications.settings.priceAlerts')}</Text>
                    <br />
                    <Text type="secondary">{t('notifications.settings.priceAlertsDesc')}</Text>
                  </div>
                  <Switch
                    checked={notificationSettings.priceAlerts}
                    onChange={(checked) => handleSettingsChange('priceAlerts', checked)}
                    disabled={!notificationSettings.enabled}
                  />
                </Space>
              </div>

              <div className="setting-item">
                <Space justify="space-between" style={{ width: '100%' }}>
                  <div>
                    <Text strong>{t('notifications.settings.riskAlerts')}</Text>
                    <br />
                    <Text type="secondary">{t('notifications.settings.riskAlertsDesc')}</Text>
                  </div>
                  <Switch
                    checked={notificationSettings.riskAlerts}
                    onChange={(checked) => handleSettingsChange('riskAlerts', checked)}
                    disabled={!notificationSettings.enabled}
                  />
                </Space>
              </div>

              <div className="setting-item">
                <Space justify="space-between" style={{ width: '100%' }}>
                  <div>
                    <Text strong>{t('notifications.settings.newsAlerts')}</Text>
                    <br />
                    <Text type="secondary">{t('notifications.settings.newsAlertsDesc')}</Text>
                  </div>
                  <Switch
                    checked={notificationSettings.newsAlerts}
                    onChange={(checked) => handleSettingsChange('newsAlerts', checked)}
                    disabled={!notificationSettings.enabled}
                  />
                </Space>
              </div>

              <div className="setting-item">
                <Space justify="space-between" style={{ width: '100%' }}>
                  <div>
                    <Text strong>{t('notifications.settings.tradingSignals')}</Text>
                    <br />
                    <Text type="secondary">{t('notifications.settings.tradingSignalsDesc')}</Text>
                  </div>
                  <Switch
                    checked={notificationSettings.tradingSignals}
                    onChange={(checked) => handleSettingsChange('tradingSignals', checked)}
                    disabled={!notificationSettings.enabled}
                  />
                </Space>
              </div>

              <div className="setting-item">
                <Space justify="space-between" style={{ width: '100%' }}>
                  <div>
                    <Text strong>{t('notifications.settings.emailNotifications')}</Text>
                    <br />
                    <Text type="secondary">{t('notifications.settings.emailNotificationsDesc')}</Text>
                  </div>
                  <Switch
                    checked={notificationSettings.emailNotifications}
                    onChange={(checked) => handleSettingsChange('emailNotifications', checked)}
                    disabled={!notificationSettings.enabled}
                  />
                </Space>
              </div>

              <div className="setting-item">
                <Space justify="space-between" style={{ width: '100%' }}>
                  <div>
                    <Text strong>{t('notifications.settings.telegramNotifications')}</Text>
                    <br />
                    <Text type="secondary">{t('notifications.settings.telegramNotificationsDesc')}</Text>
                  </div>
                  <Switch
                    checked={notificationSettings.telegramNotifications}
                    onChange={(checked) => handleSettingsChange('telegramNotifications', checked)}
                    disabled={!notificationSettings.enabled}
                  />
                </Space>
              </div>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default NotificationSystem;