import { startTransition, useCallback, useEffect, useRef, useState } from 'react';
import {
  answerReviewClarification,
  confirmReviewRevision,
  generateReviewRoadmap,
  downloadReportArtifact,
  fetchReviewResult,
  fetchReviewStatus,
  submitReviewRevisionInput,
  updateReviewRevisionStage,
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
  clarificationState: 'idle',
  revisionDecisionState: 'idle',
  revisionInputState: 'idle',
  revisionConfirmState: 'idle',
  roadmapGenerationState: 'idle',
  loadState: 'idle',
  loadError: '',
  loadRetryEligible: false,
};

function shouldRetryStatusLoad(error) {
  if (!error) {
    return false;
  }

  if (error.name === 'TimeoutError') {
    return true;
  }

  if (typeof error.status !== 'number') {
    return true;
  }

  return error.status >= 500;
}

function useReviewRun(runId, options = {}) {
  const {
    externalStatusPayload = null,
    externalLoadError = '',
    disableStatusPolling = false,
  } = options;
  const { showToast } = useToast();
  const [runState, setRunState] = useState(() => ({
    ...initialRunState,
    loadState: runId && !disableStatusPolling ? 'loading' : 'idle',
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
      loadRetryEligible: false,
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
            loadRetryEligible: false,
            failureMessage: statusPayload.status === 'failed'
              ? deriveFailureMessage(statusPayload, current.failureMessage)
              : '',
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
          loadRetryEligible: !current.statusPayload && shouldRetryStatusLoad(error),
          failureMessage: current.failureMessage || message,
        };
      });
    }
  }, [runId, showToast]);

  const fetchCompletedResult = useCallback(async ({ force = false } = {}) => {
    if (!runId) {
      return;
    }

    setRunState((current) => {
      if (!force && (current.resultState === 'ready' || current.resultState === 'loading')) {
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

  const submitClarification = useCallback(async (answers) => {
    if (!runId) {
      return;
    }

    setRunState((current) => ({
      ...current,
      clarificationState: 'submitting',
    }));

    try {
      const resultPayload = await answerReviewClarification(runId, { answers });
      startTransition(() => {
        setRunState((current) => ({
          ...current,
          resultPayload,
          resultState: 'ready',
          resultError: '',
          clarificationState: 'ready',
        }));
      });
      showToast(`Clarification applied for run ${runId}.`, 'success');
      void refreshStatus({ silent: true });
    } catch (error) {
      const message = formatApiError(error, 'Clarification answers could not be applied.');
      setRunState((current) => ({
        ...current,
        clarificationState: 'error',
        failureMessage: current.failureMessage || message,
        resultError: current.resultError || message,
      }));
      showToast(message, 'error');
    }
  }, [runId, refreshStatus, showToast]);

  const submitRevisionDecision = useCallback(async (decision) => {
    if (!runId) {
      return;
    }

    setRunState((current) => ({
      ...current,
      revisionDecisionState: 'submitting',
    }));

    try {
      const response = await updateReviewRevisionStage(runId, { decision });
      const revisionStage = response?.revision_stage ?? {};
      startTransition(() => {
        setRunState((current) => ({
          ...current,
          revisionDecisionState: 'ready',
          resultPayload: current.resultPayload
            ? { ...current.resultPayload, revision_stage: revisionStage }
            : current.resultPayload,
          statusPayload: current.statusPayload
            ? { ...current.statusPayload, revision_stage: revisionStage }
            : current.statusPayload,
        }));
      });
      showToast(
        decision === 'skip_revision'
          ? `Revision skipped for run ${runId}. You can continue to next delivery below.`
          : `Revision flow noted for run ${runId}.`,
        'success',
      );
      void refreshStatus({ silent: true });
    } catch (error) {
      const message = formatApiError(error, 'Revision choice could not be recorded.');
      setRunState((current) => ({
        ...current,
        revisionDecisionState: 'error',
        failureMessage: current.failureMessage || message,
      }));
      showToast(message, 'error');
    }
  }, [runId, refreshStatus, showToast]);

  const submitRevisionInput = useCallback(async (payload) => {
    if (!runId) {
      return;
    }

    setRunState((current) => ({
      ...current,
      revisionInputState: 'submitting',
    }));

    try {
      const response = await submitReviewRevisionInput(runId, payload);
      const revisionStage = response?.revision_stage ?? {};
      startTransition(() => {
        setRunState((current) => ({
          ...current,
          revisionInputState: 'ready',
          resultPayload: current.resultPayload
            ? { ...current.resultPayload, revision_stage: revisionStage }
            : current.resultPayload,
          statusPayload: current.statusPayload
            ? { ...current.statusPayload, revision_stage: revisionStage }
            : current.statusPayload,
        }));
      });
      showToast(`Revision input recorded for run ${runId}.`, 'success');
      void refreshStatus({ silent: true });
    } catch (error) {
      const message = formatApiError(error, 'Revision input could not be recorded.');
      setRunState((current) => ({
        ...current,
        revisionInputState: 'error',
        failureMessage: current.failureMessage || message,
      }));
      showToast(message, 'error');
    }
  }, [runId, refreshStatus, showToast]);

  const submitRevisionConfirmAction = useCallback(async (payload) => {
    if (!runId) {
      return;
    }

    setRunState((current) => ({
      ...current,
      revisionConfirmState: 'submitting',
    }));

    try {
      const response = await confirmReviewRevision(runId, payload);
      const revisionStage = response?.revision_stage ?? {};
      startTransition(() => {
        setRunState((current) => ({
          ...current,
          revisionConfirmState: 'ready',
          resultPayload: current.resultPayload
            ? { ...current.resultPayload, revision_stage: revisionStage }
            : current.resultPayload,
          statusPayload: current.statusPayload
            ? { ...current.statusPayload, revision_stage: revisionStage }
            : current.statusPayload,
        }));
      });
      showToast('Revision confirmation action applied.', 'success');
      void refreshStatus({ silent: true });
    } catch (error) {
      const message = formatApiError(error, 'Revision confirm action failed.');
      setRunState((current) => ({
        ...current,
        revisionConfirmState: 'error',
        failureMessage: current.failureMessage || message,
      }));
      showToast(message, 'error');
    }
  }, [runId, refreshStatus, showToast]);

  const generateRoadmap = useCallback(async () => {
    if (!runId) {
      return;
    }

    setRunState((current) => ({
      ...current,
      roadmapGenerationState: 'submitting',
    }));

    try {
      const response = await generateReviewRoadmap(runId);
      startTransition(() => {
        setRunState((current) => ({
          ...current,
          roadmapGenerationState: 'ready',
          resultPayload: response,
        }));
      });
      const roadmapStatus = String(response?.result?.roadmap_generation?.status || '');
      if (roadmapStatus === 'not_recommended') {
        showToast('Roadmap generation is optional and not recommended for this scope.', 'warning');
      } else {
        showToast('Roadmap generated.', 'success');
      }
      void refreshStatus({ silent: true });
    } catch (error) {
      const message = formatApiError(error, 'Roadmap generation failed.');
      setRunState((current) => ({
        ...current,
        roadmapGenerationState: 'error',
        failureMessage: current.failureMessage || message,
      }));
      showToast(message, 'error');
    }
  }, [runId, refreshStatus, showToast]);

  useEffect(() => {
    setRunState({
      ...initialRunState,
      loadState: runId && !disableStatusPolling ? 'loading' : 'idle',
    });
    previousStatusRef.current = 'idle';
    lastPollFailureToastAtRef.current = 0;

    if (!runId || disableStatusPolling) {
      return;
    }

    void refreshStatus();
  }, [disableStatusPolling, runId, refreshStatus]);

  useEffect(() => {
    if (!externalStatusPayload || !runId) {
      return;
    }

    startTransition(() => {
      setRunState((current) => ({
        ...current,
        status: externalStatusPayload.status,
        statusPayload: externalStatusPayload,
        loadState: 'ready',
        loadError: externalLoadError || '',
        loadRetryEligible: false,
        failureMessage: externalStatusPayload.status === 'failed'
          ? deriveFailureMessage(externalStatusPayload, current.failureMessage || externalLoadError)
          : current.failureMessage,
      }));
    });
  }, [externalLoadError, externalStatusPayload, runId]);

  useEffect(() => {
    if (!disableStatusPolling || !externalLoadError || externalStatusPayload) {
      return;
    }

    setRunState((current) => ({
      ...current,
      loadState: current.statusPayload ? 'ready' : 'error',
      loadError: externalLoadError,
      loadRetryEligible: false,
      failureMessage: current.failureMessage || externalLoadError,
    }));
  }, [disableStatusPolling, externalLoadError, externalStatusPayload]);

  const status = externalStatusPayload?.status ?? runState.statusPayload?.status ?? runState.status;

  useEffect(() => {
    if (disableStatusPolling || !runId || !['queued', 'running'].includes(status)) {
      return undefined;
    }

    const handle = window.setTimeout(() => {
      void refreshStatus({ silent: true });
    }, pollIntervalMs);

    return () => {
      window.clearTimeout(handle);
    };
  }, [disableStatusPolling, runId, status, refreshStatus]);

  useEffect(() => {
    if (disableStatusPolling || !runId || runState.statusPayload || runState.loadState !== 'error' || !runState.loadRetryEligible) {
      return undefined;
    }

    const handle = window.setTimeout(() => {
      void refreshStatus({ silent: true });
    }, pollIntervalMs);

    return () => {
      window.clearTimeout(handle);
    };
  }, [disableStatusPolling, runId, runState.statusPayload, runState.loadState, runState.loadRetryEligible, refreshStatus]);

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
    submitClarification,
    submitRevisionDecision,
    submitRevisionInput,
    submitRevisionConfirmAction,
    generateRoadmap,
  };
}

export default useReviewRun;
