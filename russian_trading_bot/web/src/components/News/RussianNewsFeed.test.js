import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { I18nextProvider } from 'react-i18next';
import i18n from '../../i18n/config';
import RussianNewsFeed from './RussianNewsFeed';

const renderWithI18n = (component) => {
  return render(
    <I18nextProvider i18n={i18n}>
      {component}
    </I18nextProvider>
  );
};

describe('RussianNewsFeed', () => {
  test('renders news feed component', async () => {
    renderWithI18n(<RussianNewsFeed />);
    
    // Check if the news feed title is rendered
    expect(screen.getByText(/Российские финансовые новости/i)).toBeInTheDocument();
    
    // Check if refresh button is rendered
    expect(screen.getByText(/Обновить/i)).toBeInTheDocument();
    
    // Wait for news items to load
    await waitFor(() => {
      expect(screen.getByText(/Сбербанк увеличил прогноз/i)).toBeInTheDocument();
    });
  });

  test('displays news items with correct structure', async () => {
    renderWithI18n(<RussianNewsFeed />);
    
    await waitFor(() => {
      // Check for news source tags
      expect(screen.getByText('РБК')).toBeInTheDocument();
      expect(screen.getByText('Ведомости')).toBeInTheDocument();
      
      // Check for sentiment tags
      expect(screen.getByText('Негативные')).toBeInTheDocument();
      expect(screen.getByText('Позитивные')).toBeInTheDocument();
    });
  });
});