import { describe, expect, it } from 'vitest';
import { computeProgressPercent, mergeSseProgressPayload } from '../utils/progress';

describe('progress helpers', () => {
  it('merges SSE node start and end events without mutating the current payload', () => {
    const current = {
      run_id: 'run-1',
      status: 'queued',
      progress: {
        percent: 0,
        current_node: '',
        nodes: {},
        updated_at: '',
        error: '',
      },
      report_paths: {},
    };

    const running = mergeSseProgressPayload(current, {
      run_id: 'run-1',
      node: 'parser',
      status: 'start',
      timestamp: '2026-05-14T01:00:00Z',
    });

    expect(current.status).toBe('queued');
    expect(current.progress.nodes.parser).toBeUndefined();
    expect(running.status).toBe('running');
    expect(running.progress.current_node).toBe('parser');
    expect(running.progress.nodes.parser).toMatchObject({
      status: 'running',
      runs: 1,
      last_start: '2026-05-14T01:00:00Z',
    });
    expect(running.progress.percent).toBe(5);

    const completed = mergeSseProgressPayload(running, {
      run_id: 'run-1',
      node: 'parser',
      status: 'end',
      timestamp: '2026-05-14T01:00:05Z',
    });

    expect(completed.progress.current_node).toBe('');
    expect(completed.progress.nodes.parser).toMatchObject({
      status: 'completed',
      runs: 1,
      last_end: '2026-05-14T01:00:05Z',
    });
    expect(completed.progress.percent).toBe(10);
  });

  it('marks terminal run payloads as complete even when node progress is partial', () => {
    const current = {
      run_id: 'run-1',
      status: 'running',
      progress: {
        percent: 10,
        current_node: 'parser',
        nodes: {
          parser: { status: 'completed', runs: 1 },
        },
        updated_at: '2026-05-14T01:00:05Z',
        error: '',
      },
      report_paths: {},
    };

    const next = mergeSseProgressPayload(current, {
      run_id: 'run-1',
      node: 'run',
      status: 'completed',
      terminal: true,
      timestamp: '2026-05-14T01:01:00Z',
    });

    expect(next.status).toBe('completed');
    expect(next.progress.current_node).toBe('');
    expect(next.progress.percent).toBe(100);
    expect(computeProgressPercent(next.progress.nodes, next.status)).toBe(100);
  });
});
