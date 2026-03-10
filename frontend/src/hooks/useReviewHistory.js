import { useCallback, useEffect, useState } from 'react';
import { fetchRuns } from '../api';
import { formatApiError } from '../utils/errors';

const initialHistory = {
  status: 'loading',
  runs: [],
  error: '',
  refreshing: false,
};

function useReviewHistory({ loadOnMount = true } = {}) {
  const [history, setHistory] = useState(initialHistory);

  const loadRunHistory = useCallback(async ({ preserveRuns = true } = {}) => {
    setHistory((current) => {
      const shouldPreserve = preserveRuns && current.runs.length > 0;
      return {
        ...current,
        status: shouldPreserve ? current.status : 'loading',
        refreshing: shouldPreserve,
        error: '',
      };
    });

    try {
      const payload = await fetchRuns();
      setHistory({
        status: 'ready',
        runs: Array.isArray(payload?.runs) ? payload.runs : [],
        error: '',
        refreshing: false,
      });
    } catch (error) {
      const message = formatApiError(error, 'Review history could not be loaded.');
      setHistory((current) => ({
        ...current,
        status: current.runs.length > 0 ? current.status : 'error',
        refreshing: false,
        error: message,
      }));
    }
  }, []);

  useEffect(() => {
    if (!loadOnMount) {
      return;
    }

    void loadRunHistory({ preserveRuns: false });
  }, [loadOnMount, loadRunHistory]);

  return {
    history,
    loadRunHistory,
  };
}

export default useReviewHistory;

