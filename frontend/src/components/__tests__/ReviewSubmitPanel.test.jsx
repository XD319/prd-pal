import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import HomePage from '../../pages/HomePage';
import { renderWithProviders, userEvent } from '../../test/utils';

const mockNavigate = vi.fn();
const mockSubmitReview = vi.fn();
const mockUseReviewHistory = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock('../../api', async () => {
  const actual = await vi.importActual('../../api');
  return {
    ...actual,
    submitReview: (...args) => mockSubmitReview(...args),
  };
});

vi.mock('../../hooks/useReviewHistory', () => ({
  default: (...args) => mockUseReviewHistory(...args),
}));

function createDeferred() {
  let resolve;
  let reject;
  const promise = new Promise((nextResolve, nextReject) => {
    resolve = nextResolve;
    reject = nextReject;
  });
  return { promise, resolve, reject };
}

describe('ReviewSubmitPanel', () => {
  beforeEach(() => {
    mockNavigate.mockReset();
    mockSubmitReview.mockReset();
    mockUseReviewHistory.mockReturnValue({
      history: {
        status: 'ready',
        runs: [],
        error: '',
        refreshing: false,
      },
      loadRunHistory: vi.fn(),
    });
    window.confirm = vi.fn(() => true);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders prd_text, prd_path, and source inputs together', () => {
    renderWithProviders(<HomePage />);

    expect(screen.getByLabelText('PRD Content')).toBeInTheDocument();
    expect(screen.getByLabelText('File Path')).toBeInTheDocument();
    expect(screen.getByLabelText('Document Source')).toBeInTheDocument();
  });

  it('shows validation when all inputs are empty', async () => {
    const user = userEvent.setup();
    renderWithProviders(<HomePage />);

    await user.click(screen.getByRole('button', { name: 'Submit review' }));

    expect(screen.getByText('Provide source, or exactly one of prd_text or prd_path.')).toBeInTheDocument();
    expect(mockSubmitReview).not.toHaveBeenCalled();
  });

  it('calls the submit API and shows loading state after content is entered', async () => {
    const user = userEvent.setup();
    const deferred = createDeferred();
    mockSubmitReview.mockReturnValue(deferred.promise);

    renderWithProviders(<HomePage />);

    await user.type(screen.getByLabelText('PRD Content'), 'A realistic PRD body');
    await user.click(screen.getByRole('button', { name: 'Submit review' }));

    expect(mockSubmitReview).toHaveBeenCalledWith({ prd_text: 'A realistic PRD body' });
    expect(screen.getByRole('button', { name: 'Submitting review' })).toBeDisabled();
    expect(screen.getByText('Submitting...')).toBeInTheDocument();

    deferred.resolve({ run_id: 'run-123' });

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/run/run-123');
    });
  });

  it('resets the form after a successful submission', async () => {
    const user = userEvent.setup();
    mockSubmitReview.mockResolvedValue({ run_id: 'run-456' });

    renderWithProviders(<HomePage />);

    const textarea = screen.getByLabelText('PRD Content');
    await user.type(textarea, 'Reset me after success');
    await user.click(screen.getByRole('button', { name: 'Submit review' }));

    await waitFor(() => {
      expect(textarea).toHaveValue('');
    });
  });

  it('shows an error toast when submission fails', async () => {
    const user = userEvent.setup();
    mockSubmitReview.mockRejectedValue(new Error('Submission exploded'));

    renderWithProviders(<HomePage />);

    await user.type(screen.getByLabelText('PRD Content'), 'Failure path');
    await user.click(screen.getByRole('button', { name: 'Submit review' }));

    expect(await screen.findByRole('status')).toHaveTextContent('Submission exploded');
  });
});
