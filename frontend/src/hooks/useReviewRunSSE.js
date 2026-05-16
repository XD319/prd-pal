import { startTransition, useCallback, useEffect, useRef, useState } from 'react';
import { buildReviewProgressStreamUrl, fetchReviewStatus } from '../api';
import { deriveFailureMessage } from '../utils/derivers';
import { formatApiError } from '../utils/errors';
import { mergeSseProgressPayload } from '../utils/progress';

const pollIntervalMs = 2500;
const maxReconnectDelayMs = 30000;
const fallbackThreshold = 3;

const initialState = {
  run: null,
  progress: null,
  error: '',
  isConnected: false,
  isPolling: false,
  loadState: 'idle',
};

function useReviewRunSSE(runId, options = {}) {
  const { fallbackToPolling = true } = options;
  const [state, setState] = useState(() => ({
    ...initialState,
    loadState: runId ? 'loading' : 'idle',
  }));
  const eventSourceRef = useRef(null);
  const reconnectTimeoutRef = useRef(0);
  const pollingTimeoutRef = useRef(0);
  const closedRef = useRef(false);
  const reconnectAttemptsRef = useRef(0);
  const runIdRef = useRef(runId);

  const clearReconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      window.clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = 0;
    }
  }, []);

  const clearPolling = useCallback(() => {
    if (pollingTimeoutRef.current) {
      window.clearTimeout(pollingTimeoutRef.current);
      pollingTimeoutRef.current = 0;
    }
  }, []);

  const closeConnection = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  }, []);

  const refreshStatus = useCallback(async () => {
    if (!runIdRef.current) {
      return null;
    }

    try {
      const payload = await fetchReviewStatus(runIdRef.current);
      startTransition(() => {
        setState((current) => ({
          ...current,
          run: payload,
          progress: payload?.progress ?? null,
          error: '',
          loadState: 'ready',
        }));
      });
      return payload;
    } catch (error) {
      const message = formatApiError(error, 'Live progress could not be loaded.');
      setState((current) => ({
        ...current,
        error: message,
        loadState: current.run ? 'ready' : 'error',
      }));
      return null;
    }
  }, []);

  const stopStreaming = useCallback(() => {
    clearReconnect();
    clearPolling();
    closeConnection();
  }, [clearPolling, clearReconnect, closeConnection]);

  const schedulePolling = useCallback(() => {
    clearPolling();
    pollingTimeoutRef.current = window.setTimeout(async () => {
      const payload = await refreshStatus();
      if (!payload || ['completed', 'failed'].includes(String(payload.status ?? ''))) {
        return;
      }
      schedulePolling();
    }, pollIntervalMs);
  }, [clearPolling, refreshStatus]);

  const enablePollingFallback = useCallback(() => {
    closeConnection();
    clearReconnect();
    setState((current) => ({
      ...current,
      isConnected: false,
      isPolling: true,
    }));
    void refreshStatus().then((payload) => {
      if (!payload || ['completed', 'failed'].includes(String(payload.status ?? ''))) {
        return;
      }
      schedulePolling();
    });
  }, [clearReconnect, closeConnection, refreshStatus, schedulePolling]);

  const handleTerminalPayload = useCallback((payload) => {
    startTransition(() => {
      setState((current) => {
        const nextRun = mergeSseProgressPayload(current.run, payload);
        return {
          ...current,
          run: nextRun,
          progress: nextRun?.progress ?? null,
          isConnected: false,
          loadState: 'ready',
          error: payload?.status === 'failed'
            ? deriveFailureMessage(nextRun, current.error || String(payload?.error ?? ''))
            : current.error,
        };
      });
    });
    stopStreaming();
    void refreshStatus();
  }, [refreshStatus, stopStreaming]);

  const connect = useCallback(() => {
    if (!runIdRef.current || closedRef.current || state.isPolling) {
      return;
    }

    if (typeof window === 'undefined' || typeof window.EventSource !== 'function') {
      if (fallbackToPolling) {
        enablePollingFallback();
      }
      return;
    }

    closeConnection();
    const source = new window.EventSource(buildReviewProgressStreamUrl(runIdRef.current));
    eventSourceRef.current = source;

    source.onopen = () => {
      reconnectAttemptsRef.current = 0;
      clearReconnect();
      setState((current) => ({
        ...current,
        isConnected: true,
        isPolling: false,
        error: '',
      }));
    };

    const handlePayload = (rawData, isTerminalEvent = false) => {
      let payload = null;
      try {
        payload = JSON.parse(rawData);
      } catch {
        return;
      }

      if (isTerminalEvent || payload?.terminal || payload?.node === 'run') {
        handleTerminalPayload(payload);
        return;
      }

      startTransition(() => {
        setState((current) => {
          const nextRun = mergeSseProgressPayload(current.run, payload);
          return {
            ...current,
            run: nextRun,
            progress: nextRun?.progress ?? null,
            loadState: 'ready',
          };
        });
      });
    };

    source.onmessage = (event) => {
      handlePayload(event.data, false);
    };

    source.addEventListener('complete', (event) => {
      handlePayload(event.data, true);
    });

    source.onerror = () => {
      closeConnection();
      setState((current) => ({
        ...current,
        isConnected: false,
      }));

      reconnectAttemptsRef.current += 1;
      if (fallbackToPolling && reconnectAttemptsRef.current >= fallbackThreshold) {
        enablePollingFallback();
        return;
      }

      const delay = Math.min(1000 * (2 ** Math.max(reconnectAttemptsRef.current - 1, 0)), maxReconnectDelayMs);
      clearReconnect();
      reconnectTimeoutRef.current = window.setTimeout(() => {
        connect();
      }, delay);
    };
  }, [
    clearReconnect,
    closeConnection,
    enablePollingFallback,
    fallbackToPolling,
    handleTerminalPayload,
    state.isPolling,
  ]);

  useEffect(() => {
    runIdRef.current = runId;
    closedRef.current = false;
    reconnectAttemptsRef.current = 0;
    setState({
      ...initialState,
      loadState: runId ? 'loading' : 'idle',
    });

    if (!runId) {
      stopStreaming();
      return undefined;
    }

    void refreshStatus();
    connect();

    return () => {
      closedRef.current = true;
      stopStreaming();
    };
  }, [connect, refreshStatus, runId, stopStreaming]);

  useEffect(() => {
    if (!state.run || state.isPolling) {
      return;
    }

    const status = String(state.run.status ?? '');
    if (status === 'completed' || status === 'failed') {
      stopStreaming();
    }
  }, [state.isPolling, state.run, stopStreaming]);

  return {
    run: state.run,
    progress: state.progress,
    error: state.error,
    isConnected: state.isConnected,
    isPolling: state.isPolling,
    loadState: state.loadState,
    refreshStatus,
    closeConnection: stopStreaming,
    statusPayload: state.run,
    status: state.run?.status ?? 'idle',
  };
}

export default useReviewRunSSE;
