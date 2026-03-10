import { startTransition, useCallback, useEffect, useRef, useState } from 'react';
import {
  downloadReportArtifact,
  fetchReviewResult,
  fetchReviewStatus,
  fetchRuns,
  submitReview,
} from './api';
import ArtifactDownloadPanel from './components/ArtifactDownloadPanel';
import FindingsPanel from './components/FindingsPanel';
import OpenQuestionsPanel from './components/OpenQuestionsPanel';
import ReviewHistoryPanel from './components/ReviewHistoryPanel';
import ReviewSubmitPanel from './components/ReviewSubmitPanel';
import ReviewSummaryPanel from './components/ReviewSummaryPanel';
import RisksPanel from './components/RisksPanel';
import RunProgressCard from './components/RunProgressCard';
import './styles/layout.css';
import { deriveFailureMessage } from './utils/derivers';
import { formatApiError } from './utils/errors';
import { buildSubmissionPayload, validateSubmission } from './utils/submission';

const initialForm = {
  prd_text: '',
  prd_path: '',
  source: '',
};

const initialWorkspace = {
  submitState: 'idle',
  resultState: 'idle',
  status: 'idle',
  runId: '',
  submission: null,
  statusPayload: null,
  resultPayload: null,
  submitError: '',
  failureMessage: '',
  resultError: '',
  downloadFormat: '',
};

const initialHistory = {
  status: 'loading',
  runs: [],
  error: '',
  refreshing: false,
};

const pollIntervalMs = 2500;

function App() {
  const [form, setForm] = useState(initialForm);
  const [workspace, setWorkspace] = useState(initialWorkspace);
  const [history, setHistory] = useState(initialHistory);
  const workspaceRef = useRef(initialWorkspace);
  const historyRef = useRef(initialHistory);

  const setWorkspaceState = useCallback((nextValue) => {
    const next = typeof nextValue === 'function' ? nextValue(workspaceRef.current) : nextValue;
    workspaceRef.current = next;
    setWorkspace(next);
  }, []);

  const setHistoryState = useCallback((nextValue) => {
    const next = typeof nextValue === 'function' ? nextValue(historyRef.current) : nextValue;
    historyRef.current = next;
    setHistory(next);
  }, []);

  const status = workspace.statusPayload?.status ?? workspace.status;
  const result = workspace.resultPayload?.result && typeof workspace.resultPayload.result === 'object'
    ? workspace.resultPayload.result
    : null;

  function updateField(field, value) {
    setForm((current) => ({
      ...current,
      [field]: value,
    }));
    setWorkspaceState((current) => ({
      ...current,
      submitError: '',
    }));
  }

  function loadSample() {
    setForm({
      prd_text:
        'Goal: reviewers should submit one PRD, monitor progress, inspect structured findings, and download a report without leaving the workspace.\n\nAcceptance criteria should clarify success metrics, rollout risk, and who owns ambiguous requirements before delivery planning begins.\n\nEdge cases must explain how missing inputs, failed review runs, and unavailable result artifacts are surfaced to the reviewer.',
      prd_path: '',
      source: '',
    });
  }

  function resetWorkspace() {
    const shouldReset = window.confirm('This will clear all current review data. Are you sure?');
    if (!shouldReset) {
      return;
    }

    setWorkspaceState(initialWorkspace);
    setForm(initialForm);
  }

  const loadRunHistory = useCallback(async ({ preserveRuns = true } = {}) => {
    const currentHistory = historyRef.current;
    const shouldPreserve = preserveRuns && currentHistory.runs.length > 0;

    setHistoryState({
      ...currentHistory,
      status: shouldPreserve ? currentHistory.status : 'loading',
      refreshing: shouldPreserve,
      error: '',
    });

    try {
      const payload = await fetchRuns();
      setHistoryState({
        status: 'ready',
        runs: Array.isArray(payload?.runs) ? payload.runs : [],
        error: '',
        refreshing: false,
      });
    } catch (error) {
      const message = formatApiError(error, 'Review history could not be loaded.');
      const latestHistory = historyRef.current;
      setHistoryState({
        ...latestHistory,
        status: latestHistory.runs.length > 0 ? latestHistory.status : 'error',
        refreshing: false,
        error: message,
      });
    }
  }, [setHistoryState]);

  const pollRunStatus = useCallback(async (runId) => {
    try {
      const statusPayload = await fetchReviewStatus(runId);
      setWorkspaceState((current) => {
        if (current.runId !== runId) {
          return current;
        }

        return {
          ...current,
          status: statusPayload.status,
          statusPayload,
          failureMessage: statusPayload.status === 'failed'
            ? deriveFailureMessage(statusPayload)
            : current.failureMessage,
        };
      });
    } catch (error) {
      const message = formatApiError(error, 'Status polling failed.');
      setWorkspaceState((current) => {
        if (current.runId !== runId) {
          return current;
        }
        return {
          ...current,
          failureMessage: message,
        };
      });
    }
  }, [setWorkspaceState]);

  const fetchCompletedResult = useCallback(async (runId) => {
    const currentWorkspace = workspaceRef.current;
    if (currentWorkspace.runId !== runId || currentWorkspace.resultState === 'ready') {
      return;
    }

    setWorkspaceState((current) => {
      if (current.runId !== runId || current.resultState === 'ready') {
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
        setWorkspaceState((current) => {
          if (current.runId !== runId) {
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
      setWorkspaceState((current) => {
        if (current.runId !== runId) {
          return current;
        }
        return {
          ...current,
          resultState: 'error',
          resultError: message,
          status: detail.status === 'failed' ? 'failed' : current.status,
          failureMessage: detail.status === 'failed'
            ? message
            : current.failureMessage,
        };
      });
    }
  }, [setWorkspaceState]);

  useEffect(() => {
    void loadRunHistory({ preserveRuns: false });
  }, [loadRunHistory]);

  useEffect(() => {
    if (!workspace.runId || !['queued', 'running'].includes(status)) {
      return undefined;
    }

    const handle = window.setTimeout(() => {
      void pollRunStatus(workspace.runId);
    }, pollIntervalMs);

    return () => {
      window.clearTimeout(handle);
    };
  }, [workspace.runId, status, pollRunStatus]);

  useEffect(() => {
    if (!workspace.runId || status !== 'completed' || workspace.resultPayload || workspace.resultState === 'loading') {
      return;
    }

    void fetchCompletedResult(workspace.runId);
  }, [workspace.runId, status, workspace.resultPayload, workspace.resultState, fetchCompletedResult]);

  useEffect(() => {
    if (!workspace.runId || !['completed', 'failed'].includes(status)) {
      return;
    }

    void loadRunHistory({ preserveRuns: true });
  }, [workspace.runId, status, loadRunHistory]);

  async function handleSubmit(event) {
    event.preventDefault();

    const payload = buildSubmissionPayload(form);
    const validationMessage = validateSubmission(payload);
    if (validationMessage) {
      setWorkspaceState((current) => ({
        ...current,
        submitError: validationMessage,
      }));
      return;
    }

    setWorkspaceState({
      ...initialWorkspace,
      submitState: 'submitting',
      submission: payload,
    });

    try {
      const response = await submitReview(payload);
      const queuedStatus = {
        run_id: response.run_id,
        status: 'queued',
        progress: {
          percent: 0,
          current_node: '',
          nodes: {},
          updated_at: new Date().toISOString(),
          error: '',
        },
        report_paths: {},
      };

      setWorkspaceState({
        ...initialWorkspace,
        runId: response.run_id,
        submission: payload,
        status: 'queued',
        statusPayload: queuedStatus,
      });

      void loadRunHistory({ preserveRuns: true });
      await pollRunStatus(response.run_id);
    } catch (error) {
      setWorkspaceState((current) => ({
        ...current,
        submitState: 'idle',
        submitError: formatApiError(error, 'Review submission failed.'),
      }));
    }
  }

  async function handleOpenRun(run) {
    const runId = String(run?.run_id ?? '');
    if (!runId) {
      return;
    }

    setWorkspaceState({
      ...initialWorkspace,
      runId,
      status: run.status ?? 'idle',
      statusPayload: {
        run_id: runId,
        status: run.status ?? 'idle',
        progress: {
          percent: run.status === 'completed' ? 100 : 0,
          current_node: '',
          nodes: {},
          updated_at: run.updated_at ?? run.created_at ?? '',
          error: '',
        },
        report_paths: {},
      },
    });

    await pollRunStatus(runId);
  }

  async function handleDownload(format) {
    if (!workspace.runId) {
      return;
    }

    setWorkspaceState((current) => ({
      ...current,
      downloadFormat: format,
    }));

    try {
      await downloadReportArtifact(workspace.runId, format);
    } catch (error) {
      const message = formatApiError(error, `Failed to download the ${format.toUpperCase()} report.`);
      setWorkspaceState((current) => ({
        ...current,
        failureMessage: current.failureMessage || message,
      }));
    } finally {
      setWorkspaceState((current) => ({
        ...current,
        downloadFormat: '',
      }));
    }
  }

  return (
    <div className="app-shell">
      <div className="ambient ambient-left" />
      <div className="ambient ambient-right" />

      <header className="hero hero-tight">
        <div>
          <p className="eyebrow">Requirement Review Workspace</p>
          <h1>AI-Powered Requirement Review</h1>
          <p className="hero-copy">
            Submit your PRD, get structured findings, risks, and delivery insights - all in one workspace.
          </p>
        </div>

        <div className="hero-panel">
          <span className="hero-label">Quick Start</span>
          <ol className="quick-start-list">
            <li className="quick-start-step">
              <strong>1. Paste PRD</strong>
              <p>Add the PRD content directly or point to the right source document.</p>
            </li>
            <li className="quick-start-step">
              <strong>2. Review</strong>
              <p>Track pipeline progress, inspect findings, and clarify open questions.</p>
            </li>
            <li className="quick-start-step">
              <strong>3. Download report</strong>
              <p>Export the structured review package when the run completes.</p>
            </li>
          </ol>
        </div>
      </header>

      <main className="workspace-grid workspace-grid-expanded">
        <section className="stack">
          <ReviewSubmitPanel
            form={form}
            onFieldChange={updateField}
            onSubmit={handleSubmit}
            onReset={resetWorkspace}
            onLoadSample={loadSample}
            isSubmitting={workspace.submitState === 'submitting'}
            errorMessage={workspace.submitError}
          />

          <ReviewHistoryPanel
            history={history}
            activeRunId={workspace.runId}
            onRefresh={() => loadRunHistory({ preserveRuns: true })}
            onOpenRun={handleOpenRun}
          />

          <RunProgressCard
            runId={workspace.runId}
            status={status}
            statusPayload={workspace.statusPayload}
            failureMessage={workspace.failureMessage}
          />

          <ArtifactDownloadPanel
            runId={workspace.runId}
            status={status}
            resultPayload={workspace.resultPayload}
            statusPayload={workspace.statusPayload}
            downloadFormat={workspace.downloadFormat}
            onDownload={handleDownload}
          />
        </section>

        <section className="stack stack-wide">
          <ReviewSummaryPanel
            runId={workspace.runId}
            status={status}
            result={result}
            statusPayload={workspace.statusPayload}
            resultPayload={workspace.resultPayload}
            resultState={workspace.resultState}
            failureMessage={workspace.failureMessage}
            resultError={workspace.resultError}
          />

          <div className="panel-grid panel-grid-two-up">
            <FindingsPanel result={result} status={status} resultState={workspace.resultState} />
            <RisksPanel result={result} />
          </div>

          <OpenQuestionsPanel result={result} />
        </section>
      </main>
    </div>
  );
}

export default App;
