import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { fetchReviewResult, submitFeishuReview } from '../api';
import PanelErrorBoundary from '../components/PanelErrorBoundary';
import ReviewSubmissionForm from '../components/ReviewSubmissionForm';
import { useToast } from '../components/ToastProvider';
import useReviewHistory from '../hooks/useReviewHistory';
import { deriveClarification, describeHistoryRun } from '../utils/derivers';
import { formatApiError } from '../utils/errors';
import { formatDateTime } from '../utils/formatters';
import { buildSubmissionPayload, validateSubmission } from '../utils/submission';

const initialForm = {
  prd_text: '',
  prd_path: '',
  source: '',
  mode: 'quick',
};

function FeishuEntryPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { showToast } = useToast();
  const { history, loadRunHistory } = useReviewHistory();
  const [form, setForm] = useState(initialForm);
  const [submitState, setSubmitState] = useState('idle');
  const [submitError, setSubmitError] = useState('');
  const [submittedRunId, setSubmittedRunId] = useState('');
  const [clarificationSummary, setClarificationSummary] = useState({
    status: 'idle',
    pendingCount: 0,
    runId: '',
    error: '',
  });

  const latestRun = useMemo(() => {
    if (!Array.isArray(history.runs) || history.runs.length === 0) {
      return null;
    }

    const runs = [...history.runs];
    runs.sort((left, right) => {
      const leftTime = Date.parse(left?.updated_at ?? left?.created_at ?? '') || 0;
      const rightTime = Date.parse(right?.updated_at ?? right?.created_at ?? '') || 0;
      return rightTime - leftTime;
    });

    return runs[0] ?? null;
  }, [history.runs]);

  const workspaceLabel = searchParams.get('workspace') || searchParams.get('tenant') || 'Feishu Workspace';

  function updateField(field, value) {
    setForm((current) => ({
      ...current,
      [field]: value,
    }));
    setSubmitError('');
  }

  function resetForm() {
    setForm(initialForm);
    setSubmitError('');
    setSubmittedRunId('');
  }

  async function handleSubmit(event) {
    event.preventDefault();

    const payload = buildSubmissionPayload(form, {
      includeMode: true,
      allowPrdPath: false,
    });
    const validationMessage = validateSubmission(payload, {
      allowPrdPath: false,
      requireSourceOrText: true,
    });
    if (validationMessage) {
      setSubmitError(validationMessage);
      return;
    }

    setSubmitState('submitting');
    setSubmitError('');

    try {
      const response = await submitFeishuReview(payload);
      setSubmittedRunId(response.run_id);
      setSubmitState('idle');
      showToast(`Review submitted from Feishu entry. Tracking run ${response.run_id}.`, 'success');
      void loadRunHistory();
    } catch (error) {
      setSubmitState('idle');
      setSubmitError(formatApiError(error, 'Feishu review submission failed.'));
    }
  }

  async function loadClarificationSummary(runId) {
    if (!runId) {
      setClarificationSummary({
        status: 'idle',
        pendingCount: 0,
        runId: '',
        error: '',
      });
      return;
    }

    setClarificationSummary((current) => ({
      ...current,
      status: 'loading',
      runId,
      error: '',
    }));

    try {
      const payload = await fetchReviewResult(runId);
      const clarification = deriveClarification(payload?.result ?? {});
      const pendingCount = clarification.status === 'pending' ? clarification.questions.length : 0;
      setClarificationSummary({
        status: 'ready',
        pendingCount,
        runId,
        error: '',
      });
    } catch (error) {
      setClarificationSummary({
        status: 'error',
        pendingCount: 0,
        runId,
        error: formatApiError(error, 'Clarification summary is temporarily unavailable.'),
      });
    }
  }

  function openRunDetails(runId) {
    if (!runId) {
      return;
    }
    navigate(`/run/${runId}?embed=feishu`);
  }

  function openRunSection(runId, sectionHash) {
    if (!runId) {
      return;
    }
    const normalizedHash = String(sectionHash || '').trim();
    const hashPart = normalizedHash ? `#${normalizedHash.replace(/^#/, '')}` : '';
    navigate(`/run/${runId}?embed=feishu${hashPart}`);
  }

  useEffect(() => {
    void loadClarificationSummary(latestRun?.run_id ?? '');
  }, [latestRun?.run_id]);

  const effectiveRunId = submittedRunId || latestRun?.run_id || '';
  const latestRunSummary = latestRun ? describeHistoryRun(latestRun) : null;

  return (
    <>
      <header className="hero hero-tight">
        <div>
          <p className="eyebrow">Feishu Work Entry</p>
          <h1>飞书工作入口页</h1>
          <p className="hero-copy">
            从飞书进入后，你可以直接开始新评审，回到最近一次 run，处理待澄清问题，或继续上次工作，不需要切换到完整工作台。
          </p>
        </div>

        <div className="hero-panel">
          <span className="hero-label">Current Workspace</span>
          <strong>{workspaceLabel}</strong>
          <p>
            推荐使用飞书文档链接发起评审。提交后可直接进入嵌入式 run 详情页继续跟进。
          </p>
        </div>
      </header>

      <main className="workspace-grid workspace-grid-feishu-entry">
        <section className="stack">
          <PanelErrorBoundary panelTitle="Feishu Entry" resetKey={`${submitState}:${submittedRunId}`}>
            <ReviewSubmissionForm
              form={form}
              onFieldChange={updateField}
              onSubmit={handleSubmit}
              onReset={resetForm}
              onLoadSample={() => {}}
              isSubmitting={submitState === 'submitting'}
              errorMessage={submitError}
              kicker="发起新评审"
              title="开始评审"
              helperText="优先粘贴飞书文档链接；若暂无链接，可直接粘贴 PRD 正文。"
              submitLabel="开始评审"
              resetLabel="Clear form"
              sourceLabel="飞书来源"
              sourcePlaceholder="e.g. https://your-domain.feishu.cn/docx/... or feishu://docx/..."
              showFilePath={false}
              showLoadSample={false}
              showMode
              sourceFirst
              sourceEmphasis="推荐：粘贴飞书文档链接或 connector source。"
              sourceHelper="提交后会优先引导到最近 run，并支持继续澄清。"
              formAriaLabel="Feishu review submission form"
            />
          </PanelErrorBoundary>
        </section>

        <section className="stack feishu-entry-stack">
          <section className="panel">
            <div className="panel-header">
              <div>
                <p className="section-kicker">最近一次 Run</p>
                <h2>查看最近结果</h2>
              </div>
              <button type="button" className="ghost-button" onClick={() => loadRunHistory()} disabled={history.refreshing}>
                {history.refreshing ? '刷新中...' : '刷新'}
              </button>
            </div>

            {latestRun ? (
              <div className="submission-success-card">
                <span className="inline-meta">{latestRunSummary?.statusLabel ?? 'Unknown'}</span>
                <h3>{latestRun.run_id}</h3>
                <p className="panel-copy">
                  {latestRunSummary?.detail ?? '可进入 run 详情页查看结果、风险、问题与产物。'}
                </p>
                <p className="inline-meta inline-meta-soft">更新时间：{formatDateTime(latestRun.updated_at ?? latestRun.created_at)}</p>
                <div className="action-row">
                  <button
                    type="button"
                    className="primary-button"
                    onClick={() => openRunDetails(latestRun.run_id)}
                  >
                    查看结果
                  </button>
                  <button type="button" className="secondary-button" onClick={() => openRunDetails(latestRun.run_id)}>
                    继续上次评审
                  </button>
                </div>
              </div>
            ) : (
              <div className="empty-state empty-state-compact">
                <div>
                  <h3>暂无历史 run</h3>
                  <p>
                    开始一次评审后，这里会展示最近 run 的状态和“继续工作”入口。
                  </p>
                </div>
              </div>
            )}
          </section>

          <section className="panel">
            <div className="panel-header">
              <div>
                <p className="section-kicker">待处理澄清</p>
                <h2>继续澄清</h2>
              </div>
            </div>

            {clarificationSummary.status === 'loading' ? <p className="panel-copy">正在读取最近 run 的澄清状态...</p> : null}
            {clarificationSummary.status === 'error' ? (
              <div className="feedback-banner feedback-error" aria-live="polite">{clarificationSummary.error}</div>
            ) : null}
            {clarificationSummary.status !== 'loading' ? (
              <>
                <p className="panel-copy">
                  {clarificationSummary.pendingCount > 0
                    ? `最近 run 有 ${clarificationSummary.pendingCount} 条待回答澄清，建议优先处理。`
                    : '最近 run 暂无待处理澄清问题。'}
                </p>
                <div className="action-row">
                  <button
                    type="button"
                    className="primary-button"
                    onClick={() => openRunDetails(clarificationSummary.runId || effectiveRunId)}
                    disabled={!clarificationSummary.runId && !effectiveRunId}
                  >
                    继续澄清
                  </button>
                  <button
                    type="button"
                    className="ghost-button"
                    onClick={() => openRunDetails(effectiveRunId)}
                    disabled={!effectiveRunId}
                  >
                    查看结果
                  </button>
                </div>
              </>
            ) : null}
          </section>

          <section className="panel">
            <div className="panel-header">
              <div>
                <p className="section-kicker">快捷动作</p>
                <h2>继续处理</h2>
              </div>
            </div>
            <div className="action-row">
              <button
                type="button"
                className="secondary-button"
                onClick={() => openRunDetails(effectiveRunId)}
                disabled={!effectiveRunId}
              >
                查看最新结果
              </button>
              <button
                type="button"
                className="secondary-button"
                onClick={() => openRunSection(effectiveRunId, 'clarification')}
                disabled={!effectiveRunId}
              >
                继续澄清
              </button>
              <button type="button" className="ghost-button" onClick={resetForm}>重新提交</button>
              <button
                type="button"
                className="ghost-button"
                onClick={() => openRunSection(effectiveRunId, 'next-delivery')}
                disabled={!effectiveRunId}
              >
                生成下一步交付
              </button>
              <Link to="/" className="ghost-button">打开完整工作台</Link>
            </div>
          </section>
        </section>
      </main>
    </>
  );
}

export default FeishuEntryPage;
