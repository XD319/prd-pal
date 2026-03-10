"""Minimal smoke validation for review-engine CLI and FastAPI flows.

Usage:
    python eval/smoke_review_engine.py
"""

from __future__ import annotations

import asyncio
import io
import json
import os
import sys
import time
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from requirement_review_v1.main import main as cli_main
import requirement_review_v1.main as cli_module
from requirement_review_v1.server import app as app_module


async def _run_cli_smoke(workspace: Path) -> dict[str, object]:
    input_path = workspace / "smoke_prd.md"
    input_path.write_text("# Smoke PRD\n\n- Requirement: generate a review report.\n", encoding="utf-8")

    run_dir = workspace / "cli-run"
    run_dir.mkdir(parents=True, exist_ok=True)
    summary = SimpleNamespace(
        report_md_path=str(run_dir / "report.md"),
        report_json_path=str(run_dir / "report.json"),
        run_trace_path=str(run_dir / "run_trace.json"),
    )
    Path(summary.report_md_path).write_text("# Smoke Report", encoding="utf-8")
    Path(summary.report_json_path).write_text(json.dumps({"status": "completed"}, ensure_ascii=False), encoding="utf-8")
    Path(summary.run_trace_path).write_text(json.dumps({"reporter": {"status": "ok"}}, ensure_ascii=False), encoding="utf-8")

    original_review = cli_module.review_prd_text_async
    original_argv = list(sys.argv)
    buffer = io.StringIO()
    try:
        cli_module.review_prd_text_async = AsyncMock(return_value=summary)
        sys.argv = ["requirement_review_v1.main", "--input", str(input_path)]
        with redirect_stdout(buffer):
            await cli_main()
    finally:
        cli_module.review_prd_text_async = original_review
        sys.argv = original_argv

    output = buffer.getvalue()
    return {
        "passed": all(token in output for token in ("Report :", "State  :", "Trace  :")),
        "output": output.strip(),
        "artifacts": {
            "report_md": summary.report_md_path,
            "report_json": summary.report_json_path,
            "run_trace": summary.run_trace_path,
        },
    }


def _run_fastapi_smoke(workspace: Path) -> dict[str, object]:
    outputs_root = workspace / "fastapi-outputs"
    outputs_root.mkdir(parents=True, exist_ok=True)
    run_id = "20260310T120000Z"

    async def fake_run_job(job, *, prd_text=None, prd_path=None, source=None):
        report_dir = outputs_root / job.run_id
        report_dir.mkdir(parents=True, exist_ok=True)
        report_payload = {
            "run_id": job.run_id,
            "status": "completed",
            "trace": {"reporter": {"status": "ok"}},
            "metrics": {"coverage_ratio": 1.0},
        }
        (report_dir / "report.md").write_text("# Smoke Report", encoding="utf-8")
        (report_dir / "report.json").write_text(json.dumps(report_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        (report_dir / "run_trace.json").write_text(json.dumps(report_payload["trace"], ensure_ascii=False, indent=2), encoding="utf-8")
        job.status = "completed"
        job.report_paths = {
            "report_md": str(report_dir / "report.md"),
            "report_json": str(report_dir / "report.json"),
            "run_trace": str(report_dir / "run_trace.json"),
        }

    original_outputs = app_module.OUTPUTS_ROOT
    original_make_run_id = app_module.make_run_id
    original_run_job = app_module._run_job
    original_auth_disabled = os.environ.get("MARRDP_API_AUTH_DISABLED")
    original_rate_disabled = os.environ.get("MARRDP_API_RATE_LIMIT_DISABLED")
    app_module._jobs.clear()
    app_module._reset_submission_rate_limits()
    try:
        os.environ["MARRDP_API_AUTH_DISABLED"] = "true"
        os.environ["MARRDP_API_RATE_LIMIT_DISABLED"] = "true"
        app_module.OUTPUTS_ROOT = outputs_root
        app_module.make_run_id = lambda: run_id
        app_module._run_job = fake_run_job

        client = TestClient(app_module.app)
        create_response = client.post("/api/review", json={"prd_text": "# Smoke review"})
        time.sleep(0.05)
        status_response = client.get(f"/api/review/{run_id}")
        result_response = client.get(f"/api/review/{run_id}/result")
    finally:
        if original_auth_disabled is None:
            os.environ.pop("MARRDP_API_AUTH_DISABLED", None)
        else:
            os.environ["MARRDP_API_AUTH_DISABLED"] = original_auth_disabled
        if original_rate_disabled is None:
            os.environ.pop("MARRDP_API_RATE_LIMIT_DISABLED", None)
        else:
            os.environ["MARRDP_API_RATE_LIMIT_DISABLED"] = original_rate_disabled
        app_module.OUTPUTS_ROOT = original_outputs
        app_module.make_run_id = original_make_run_id
        app_module._run_job = original_run_job
        app_module._jobs.clear()
        app_module._reset_submission_rate_limits()

    passed = (
        create_response.status_code == 200
        and status_response.status_code == 200
        and result_response.status_code == 200
        and status_response.json().get("status") == "completed"
        and result_response.json().get("status") == "completed"
    )
    return {
        "passed": passed,
        "create": create_response.json(),
        "status": status_response.json(),
        "result": result_response.json(),
    }


def main() -> None:
    out_path = PROJECT_ROOT / "eval" / "smoke_report.json"
    with TemporaryDirectory() as tmp_dir:
        workspace = Path(tmp_dir)
        cli_summary = asyncio.run(_run_cli_smoke(workspace))
        api_summary = _run_fastapi_smoke(workspace)

    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "scope": "review-engine-only",
        "checks": {
            "cli": cli_summary,
            "fastapi": api_summary,
        },
        "passed": bool(cli_summary["passed"] and api_summary["passed"]),
    }
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
