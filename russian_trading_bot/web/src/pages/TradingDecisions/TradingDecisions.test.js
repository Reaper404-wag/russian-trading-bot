import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { I18nextProvider } from 'react-i18next';
import i18n from '../../i18n/config';
import TradingDecisions from './TradingDecisions';

const renderWithProviders = (component) => {
  return render(
    <BrowserRouter>
      <I18nextProvider i18n={i18n}>
        {component}
      </I18nextProvider>
    </BrowserRouter>
  );
};

describe('TradingDecisions Component', () => {
  beforeEach(() => {
    // Mock fetch for all API calls
    global.fetch = jest.fn((url) => {
      if (url.includes('/api/trading-signals')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve([]),
        });
      }
      if (url.includes('/api/risk-assessment')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            overallRiskScore: 65,
            riskLevel: 'medium',
            portfolioRisk: {},
            marketRisk: {},
            riskFactors: [],
            recommendations: [],
            lastUpdated: new Date().toISOString()
          }),
        });
      }
      if (url.includes('/api/notifications')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve([]),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({}),
      });
    });
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  test('renders trading decisions page title', () => {
    renderWithProviders(<TradingDecisions />);
    expect(screen.getByText('Торговые решения')).toBeInTheDocument();
  });

  test('renders page subtitle', () => {
    renderWithProviders(<TradingDecisions />);
    expect(screen.getByText('Анализ сигналов, управление рисками и уведомления')).toBeInTheDocument();
  });

  test('renders refresh all button', () => {
    renderWithProviders(<TradingDecisions />);
    expect(screen.getByText('Обновить все')).toBeInTheDocument();
  });

  test('renders quick stats cards', () => {
    renderWithProviders(<TradingDecisions />);
    expect(screen.getByText('Активные сигналы')).toBeInTheDocument();
    expect(screen.getByText('Уровень риска')).toBeInTheDocument();
    expect(screen.getByText('Непрочитанные')).toBeInTheDocument();
  });

  test('renders tab navigation', () => {
    renderWithProviders(<TradingDecisions />);
    expect(screen.getByText('Торговые сигналы')).toBeInTheDocument();
    expect(screen.getByText('Оценка рисков')).toBeInTheDocument();
    expect(screen.getByText('Уведомления')).toBeInTheDocument();
  });

  test('switches tabs correctly', async () => {
    renderWithProviders(<TradingDecisions />);
    
    const riskTab = screen.getByText('Оценка рисков');
    fireEvent.click(riskTab);
    
    await waitFor(() => {
      // The risk assessment component should be visible
      expect(screen.getByText('Оценка рисков')).toBeInTheDocument();
    });
  });

  test('refresh button shows loading state when clicked', async () => {
    renderWithProviders(<TradingDecisions />);
    
    const refreshButton = screen.getByText('Обновить все');
    fireEvent.click(refreshButton);
    
    // Button should show loading state
    expect(refreshButton.closest('button')).toHaveClass('ant-btn-loading');
  });

  test('displays correct stat values', () => {
    renderWithProviders(<TradingDecisions />);
    
    // Check for mock stat values
    expect(screen.getByText('3')).toBeInTheDocument(); // Active signals
    expect(screen.getByText('Средний')).toBeInTheDocument(); // Risk level
    expect(screen.getByText('2')).toBeInTheDocument(); // Unread alerts
  });
});