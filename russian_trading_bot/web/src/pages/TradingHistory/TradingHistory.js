import React, { useState, useEffect } from 'react';
import { Card, Table, Typography, Tag, Space, DatePicker, Select, Button, Spin } from 'antd';
import { useTranslation } from 'react-i18next';
import { SearchOutlined, ReloadOutlined } from '@ant-design/icons';
import moment from 'moment';
import 'moment/locale/ru';
import './TradingHistory.css';

const { Title } = Typography;
const { RangePicker } = DatePicker;
const { Option } = Select;

// Set moment locale to Russian
moment.locale('ru');

const TradingHistory = () => {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [filteredData, setFilteredData] = useState([]);
  const [filters, setFilters] = useState({
    dateRange: null,
    symbol: null,
    action: null,
    status: null
  });

  const [tradingData] = useState([
    {
      key: '1',
      date: '2024-01-15',
      time: '10:30:15',
      symbol: 'SBER',
      name: 'Сбербанк',
      action: 'buy',
      quantity: 100,
      price: 280.50,
      total: 28050,
      status: 'executed',
      reasoning: 'Технический анализ показывает пробой уровня сопротивления. RSI в зоне перепроданности.'
    },
    {
      key: '2',
      date: '2024-01-15',
      time: '11:45:22',
      symbol: 'GAZP',
      name: 'Газпром',
      action: 'sell',
      quantity: 50,
      price: 178.20,
      total: 8910,
      status: 'executed',
      reasoning: 'Фиксация прибыли после достижения целевого уровня. Негативные новости по сектору.'
    },
    {
      key: '3',
      date: '2024-01-15',
      time: '14:20:10',
      symbol: 'LKOH',
      name: 'ЛУКОЙЛ',
      action: 'buy',
      quantity: 25,
      price: 6850.00,
      total: 171250,
      status: 'executed',
      reasoning: 'Сильные финансовые показатели. Дивидендная доходность выше среднерыночной.'
    },
    {
      key: '4',
      date: '2024-01-16',
      time: '09:15:30',
      symbol: 'ROSN',
      name: 'Роснефть',
      action: 'buy',
      quantity: 75,
      price: 520.30,
      total: 39022.50,
      status: 'pending',
      reasoning: 'Ожидается рост цен на нефть. Техническая картина улучшается.'
    },
    {
      key: '5',
      date: '2024-01-16',
      time: '15:30:45',
      symbol: 'SBER',
      name: 'Сбербанк',
      action: 'sell',
      quantity: 50,
      price: 285.50,
      total: 14275,
      status: 'cancelled',
      reasoning: 'Отмена из-за изменения рыночных условий. Высокая волатильность.'
    }
  ]);

  useEffect(() => {
    // Simulate data loading
    const timer = setTimeout(() => {
      setFilteredData(tradingData);
      setLoading(false);
    }, 1000);

    return () => clearTimeout(timer);
  }, [tradingData]);

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'RUB',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value);
  };

  const formatDateTime = (date, time) => {
    const dateTime = moment(`${date} ${time}`, 'YYYY-MM-DD HH:mm:ss');
    return {
      date: dateTime.format('DD.MM.YYYY'),
      time: dateTime.format('HH:mm:ss'),
      full: dateTime.format('DD.MM.YYYY HH:mm:ss')
    };
  };

  const getActionTag = (action) => {
    const actionMap = {
      buy: { color: 'green', text: t('trading.buy') },
      sell: { color: 'red', text: t('trading.sell') }
    };
    const actionInfo = actionMap[action];
    return <Tag color={actionInfo.color}>{actionInfo.text}</Tag>;
  };

  const getStatusTag = (status) => {
    const statusMap = {
      executed: { color: 'green', text: t('trading.executed') },
      pending: { color: 'orange', text: t('trading.pending') },
      cancelled: { color: 'red', text: t('trading.cancelled') }
    };
    const statusInfo = statusMap[status];
    return <Tag color={statusInfo.color}>{statusInfo.text}</Tag>;
  };

  const handleFilter = () => {
    let filtered = [...tradingData];

    if (filters.dateRange) {
      const [start, end] = filters.dateRange;
      filtered = filtered.filter(item => {
        const itemDate = moment(item.date);
        return itemDate.isBetween(start, end, 'day', '[]');
      });
    }

    if (filters.symbol) {
      filtered = filtered.filter(item => item.symbol === filters.symbol);
    }

    if (filters.action) {
      filtered = filtered.filter(item => item.action === filters.action);
    }

    if (filters.status) {
      filtered = filtered.filter(item => item.status === filters.status);
    }

    setFilteredData(filtered);
  };

  const handleReset = () => {
    setFilters({
      dateRange: null,
      symbol: null,
      action: null,
      status: null
    });
    setFilteredData(tradingData);
  };

  const columns = [
    {
      title: t('trading.date'),
      dataIndex: 'date',
      key: 'date',
      render: (text, record) => {
        const formatted = formatDateTime(record.date, record.time);
        return (
          <div>
            <div>{formatted.date}</div>
            <div style={{ fontSize: '12px', color: '#666' }}>{formatted.time}</div>
          </div>
        );
      },
      sorter: (a, b) => moment(a.date).unix() - moment(b.date).unix(),
    },
    {
      title: t('trading.symbol'),
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
      title: t('trading.action'),
      dataIndex: 'action',
      key: 'action',
      render: (action) => getActionTag(action),
      filters: [
        { text: t('trading.buy'), value: 'buy' },
        { text: t('trading.sell'), value: 'sell' },
      ],
      onFilter: (value, record) => record.action === value,
    },
    {
      title: t('trading.quantity'),
      dataIndex: 'quantity',
      key: 'quantity',
      align: 'right',
      render: (value) => new Intl.NumberFormat('ru-RU').format(value),
    },
    {
      title: t('trading.price'),
      dataIndex: 'price',
      key: 'price',
      align: 'right',
      render: (value) => formatCurrency(value),
    },
    {
      title: t('trading.total'),
      dataIndex: 'total',
      key: 'total',
      align: 'right',
      render: (value) => formatCurrency(value),
    },
    {
      title: t('trading.status'),
      dataIndex: 'status',
      key: 'status',
      render: (status) => getStatusTag(status),
      filters: [
        { text: t('trading.executed'), value: 'executed' },
        { text: t('trading.pending'), value: 'pending' },
        { text: t('trading.cancelled'), value: 'cancelled' },
      ],
      onFilter: (value, record) => record.status === value,
    },
  ];

  const expandedRowRender = (record) => (
    <div className="expanded-row">
      <Title level={5}>{t('trading.reasoning')}:</Title>
      <p>{record.reasoning}</p>
    </div>
  );

  if (loading) {
    return (
      <div className="loading-container">
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div className="trading-history-container">
      <Title level={2}>{t('trading.title')}</Title>
      
      {/* Filters */}
      <Card style={{ marginBottom: 24 }}>
        <Space wrap>
          <RangePicker
            value={filters.dateRange}
            onChange={(dates) => setFilters({ ...filters, dateRange: dates })}
            format="DD.MM.YYYY"
            placeholder={['Дата от', 'Дата до']}
          />
          <Select
            placeholder="Символ"
            style={{ width: 120 }}
            value={filters.symbol}
            onChange={(value) => setFilters({ ...filters, symbol: value })}
            allowClear
          >
            <Option value="SBER">SBER</Option>
            <Option value="GAZP">GAZP</Option>
            <Option value="LKOH">LKOH</Option>
            <Option value="ROSN">ROSN</Option>
          </Select>
          <Select
            placeholder="Действие"
            style={{ width: 120 }}
            value={filters.action}
            onChange={(value) => setFilters({ ...filters, action: value })}
            allowClear
          >
            <Option value="buy">{t('trading.buy')}</Option>
            <Option value="sell">{t('trading.sell')}</Option>
          </Select>
          <Select
            placeholder="Статус"
            style={{ width: 120 }}
            value={filters.status}
            onChange={(value) => setFilters({ ...filters, status: value })}
            allowClear
          >
            <Option value="executed">{t('trading.executed')}</Option>
            <Option value="pending">{t('trading.pending')}</Option>
            <Option value="cancelled">{t('trading.cancelled')}</Option>
          </Select>
          <Button type="primary" icon={<SearchOutlined />} onClick={handleFilter}>
            Фильтр
          </Button>
          <Button icon={<ReloadOutlined />} onClick={handleReset}>
            Сброс
          </Button>
        </Space>
      </Card>

      {/* Trading History Table */}
      <Card>
        <Table
          columns={columns}
          dataSource={filteredData}
          expandable={{
            expandedRowRender,
            rowExpandable: (record) => !!record.reasoning,
          }}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => 
              `${range[0]}-${range[1]} из ${total} записей`,
          }}
          scroll={{ x: 1000 }}
          className="trading-history-table"
        />
      </Card>
    </div>
  );
};

export default TradingHistory;