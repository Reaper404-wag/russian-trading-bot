import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { I18nextProvider } from 'react-i18next';
import i18n from '../../i18n/config';
import TradingSignals from './TradingSignals';

// Mock the API calls
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
    reasoning: 'Технический анализ показывает пробой уровня сопротивления.',
    riskLevel: 'medium',
    expectedReturn: 3.3,
    timestamp: new Date().toISOString(),
    status: 'pending'
  }
];

const renderWithProviders = (component) => {
  return render(
    <BrowserRouter>
      <I18nextProvider i18n={i18n}>
        {component}
      </I18nextProvider>
    </BrowserRouter>
  );
};

describe('TradingSignals Component', () => {
  beforeEach(() => {
    // Mock fetch
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockSignals),
      })
    );
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  test('renders trading signals title', async () => {
    renderWithProviders(<TradingSignals />);
    
    await waitFor(() => {
      expect(screen.getByText('Торговые сигналы')).toBeInTheDocument();
    });
  });

  test('displays signal information correctly', async () => {
    renderWithProviders(<TradingSignals />);
    
    await waitFor(() => {
      expect(screen.getByText('SBER')).toBeInTheDocument();
      expect(screen.getByText('(Сбербанк)')).toBeInTheDocument();
      expect(screen.getByText('Покупка')).toBeInTheDocument();
      expect(screen.getByText('85%')).toBeInTheDocument();
    });
  });

  test('shows approve and reject buttons for pending signals', async () => {
    renderWithProviders(<TradingSignals />);
    
    await waitFor(() => {
      expect(screen.getByText('Одобрить')).toBeInTheDocument();
      expect(screen.getByText('Отклонить')).toBeInTheDocument();
    });
  });

  test('opens approval modal when approve button is clicked', async () => {
    renderWithProviders(<TradingSignals />);
    
    await waitFor(() => {
      const approveButton = screen.getByText('Одобрить');
      fireEvent.click(approveButton);
    });

    await waitFor(() => {
      expect(screen.getByText('Подтверждение торгового сигнала')).toBeInTheDocument();
    });
  });

  test('formats currency correctly', async () => {
    renderWithProviders(<TradingSignals />);
    
    await waitFor(() => {
      expect(screen.getByText('285,50 ₽')).toBeInTheDocument();
      expect(screen.getByText('295,00 ₽')).toBeInTheDocument();
    });
  });

  test('displays confidence with correct color coding', async () => {
    renderWithProviders(<TradingSignals />);
    
    await waitFor(() => {
      const confidenceElement = screen.getByText('85%');
      expect(confidenceElement).toHaveStyle('color: #52c41a'); // Green for high confidence
    });
  });
});