import { useEffect, useState } from 'react';
import '../styles/panels.css';
import '../styles/components.css';
import { deriveClarification, deriveOpenQuestions } from '../utils/derivers';
import { joinList, pluralize } from '../utils/formatters';

function ClarificationPanel({ result, onSubmit, isSubmitting }) {
  const clarification = deriveClarification(result);
  const openQuestions = result ? deriveOpenQuestions(result) : [];
  const [answers, setAnswers] = useState({});

  useEffect(() => {
    const nextAnswers = {};
    clarification.questions.forEach((item) => {
      nextAnswers[item.id] = '';
    });
    setAnswers(nextAnswers);
  }, [clarification.questions]);

  const hasPendingQuestions = clarification.triggered && clarification.status === 'pending' && clarification.questions.length > 0;

  const handleSubmit = async (event) => {
    event.preventDefault();
    const payload = clarification.questions
      .map((item) => ({
        question_id: item.id,
        answer: String(answers[item.id] ?? '').trim(),
      }))
      .filter((item) => item.answer);

    if (payload.length === 0) {
      return;
    }
    await onSubmit(payload);
  };

  return (
    <section className="panel open-questions-panel">
      <div className="panel-header">
        <div>
          <p className="section-kicker">Clarification Gate</p>
          <h2>Clarification panel</h2>
        </div>
        <span className="inline-meta">
          {hasPendingQuestions ? pluralize(clarification.questions.length, 'question') : pluralize(openQuestions.length, 'item')}
        </span>
      </div>

      {hasPendingQuestions ? (
        <form className="list-stack" onSubmit={handleSubmit}>
          {clarification.questions.map((item) => (
            <article key={item.id} className="question-card">
              <h4>{item.question}</h4>
              <div className="detail-row">
                {item.reviewer && <span>{item.reviewer}</span>}
                {item.findingIds.length > 0 && <span>{joinList(item.findingIds)}</span>}
              </div>
              <textarea
                rows={4}
                value={answers[item.id] ?? ''}
                onChange={(event) => {
                  const value = event.target.value;
                  setAnswers((current) => ({ ...current, [item.id]: value }));
                }}
                placeholder="Add the missing clarification so we can re-evaluate the affected findings."
              />
            </article>
          ))}
          <div className="detail-row">
            <span>Only high-severity, unanswerable findings are paused for clarification.</span>
          </div>
          <button type="submit" className="ghost-button" disabled={isSubmitting}>
            {isSubmitting ? 'Submitting...' : 'Submit clarification'}
          </button>
        </form>
      ) : clarification.status === 'answered' ? (
        <div className="list-stack">
          <div className="subtle-note">Clarification answers were applied to this run.</div>
          {clarification.findingsUpdated.map((item) => (
            <article key={`${item.finding_id}-${item.question_id}`} className="question-card">
              <h4>{item.finding_id}</h4>
              <div className="detail-row">
                <span>{item.severity_before} to {item.severity_after}</span>
                {item.reviewer && <span>{item.reviewer}</span>}
              </div>
            </article>
          ))}
        </div>
      ) : openQuestions.length === 0 ? (
        <div className="empty-inline">No clarification or open questions were generated for this run.</div>
      ) : (
        <div className="list-stack">
          {openQuestions.map((question) => (
            <article key={question.id} className="question-card">
              <h4>{question.question}</h4>
              {question.detail && <p>{question.detail}</p>}
              {question.reviewers.length > 0 && (
                <div className="detail-row">
                  <span>{joinList(question.reviewers)}</span>
                </div>
              )}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

export default ClarificationPanel;
