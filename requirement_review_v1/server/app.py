from __future__ import annotations

import asyncio
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from requirement_review_v1.monitoring import query_audit_events
from requirement_review_v1.run_review import make_run_id
from requirement_review_v1.server.job_state import (
    ClarificationAnswerRequest,
    JobRecord,
    RUN_PROGRESS_FILENAME,
    ReviewCreateRequest,
    build_run_list_entry,
    job_status_payload as _job_status_payload,
    persisted_status_payload as _persisted_status_payload,
    persist_job_snapshot as _persist_job_snapshot,
    resolve_review_inputs as _resolve_review_inputs,
    resolve_runtime_llm_options as _resolve_runtime_llm_options,
    result_unavailable_detail as _result_unavailable_detail,
    run_job as _run_job_impl,
    run_sort_timestamp,
    terminal_payload_for_job as _terminal_payload_for_job,
    terminal_payload_for_run_dir as _terminal_payload_for_run_dir,
)
from requirement_review_v1.server.report_exports import (
    build_report_csv as _build_report_csv,
    build_report_html as _build_report_html,
    load_report_payload as _load_report_payload,
)
from requirement_review_v1.server.security import (
    authenticate_request,
    client_ip,
    controlled_error_response,
    enforce_submission_rate_limit,
    reset_submission_rate_limits as _reset_submission_rate_limits,
    security_settings,
    should_skip_request_logging,
)
from requirement_review_v1.server.sse import ProgressBroadcaster
from requirement_review_v1.service.comparison_service import compare_runs, get_run_stats_summary, get_trend_data
from requirement_review_v1.service.report_service import RUN_ID_PATTERN
from requirement_review_v1.service.review_service import (
    ReviewArtifactNotFoundError,
    ReviewResultNotReadyError,
    ReviewRunNotFoundError,
    answer_review_clarification,
    get_review_artifact_preview_payload,
    get_review_result_payload,
)
from requirement_review_v1.templates import TemplateRegistryError, list_template_records
from requirement_review_v1.utils.logging import get_logger

OUTPUTS_ROOT = Path("outputs")
FRONTEND_DIST_ROOT = Path(__file__).resolve().parents[2] / "frontend" / "dist"
log = get_logger("server.http")


@asynccontextmanager
async def _app_lifespan(_: FastAPI):
    load_dotenv()
    yield


app = FastAPI(title="Requirement Review V2 API", version="2.0", lifespan=_app_lifespan)
_jobs: dict[str, JobRecord] = {}
_jobs_lock = asyncio.Lock()


async def _run_job(
    job: JobRecord,
    *,
    prd_text: str | None = None,
    prd_path: str | None = None,
    source: str | None = None,
    mode: str | None = None,
    llm_options: dict[str, Any] | None = None,
) -> None:
    await _run_job_impl(
        job,
        outputs_root=OUTPUTS_ROOT,
        prd_text=prd_text,
        prd_path=prd_path,
        source=source,
        mode=mode,
        llm_options=llm_options,
    )


@app.middleware("http")
async def _request_logging_middleware(request: Request, call_next):
    path = request.url.path
    if should_skip_request_logging(path):
        return await call_next(request)

    trace_id = uuid.uuid4().hex
    started = time.perf_counter()
    response = None
    try:
        response = await call_next(request)
        return response
    finally:
        duration_ms = round((time.perf_counter() - started) * 1000)
        status_code = response.status_code if response is not None else 500
        log.info(
            "request completed",
            extra={
                "trace_id": trace_id,
                "method": request.method,
                "path": path,
                "status_code": status_code,
                "duration_ms": duration_ms,
                "client_ip": client_ip(request),
            },
        )
        if response is not None:
            response.headers["X-Trace-ID"] = trace_id


@app.middleware("http")
async def _api_security_middleware(request: Request, call_next):
    if not request.url.path.startswith("/api/"):
        return await call_next(request)

    settings = security_settings()
    auth_error = authenticate_request(request, settings)
    if auth_error is not None:
        return auth_error

    rate_limit_error = enforce_submission_rate_limit(request, settings)
    if rate_limit_error is not None:
        return rate_limit_error

    return await call_next(request)


@app.exception_handler(RequestValidationError)
async def _handle_request_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    return controlled_error_response(
        422,
        code="request_validation_error",
        message="Request validation failed.",
        extra={"errors": exc.errors()},
    )


@app.exception_handler(Exception)
async def _handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
    return controlled_error_response(
        500,
        code="internal_server_error",
        message=f"The server could not process the request: {type(exc).__name__}.",
    )


@app.get("/api/templates")
def list_templates_endpoint(version: str | None = Query(default=None)) -> dict[str, Any]:
    try:
        templates = list(list_template_records(version=version))
    except TemplateRegistryError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"count": len(templates), "templates": templates}


@app.get("/api/templates/{template_type}")
def list_templates_by_type_endpoint(template_type: str, version: str | None = Query(default=None)) -> dict[str, Any]:
    try:
        templates = list(list_template_records(template_type=template_type, version=version))
    except TemplateRegistryError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"template_type": template_type, "count": len(templates), "templates": templates}


@app.get("/api/audit")
def list_audit_events_endpoint(
    run_id: str | None = Query(default=None),
    bundle_id: str | None = Query(default=None),
    task_id: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
) -> dict[str, Any]:
    events = query_audit_events(
        OUTPUTS_ROOT,
        run_id=run_id,
        bundle_id=bundle_id,
        task_id=task_id,
        event_type=event_type,
        status=status,
    )
    return {
        "count": len(events),
        "events": events,
        "filters": {
            "run_id": run_id,
            "bundle_id": bundle_id,
            "task_id": task_id,
            "event_type": event_type,
            "status": status,
        },
    }


@app.get("/api/runs")
async def list_runs() -> dict[str, Any]:
    async with _jobs_lock:
        jobs = dict(_jobs)

    if not OUTPUTS_ROOT.exists() or not OUTPUTS_ROOT.is_dir():
        return {"count": 0, "runs": []}

    runs: list[tuple[float, str, dict[str, Any]]] = []
    for run_dir in OUTPUTS_ROOT.iterdir():
        if not run_dir.is_dir() or not RUN_ID_PATTERN.fullmatch(run_dir.name):
            continue
        job = jobs.get(run_dir.name)
        runs.append(
            (
                run_sort_timestamp(run_dir, job),
                run_dir.name,
                build_run_list_entry(run_dir, persisted_status_payload=_persisted_status_payload, job=job),
            )
        )

    runs.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return {"count": len(runs), "runs": [item[2] for item in runs]}


@app.post("/api/review")
async def create_review(payload: ReviewCreateRequest) -> dict[str, str]:
    review_inputs = _resolve_review_inputs(payload)
    llm_options = _resolve_runtime_llm_options(payload)
    run_id = make_run_id()
    run_dir = OUTPUTS_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    job = JobRecord(run_id=run_id, run_dir=run_dir)
    _persist_job_snapshot(job)
    task = asyncio.create_task(_run_job(job, **review_inputs, llm_options=llm_options))
    job.task = task

    async with _jobs_lock:
        _jobs[run_id] = job
    return {"run_id": run_id}


@app.get("/api/review/{run_id}")
async def get_review_status(run_id: str) -> dict[str, Any]:
    async with _jobs_lock:
        job = _jobs.get(run_id)

    if job:
        return _job_status_payload(job)

    run_dir = OUTPUTS_ROOT / run_id
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail=f"run_id not found: {run_id}")

    return _persisted_status_payload(run_id, run_dir)


@app.get("/api/review/{run_id}/progress/stream")
async def stream_review_progress(run_id: str) -> StreamingResponse:
    async with _jobs_lock:
        job = _jobs.get(run_id)

    run_dir = OUTPUTS_ROOT / run_id
    if job is None and not run_dir.exists():
        raise HTTPException(status_code=404, detail=f"run_id not found: {run_id}")

    broadcaster = ProgressBroadcaster()

    async def event_stream():
        terminal_payload = _terminal_payload_for_job(job) if job is not None else None
        if terminal_payload is None and job is None and run_dir.exists():
            terminal_payload = _terminal_payload_for_run_dir(
                run_id,
                run_dir,
                persisted_status_payload=_persisted_status_payload,
            )
        if terminal_payload is not None:
            yield broadcaster.encode_event(terminal_payload)
            return

        async for event in broadcaster.subscribe(run_id):
            yield event

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/review/{run_id}/clarification")
async def submit_review_clarification(run_id: str, payload: ClarificationAnswerRequest) -> dict[str, Any]:
    try:
        return answer_review_clarification(
            run_id=run_id,
            answers=[item.model_dump(mode="python") for item in payload.answers],
            outputs_root=OUTPUTS_ROOT,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "run_not_found", "message": str(exc)},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "clarification_unavailable", "message": str(exc), "run_id": run_id},
        ) from exc
    except TypeError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "invalid_clarification_payload", "message": str(exc), "run_id": run_id},
        ) from exc


@app.get("/api/review/{run_id}/result")
async def get_review_result(run_id: str) -> dict[str, Any]:
    try:
        return get_review_result_payload(run_id=run_id, outputs_root=OUTPUTS_ROOT)
    except ReviewRunNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "run_not_found", "message": str(exc)},
        ) from exc
    except ReviewResultNotReadyError as exc:
        async with _jobs_lock:
            job = _jobs.get(run_id)

        detail = _result_unavailable_detail(run_id, job, outputs_root=OUTPUTS_ROOT)
        if detail.get("code") == "result_not_ready":
            detail["message"] = str(exc)
        raise HTTPException(status_code=409, detail=detail) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=500,
            detail={"code": "invalid_report_content", "message": str(exc)},
        ) from exc


@app.get("/api/review/{run_id}/artifacts/{artifact_key}")
async def get_review_artifact_preview(run_id: str, artifact_key: str) -> dict[str, Any]:
    try:
        return get_review_artifact_preview_payload(
            run_id=run_id,
            artifact_key=artifact_key,
            outputs_root=OUTPUTS_ROOT,
        )
    except ReviewRunNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "run_not_found", "message": str(exc)},
        ) from exc
    except ReviewResultNotReadyError as exc:
        async with _jobs_lock:
            job = _jobs.get(run_id)

        detail = _result_unavailable_detail(run_id, job, outputs_root=OUTPUTS_ROOT)
        if detail.get("code") == "result_not_ready":
            detail["message"] = str(exc)
        raise HTTPException(status_code=409, detail=detail) from exc
    except ReviewArtifactNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "artifact_not_found", "message": str(exc), "run_id": run_id},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=500,
            detail={"code": "invalid_artifact_preview", "message": str(exc), "run_id": run_id},
        ) from exc


@app.get("/api/compare")
async def compare_review_runs(run_a: str = Query(...), run_b: str = Query(...)) -> dict[str, Any]:
    try:
        return compare_runs(run_id_a=run_a, run_id_b=run_b, outputs_root=OUTPUTS_ROOT).model_dump(mode="json")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"code": "run_not_found", "message": str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "invalid_compare_request", "message": str(exc)}) from exc


@app.get("/api/trends")
async def get_review_trends(limit: int = Query(default=20, ge=1, le=200)) -> dict[str, Any]:
    return get_trend_data(outputs_root=OUTPUTS_ROOT, limit=limit).model_dump(mode="json")


@app.get("/api/stats")
async def get_review_stats() -> dict[str, Any]:
    return get_run_stats_summary(outputs_root=OUTPUTS_ROOT).model_dump(mode="json")


@app.get("/api/report/{run_id}")
async def get_report(run_id: str, format: Literal["md", "json", "html", "csv"] = Query(default="md")) -> Response:
    run_dir = OUTPUTS_ROOT / run_id
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail=f"run_id not found: {run_id}")

    if format in {"md", "json"}:
        filename = "report.md" if format == "md" else "report.json"
        path = run_dir / filename
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"{filename} not found for run_id={run_id}")

        media_type = "text/markdown; charset=utf-8" if format == "md" else "application/json"
        return FileResponse(path=str(path), media_type=media_type, filename=filename)

    report_payload = _load_report_payload(run_dir)
    report_md_path = run_dir / "report.md"
    if not report_md_path.exists() and format == "html":
        raise HTTPException(status_code=404, detail=f"report.md not found for run_id={run_id}")

    if format == "html":
        report_md = report_md_path.read_text(encoding="utf-8")
        html_content = _build_report_html(
            run_id=run_id,
            report_payload=report_payload,
            report_md=report_md,
            run_dir=run_dir,
        )
        return Response(
            content=html_content,
            media_type="text/html; charset=utf-8",
            headers={"Content-Disposition": 'inline; filename="report.html"'},
        )

    csv_content = _build_report_csv(report_payload)
    return Response(
        content=csv_content.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="report.csv"'},
    )


if FRONTEND_DIST_ROOT.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST_ROOT, html=True), name="frontend")
