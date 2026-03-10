import { startTransition, useCallback, useEffect, useRef, useState } from 'react';
import {
  downloadReportArtifact,
  fetchReviewResult,
  fetchReviewStatus,
} from '../api';
import { useToast } from '../components/ToastProvider';
import { deriveFailureMessage } from '../utils/derivers';
import { formatApiError } from '../utils/errors';

const pollIntervalMs = 2500;
const pollFailureToastCooldownMs = 6000;

const initialRunState = {
  status: 'idle',
  statusPayload: null,
  resultPayload: null,
  resultState: 'idle',
  failureMessage: '',
  resultError: '',
  downloadFormat: '',
  loadState: 'idle',
  loadError: '',
};

function useReviewRun(runId) {
  const { showToast } = useToast();
  const [runState, setRunState] = useState(() => ({
    ...initialRunState,
    loadState: runId ? 'loading' : 'idle',
  }));
  const activeRunIdRef = useRef(runId);
  const previousStatusRef = useRef('idle');
  const lastPollFailureToastAtRef = useRef(0);

  useEffect(() => {
    activeRunIdRef.current = runId;
  }, [runId]);

  const refreshStatus = useCallback(async ({ silent = false } = {}) => {
    if (!runId) {
      return;
    }

    setRunState((current) => ({
      ...current,
      loadState: silent && current.statusPayload ? current.loadState : 'loading',
      loadError: '',
    }));

    try {
      const statusPayload = await fetchReviewStatus(runId);
      startTransition(() => {
        setRunState((current) => {
          if (activeRunIdRef.current !== runId) {
            return current;
          }

          return {
            ...current,
            status: statusPayload.status,
            statusPayload,
            loadState: 'ready',
            loadError: '',
            failureMessage: statusPayload.status === 'failed'
              ? deriveFailureMessage(statusPayload, current.failureMessage)
              : current.failureMessage,
          };
        });
      });
    } catch (error) {
      const message = formatApiError(error, silent ? 'Status polling failed.' : 'Review status could not be loaded.');
      if (silent) {
        const now = Date.now();
        if (now - lastPollFailureToastAtRef.current >= pollFailureToastCooldownMs) {
          showToast('Status check failed. Retrying...', 'warning');
          lastPollFailureToastAtRef.current = now;
        }
      }
      setRunState((current) => {
        if (activeRunIdRef.current !== runId) {
          return current;
        }

        return {
          ...current,
          loadState: current.statusPayload ? 'ready' : 'error',
          loadError: message,
          failureMessage: current.failureMessage || message,
        };
      });
    }
  }, [runId, showToast]);

  const fetchCompletedResult = useCallback(async () => {
    if (!runId) {
      return;
    }

    setRunState((current) => {
      if (current.resultState === 'ready' || current.resultState === 'loading') {
        return current;
      }

      return {
        ...current,
        resultState: 'loading',
        resultError: '',
      };
    });

    try {
      const resultPayload = await fetchReviewResult(runId);
      startTransition(() => {
        setRunState((current) => {
          if (activeRunIdRef.current !== runId) {
            return current;
          }

          return {
            ...current,
            resultPayload,
            resultState: 'ready',
            resultError: '',
          };
        });
      });
    } catch (error) {
      const message = formatApiError(error, 'The run finished, but the structured result could not be loaded.');
      const detail = error?.payload?.detail ?? {};

      setRunState((current) => {
        if (activeRunIdRef.current !== runId) {
          return current;
        }

        return {
          ...current,
          resultState: 'error',
          resultError: message,
          status: detail.status === 'failed' ? 'failed' : current.status,
          failureMessage: detail.status === 'failed' ? message : current.failureMessage,
        };
      });
    }
  }, [runId]);

  useEffect(() => {
    setRunState({
      ...initialRunState,
      loadState: runId ? 'loading' : 'idle',
    });
    previousStatusRef.current = 'idle';
    lastPollFailureToastAtRef.current = 0;

    if (!runId) {
      return;
    }

    void refreshStatus();
  }, [runId, refreshStatus]);

  const status = runState.statusPayload?.status ?? runState.status;

  useEffect(() => {
    if (!runId || !['queued', 'running'].includes(status)) {
      return undefined;
    }

    const handle = window.setTimeout(() => {
      void refreshStatus({ silent: true });
    }, pollIntervalMs);

    return () => {
      window.clearTimeout(handle);
    };
  }, [runId, status, refreshStatus]);

  useEffect(() => {
    if (!runId || status !== 'completed' || runState.resultPayload || runState.resultState === 'loading') {
      return;
    }

    void fetchCompletedResult();
  }, [runId, status, runState.resultPayload, runState.resultState, fetchCompletedResult]);

  useEffect(() => {
    if (!runId || !status) {
      previousStatusRef.current = status || 'idle';
      return;
    }

    const previousStatus = previousStatusRef.current;
    const transitionedFromActive = previousStatus === 'queued' || previousStatus === 'running';

    if (status === 'completed' && transitionedFromActive) {
      showToast(`Run ${runId} completed. Results are ready.`, 'success');
    }

    if (status === 'failed' && transitionedFromActive) {
      showToast(`Run ${runId} failed.`, 'error');
    }

    previousStatusRef.current = status;
  }, [runId, showToast, status]);

  const downloadArtifact = useCallback(async (format) => {
    if (!runId) {
      return;
    }

    setRunState((current) => ({
      ...current,
      downloadFormat: format,
    }));

    try {
      await downloadReportArtifact(runId, format);
      showToast('Report downloaded.', 'success');
    } catch (error) {
      const message = formatApiError(error, `Failed to download the ${format.toUpperCase()} report.`);
      setRunState((current) => ({
        ...current,
        failureMessage: current.failureMessage || message,
      }));
    } finally {
      setRunState((current) => ({
        ...current,
        downloadFormat: '',
      }));
    }
  }, [runId, showToast]);

  const result = runState.resultPayload?.result && typeof runState.resultPayload.result === 'object'
    ? runState.resultPayload.result
    : null;

  return {
    runState,
    status,
    result,
    refreshStatus,
    downloadArtifact,
  };
}

export default useReviewRun;
