import { useEffect, useMemo, useState } from 'react';
import { fetchComparison, fetchRuns } from '../api';
import MetricDelta from '../components/MetricDelta';
import PanelErrorBoundary from '../components/PanelErrorBoundary';
import { formatApiError } from '../utils/errors';
import '../styles/panels.css';
import '../styles/components.css';

function formatRunLabel(run) {
  const runId = String(run?.run_id ?? '');
  const status = String(run?.status ?? '').trim();
  return status ? `${runId} · ${status}` : runId;
}

function getMetricValue(comparison, key) {
  const payload = comparison?.metrics?.[key];
  if (!payload) {
    return { before: 0, after: 0, delta: 0 };
  }
  return {
    before: Number(payload.before ?? 0),
    after: Number(payload.after ?? 0),
    delta: Number(payload.delta ?? 0),
  };
}

function findingStatusLabel(status) {
  switch (status) {
    case 'removed':
      return '已修复';
    case 'added':
      return '新增';
    case 'changed':
      return '变更';
    default:
      return '未变化';
  }
}

function summarizeFinding(items) {
  if (!Array.isArray(items) || items.length === 0) {
    return 'No finding details';
  }
  const first = items[0] ?? {};
  return String(first.title ?? first.description ?? first.detail ?? 'Untitled finding');
}

function riskSummary(item) {
  if (!item) {
    return 'No matching risk';
  }
  return String(item.title ?? item.description ?? item.detail ?? item.id ?? 'Unnamed risk');
}

function ComparisonPage() {
  const [runsState, setRunsState] = useState({ status: 'loading', runs: [], error: '' });
  const [selection, setSelection] = useState({ runA: '', runB: '' });
  const [comparisonState, setComparisonState] = useState({ status: 'idle', data: null, error: '' });

  useEffect(() => {
    let cancelled = false;

    async function loadRuns() {
      setRunsState({ status: 'loading', runs: [], error: '' });
      try {
        const payload = await fetchRuns();
        if (cancelled) {
          return;
        }
        const runs = Array.isArray(payload?.runs) ? payload.runs : [];
        setRunsState({ status: 'success', runs, error: '' });
        setSelection((current) => {
          const completedRuns = runs.filter((run) => run?.status === 'completed');
          const fallbackA = current.runA || completedRuns[0]?.run_id || runs[0]?.run_id || '';
          const fallbackB = current.runB || completedRuns[1]?.run_id || completedRuns[0]?.run_id || runs[1]?.run_id || '';
          return { runA: fallbackA, runB: fallbackB };
        });
      } catch (error) {
        if (cancelled) {
          return;
        }
        setRunsState({ status: 'error', runs: [], error: formatApiError(error, 'Run list is unavailable.') });
      }
    }

    loadRuns();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleCompare(event) {
    event.preventDefault();
    if (!selection.runA || !selection.runB) {
      setComparisonState({ status: 'error', data: null, error: '请选择两个已完成的 run。' });
      return;
    }
    if (selection.runA === selection.runB) {
      setComparisonState({ status: 'error', data: null, error: '请选择两个不同的 run 进行对比。' });
      return;
    }

    setComparisonState({ status: 'loading', data: null, error: '' });
    try {
      const payload = await fetchComparison(selection.runA, selection.runB);
      setComparisonState({ status: 'success', data: payload, error: '' });
    } catch (error) {
      setComparisonState({
        status: 'error',
        data: null,
        error: formatApiError(error, 'Comparison request failed.'),
      });
    }
  }

  const runOptions = useMemo(
    () => runsState.runs.filter((run) => String(run?.status ?? '') === 'completed'),
    [runsState.runs],
  );

  const findingsMetric = getMetricValue(comparisonState.data, 'finding_count');
  const riskMetric = getMetricValue(comparisonState.data, 'risk_score');
  const coverageMetric = getMetricValue(comparisonState.data, 'coverage');

  return (
    <>
      <header className="page-header">
        <div>
          <p className="eyebrow">Run comparison workspace</p>
          <h1>对比两次 Review</h1>
          <p className="hero-copy">
            选择两次已完成的 review，快速查看指标变化、问题修复情况，以及风险项是收敛了还是扩散了。
          </p>
        </div>
      </header>

      <main className="workspace-grid comparison-layout">
        <section className="stack">
          <PanelErrorBoundary panelTitle="Run selection" resetKey={runsState.status}>
            <div className="panel">
              <div className="panel-header">
                <div>
                  <p className="section-kicker">Comparison setup</p>
                  <h2>选择两个 run</h2>
                </div>
              </div>

              <form className="compact-fields comparison-form" onSubmit={handleCompare}>
                <label className="field">
                  <span>基线 run</span>
                  <select
                    value={selection.runA}
                    onChange={(event) => setSelection((current) => ({ ...current, runA: event.target.value }))}
                    disabled={runsState.status === 'loading'}
                  >
                    <option value="">请选择</option>
                    {runOptions.map((run) => (
                      <option key={`run-a-${run.run_id}`} value={run.run_id}>
                        {formatRunLabel(run)}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="field">
                  <span>目标 run</span>
                  <select
                    value={selection.runB}
                    onChange={(event) => setSelection((current) => ({ ...current, runB: event.target.value }))}
                    disabled={runsState.status === 'loading'}
                  >
                    <option value="">请选择</option>
                    {runOptions.map((run) => (
                      <option key={`run-b-${run.run_id}`} value={run.run_id}>
                        {formatRunLabel(run)}
                      </option>
                    ))}
                  </select>
                </label>

                <div className="action-row">
                  <button type="submit" className="primary-button" disabled={comparisonState.status === 'loading'}>
                    {comparisonState.status === 'loading' ? '对比中...' : '开始对比'}
                  </button>
                  <button
                    type="button"
                    className="secondary-button"
                    onClick={() => setComparisonState({ status: 'idle', data: null, error: '' })}
                  >
                    清空结果
                  </button>
                </div>
              </form>

              {runsState.error ? <div className="feedback-banner feedback-error">{runsState.error}</div> : null}
              {comparisonState.error ? <div className="feedback-banner feedback-error">{comparisonState.error}</div> : null}
            </div>
          </PanelErrorBoundary>

          <PanelErrorBoundary panelTitle="Summary cards" resetKey={comparisonState.status}>
            <div className="panel">
              <div className="panel-header">
                <div>
                  <p className="section-kicker">Metrics delta</p>
                  <h2>概要卡片</h2>
                </div>
              </div>

              {comparisonState.data ? (
                <div className="comparison-summary-grid">
                  <MetricDelta
                    label="Findings 数"
                    previousValue={findingsMetric.before}
                    nextValue={findingsMetric.after}
                    betterWhen="down"
                    hint="问题减少通常代表质量改善。"
                  />
                  <MetricDelta
                    label="Risk score"
                    previousValue={riskMetric.before}
                    nextValue={riskMetric.after}
                    betterWhen="down"
                    formatter={(value) => value.toFixed(1)}
                    hint="风险分越低越好。"
                  />
                  <MetricDelta
                    label="Coverage"
                    previousValue={coverageMetric.before}
                    nextValue={coverageMetric.after}
                    betterWhen="up"
                    formatter={(value) => `${value.toFixed(1)}%`}
                    hint="覆盖率越高越接近完整评审。"
                  />
                </div>
              ) : (
                <div className="empty-state empty-state-compact">
                  <div className="empty-grid" aria-hidden="true" />
                  <div className="empty-orb" aria-hidden="true" />
                  <div>
                    <h3>等待对比结果</h3>
                    <p>选择两个已完成的 run 后，即可在这里看到核心指标的涨跌方向。</p>
                  </div>
                </div>
              )}
            </div>
          </PanelErrorBoundary>
        </section>

        <section className="stack stack-wide">
          <PanelErrorBoundary panelTitle="Findings diff" resetKey={`findings:${comparisonState.status}`}>
            <div className="panel">
              <div className="panel-header">
                <div>
                  <p className="section-kicker">Findings diff</p>
                  <h2>问题变化表</h2>
                </div>
              </div>

              {comparisonState.data ? (
                <div className="table-scroll">
                  <table className="diff-table">
                    <thead>
                      <tr>
                        <th>Requirement</th>
                        <th>状态</th>
                        <th>{comparisonState.data.run_a}</th>
                        <th>{comparisonState.data.run_b}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {comparisonState.data.findings.map((item) => (
                        <tr key={item.requirement_id} className={`diff-row diff-row-${item.status}`}>
                          <td>{item.requirement_id}</td>
                          <td>
                            <span className={`inline-meta diff-status diff-status-${item.status}`}>
                              {findingStatusLabel(item.status)}
                            </span>
                          </td>
                          <td>{summarizeFinding(item.before)}</td>
                          <td>{summarizeFinding(item.after)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="empty-state empty-state-compact">
                  <div className="empty-grid" aria-hidden="true" />
                  <div>
                    <h3>还没有 findings diff</h3>
                    <p>对比后这里会按 requirement_id 展示新增、修复、变化和未变化的问题。</p>
                  </div>
                </div>
              )}
            </div>
          </PanelErrorBoundary>

          <PanelErrorBoundary panelTitle="Risk comparison" resetKey={`risks:${comparisonState.status}`}>
            <div className="panel">
              <div className="panel-header">
                <div>
                  <p className="section-kicker">Risk side by side</p>
                  <h2>风险对比</h2>
                </div>
              </div>

              {comparisonState.data ? (
                <div className="risk-compare-list">
                  {comparisonState.data.risks.map((item) => (
                    <article key={item.match_key} className="risk-compare-card">
                      <div className="risk-compare-head">
                        <strong>{item.match_key}</strong>
                        <span className={`inline-meta diff-status diff-status-${item.status}`}>{findingStatusLabel(item.status)}</span>
                      </div>
                      <div className="risk-compare-columns">
                        <div className="risk-compare-column">
                          <span>{comparisonState.data.run_a}</span>
                          <p>{riskSummary(item.before)}</p>
                        </div>
                        <div className="risk-compare-column">
                          <span>{comparisonState.data.run_b}</span>
                          <p>{riskSummary(item.after)}</p>
                        </div>
                      </div>
                    </article>
                  ))}
                </div>
              ) : (
                <div className="empty-state empty-state-compact">
                  <div className="empty-grid" aria-hidden="true" />
                  <div>
                    <h3>风险变化会显示在这里</h3>
                    <p>左右对照能更容易看出旧风险是否已缓解，或者新风险是否开始冒头。</p>
                  </div>
                </div>
              )}
            </div>
          </PanelErrorBoundary>
        </section>
      </main>
    </>
  );
}

export default ComparisonPage;
