import { Link, useParams } from 'react-router-dom';
import ArtifactDownloadPanel from '../components/ArtifactDownloadPanel';
import FindingsPanel from '../components/FindingsPanel';
import OpenQuestionsPanel from '../components/OpenQuestionsPanel';
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
          <Link to="/">Home</Link>
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

          <button type="button" className="ghost-button" onClick={() => refreshStatus()}>
            Refresh status
          </button>
        </div>

        {runState.loadError && <div className="feedback-banner feedback-error">{runState.loadError}</div>}
      </header>

      <main className="workspace-grid workspace-grid-detail">
        <section className="stack">
          <RunProgressCard
            runId={runId}
            status={status}
            statusPayload={runState.statusPayload}
            failureMessage={runState.failureMessage}
          />

          <ArtifactDownloadPanel
            runId={runId}
            status={status}
            resultPayload={runState.resultPayload}
            statusPayload={runState.statusPayload}
            downloadFormat={runState.downloadFormat}
            onDownload={downloadArtifact}
          />
        </section>

        <section className="stack stack-wide">
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

          <div className="panel-grid panel-grid-two-up">
            <FindingsPanel result={result} status={status} resultState={runState.resultState} />
            <RisksPanel result={result} />
          </div>

          <OpenQuestionsPanel result={result} />
        </section>
      </main>
    </>
  );
}

export default RunDetailsPage;

