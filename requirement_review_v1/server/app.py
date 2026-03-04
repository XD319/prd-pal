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

from requirement_review_v1.run_review import make_run_id, run_review

OUTPUTS_ROOT = Path("outputs")
PRIMARY_NODES = ("parser", "planner", "risk", "reviewer", "reporter")
TRACKED_NODES = ("parser", "clarify", "planner", "risk", "reviewer", "route_decider", "reporter")


class ReviewCreateRequest(BaseModel):
    prd_text: str | None = None
    prd_path: str | None = None

    @model_validator(mode="after")
    def _validate_input(self) -> "ReviewCreateRequest":
        has_text = bool(self.prd_text and self.prd_text.strip())
        has_path = bool(self.prd_path and self.prd_path.strip())
        if has_text == has_path:
            raise ValueError("Exactly one of prd_text or prd_path must be provided.")
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


def _resolve_input_text(payload: ReviewCreateRequest) -> str:
    if payload.prd_text:
        return payload.prd_text
    if not payload.prd_path:
        raise HTTPException(status_code=400, detail="Missing prd_path")

    prd_file = Path(payload.prd_path).expanduser()
    if not prd_file.is_absolute():
        prd_file = Path.cwd() / prd_file
    if not prd_file.exists() or not prd_file.is_file():
        raise HTTPException(status_code=404, detail=f"PRD file not found: {prd_file}")
    return prd_file.read_text(encoding="utf-8")


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
    for node_name, node_trace in trace_data.items():
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


async def _run_job(job: JobRecord, requirement_doc: str) -> None:
    job.status = "running"
    job.updated_at = datetime.now(timezone.utc).isoformat()
    try:
        result = await run_review(
            requirement_doc=requirement_doc,
            run_id=job.run_id,
            outputs_root=OUTPUTS_ROOT,
            progress_hook=lambda event, node, state: _apply_progress_event(job, event, node, state),
        )
        job.status = "completed"
        job.current_node = ""
        job.report_paths = result["report_paths"]
    except Exception as exc:
        job.status = "failed"
        job.error = str(exc)
        job.current_node = ""
    finally:
        job.updated_at = datetime.now(timezone.utc).isoformat()


@app.on_event("startup")
async def _load_env() -> None:
    load_dotenv()


@app.post("/api/review")
async def create_review(payload: ReviewCreateRequest) -> dict[str, str]:
    requirement_doc = _resolve_input_text(payload)
    run_id = make_run_id()
    run_dir = OUTPUTS_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    job = JobRecord(run_id=run_id, run_dir=run_dir)
    task = asyncio.create_task(_run_job(job, requirement_doc))
    job.task = task

    async with _jobs_lock:
        _jobs[run_id] = job
    return {"run_id": run_id}


@app.get("/api/review/{run_id}")
async def get_review_status(run_id: str) -> dict[str, Any]:
    async with _jobs_lock:
        job = _jobs.get(run_id)

    if job:
        return {
            "run_id": run_id,
            "status": job.status,
            "progress": job.as_progress_payload(),
            "report_paths": job.report_paths,
        }

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
