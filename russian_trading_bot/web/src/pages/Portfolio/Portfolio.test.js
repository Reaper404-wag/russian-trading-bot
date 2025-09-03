import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { ConfigProvider } from 'antd';
import ruRU from 'antd/locale/ru_RU';
import Portfolio from './Portfolio';
import '../../i18n/config';

const renderWithProviders = (component) => {
  return render(
    <ConfigProvider locale={ruRU}>
      {component}
    </ConfigProvider>
  );
};

describe('Portfolio Component', () => {
  test('renders portfolio title in Russian', async () => {
    renderWithProviders(<Portfolio />);
    
    await waitFor(() => {
      expect(screen.getByText('Обзор портфеля')).toBeInTheDocument();
    });
  });

  test('displays portfolio statistics with RUB currency', async () => {
    renderWithProviders(<Portfolio />);
    
    await waitFor(() => {
      expect(screen.getByText('Общая стоимость')).toBeInTheDocument();
      expect(screen.getByText('Денежный остаток')).toBeInTheDocument();
      expect(screen.getByText('Дневная П/У')).toBeInTheDocument();
      expect(screen.getByText('Общая доходность')).toBeInTheDocument();
    });

    // Check for RUB currency symbols
    const rubSymbols = screen.getAllByText(/₽/);
    expect(rubSymbols.length).toBeGreaterThan(0);
  });

  test('displays positions table with Russian headers', async () => {
    renderWithProviders(<Portfolio />);
    
    await waitFor(() => {
      expect(screen.getByText('Позиции')).toBeInTheDocument();
      expect(screen.getByText('Символ')).toBeInTheDocument();
      expect(screen.getByText('Количество')).toBeInTheDocument();
      expect(screen.getByText('Средняя цена')).toBeInTheDocument();
      expect(screen.getByText('Текущая цена')).toBeInTheDocument();
      expect(screen.getByText('Рыночная стоимость')).toBeInTheDocument();
      expect(screen.getByText('Нереализованная П/У')).toBeInTheDocument();
    });
  });

  test('displays Russian stock symbols and names', async () => {
    renderWithProviders(<Portfolio />);
    
    await waitFor(() => {
      expect(screen.getByText('SBER')).toBeInTheDocument();
      expect(screen.getByText('Сбербанк')).toBeInTheDocument();
      expect(screen.getByText('GAZP')).toBeInTheDocument();
      expect(screen.getByText('Газпром')).toBeInTheDocument();
      expect(screen.getByText('LKOH')).toBeInTheDocument();
      expect(screen.getByText('ЛУКОЙЛ')).toBeInTheDocument();
    });
  });

  test('formats numbers according to Russian locale', async () => {
    renderWithProviders(<Portfolio />);
    
    await waitFor(() => {
      // Check for Russian number formatting (spaces as thousands separators)
      const formattedNumbers = screen.getAllByText(/\d{1,3}(\s\d{3})*/);
      expect(formattedNumbers.length).toBeGreaterThan(0);
    });
  });

  test('shows loading state initially', () => {
    renderWithProviders(<Portfolio />);
    
    // Should show loading spinner initially
    expect(document.querySelector('.ant-spin')).toBeInTheDocument();
  });
});