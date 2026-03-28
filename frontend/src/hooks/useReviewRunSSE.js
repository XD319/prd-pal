import { startTransition, useCallback, useEffect, useRef, useState } from 'react';
import { fetchReviewStatus } from '../api';
import { deriveFailureMessage } from '../utils/derivers';
import { formatApiError } from '../utils/errors';

const pollIntervalMs = 2500;
const maxReconnectDelayMs = 30000;
const fallbackThreshold = 3;
const primaryNodes = [
  'parser',
  'parallel_start',
  'planner',
  'risk',
  'review_join',
  'delivery_planning',
  'reviewer',
  'route_decider',
  'reporter',
  'finalize_artifacts',
];

const initialState = {
  run: null,
  progress: null,
  error: '',
  isConnected: false,
  isPolling: false,
  loadState: 'idle',
};

function clonePayload(payload) {
  if (!payload || typeof payload !== 'object') {
    return null;
  }
  return {
    ...payload,
    progress: payload.progress && typeof payload.progress === 'object'
      ? {
        ...payload.progress,
        nodes: payload.progress.nodes && typeof payload.progress.nodes === 'object'
          ? Object.fromEntries(
            Object.entries(payload.progress.nodes).map(([key, value]) => [key, { ...value }]),
          )
          : {},
      }
      : { nodes: {} },
  };
}

function nodeWeight(status) {
  const normalized = String(status ?? '').toLowerCase();
  if (normalized === 'running') {
    return 0.5;
  }
  if (normalized === 'completed' || normalized === 'failed') {
    return 1;
  }
  return 0;
}

function computePercent(nodes, runStatus) {
  if (runStatus === 'completed') {
    return 100;
  }

  const completedWeight = primaryNodes.reduce((total, nodeId) => {
    const node = nodes?.[nodeId];
    return total + nodeWeight(node?.status);
  }, 0);

  const percent = primaryNodes.length
    ? Math.round((completedWeight / primaryNodes.length) * 100)
    : 0;

  return runStatus === 'failed' ? percent : Math.min(percent, 99);
}

function normalizeNodeStatus(eventStatus, payload) {
  const normalized = String(eventStatus ?? '').toLowerCase();
  if (normalized === 'start') {
    return 'running';
  }
  if (normalized === 'end') {
    return payload?.error ? 'failed' : 'completed';
  }
  if (normalized === 'running' || normalized === 'completed' || normalized === 'failed') {
    return normalized;
  }
  return 'pending';
}

function mergeSsePayload(currentPayload, payload) {
  if (!payload || typeof payload !== 'object') {
    return currentPayload;
  }

  const nextPayload = clonePayload(currentPayload) ?? {
    run_id: String(payload.run_id ?? ''),
    status: 'running',
    progress: {
      percent: 0,
      current_node: '',
      nodes: {},
      updated_at: String(payload.timestamp ?? ''),
      error: '',
    },
    report_paths: {},
  };

  const nextProgress = nextPayload.progress ?? { nodes: {} };
  nextProgress.nodes = nextProgress.nodes ?? {};

  if (payload.node === 'run' || payload.terminal) {
    nextPayload.status = String(payload.status ?? nextPayload.status ?? 'running');
    nextProgress.current_node = '';
    nextProgress.updated_at = String(payload.timestamp ?? nextProgress.updated_at ?? '');
    nextProgress.error = String(payload.error ?? nextProgress.error ?? '');
    nextProgress.percent = computePercent(nextProgress.nodes, nextPayload.status);
    if (nextPayload.status === 'completed') {
      nextProgress.percent = 100;
    }
    nextPayload.progress = nextProgress;
    return nextPayload;
  }

  const nodeId = String(payload.node ?? '').trim();
  if (!nodeId) {
    return nextPayload;
  }

  const node = { ...(nextProgress.nodes[nodeId] ?? { status: 'pending', runs: 0 }) };
  const nodeStatus = normalizeNodeStatus(payload.status, payload);
  if (String(payload.status ?? '').toLowerCase() === 'start') {
    node.runs = Number(node.runs ?? 0) + 1;
    node.last_start = String(payload.timestamp ?? node.last_start ?? '');
    nextProgress.current_node = nodeId;
  } else if (String(payload.status ?? '').toLowerCase() === 'end') {
    node.last_end = String(payload.timestamp ?? node.last_end ?? '');
    if (nextProgress.current_node === nodeId) {
      nextProgress.current_node = '';
    }
  }

  node.status = nodeStatus;
  nextProgress.nodes[nodeId] = node;
  nextProgress.updated_at = String(payload.timestamp ?? nextProgress.updated_at ?? '');
  if (payload.error) {
    nextProgress.error = String(payload.error);
  }
  nextPayload.status = nextPayload.status === 'queued' ? 'running' : (nextPayload.status ?? 'running');
  nextProgress.percent = computePercent(nextProgress.nodes, nextPayload.status);
  nextPayload.progress = nextProgress;
  return nextPayload;
}

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
        const nextRun = mergeSsePayload(current.run, payload);
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
    const source = new window.EventSource(`/api/review/${encodeURIComponent(runIdRef.current)}/progress/stream`);
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
          const nextRun = mergeSsePayload(current.run, payload);
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
