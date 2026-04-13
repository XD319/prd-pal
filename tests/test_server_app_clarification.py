from __future__ import annotations

import json

from fastapi.testclient import TestClient

from prd_pal.server import app as app_module


def test_submit_review_clarification_updates_findings_and_returns_refreshed_result(tmp_path, monkeypatch):
    run_id = '20260309T010206Z'
    run_dir = tmp_path / run_id
    run_dir.mkdir(parents=True)

    parallel_review = {
        'review_mode': 'full',
        'findings': [
            {
                'finding_id': 'finding-clarify-1',
                'title': 'Missing success metric',
                'detail': 'The requirement does not define success.',
                'description': 'The requirement does not define success.',
                'severity': 'high',
                'category': 'scope',
                'source_reviewer': 'product',
                'reviewers': ['product'],
                'ambiguity_type': 'unanswerable',
                'clarification_applied': False,
                'original_severity': '',
                'user_clarification': '',
            }
        ],
        'reviewer_summaries': [
            {
                'reviewer': 'product',
                'summary': 'Need clarification before approval.',
                'status': 'completed',
                'ambiguity_type': 'missing_product_goal',
                'clarification_question': 'What measurable user outcome defines success?',
                'notes': [],
            }
        ],
        'clarification': {
            'triggered': True,
            'status': 'pending',
            'questions': [
                {
                    'id': 'clarify-123',
                    'question': 'What measurable user outcome defines success?',
                    'reviewer': 'product',
                    'ambiguity_type': 'unanswerable',
                    'finding_ids': ['finding-clarify-1'],
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
    }
    report_payload = {
        'run_id': run_id,
        'mode': 'full',
        'review_mode': 'full',
        'gating': {'selected_mode': 'full', 'reasons': [], 'skipped': False},
        'parallel_review': parallel_review,
        'clarification': dict(parallel_review['clarification']),
        'review_clarification': dict(parallel_review['clarification']),
        'parallel_review_meta': {
            'selected_mode': 'full',
            'review_mode': 'full',
            'gating': {'selected_mode': 'full', 'reasons': [], 'skipped': False},
            'artifact_paths': {'review_result_json': str(run_dir / 'review_result.json')},
        },
        'trace': {'reviewer': {'status': 'ok'}},
    }

    for name, content in {
        'report.json': report_payload,
        'review_result.json': parallel_review,
        'review_report.json': parallel_review,
    }.items():
        (run_dir / name).write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding='utf-8')
    (run_dir / 'report.md').write_text('# Review Report', encoding='utf-8')
    (run_dir / 'run_trace.json').write_text('{}', encoding='utf-8')
    (run_dir / 'review_report.md').write_text('# Review Report', encoding='utf-8')
    (run_dir / 'review_summary.md').write_text('# Review Summary', encoding='utf-8')

    monkeypatch.setattr(app_module, 'OUTPUTS_ROOT', tmp_path)
    app_module._jobs.clear()

    client = TestClient(app_module.app)
    response = client.post(
        f'/api/review/{run_id}/clarification',
        json={
            'answers': [
                {
                    'question_id': 'clarify-123',
                    'answer': 'Success means recruiters can finish login and reach the dashboard within 30 seconds.',
                }
            ]
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['clarification']['status'] == 'answered'
    finding = payload['result']['parallel_review']['findings'][0]
    assert finding['clarification_applied'] is True
    assert finding['original_severity'] == 'high'
    assert finding['severity'] == 'medium'
    assert finding['user_clarification'].startswith('Success means recruiters can finish login')

    refreshed_parallel = json.loads((run_dir / 'review_result.json').read_text(encoding='utf-8'))
    assert refreshed_parallel['clarification']['status'] == 'answered'
    assert refreshed_parallel['findings'][0]['clarification_applied'] is True
