from __future__ import annotations

import json

from prd_pal.mcp_server import server as mcp_server


def test_answer_review_clarification_tool_updates_review_payload(tmp_path):
    run_id = '20260309T010207Z'
    run_dir = tmp_path / run_id
    run_dir.mkdir(parents=True)

    report_payload = {
        'run_id': run_id,
        'review_mode': 'full',
        'mode': 'full',
        'gating': {'selected_mode': 'full', 'reasons': [], 'skipped': False},
        'parallel_review': {
            'review_mode': 'full',
            'findings': [
                {
                    'finding_id': 'finding-clarify-2',
                    'title': 'Missing rollback criteria',
                    'detail': 'Rollback behavior is not defined.',
                    'description': 'Rollback behavior is not defined.',
                    'severity': 'high',
                    'category': 'testability',
                    'source_reviewer': 'qa',
                    'reviewers': ['qa'],
                    'ambiguity_type': 'unanswerable',
                    'clarification_applied': False,
                    'original_severity': '',
                    'user_clarification': '',
                }
            ],
            'reviewer_summaries': [
                {
                    'reviewer': 'qa',
                    'summary': 'QA cannot infer rollback behavior.',
                    'status': 'completed',
                    'ambiguity_type': 'missing_test_oracle',
                    'clarification_question': 'What rollback and negative-case checks must QA validate?',
                    'notes': [],
                }
            ],
            'clarification': {
                'triggered': True,
                'status': 'pending',
                'questions': [
                    {
                        'id': 'clarify-qa-1',
                        'question': 'What rollback and negative-case checks must QA validate?',
                        'reviewer': 'qa',
                        'ambiguity_type': 'unanswerable',
                        'finding_ids': ['finding-clarify-2'],
                    }
                ],
                'answers_applied': [],
                'findings_updated': [],
            },
            'artifacts': {
                'review_result_json': str(run_dir / 'review_result.json'),
                'review_report_json': str(run_dir / 'review_report.json'),
                'review_report_md': str(run_dir / 'review_report.md'),
                'review_summary_md': str(run_dir / 'review_summary.md'),
            },
        },
        'clarification': {
            'triggered': True,
            'status': 'pending',
            'questions': [
                {
                    'id': 'clarify-qa-1',
                    'question': 'What rollback and negative-case checks must QA validate?',
                    'reviewer': 'qa',
                    'ambiguity_type': 'unanswerable',
                    'finding_ids': ['finding-clarify-2'],
                }
            ],
            'answers_applied': [],
            'findings_updated': [],
        },
        'parallel_review_meta': {
            'selected_mode': 'full',
            'review_mode': 'full',
            'gating': {'selected_mode': 'full', 'reasons': [], 'skipped': False},
            'artifact_paths': {'review_result_json': str(run_dir / 'review_result.json')},
        },
        'trace': {'reviewer': {'status': 'ok'}},
    }

    (run_dir / 'report.json').write_text(json.dumps(report_payload, ensure_ascii=False, indent=2), encoding='utf-8')
    (run_dir / 'report.md').write_text('# Review Report', encoding='utf-8')
    (run_dir / 'run_trace.json').write_text('{}', encoding='utf-8')
    (run_dir / 'review_result.json').write_text(json.dumps(report_payload['parallel_review'], ensure_ascii=False, indent=2), encoding='utf-8')
    (run_dir / 'review_report.json').write_text(json.dumps(report_payload['parallel_review'], ensure_ascii=False, indent=2), encoding='utf-8')
    (run_dir / 'review_report.md').write_text('# Review Report', encoding='utf-8')
    (run_dir / 'review_summary.md').write_text('# Review Summary', encoding='utf-8')

    result = mcp_server.answer_review_clarification(
        run_id=run_id,
        answers=[
            {
                'question_id': 'clarify-qa-1',
                'answer': 'QA must verify rollback restores the previous state, rejects invalid payloads, and logs the failure path.',
            }
        ],
        options={'outputs_root': str(tmp_path)},
    )

    assert 'error' not in result
    assert result['run_id'] == run_id
    assert result['clarification']['status'] == 'answered'
    assert result['findings'][0]['clarification_applied'] is True
    assert result['findings'][0]['original_severity'] == 'high'
    assert result['findings'][0]['user_clarification'].startswith('QA must verify rollback restores the previous state')
