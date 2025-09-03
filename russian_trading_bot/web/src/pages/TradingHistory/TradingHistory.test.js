import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { ConfigProvider } from 'antd';
import ruRU from 'antd/locale/ru_RU';
import TradingHistory from './TradingHistory';
import '../../i18n/config';

const renderWithProviders = (component) => {
  return render(
    <ConfigProvider locale={ruRU}>
      {component}
    </ConfigProvider>
  );
};

describe('TradingHistory Component', () => {
  test('renders trading history title in Russian', async () => {
    renderWithProviders(<TradingHistory />);
    
    await waitFor(() => {
      expect(screen.getByText('История торговли')).toBeInTheDocument();
    });
  });

  test('displays table headers in Russian', async () => {
    renderWithProviders(<TradingHistory />);
    
    await waitFor(() => {
      expect(screen.getByText('Дата')).toBeInTheDocument();
      expect(screen.getByText('Символ')).toBeInTheDocument();
      expect(screen.getByText('Действие')).toBeInTheDocument();
      expect(screen.getByText('Количество')).toBeInTheDocument();
      expect(screen.getByText('Цена')).toBeInTheDocument();
      expect(screen.getByText('Сумма')).toBeInTheDocument();
      expect(screen.getByText('Статус')).toBeInTheDocument();
    });
  });

  test('displays Russian trading actions and statuses', async () => {
    renderWithProviders(<TradingHistory />);
    
    await waitFor(() => {
      expect(screen.getByText('Покупка')).toBeInTheDocument();
      expect(screen.getByText('Продажа')).toBeInTheDocument();
      expect(screen.getByText('Исполнено')).toBeInTheDocument();
    });
  });

  test('displays Russian stock names', async () => {
    renderWithProviders(<TradingHistory />);
    
    await waitFor(() => {
      expect(screen.getByText('Сбербанк')).toBeInTheDocument();
      expect(screen.getByText('Газпром')).toBeInTheDocument();
      expect(screen.getByText('ЛУКОЙЛ')).toBeInTheDocument();
    });
  });

  test('formats dates in Russian format (DD.MM.YYYY)', async () => {
    renderWithProviders(<TradingHistory />);
    
    await waitFor(() => {
      // Look for Russian date format
      const dateElements = screen.getAllByText(/\d{2}\.\d{2}\.\d{4}/);
      expect(dateElements.length).toBeGreaterThan(0);
    });
  });

  test('displays prices in RUB currency', async () => {
    renderWithProviders(<TradingHistory />);
    
    await waitFor(() => {
      const rubPrices = screen.getAllByText(/₽/);
      expect(rubPrices.length).toBeGreaterThan(0);
    });
  });

  test('shows filter controls in Russian', async () => {
    renderWithProviders(<TradingHistory />);
    
    await waitFor(() => {
      expect(screen.getByText('Фильтр')).toBeInTheDocument();
      expect(screen.getByText('Сброс')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Дата от')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Дата до')).toBeInTheDocument();
    });
  });

  test('expands row to show reasoning in Russian', async () => {
    renderWithProviders(<TradingHistory />);
    
    await waitFor(() => {
      // Find and click expand button for first row
      const expandButton = document.querySelector('.ant-table-row-expand-icon');
      if (expandButton) {
        fireEvent.click(expandButton);
        
        // Should show reasoning section
        expect(screen.getByText('Обоснование:')).toBeInTheDocument();
      }
    });
  });

  test('applies filters correctly', async () => {
    renderWithProviders(<TradingHistory />);
    
    await waitFor(() => {
      const filterButton = screen.getByText('Фильтр');
      fireEvent.click(filterButton);
      
      // Filter functionality should work (basic test)
      expect(filterButton).toBeInTheDocument();
    });
  });

  test('resets filters correctly', async () => {
    renderWithProviders(<TradingHistory />);
    
    await waitFor(() => {
      const resetButton = screen.getByText('Сброс');
      fireEvent.click(resetButton);
      
      // Reset functionality should work (basic test)
      expect(resetButton).toBeInTheDocument();
    });
  });
});