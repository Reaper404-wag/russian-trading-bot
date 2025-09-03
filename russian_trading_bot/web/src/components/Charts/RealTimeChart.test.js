import React from 'react';
import { render, screen } from '@testing-library/react';
import { I18nextProvider } from 'react-i18next';
import i18n from '../../i18n/config';
import RealTimeChart from './RealTimeChart';

// Mock lightweight-charts
jest.mock('lightweight-charts', () => ({
  createChart: jest.fn(() => ({
    addCandlestickSeries: jest.fn(() => ({
      setData: jest.fn(),
    })),
    addHistogramSeries: jest.fn(() => ({
      setData: jest.fn(),
    })),
    applyOptions: jest.fn(),
    remove: jest.fn(),
  })),
}));

const renderWithI18n = (component) => {
  return render(
    <I18nextProvider i18n={i18n}>
      {component}
    </I18nextProvider>
  );
};

describe('RealTimeChart', () => {
  test('renders real-time chart component', () => {
    renderWithI18n(<RealTimeChart />);
    
    // Check if the chart title is rendered
    expect(screen.getByText(/Цена в реальном времени/i)).toBeInTheDocument();
    
    // Check if stock selector is rendered
    expect(screen.getByDisplayValue(/SBER/i)).toBeInTheDocument();
  });

  test('renders loading state initially', () => {
    renderWithI18n(<RealTimeChart />);
    
    // Should show loading spinner initially
    expect(screen.getByText(/Загрузка/i)).toBeInTheDocument();
  });
});