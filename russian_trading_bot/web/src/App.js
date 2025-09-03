import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import ruRU from 'antd/locale/ru_RU';
import Layout from './components/Layout/Layout';
import Dashboard from './pages/Dashboard/Dashboard';
import Portfolio from './pages/Portfolio/Portfolio';
import TradingHistory from './pages/TradingHistory/TradingHistory';
import TradingDecisions from './pages/TradingDecisions/TradingDecisions';
import './App.css';

function App() {
  return (
    <ConfigProvider locale={ruRU}>
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/portfolio" element={<Portfolio />} />
            <Route path="/trading-history" element={<TradingHistory />} />
            <Route path="/trading-decisions" element={<TradingDecisions />} />
          </Routes>
        </Layout>
      </Router>
    </ConfigProvider>
  );
}

export default App;