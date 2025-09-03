import React, { useState } from 'react';
import { Layout as AntLayout, Menu, Typography, Space } from 'antd';
import { useNavigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  DashboardOutlined,
  PieChartOutlined,
  HistoryOutlined,
  BarChartOutlined,
  SettingOutlined
} from '@ant-design/icons';
import './Layout.css';

const { Header, Sider, Content } = AntLayout;
const { Title } = Typography;

const Layout = ({ children }) => {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { t } = useTranslation();

  const menuItems = [
    {
      key: '/',
      icon: <DashboardOutlined />,
      label: t('navigation.dashboard'),
    },
    {
      key: '/portfolio',
      icon: <PieChartOutlined />,
      label: t('navigation.portfolio'),
    },
    {
      key: '/trading-decisions',
      icon: <BarChartOutlined />,
      label: t('navigation.tradingDecisions'),
    },
    {
      key: '/trading-history',
      icon: <HistoryOutlined />,
      label: t('navigation.history'),
    },
    {
      key: '/settings',
      icon: <SettingOutlined />,
      label: t('navigation.settings'),
    },
  ];

  const handleMenuClick = ({ key }) => {
    navigate(key);
  };

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        theme="dark"
        width={250}
      >
        <div className="logo">
          <Space direction="vertical" size="small" style={{ padding: '16px' }}>
            <Title level={4} style={{ color: 'white', margin: 0 }}>
              {collapsed ? 'РТБ' : 'Российский Торговый Бот'}
            </Title>
          </Space>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={handleMenuClick}
        />
      </Sider>
      <AntLayout>
        <Header className="site-layout-header">
          <div className="header-content">
            <Title level={3} style={{ margin: 0, color: 'white' }}>
              {t('navigation.dashboard')}
            </Title>
            <Space>
              <span style={{ color: 'white' }}>
                {new Date().toLocaleDateString('ru-RU', {
                  weekday: 'long',
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric'
                })}
              </span>
            </Space>
          </div>
        </Header>
        <Content className="site-layout-content">
          {children}
        </Content>
      </AntLayout>
    </AntLayout>
  );
};

export default Layout;