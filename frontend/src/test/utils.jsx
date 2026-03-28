import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { ToastProvider } from '../components/ToastProvider';

function TestProviders({ children }) {
  return (
    <ToastProvider>
      <BrowserRouter>
        {children}
      </BrowserRouter>
    </ToastProvider>
  );
}

export function renderWithProviders(component, options) {
  return render(component, {
    wrapper: TestProviders,
    ...options,
  });
}

export { fireEvent, screen, userEvent, waitFor };
