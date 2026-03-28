import { describe, expect, it, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import useReviewHistory from '../useReviewHistory';

const mockFetchRuns = vi.fn();

vi.mock('../../api', async () => {
  const actual = await vi.importActual('../../api');
  return {
    ...actual,
    fetchRuns: (...args) => mockFetchRuns(...args),
  };
});

describe('useReviewHistory', () => {
  it('starts in a loading state', () => {
    mockFetchRuns.mockReturnValue(new Promise(() => {}));

    const { result } = renderHook(() => useReviewHistory());

    expect(result.current.history.status).toBe('loading');
    expect(result.current.history.runs).toEqual([]);
  });

  it('updates the runs list after a successful fetch', async () => {
    mockFetchRuns.mockResolvedValue({
      runs: [{ run_id: 'run-1', status: 'completed' }],
    });

    const { result } = renderHook(() => useReviewHistory());

    await waitFor(() => {
      expect(result.current.history.status).toBe('ready');
    });

    expect(result.current.history.runs).toEqual([{ run_id: 'run-1', status: 'completed' }]);
    expect(result.current.history.error).toBe('');
  });

  it('sets an error state when fetching history fails', async () => {
    mockFetchRuns.mockRejectedValue(new Error('Network unavailable'));

    const { result } = renderHook(() => useReviewHistory());

    await waitFor(() => {
      expect(result.current.history.status).toBe('error');
    });

    expect(result.current.history.error).toBe('Network unavailable');
    expect(result.current.history.runs).toEqual([]);
  });
});
