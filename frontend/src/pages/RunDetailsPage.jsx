import { Link, useParams } from 'react-router-dom';
import ArtifactDownloadPanel from '../components/ArtifactDownloadPanel';
import FindingsPanel from '../components/FindingsPanel';
import OpenQuestionsPanel from '../components/OpenQuestionsPanel';
import PanelErrorBoundary from '../components/PanelErrorBoundary';
import ReviewSummaryPanel from '../components/ReviewSummaryPanel';
import RisksPanel from '../components/RisksPanel';
import RunProgressCard from '../components/RunProgressCard';
import useReviewRun from '../hooks/useReviewRun';

function RunDetailsPage() {
  const { runId = '' } = useParams();
  const { runState, status, result, refreshStatus, downloadArtifact } = useReviewRun(runId);

  return (
    <>
      <header className="page-header">
        <nav className="breadcrumbs" aria-label="Breadcrumb">
          <Link to="/" aria-label="Return to home page">Home</Link>
          <span>{'>'}</span>
          <span>Run</span>
          <span>{'>'}</span>
          <span aria-current="page">{runId}</span>
        </nav>

        <div className="page-header-row">
          <div>
            <p className="eyebrow">Run detail workspace</p>
            <h1>Run {runId}</h1>
            <p className="hero-copy">
              Track execution, inspect structured review output, and download artifacts from one dedicated run URL.
            </p>
          </div>

          <button
            type="button"
            className="ghost-button"
            onClick={() => refreshStatus()}
            aria-label={`Refresh status for run ${runId}`}
          >
            Refresh status
          </button>
        </div>

        {runState.loadError && <div className="feedback-banner feedback-error" aria-live="polite">{runState.loadError}</div>}
      </header>

      <main className="workspace-grid workspace-grid-detail">
        <section className="stack">
          <PanelErrorBoundary panelTitle="运行进度" resetKey={`${runId}:${status}`}>
            <RunProgressCard
              runId={runId}
              status={status}
              statusPayload={runState.statusPayload}
              failureMessage={runState.failureMessage}
            />
          </PanelErrorBoundary>

          <PanelErrorBoundary panelTitle="产物下载" resetKey={`${runId}:${runState.downloadFormat}`}>
            <ArtifactDownloadPanel
              runId={runId}
              status={status}
              resultPayload={runState.resultPayload}
              statusPayload={runState.statusPayload}
              downloadFormat={runState.downloadFormat}
              onDownload={downloadArtifact}
            />
          </PanelErrorBoundary>
        </section>

        <section className="stack stack-wide">
          <PanelErrorBoundary panelTitle="结果总览" resetKey={`${runId}:${runState.resultState}`}>
            <ReviewSummaryPanel
              runId={runId}
              status={status}
              result={result}
              statusPayload={runState.statusPayload}
              resultPayload={runState.resultPayload}
              resultState={runState.resultState}
              failureMessage={runState.failureMessage}
              resultError={runState.resultError}
            />
          </PanelErrorBoundary>

          <div className="panel-grid panel-grid-two-up">
            <PanelErrorBoundary panelTitle="发现列表" resetKey={`${runId}:${runState.resultState}:findings`}>
              <FindingsPanel result={result} status={status} resultState={runState.resultState} />
            </PanelErrorBoundary>
            <PanelErrorBoundary panelTitle="风险列表" resetKey={`${runId}:${runState.resultState}:risks`}>
              <RisksPanel result={result} />
            </PanelErrorBoundary>
          </div>

          <PanelErrorBoundary panelTitle="开放问题" resetKey={`${runId}:${runState.resultState}:questions`}>
            <OpenQuestionsPanel result={result} />
          </PanelErrorBoundary>
        </section>
      </main>
    </>
  );
}

export default RunDetailsPage;
