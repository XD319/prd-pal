import '../styles/panels.css';
import '../styles/components.css';
import { useState } from 'react';
import { fetchArtifactPreview } from '../api';

const DECISION_OPTIONS = [
  {
    value: 'generate_from_review',
    label: '根据本次评审结果生成修订版 PRD',
    tone: 'primary-button',
  },
  {
    value: 'custom_requirements',
    label: '我想加上自己的修订要求',
    tone: 'secondary-button',
  },
  {
    value: 'upload_notes',
    label: '我想上传会议纪要后再修订',
    tone: 'secondary-button',
  },
  {
    value: 'skip_revision',
    label: '暂不修订，继续后续交付',
    tone: 'ghost-button',
  },
];

function getDecisionDescription(decision) {
  if (decision === 'generate_from_review') {
    return '系统将基于本次评审结论进入修订输入阶段，但不会自动直接改写当前 PRD。';
  }
  if (decision === 'custom_requirements') {
    return '系统将等待你补充额外的修订要求，再进入 PRD 修订流程。';
  }
  if (decision === 'upload_notes') {
    return '系统将等待你补充会议纪要等输入，再进入 PRD 修订流程。';
  }
  if (decision === 'skip_revision') {
    return '你已选择暂不修订，可以继续使用下面的 next-delivery / handoff 能力。';
  }
  return '';
}

const BASIS_OPTIONS = [
  { value: 'all_review_suggestions', label: '采纳全部评审建议' },
  { value: 'partial_review_suggestions', label: '采纳部分评审建议' },
  { value: 'user_only', label: '仅按用户额外要求修订' },
];

function RevisionDecisionPanel({
  runId,
  revisionStage,
  onDecide,
  onSubmitRevisionInput,
  onConfirmAction,
  isSubmitting,
  isSubmittingInput,
  isSubmittingConfirm,
}) {
  const status = String(revisionStage?.status ?? 'unavailable');
  const decision = String(revisionStage?.decision ?? '');
  const shouldShowActions = status === 'prompted';
  const description = getDecisionDescription(decision);
  const shouldShowInputForm = status === 'collecting_inputs' || status === 'inputs_recorded';
  const [selectedReviewBasis, setSelectedReviewBasis] = useState('all_review_suggestions');
  const [extraInstructions, setExtraInstructions] = useState('');
  const [meetingNotesText, setMeetingNotesText] = useState('');
  const [meetingNotesFileRef, setMeetingNotesFileRef] = useState(null);
  const [revisionPreview, setRevisionPreview] = useState({ status: 'idle', content: '', error: '' });
  const [regenerateRequirements, setRegenerateRequirements] = useState('');
  const [localError, setLocalError] = useState('');
  const hasRevisionDraft = Boolean(revisionStage?.draft_revision_ref);
  const isRevisionConfirmed = Boolean(revisionStage?.revision_confirmed);

  const handleNotesFileChange = async (event) => {
    const file = event.target.files?.[0];
    if (!file) {
      setMeetingNotesFileRef(null);
      return;
    }

    const refPayload = {
      filename: file.name,
      content_type: file.type || '',
      size_bytes: file.size,
      uploaded_at: new Date().toISOString(),
    };
    setMeetingNotesFileRef(refPayload);

    if (file.type.startsWith('text/')) {
      try {
        const text = await file.text();
        setMeetingNotesText(text);
      } catch {
        setLocalError('会议纪要文件读取失败，请改为直接粘贴文本。');
      }
    }
  };

  const handleSubmitRevisionInput = async (event) => {
    event.preventDefault();
    setLocalError('');

    if (typeof onSubmitRevisionInput !== 'function') {
      setLocalError('修订输入接口尚未就绪，请稍后重试。');
      return;
    }

    const payload = {
      selected_review_basis: selectedReviewBasis,
      extra_instructions: extraInstructions.trim(),
      meeting_notes_text: meetingNotesText.trim(),
      meeting_notes_file_ref: meetingNotesFileRef || null,
    };

    await onSubmitRevisionInput(payload);
  };

  const quickApplyReviewResult = async () => {
    setSelectedReviewBasis('all_review_suggestions');
    setExtraInstructions('按评审结果直接改');
    setMeetingNotesText('');
    setMeetingNotesFileRef(null);
    if (typeof onSubmitRevisionInput === 'function') {
      await onSubmitRevisionInput({
        selected_review_basis: 'all_review_suggestions',
        extra_instructions: '按评审结果直接改',
        meeting_notes_text: '',
        meeting_notes_file_ref: null,
      });
    }
  };

  const handleLoadRevisionPreview = async () => {
    if (!hasRevisionDraft || !runId) {
      return;
    }
    setRevisionPreview({ status: 'loading', content: '', error: '' });
    try {
      const payload = await fetchArtifactPreview(runId, 'revised_prd');
      setRevisionPreview({ status: 'ready', content: String(payload.content ?? ''), error: '' });
    } catch (error) {
      setRevisionPreview({
        status: 'error',
        content: '',
        error: error?.message || '修订版预览加载失败。',
      });
    }
  };

  const handleConfirmAction = async (action) => {
    if (typeof onConfirmAction !== 'function') {
      setLocalError('修订版确认接口尚未就绪，请稍后重试。');
      return;
    }
    await onConfirmAction({
      action,
      additional_requirements: regenerateRequirements.trim(),
    });
  };

  return (
    <section className="panel revision-decision-panel">
      <div className="panel-header">
        <div>
          <p className="section-kicker">Revision Decision</p>
          <h2>修订 PRD</h2>
        </div>
        <span className="inline-meta">
          {status === 'prompted' ? '等待你的选择' : status.replace(/_/g, ' ')}
        </span>
      </div>

      <p className="panel-copy">
        评审结果已经稳定。你可以选择是否进入 PRD 修订流程；系统不会在未确认前直接修改当前 PRD。
      </p>

      {description ? (
        <div className={`feedback-banner ${decision === 'skip_revision' ? 'feedback-success' : 'feedback-info'}`} aria-live="polite">
          {description}
        </div>
      ) : null}

      {shouldShowActions ? (
        <div className="list-stack">
          <div className="revision-option-grid">
            {DECISION_OPTIONS.map((option) => (
              <button
                key={option.value}
                type="button"
                className={option.tone}
                disabled={isSubmitting}
                onClick={() => onDecide(option.value)}
              >
                {isSubmitting ? '提交中...' : option.label}
              </button>
            ))}
          </div>
          <div className="subtle-note">
            如果你选择“暂不修订”，下方交付区会继续沿用现有 handoff / next-delivery 流程。
          </div>
        </div>
      ) : (
        <div className="subtle-note">
          {decision
            ? '你的修订选择已记录。你仍可继续查看结果，或直接进入下方交付区。'
            : '当前 run 还未进入可发起修订决策的阶段。'}
        </div>
      )}

      {shouldShowInputForm ? (
        <form className="list-stack revision-input-form" onSubmit={handleSubmitRevisionInput}>
          <label htmlFor="selected-review-basis" className="field-label">修订依据选择</label>
          <select
            id="selected-review-basis"
            value={selectedReviewBasis}
            onChange={(event) => setSelectedReviewBasis(event.target.value)}
            disabled={isSubmittingInput}
          >
            {BASIS_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>

          <label htmlFor="extra-instructions" className="field-label">用户额外修订要求（可选）</label>
          <textarea
            id="extra-instructions"
            rows={4}
            value={extraInstructions}
            onChange={(event) => setExtraInstructions(event.target.value)}
            placeholder="例如：保留原目标不变，重点重写里程碑与验收标准。"
            disabled={isSubmittingInput}
          />

          <label htmlFor="meeting-notes-text" className="field-label">会议纪要文本（可选）</label>
          <textarea
            id="meeting-notes-text"
            rows={4}
            value={meetingNotesText}
            onChange={(event) => setMeetingNotesText(event.target.value)}
            placeholder="未上传文件时可直接粘贴纪要。留空也可继续。"
            disabled={isSubmittingInput}
          />

          <label htmlFor="meeting-notes-file" className="field-label">会议纪要文件（可选，文本文件优先）</label>
          <input
            id="meeting-notes-file"
            type="file"
            accept=".txt,.md,.json,text/plain,text/markdown,application/json"
            onChange={handleNotesFileChange}
            disabled={isSubmittingInput}
          />
          {meetingNotesFileRef ? (
            <div className="subtle-note">
              已选择文件：{meetingNotesFileRef.filename}（{meetingNotesFileRef.size_bytes} bytes）
            </div>
          ) : (
            <div className="subtle-note">
              可不上传，直接提交空会议纪要。
            </div>
          )}

          {localError ? (
            <div className="feedback-banner feedback-error" aria-live="polite">
              {localError}
            </div>
          ) : null}

          <div className="revision-option-grid">
            <button type="submit" className="primary-button" disabled={isSubmittingInput}>
              {isSubmittingInput ? '提交中...' : '提交修订输入包'}
            </button>
            <button
              type="button"
              className="secondary-button"
              disabled={isSubmittingInput}
              onClick={quickApplyReviewResult}
            >
              {isSubmittingInput ? '提交中...' : '按评审结果直接改'}
            </button>
          </div>
        </form>
      ) : null}

      {hasRevisionDraft ? (
        <div className="list-stack">
          <div className="feedback-banner feedback-info" aria-live="polite">
            当前修订版为草稿。你可以确认采用、补充要求后重新生成，或先继续原始流程。
          </div>
          {isRevisionConfirmed ? (
            <div className="feedback-banner feedback-success" aria-live="polite">
              已确认修订版：{revisionStage.confirmed_revision_ref}
            </div>
          ) : null}
          <div className="action-row">
            <button
              type="button"
              className="secondary-button"
              onClick={handleLoadRevisionPreview}
              disabled={isSubmittingConfirm || revisionPreview.status === 'loading'}
            >
              {revisionPreview.status === 'loading' ? '加载中...' : '预览修订版草稿'}
            </button>
            <button
              type="button"
              className="primary-button"
              onClick={() => handleConfirmAction('confirm_revision')}
              disabled={isSubmittingConfirm}
            >
              {isSubmittingConfirm ? '提交中...' : '确认此修订版'}
            </button>
            <button
              type="button"
              className="ghost-button"
              onClick={() => handleConfirmAction('continue_without_revision')}
              disabled={isSubmittingConfirm}
            >
              {isSubmittingConfirm ? '提交中...' : '暂不采用修订版，继续原始流程'}
            </button>
          </div>

          <label htmlFor="regenerate-requirements" className="field-label">附加要求（用于重新生成）</label>
          <textarea
            id="regenerate-requirements"
            rows={3}
            value={regenerateRequirements}
            onChange={(event) => setRegenerateRequirements(event.target.value)}
            placeholder="例如：保留原目标，重点重写验收标准并补充阶段里程碑。"
            disabled={isSubmittingConfirm}
          />
          <button
            type="button"
            className="secondary-button"
            onClick={() => handleConfirmAction('regenerate_revision')}
            disabled={isSubmittingConfirm}
          >
            {isSubmittingConfirm ? '提交中...' : '重新生成（带附加要求）'}
          </button>

          {revisionPreview.status === 'ready' ? (
            <pre className="artifact-preview-markdown">{revisionPreview.content}</pre>
          ) : null}
          {revisionPreview.status === 'error' ? (
            <div className="feedback-banner feedback-error" aria-live="polite">{revisionPreview.error}</div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

export default RevisionDecisionPanel;
