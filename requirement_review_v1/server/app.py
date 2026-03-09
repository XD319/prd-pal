from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, model_validator

from requirement_review_v1.monitoring import query_audit_events
from requirement_review_v1.run_review import make_run_id
from requirement_review_v1.service.review_service import (
    ReviewResultNotReadyError,
    ReviewRunNotFoundError,
    classify_review_input_error,
    get_review_result_payload,
    review_prd_text_async,
)
from requirement_review_v1.service.report_service import RUN_ID_PATTERN
from requirement_review_v1.templates import TemplateRegistryError, list_template_records

OUTPUTS_ROOT = Path("outputs")
PRIMARY_NODES = ("parser", "planner", "risk", "reviewer", "reporter")
TRACKED_NODES = ("parser", "clarify", "planner", "risk", "reviewer", "route_decider", "reporter")
RUN_LIST_ARTIFACTS: dict[str, str] = {
    "report_md": "report.md",
    "report_json": "report.json",
    "run_trace": "run_trace.json",
    "review_report_json": "review_report.json",
    "risk_items_json": "risk_items.json",
    "open_questions_json": "open_questions.json",
    "review_summary_md": "review_summary.md",
}


def _run_id_to_datetime(run_id: str) -> datetime | None:
    normalized = str(run_id or "").strip()
    if not RUN_ID_PATTERN.fullmatch(normalized):
        return None
    return datetime.strptime(normalized, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)


def _timestamp_to_iso(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def _safe_iso_to_datetime(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value or "").strip())
    except ValueError:
        return None


def _artifact_presence(run_dir: Path) -> dict[str, bool]:
    return {key: (run_dir / filename).exists() for key, filename in RUN_LIST_ARTIFACTS.items()}


def _latest_run_timestamp(run_dir: Path) -> float:
    timestamps = [run_dir.stat().st_mtime]
    for child in run_dir.iterdir():
        try:
            timestamps.append(child.stat().st_mtime)
        except OSError:
            continue
    return max(timestamps)


def _build_run_list_entry(run_dir: Path, job: JobRecord | None = None) -> dict[str, Any]:
    run_id = run_dir.name
    artifacts = _artifact_presence(run_dir)
    created_dt = _safe_iso_to_datetime(job.created_at) if job else None
    if created_dt is None:
        created_dt = _run_id_to_datetime(run_id)
    created_at = created_dt.isoformat() if created_dt else _timestamp_to_iso(run_dir.stat().st_ctime)

    updated_dt = _safe_iso_to_datetime(job.updated_at) if job else None
    updated_at = updated_dt.isoformat() if updated_dt else _timestamp_to_iso(_latest_run_timestamp(run_dir))

    status = job.status if job else ("completed" if artifacts["report_json"] else "running")
    return {
        "run_id": run_id,
        "status": status,
        "created_at": created_at,
        "updated_at": updated_at,
        "artifact_presence": artifacts,
    }


def _run_sort_timestamp(run_dir: Path, job: JobRecord | None = None) -> float:
    if job is not None:
        created_dt = _safe_iso_to_datetime(job.created_at)
        if created_dt is not None:
            return created_dt.timestamp()
    run_dt = _run_id_to_datetime(run_dir.name)
    if run_dt is not None:
        return run_dt.timestamp()
    return _latest_run_timestamp(run_dir)


class ReviewCreateRequest(BaseModel):
    prd_text: str | None = None
    prd_path: str | None = None
    source: str | None = None

    @model_validator(mode="after")
    def _validate_input(self) -> "ReviewCreateRequest":
        has_source = bool(self.source and self.source.strip())
        if has_source:
            return self

        has_text = bool(self.prd_text and self.prd_text.strip())
        has_path = bool(self.prd_path and self.prd_path.strip())
        if has_text == has_path:
            raise ValueError("Provide source, or exactly one of prd_text or prd_path.")
        return self


@dataclass
class JobRecord:
    run_id: str
    run_dir: Path
    status: Literal["queued", "running", "completed", "failed"] = "queued"
    current_node: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    error: str = ""
    error_code: str = ""
    report_paths: dict[str, str] = field(default_factory=dict)
    node_progress: dict[str, dict[str, Any]] = field(
        default_factory=lambda: {name: {"status": "pending", "runs": 0} for name in TRACKED_NODES}
    )
    task: asyncio.Task[Any] | None = None

    def as_progress_payload(self) -> dict[str, Any]:
        completed_primary = sum(
            1
            for node_name in PRIMARY_NODES
            if self.node_progress.get(node_name, {}).get("status") == "completed"
        )
        percent = int((completed_primary / len(PRIMARY_NODES)) * 100)
        if self.status in ("queued", "running"):
            percent = min(percent, 99)
        if self.status == "completed":
            percent = 100
        return {
            "percent": percent,
            "current_node": self.current_node,
            "nodes": self.node_progress,
            "updated_at": self.updated_at,
            "error": self.error,
        }


app = FastAPI(title="Requirement Review V2 API", version="2.0")
_jobs: dict[str, JobRecord] = {}
_jobs_lock = asyncio.Lock()


def _resolve_review_inputs(payload: ReviewCreateRequest) -> dict[str, str | None]:
    if payload.source and payload.source.strip():
        return {"prd_text": None, "prd_path": None, "source": payload.source.strip()}

    if payload.prd_text:
        return {"prd_text": payload.prd_text, "prd_path": None, "source": None}

    if not payload.prd_path:
        raise HTTPException(status_code=400, detail="Missing prd_path")

    prd_file = Path(payload.prd_path).expanduser()
    if not prd_file.is_absolute():
        prd_file = Path.cwd() / prd_file
    if not prd_file.exists() or not prd_file.is_file():
        raise HTTPException(status_code=404, detail=f"PRD file not found: {prd_file}")
    return {"prd_text": None, "prd_path": str(prd_file), "source": None}


def _apply_progress_event(job: JobRecord, event: str, node_name: str, state: dict[str, Any]) -> None:
    now = datetime.now(timezone.utc).isoformat()
    node = job.node_progress.setdefault(node_name, {"status": "pending", "runs": 0})
    if event == "start":
        job.current_node = node_name
        node["status"] = "running"
        node["runs"] = int(node.get("runs", 0) or 0) + 1
        node["last_start"] = now
    elif event == "end":
        trace = state.get("trace", {}) if isinstance(state, dict) else {}
        node_status = "completed"
        if isinstance(trace, dict):
            trace_status = trace.get(node_name, {}).get("status")
            if isinstance(trace_status, str) and trace_status:
                node_status = "completed" if trace_status in ("ok", "success") else "failed"
        node["status"] = node_status
        node["last_end"] = now
        if node_status == "failed":
            job.error = f"node failed: {node_name}"
    job.updated_at = now


def _read_trace_progress(run_dir: Path) -> dict[str, Any] | None:
    trace_path = run_dir / "run_trace.json"
    if not trace_path.exists():
        return None
    try:
        trace_data = json.loads(trace_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(trace_data, dict):
        return None

    nodes = {name: {"status": "pending", "runs": 0} for name in TRACKED_NODES}
    for node_name in TRACKED_NODES:
        node_trace = trace_data.get(node_name)
        if not isinstance(node_trace, dict):
            continue
        status = node_trace.get("status", "ok")
        nodes[node_name] = {
            "status": "completed" if status in ("ok", "success") else "failed",
            "runs": 1,
            "last_start": node_trace.get("start"),
            "last_end": node_trace.get("end"),
        }
    return nodes


async def _run_job(
    job: JobRecord,
    *,
    prd_text: str | None = None,
    prd_path: str | None = None,
    source: str | None = None,
) -> None:
    job.status = "running"
    job.error = ""
    job.error_code = ""
    job.updated_at = datetime.now(timezone.utc).isoformat()
    try:
        summary = await review_prd_text_async(
            prd_text=prd_text,
            prd_path=prd_path,
            source=source,
            run_id=job.run_id,
            config_overrides={
                "outputs_root": OUTPUTS_ROOT,
                "progress_hook": lambda event, node, state: _apply_progress_event(job, event, node, state),
            },
        )
        job.status = summary.status
        job.current_node = ""
        job.report_paths = summary.to_report_paths()
    except Exception as exc:
        job.status = "failed"
        classified_error = classify_review_input_error(exc)
        job.error_code = classified_error.code if classified_error is not None else "INTERNAL_ERROR"
        job.error = classified_error.message if classified_error is not None else str(exc)
        job.current_node = ""
    finally:
        job.updated_at = datetime.now(timezone.utc).isoformat()


@app.on_event("startup")
async def _load_env() -> None:
    load_dotenv()


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
        runs.append((_run_sort_timestamp(run_dir, job), run_dir.name, _build_run_list_entry(run_dir, job)))

    runs.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return {"count": len(runs), "runs": [item[2] for item in runs]}


@app.post("/api/review")
async def create_review(payload: ReviewCreateRequest) -> dict[str, str]:
    review_inputs = _resolve_review_inputs(payload)
    run_id = make_run_id()
    run_dir = OUTPUTS_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    job = JobRecord(run_id=run_id, run_dir=run_dir)
    task = asyncio.create_task(_run_job(job, **review_inputs))
    job.task = task

    async with _jobs_lock:
        _jobs[run_id] = job
    return {"run_id": run_id}


@app.get("/api/review/{run_id}")
async def get_review_status(run_id: str) -> dict[str, Any]:
    async with _jobs_lock:
        job = _jobs.get(run_id)

    if job:
        payload = {
            "run_id": run_id,
            "status": job.status,
            "progress": job.as_progress_payload(),
            "report_paths": job.report_paths,
        }
        if job.error_code:
            payload["error"] = {"code": job.error_code, "message": job.error}
        return payload

    run_dir = OUTPUTS_ROOT / run_id
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail=f"run_id not found: {run_id}")

    report_md = run_dir / "report.md"
    report_json = run_dir / "report.json"
    trace_nodes = _read_trace_progress(run_dir)
    completed = report_md.exists() and report_json.exists()
    return {
        "run_id": run_id,
        "status": "completed" if completed else "running",
        "progress": {
            "percent": 100 if completed else 0,
            "current_node": "",
            "nodes": trace_nodes or {},
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "error": "",
        },
        "report_paths": {
            "report_md": str(report_md),
            "report_json": str(report_json),
            "run_trace": str(run_dir / "run_trace.json"),
        },
    }


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

        status = job.status if job else "running"
        if status in {"queued", "running"}:
            detail = {
                "code": "result_not_ready",
                "message": str(exc),
                "run_id": run_id,
                "status": status,
            }
        else:
            detail = {
                "code": job.error_code if job and job.error_code else "result_unavailable",
                "message": job.error if job and job.error else f"review result unavailable for run_id={run_id}",
                "run_id": run_id,
                "status": status,
            }
        if job:
            detail["progress"] = job.as_progress_payload()
            if job.error_code:
                detail["error"] = {"code": job.error_code, "message": job.error}
        raise HTTPException(status_code=409, detail=detail) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=500,
            detail={"code": "invalid_report_content", "message": str(exc)},
        ) from exc


@app.get("/api/report/{run_id}")
async def get_report(run_id: str, format: Literal["md", "json"] = Query(default="md")) -> FileResponse:
    run_dir = OUTPUTS_ROOT / run_id
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail=f"run_id not found: {run_id}")

    filename = "report.md" if format == "md" else "report.json"
    path = run_dir / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"{filename} not found for run_id={run_id}")

    media_type = "text/markdown; charset=utf-8" if format == "md" else "application/json"
    return FileResponse(path=str(path), media_type=media_type, filename=filename)
