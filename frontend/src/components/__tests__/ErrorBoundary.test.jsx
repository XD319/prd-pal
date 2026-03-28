import { afterEach, describe, expect, it, vi } from 'vitest';
import ErrorBoundary from '../ErrorBoundary';
import { renderWithProviders, screen } from '../../test/utils';

function HealthyChild() {
  return <div>Child rendered normally</div>;
}

function BrokenChild() {
  throw new Error('Boom from child');
}

describe('ErrorBoundary', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('does not show the error UI when the child renders normally', () => {
    renderWithProviders(
      <ErrorBoundary>
        <HealthyChild />
      </ErrorBoundary>,
    );

    expect(screen.getByText('Child rendered normally')).toBeInTheDocument();
    expect(screen.queryByText('Something went wrong')).not.toBeInTheDocument();
  });

  it('shows fallback UI when the child throws an error', () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});

    renderWithProviders(
      <ErrorBoundary>
        <BrokenChild />
      </ErrorBoundary>,
    );

    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
  });

  it('displays the thrown error message', () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});

    renderWithProviders(
      <ErrorBoundary>
        <BrokenChild />
      </ErrorBoundary>,
    );

    expect(screen.getByText('Boom from child')).toBeInTheDocument();
  });
});
