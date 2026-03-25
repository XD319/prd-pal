import { describe, expect, it } from 'vitest';
import RunProgressCard from '../RunProgressCard';
import { renderWithProviders, screen } from '../../test/utils';

const statusPayload = {
  status: 'running',
  progress: {
    percent: 55,
    current_node: 'planner',
    updated_at: '2026-03-25T12:00:00Z',
    nodes: {
      parser: {
        status: 'completed',
        runs: 1,
        last_end: '2026-03-25T11:55:00Z',
      },
      planner: {
        status: 'running',
        runs: 1,
        last_start: '2026-03-25T11:56:00Z',
      },
      reviewer: {
        status: 'pending',
        runs: 0,
      },
      finalize_artifacts: {
        status: 'failed',
        runs: 1,
        last_end: '2026-03-25T11:59:00Z',
      },
    },
  },
};

describe('RunProgressCard', () => {
  it('renders pending, running, completed, and failed step states', () => {
    const { container } = renderWithProviders(
      <RunProgressCard
        runId="run-123"
        status="running"
        statusPayload={statusPayload}
        loadState="ready"
      />,
    );

    expect(container.querySelector('.stepper-step-completed')).toBeInTheDocument();
    expect(container.querySelector('.stepper-step-running')).toBeInTheDocument();
    expect(container.querySelector('.stepper-step-pending')).toBeInTheDocument();
    expect(container.querySelector('.stepper-step-failed')).toBeInTheDocument();
  });

  it('highlights the current active step', () => {
    const { container } = renderWithProviders(
      <RunProgressCard
        runId="run-123"
        status="running"
        statusPayload={statusPayload}
        loadState="ready"
      />,
    );

    expect(container.querySelector('.stepper-step.is-current[aria-current="step"]')).toHaveTextContent('planner');
  });

  it('shows a completed success state when every step is finished', () => {
    renderWithProviders(
      <RunProgressCard
        runId="run-999"
        status="completed"
        loadState="ready"
        statusPayload={{
          status: 'completed',
          progress: {
            percent: 100,
            current_node: 'finalize_artifacts',
            updated_at: '2026-03-25T12:10:00Z',
            nodes: {
              parser: { status: 'completed', runs: 1, last_end: '2026-03-25T12:01:00Z' },
              finalize_artifacts: { status: 'completed', runs: 1, last_end: '2026-03-25T12:10:00Z' },
            },
          },
        }}
      />,
    );

    expect(screen.getAllByText('Completed').length).toBeGreaterThan(0);
    expect(screen.getByText('100%')).toBeInTheDocument();
  });
});
