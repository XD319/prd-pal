import { useEffect, useMemo, useState } from 'react';
import '../styles/panels.css';
import '../styles/components.css';
import { describeHistoryRun } from '../utils/derivers';
import { formatDateTime } from '../utils/formatters';

function ReviewHistoryPanel({ history, activeRunId, onRefresh, onOpenRun }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [page, setPage] = useState(1);
  const pageSize = 10;
  const filterOptions = [
    { value: 'all', label: 'All' },
    { value: 'running', label: 'Running' },
    { value: 'completed', label: 'Completed' },
    { value: 'failed', label: 'Failed' },
  ];

  const filteredRuns = useMemo(() => history.runs.filter((run) => {
    const matchesSearch = String(run.run_id ?? '').toLowerCase().includes(searchTerm.trim().toLowerCase());
    const normalizedStatus = String(run.status ?? '').toLowerCase();
    const matchesStatus = statusFilter === 'all'
      ? true
      : statusFilter === 'running'
        ? normalizedStatus === 'running' || normalizedStatus === 'queued'
        : normalizedStatus === statusFilter;
    return matchesSearch && matchesStatus;
  }), [history.runs, searchTerm, statusFilter]);

  const totalPages = Math.max(1, Math.ceil(filteredRuns.length / pageSize));
  const currentPage = Math.min(page, totalPages);
  const paginatedRuns = filteredRuns.slice((currentPage - 1) * pageSize, currentPage * pageSize);
  const resultAnnouncement = `${filteredRuns.length} run${filteredRuns.length === 1 ? '' : 's'} shown on page ${currentPage} of ${totalPages}.`;

  useEffect(() => {
    setPage(1);
  }, [searchTerm, statusFilter]);

  return (
    <section className="panel review-history-panel">
      <div className="panel-header">
        <div>
          <p className="section-kicker">Review History</p>
          <h2>Recent runs</h2>
        </div>
        <button
          type="button"
          className="ghost-button"
          onClick={onRefresh}
          disabled={history.refreshing}
          aria-label={history.refreshing ? 'Refreshing review history' : 'Refresh review history'}
        >
          {history.refreshing ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      <div className="history-toolbar">
        <label className="field history-search">
          <span>Search by run ID</span>
          <input
            type="search"
            value={searchTerm}
            placeholder="Search run_id"
            onChange={(event) => setSearchTerm(event.target.value)}
            aria-label="Search review history by run ID"
          />
        </label>

        <div className="history-filter-group" role="group" aria-label="Filter review history by status">
          {filterOptions.map((option) => (
            <button
              key={option.value}
              type="button"
              className={`filter-chip${statusFilter === option.value ? ' filter-chip-active' : ''}`}
              onClick={() => setStatusFilter(option.value)}
              aria-pressed={statusFilter === option.value}
              aria-label={`Filter history by ${option.label}`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      <p className="sr-only" aria-live="polite">{resultAnnouncement}</p>

      {history.status === 'loading' && history.runs.length === 0 ? (
        <div className="loading-state loading-state-history">
          <div className="history-skeleton-card" />
          <div className="history-skeleton-card" />
          <div className="history-skeleton-card" />
        </div>
      ) : history.status === 'error' && history.runs.length === 0 ? (
        <div className="empty-state empty-state-compact">
          <div className="empty-grid" />
          <h3>Run history is unavailable</h3>
          <p>{history.error}</p>
        </div>
      ) : filteredRuns.length === 0 ? (
        <div className="empty-state empty-state-compact">
          <div className="empty-grid" />
          <h3>{history.runs.length === 0 ? 'No review runs yet' : 'No runs match your filters'}</h3>
          <p>
            {history.runs.length === 0
              ? 'Completed and in-progress review runs from GET /api/runs will appear here for quick follow-up.'
              : 'Try a different run ID search or switch the status filter to widen the results.'}
          </p>
        </div>
      ) : (
        <div className="history-list">
          {history.status === 'error' && <div className="feedback-banner feedback-error" aria-live="polite">{history.error}</div>}

          {paginatedRuns.map((run) => {
            const summary = describeHistoryRun(run);
            const isActive = run.run_id === activeRunId;

            return (
              <article key={run.run_id} className={`history-card${isActive ? ' history-card-active' : ''}`}>
                <div className="history-header">
                  <div>
                    <span className="history-kicker">{run.run_id}</span>
                    <h3>{summary.hasResult ? 'Result ready for inspection' : 'Review run in motion'}</h3>
                  </div>
                  <span className={`status-badge status-${summary.status}`}>{summary.statusLabel}</span>
                </div>

                <p className="history-note">{summary.detail}</p>

                <div className="history-meta">
                  <div>
                    <span>Created</span>
                    <strong>{formatDateTime(run.created_at)}</strong>
                  </div>
                  <div>
                    <span>Updated</span>
                    <strong>{formatDateTime(run.updated_at)}</strong>
                  </div>
                </div>

                <div className="history-actions">
                  <button
                    type="button"
                    className="secondary-button"
                    onClick={() => onOpenRun(run)}
                    aria-label={`Open run ${run.run_id}`}
                  >
                    {summary.actionLabel}
                  </button>
                  <span className="inline-meta inline-meta-soft">
                    {run.artifact_presence?.report_json ? 'Report artifact ready' : 'Waiting on report artifact'}
                  </span>
                </div>
              </article>
            );
          })}

          {totalPages > 1 && (
            <nav className="pagination-nav" aria-label="Review history pages">
              <button
                type="button"
                className="pagination-button"
                onClick={() => setPage((current) => Math.max(1, current - 1))}
                disabled={currentPage === 1}
                aria-label="Go to previous history page"
              >
                Previous
              </button>

              {Array.from({ length: totalPages }, (_, index) => {
                const nextPage = index + 1;
                return (
                  <button
                    key={nextPage}
                    type="button"
                    className={`pagination-button${nextPage === currentPage ? ' pagination-button-active' : ''}`}
                    onClick={() => setPage(nextPage)}
                    aria-label={`Go to history page ${nextPage}`}
                    aria-current={nextPage === currentPage ? 'page' : undefined}
                  >
                    {nextPage}
                  </button>
                );
              })}

              <button
                type="button"
                className="pagination-button"
                onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
                disabled={currentPage === totalPages}
                aria-label="Go to next history page"
              >
                Next
              </button>
            </nav>
          )}
        </div>
      )}
    </section>
  );
}

export default ReviewHistoryPanel;
