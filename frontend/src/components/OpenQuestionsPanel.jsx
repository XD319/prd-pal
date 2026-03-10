import '../styles/panels.css';
import '../styles/components.css';
import { deriveOpenQuestions } from '../utils/derivers';
import { joinList, pluralize } from '../utils/formatters';

function OpenQuestionsPanel({ result }) {
  const questions = result ? deriveOpenQuestions(result) : [];

  return (
    <section className="panel open-questions-panel">
      <div className="panel-header">
        <div>
          <p className="section-kicker">Open Questions</p>
          <h2>Open questions</h2>
        </div>
        <span className="inline-meta">{pluralize(questions.length, 'item')}</span>
      </div>

      {questions.length === 0 ? (
        <div className="empty-inline">No open questions were generated for this run.</div>
      ) : (
        <div className="list-stack">
          {questions.map((question) => (
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

export default OpenQuestionsPanel;