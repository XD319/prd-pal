import { describe, expect, it, vi } from 'vitest';
import ReviewHistoryPanel from '../ReviewHistoryPanel';
import { renderWithProviders, screen, userEvent } from '../../test/utils';
import { formatDateTime } from '../../utils/formatters';

function makeRun(index, overrides = {}) {
  return {
    run_id: `run-${index}`,
    status: index % 2 === 0 ? 'completed' : 'running',
    created_at: `2026-03-${String((index % 20) + 1).padStart(2, '0')}T08:00:00Z`,
    updated_at: `2026-03-${String((index % 20) + 1).padStart(2, '0')}T09:00:00Z`,
    artifact_presence: {
      report_json: index % 2 === 0,
    },
    ...overrides,
  };
}

describe('ReviewHistoryPanel', () => {
  it('shows loading skeletons while history is loading', () => {
    const { container } = renderWithProviders(
      <ReviewHistoryPanel
        history={{ status: 'loading', runs: [], error: '', refreshing: false }}
        activeRunId=""
        onRefresh={vi.fn()}
        onOpenRun={vi.fn()}
      />,
    );

    expect(container.querySelector('.loading-state-history')).toBeInTheDocument();
  });

  it('shows an empty placeholder when there are no runs', () => {
    renderWithProviders(
      <ReviewHistoryPanel
        history={{ status: 'ready', runs: [], error: '', refreshing: false }}
        activeRunId=""
        onRefresh={vi.fn()}
        onOpenRun={vi.fn()}
      />,
    );

    expect(screen.getByText('No review runs yet')).toBeInTheDocument();
  });

  it('renders run id, status, and timestamps for normal history items', () => {
    const run = makeRun(1, { status: 'failed' });

    renderWithProviders(
      <ReviewHistoryPanel
        history={{ status: 'ready', runs: [run], error: '', refreshing: false }}
        activeRunId=""
        onRefresh={vi.fn()}
        onOpenRun={vi.fn()}
      />,
    );

    const article = screen.getByText(run.run_id).closest('article');

    expect(article).toHaveTextContent(run.run_id);
    expect(article).toHaveTextContent('Failed');
    expect(article).toHaveTextContent(formatDateTime(run.created_at));
    expect(article).toHaveTextContent(formatDateTime(run.updated_at));
  });

  it('filters the list based on the search input', async () => {
    const user = userEvent.setup();

    renderWithProviders(
      <ReviewHistoryPanel
        history={{ status: 'ready', runs: [makeRun(1), makeRun(2), makeRun(20)], error: '', refreshing: false }}
        activeRunId=""
        onRefresh={vi.fn()}
        onOpenRun={vi.fn()}
      />,
    );

    await user.type(screen.getByRole('searchbox', { name: 'Search review history by run ID' }), 'run-20');

    expect(screen.getByText('run-20')).toBeInTheDocument();
    expect(screen.queryByText('run-1')).not.toBeInTheDocument();
    expect(screen.queryByText('run-2')).not.toBeInTheDocument();
  });

  it('updates pagination buttons disabled state across pages', async () => {
    const user = userEvent.setup();
    const runs = Array.from({ length: 11 }, (_, index) => makeRun(index + 1));

    renderWithProviders(
      <ReviewHistoryPanel
        history={{ status: 'ready', runs, error: '', refreshing: false }}
        activeRunId=""
        onRefresh={vi.fn()}
        onOpenRun={vi.fn()}
      />,
    );

    const previousButton = screen.getByRole('button', { name: 'Go to previous history page' });
    const nextButton = screen.getByRole('button', { name: 'Go to next history page' });

    expect(previousButton).toBeDisabled();
    expect(nextButton).toBeEnabled();

    await user.click(nextButton);

    expect(previousButton).toBeEnabled();
    expect(nextButton).toBeDisabled();
  });
});
