from __future__ import annotations

import json

from fastapi.testclient import TestClient

from requirement_review_v1.server import app as app_module


def test_get_review_result_returns_parsed_report_and_stable_artifacts(tmp_path, monkeypatch):
    run_id = '20260309T010203Z'
    run_dir = tmp_path / run_id
    run_dir.mkdir(parents=True)

    report_payload = {
        'run_id': run_id,
        'schema_version': 'v1.1',
        'trace': {'reviewer': {'status': 'ok'}},
    }
    (run_dir / 'report.md').write_text('# Review Report', encoding='utf-8')
    (run_dir / 'report.json').write_text(json.dumps(report_payload, ensure_ascii=False, indent=2), encoding='utf-8')
    (run_dir / 'run_trace.json').write_text('{}', encoding='utf-8')
    (run_dir / 'review_report.json').write_text('{}', encoding='utf-8')
    (run_dir / 'risk_items.json').write_text('{}', encoding='utf-8')
    (run_dir / 'open_questions.json').write_text('{}', encoding='utf-8')
    (run_dir / 'review_summary.md').write_text('# Review Summary', encoding='utf-8')

    monkeypatch.setattr(app_module, 'OUTPUTS_ROOT', tmp_path)
    app_module._jobs.clear()

    client = TestClient(app_module.app)
    response = client.get(f'/api/review/{run_id}/result')

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        'run_id': run_id,
        'status': 'completed',
        'result': report_payload,
        'artifact_paths': {
            'report_md': str(run_dir / 'report.md'),
            'report_json': str(run_dir / 'report.json'),
            'run_trace': str(run_dir / 'run_trace.json'),
            'review_report_json': str(run_dir / 'review_report.json'),
            'risk_items_json': str(run_dir / 'risk_items.json'),
            'open_questions_json': str(run_dir / 'open_questions.json'),
            'review_summary_md': str(run_dir / 'review_summary.md'),
        },
    }
    app_module._jobs.clear()


def test_get_review_result_returns_404_for_missing_run(tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, 'OUTPUTS_ROOT', tmp_path)
    app_module._jobs.clear()

    client = TestClient(app_module.app)
    response = client.get('/api/review/20260309T010204Z/result')

    assert response.status_code == 404
    assert response.json()['detail'] == {
        'code': 'run_not_found',
        'message': 'run_id not found: 20260309T010204Z',
    }
    app_module._jobs.clear()


def test_get_review_result_returns_409_when_report_is_not_ready(tmp_path, monkeypatch):
    run_id = '20260309T010205Z'
    run_dir = tmp_path / run_id
    run_dir.mkdir(parents=True)

    monkeypatch.setattr(app_module, 'OUTPUTS_ROOT', tmp_path)
    app_module._jobs.clear()
    job = app_module.JobRecord(run_id=run_id, run_dir=run_dir, status='running', current_node='planner')
    job.node_progress['planner']['status'] = 'running'
    app_module._jobs[run_id] = job

    client = TestClient(app_module.app)
    response = client.get(f'/api/review/{run_id}/result')

    assert response.status_code == 409
    detail = response.json()['detail']
    assert detail['code'] == 'result_not_ready'
    assert detail['message'] == f'report.json not ready for run_id={run_id}'
    assert detail['run_id'] == run_id
    assert detail['status'] == 'running'
    assert detail['progress']['current_node'] == 'planner'
    app_module._jobs.clear()


def test_get_review_status_returns_structured_feishu_error_for_failed_run(tmp_path, monkeypatch):
    run_id = '20260309T010206Z'
    run_dir = tmp_path / run_id
    run_dir.mkdir(parents=True)

    monkeypatch.setattr(app_module, 'OUTPUTS_ROOT', tmp_path)
    app_module._jobs.clear()
    app_module._jobs[run_id] = app_module.JobRecord(
        run_id=run_id,
        run_dir=run_dir,
        status='failed',
        error='Feishu authentication failed because app credentials are missing.',
        error_code='AUTHENTICATION_FAILED',
    )

    client = TestClient(app_module.app)
    response = client.get(f'/api/review/{run_id}')

    assert response.status_code == 200
    payload = response.json()
    assert payload['status'] == 'failed'
    assert payload['progress']['error'] == 'Feishu authentication failed because app credentials are missing.'
    assert payload['error'] == {
        'code': 'AUTHENTICATION_FAILED',
        'message': 'Feishu authentication failed because app credentials are missing.',
    }
    app_module._jobs.clear()


def test_get_review_result_returns_controlled_feishu_error_for_failed_run(tmp_path, monkeypatch):
    run_id = '20260309T010207Z'
    run_dir = tmp_path / run_id
    run_dir.mkdir(parents=True)

    monkeypatch.setattr(app_module, 'OUTPUTS_ROOT', tmp_path)
    app_module._jobs.clear()
    app_module._jobs[run_id] = app_module.JobRecord(
        run_id=run_id,
        run_dir=run_dir,
        status='failed',
        current_node='',
        error="Permission denied while fetching Feishu source 'feishu://docx/doc-token': HTTP 403: permission denied",
        error_code='PERMISSION_DENIED',
    )

    client = TestClient(app_module.app)
    response = client.get(f'/api/review/{run_id}/result')

    assert response.status_code == 409
    detail = response.json()['detail']
    assert detail['code'] == 'PERMISSION_DENIED'
    assert detail['status'] == 'failed'
    assert detail['error'] == {
        'code': 'PERMISSION_DENIED',
        'message': "Permission denied while fetching Feishu source 'feishu://docx/doc-token': HTTP 403: permission denied",
    }
    assert detail['message'] == "Permission denied while fetching Feishu source 'feishu://docx/doc-token': HTTP 403: permission denied"
    app_module._jobs.clear()


def test_get_review_artifact_preview_returns_text_payload(tmp_path, monkeypatch):
    run_id = '20260309T010208Z'
    run_dir = tmp_path / run_id
    run_dir.mkdir(parents=True)

    report_payload = {
        'run_id': run_id,
        'schema_version': 'v1.1',
        'trace': {'reviewer': {'status': 'ok'}},
    }
    (run_dir / 'report.json').write_text(json.dumps(report_payload, ensure_ascii=False, indent=2), encoding='utf-8')
    (run_dir / 'report.md').write_text('# Review Report', encoding='utf-8')
    (run_dir / 'review_summary.md').write_text('# Preview Heading\n\nArtifact body', encoding='utf-8')

    monkeypatch.setattr(app_module, 'OUTPUTS_ROOT', tmp_path)
    app_module._jobs.clear()

    client = TestClient(app_module.app)
    response = client.get(f'/api/review/{run_id}/artifacts/review_summary_md')

    assert response.status_code == 200
    payload = response.json()
    assert payload['run_id'] == run_id
    assert payload['artifact_key'] == 'review_summary_md'
    assert payload['format'] == 'markdown'
    assert payload['content'] == '# Preview Heading\n\nArtifact body'
    assert payload['path'] == str(run_dir / 'review_summary.md')
    app_module._jobs.clear()


def test_get_review_artifact_preview_returns_404_for_unknown_artifact(tmp_path, monkeypatch):
    run_id = '20260309T010209Z'
    run_dir = tmp_path / run_id
    run_dir.mkdir(parents=True)

    report_payload = {
        'run_id': run_id,
        'schema_version': 'v1.1',
        'trace': {'reviewer': {'status': 'ok'}},
    }
    (run_dir / 'report.json').write_text(json.dumps(report_payload, ensure_ascii=False, indent=2), encoding='utf-8')
    (run_dir / 'report.md').write_text('# Review Report', encoding='utf-8')

    monkeypatch.setattr(app_module, 'OUTPUTS_ROOT', tmp_path)
    app_module._jobs.clear()

    client = TestClient(app_module.app)
    response = client.get(f'/api/review/{run_id}/artifacts/review_summary_md')

    assert response.status_code == 404
    assert response.json()['detail'] == {
        'code': 'artifact_not_found',
        'message': f"artifact 'review_summary_md' not found for run_id={run_id}",
        'run_id': run_id,
    }
    app_module._jobs.clear()
