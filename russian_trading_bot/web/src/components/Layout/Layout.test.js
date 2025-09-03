import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import ruRU from 'antd/locale/ru_RU';
import Layout from './Layout';
import '../../i18n/config';

// Mock useNavigate
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
  useLocation: () => ({ pathname: '/' })
}));

const renderWithProviders = (component) => {
  return render(
    <ConfigProvider locale={ruRU}>
      <BrowserRouter>
        {component}
      </BrowserRouter>
    </ConfigProvider>
  );
};

describe('Layout Component', () => {
  beforeEach(() => {
    mockNavigate.mockClear();
  });

  test('renders layout with Russian title', () => {
    renderWithProviders(
      <Layout>
        <div>Test Content</div>
      </Layout>
    );

    expect(screen.getByText('Российский Торговый Бот')).toBeInTheDocument();
    expect(screen.getByText('Test Content')).toBeInTheDocument();
  });

  test('renders navigation menu items in Russian', () => {
    renderWithProviders(
      <Layout>
        <div>Test Content</div>
      </Layout>
    );

    expect(screen.getByText('Панель управления')).toBeInTheDocument();
    expect(screen.getByText('Портфель')).toBeInTheDocument();
    expect(screen.getByText('История')).toBeInTheDocument();
  });

  test('displays current date in Russian format', () => {
    renderWithProviders(
      <Layout>
        <div>Test Content</div>
      </Layout>
    );

    // Check if date is displayed (format may vary based on current date)
    const dateElement = screen.getByText(/\d{4}/); // Look for year
    expect(dateElement).toBeInTheDocument();
  });

  test('navigates to correct route when menu item is clicked', () => {
    renderWithProviders(
      <Layout>
        <div>Test Content</div>
      </Layout>
    );

    const portfolioMenuItem = screen.getByText('Портфель');
    fireEvent.click(portfolioMenuItem);

    expect(mockNavigate).toHaveBeenCalledWith('/portfolio');
  });

  test('collapses sidebar when collapse button is clicked', () => {
    renderWithProviders(
      <Layout>
        <div>Test Content</div>
      </Layout>
    );

    // Find and click the collapse button
    const collapseButton = document.querySelector('.ant-layout-sider-trigger');
    if (collapseButton) {
      fireEvent.click(collapseButton);
      // After collapse, title should change to abbreviated form
      expect(screen.getByText('РТБ')).toBeInTheDocument();
    }
  });
});