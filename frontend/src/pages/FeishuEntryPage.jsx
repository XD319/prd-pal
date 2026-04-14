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

function deriveRevisionQuickAction(payload, runStatus = '') {
  const revisionStage = payload?.revision_stage ?? payload?.result?.revision_stage ?? {};
  const normalizedStageStatus = String(revisionStage?.status ?? '').trim().toLowerCase();
  const normalizedRunStatus = String(runStatus || '').trim().toLowerCase();
  const hasDraft = Boolean(revisionStage?.draft_revision_ref);
  const isConfirmed = Boolean(revisionStage?.revision_confirmed)
    || normalizedStageStatus === 'confirmed'
    || normalizedRunStatus === 'revision_confirmed';
  const isPrompted = normalizedStageStatus === 'prompted' || normalizedRunStatus === 'revision_prompted';
  const isGenerated = normalizedRunStatus === 'revision_generated'
    || normalizedStageStatus === 'inputs_recorded'
    || hasDraft;

  if (isConfirmed) {
    return {
      stage: 'confirmed',
      title: '修订版已确认，可继续交付',
      detail: '你可以直接进入 next-delivery / handoff，默认会优先采用已确认修订版作为交付来源。',
      primaryLabel: '继续下一步交付',
      secondaryLabel: '查看修订版',
    };
  }
  if (isGenerated) {
    return {
      stage: 'generated',
      title: '修订版已生成，等待确认',
      detail: '建议先进入修订区预览并确认修订版，再决定是否继续后续交付。',
      primaryLabel: '查看修订版',
      secondaryLabel: '继续修订',
    };
  }
  if (isPrompted) {
    return {
      stage: 'prompted',
      title: '需要决定是否修订',
      detail: '最近 run 已进入修订决策阶段，可立即继续“修订 PRD”流程。',
      primaryLabel: '继续修订',
      secondaryLabel: '查看结果',
    };
  }
  return {
    stage: 'none',
    title: '',
    detail: '',
    primaryLabel: '',
    secondaryLabel: '',
  };
}

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
  const [revisionSummary, setRevisionSummary] = useState({
    status: 'idle',
    stage: 'none',
    runId: '',
    title: '',
    detail: '',
    primaryLabel: '',
    secondaryLabel: '',
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
  const preservedRunQueryKeys = ['open_id', 'tenant_key', 'lang', 'locale', 'user_id', 'trigger_source'];

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
      setRevisionSummary({
        status: 'idle',
        stage: 'none',
        runId: '',
        title: '',
        detail: '',
        primaryLabel: '',
        secondaryLabel: '',
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
    setRevisionSummary((current) => ({
      ...current,
      status: 'loading',
      runId,
      error: '',
    }));

    try {
      const payload = await fetchReviewResult(runId);
      const clarification = deriveClarification(payload?.result ?? {});
      const pendingCount = clarification.status === 'pending' ? clarification.questions.length : 0;
      const revisionQuickAction = deriveRevisionQuickAction(payload, latestRun?.status);
      setClarificationSummary({
        status: 'ready',
        pendingCount,
        runId,
        error: '',
      });
      setRevisionSummary({
        status: 'ready',
        stage: revisionQuickAction.stage,
        runId,
        title: revisionQuickAction.title,
        detail: revisionQuickAction.detail,
        primaryLabel: revisionQuickAction.primaryLabel,
        secondaryLabel: revisionQuickAction.secondaryLabel,
        error: '',
      });
    } catch (error) {
      setClarificationSummary({
        status: 'error',
        pendingCount: 0,
        runId,
        error: formatApiError(error, 'Clarification summary is temporarily unavailable.'),
      });
      setRevisionSummary({
        status: 'error',
        stage: 'none',
        runId,
        title: '',
        detail: '',
        primaryLabel: '',
        secondaryLabel: '',
        error: formatApiError(error, 'Revision summary is temporarily unavailable.'),
      });
    }
  }

  function openRunDetails(runId) {
    if (!runId) {
      return;
    }
    navigate(buildFeishuRunUrl(runId));
  }

  function openRunSection(runId, sectionHash) {
    if (!runId) {
      return;
    }
    navigate(buildFeishuRunUrl(runId, sectionHash));
  }

  function buildFeishuRunUrl(runId, sectionHash = '') {
    const params = new URLSearchParams();
    params.set('embed', 'feishu');
    params.set('trigger_source', 'feishu');
    preservedRunQueryKeys.forEach((key) => {
      const value = String(searchParams.get(key) || '').trim();
      if (value) {
        params.set(key, value);
      }
    });
    const normalizedHash = String(sectionHash || '').trim();
    const hashPart = normalizedHash ? `#${normalizedHash.replace(/^#/, '')}` : '';
    return `/run/${runId}?${params.toString()}${hashPart}`;
  }

  useEffect(() => {
    void loadClarificationSummary(latestRun?.run_id ?? '');
  }, [latestRun?.run_id]);

  const effectiveRunId = submittedRunId || latestRun?.run_id || '';
  const latestRunSummary = latestRun ? describeHistoryRun(latestRun) : null;
  const hasRevisionShortcut = revisionSummary.stage !== 'none';

  function handleRevisionPrimaryAction() {
    if (!effectiveRunId) {
      return;
    }
    if (revisionSummary.stage === 'confirmed') {
      openRunSection(effectiveRunId, 'next-delivery');
      return;
    }
    openRunSection(effectiveRunId, 'revise-prd');
  }

  function handleRevisionSecondaryAction() {
    if (!effectiveRunId) {
      return;
    }
    if (revisionSummary.stage === 'prompted') {
      openRunDetails(effectiveRunId);
      return;
    }
    openRunSection(effectiveRunId, 'revise-prd');
  }

  return (
    <>
      <header className="hero hero-tight">
        <div>
          <p className="eyebrow">Feishu Work Entry</p>
          <h1>飞书工作入口页</h1>
          <p className="hero-copy">
            从飞书进入后，你可以在一个页面完成完整闭环：发起评审、查看结果、回答澄清、继续下一步动作，不需要切换到完整工作台。
          </p>
        </div>

        <div className="hero-panel">
          <span className="hero-label">Current Workspace</span>
          <strong>{workspaceLabel}</strong>
          <p>
            推荐使用飞书文档链接发起评审。入口页会自动保留飞书上下文并跳转到完整 H5 结果页。
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
                <p className="section-kicker">修订状态</p>
                <h2>继续修订 PRD</h2>
              </div>
            </div>

            {revisionSummary.status === 'loading' ? <p className="panel-copy">正在读取最近 run 的修订阶段...</p> : null}
            {revisionSummary.status === 'error' ? (
              <div className="feedback-banner feedback-error" aria-live="polite">{revisionSummary.error}</div>
            ) : null}
            {revisionSummary.status !== 'loading' ? (
              <>
                <p className="panel-copy">
                  {hasRevisionShortcut
                    ? revisionSummary.detail
                    : '最近 run 暂未进入修订相关阶段，可先查看结果或继续澄清。'}
                </p>
                <div className="action-row">
                  <button
                    type="button"
                    className="primary-button"
                    onClick={handleRevisionPrimaryAction}
                    disabled={!effectiveRunId || !hasRevisionShortcut}
                  >
                    {hasRevisionShortcut ? revisionSummary.primaryLabel : '继续修订'}
                  </button>
                  <button
                    type="button"
                    className="ghost-button"
                    onClick={handleRevisionSecondaryAction}
                    disabled={!effectiveRunId || !hasRevisionShortcut}
                  >
                    {hasRevisionShortcut ? revisionSummary.secondaryLabel : '查看修订版'}
                  </button>
                </div>
              </>
            ) : null}
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
                    ? `最近 run 有 ${clarificationSummary.pendingCount} 条待回答澄清，建议优先处理后再进入下一步。`
                    : '最近 run 暂无待处理澄清问题，可直接进入下一步交付。'}
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
                className="primary-button"
                onClick={hasRevisionShortcut ? handleRevisionPrimaryAction : () => openRunDetails(effectiveRunId)}
                disabled={!effectiveRunId}
              >
                {hasRevisionShortcut ? revisionSummary.primaryLabel : '查看最新结果'}
              </button>
              <button
                type="button"
                className="secondary-button"
                onClick={hasRevisionShortcut ? handleRevisionSecondaryAction : () => openRunSection(effectiveRunId, 'clarification')}
                disabled={!effectiveRunId}
              >
                {hasRevisionShortcut ? revisionSummary.secondaryLabel : '继续澄清'}
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
