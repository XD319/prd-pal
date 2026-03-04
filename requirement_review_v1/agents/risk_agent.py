"""Risk agent — LangGraph node that identifies delivery risks from the
planner's output.

tasks + milestones + dependencies + estimation  →  risks
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

from gpt_researcher.config.config import Config

from ..prompts import RISK_SYSTEM_PROMPT, RISK_USER_PROMPT
from ..schemas import RiskOutput, validate_risk_output
from ..state import ReviewState
from ..tools.risk_catalog_search import search_risk_catalog
from ..utils.io import save_raw_agent_output
from ..utils.llm_structured_call import StructuredCallError, llm_structured_call
from ..utils.trace import trace_start

_AGENT = "risk"
_RISK_TOOL_ENV = "RISK_AGENT_ENABLE_CATALOG_TOOL"
_RISK_TOOL_TOP_K_ENV = "RISK_AGENT_CATALOG_TOP_K"


def _env_enabled(name: str, default: bool = True) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def _plan_query(tasks: list[dict], milestones: list[dict], estimation: dict) -> str:
    task_titles = "; ".join(str(t.get("title", "")) for t in tasks[:20] if t.get("title"))
    owners = ", ".join(sorted({str(t.get("owner", "")).strip() for t in tasks if t.get("owner")}))
    milestone_titles = "; ".join(
        str(m.get("title", "")) for m in milestones[:10] if m.get("title")
    )
    total_days = estimation.get("total_days", "")
    buffer_days = estimation.get("buffer_days", "")
    return (
        f"tasks: {task_titles}\n"
        f"owners: {owners}\n"
        f"milestones: {milestone_titles}\n"
        f"total_days: {total_days}, buffer_days: {buffer_days}"
    )


def _evidence_for_prompt(hits: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "id": str(item.get("id", "")),
            "title": str(item.get("title", "")),
            "snippet": str(item.get("snippet", "")),
        }
        for item in hits
    ]


def _attach_fallback_evidence(
    risks: list[dict[str, Any]],
    evidence_hits: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    fallback_ids = [str(hit.get("id", "")) for hit in evidence_hits[:2] if hit.get("id")]
    fallback_snippets = [str(hit.get("snippet", "")) for hit in evidence_hits[:2] if hit.get("snippet")]
    for risk in risks:
        risk.setdefault("evidence_ids", [])
        risk.setdefault("evidence_snippets", [])
        if evidence_hits and not risk["evidence_ids"]:
            risk["evidence_ids"] = fallback_ids
        if evidence_hits and not risk["evidence_snippets"]:
            risk["evidence_snippets"] = fallback_snippets
    return risks


async def run(state: ReviewState) -> ReviewState:
    """Identify delivery risks from the planner's output.

    Returns a partial state update with *risks* and *trace*.
    On failure the risks list is empty and the trace carries the error.
    """
    tasks: list[dict] = state.get("tasks", [])
    milestones: list[dict] = state.get("milestones", [])
    dependencies: list[dict] = state.get("dependencies", [])
    estimation: dict = state.get("estimation", {})
    trace: dict[str, Any] = dict(state.get("trace", {}))
    run_dir: str = state.get("run_dir", "")
    raw = ""

    plan_data = {
        "tasks": tasks,
        "milestones": milestones,
        "dependencies": dependencies,
        "estimation": estimation,
    }

    if not tasks:
        span = trace_start(_AGENT, model="none", input_chars=0)
        trace[_AGENT] = span.end(
            status="error",
            error_message="tasks is empty — nothing to assess",
        )
        return {"risks": [], "trace": trace}

    plan_json = json.dumps(plan_data, ensure_ascii=False, indent=2)
    span = trace_start(_AGENT, input_chars=len(plan_json))

    tool_enabled = _env_enabled(_RISK_TOOL_ENV, default=True)
    top_k_raw = os.getenv(_RISK_TOOL_TOP_K_ENV, "5")
    try:
        top_k = max(1, int(top_k_raw))
    except ValueError:
        top_k = 5

    evidence_hits: list[dict[str, Any]] = []
    tool_meta: dict[str, Any] = {"risk_catalog_tool_enabled": tool_enabled, "risk_catalog_tool_top_k": top_k}
    query = _plan_query(tasks, milestones, estimation)
    if tool_enabled:
        t0 = time.perf_counter()
        try:
            evidence_hits = search_risk_catalog(query, top_k=top_k)
            duration_ms = int((time.perf_counter() - t0) * 1000)
            tool_meta.update(
                {
                    "risk_catalog_tool_status": "ok",
                    "risk_catalog_tool_duration_ms": duration_ms,
                    "risk_catalog_hits": len(evidence_hits),
                    "risk_catalog_top_ids": [
                        str(item.get("id", "")) for item in evidence_hits if item.get("id")
                    ],
                }
            )
        except Exception as exc:
            duration_ms = int((time.perf_counter() - t0) * 1000)
            tool_meta.update(
                {
                    "risk_catalog_tool_status": "degraded_error",
                    "risk_catalog_tool_duration_ms": duration_ms,
                    "risk_catalog_hits": 0,
                    "risk_catalog_top_ids": [],
                    "risk_catalog_tool_error": str(exc),
                }
            )
    else:
        tool_meta.update(
            {
                "risk_catalog_tool_status": "degraded_disabled",
                "risk_catalog_tool_duration_ms": 0,
                "risk_catalog_hits": 0,
                "risk_catalog_top_ids": [],
                "risk_catalog_tool_reason": (
                    f"disabled by env {_RISK_TOOL_ENV}; evidence retrieval skipped"
                ),
            }
        )
    span.set_attrs(tool_meta)

    evidence_json = json.dumps(_evidence_for_prompt(evidence_hits), ensure_ascii=False, indent=2)
    prompt = f"{RISK_SYSTEM_PROMPT}\n\n{RISK_USER_PROMPT.format(plan_json=plan_json, evidence_json=evidence_json)}"

    try:
        cfg = Config()
        span.model = cfg.smart_llm_model or "unknown"

        call_meta: dict[str, Any] = {
            "agent_name": _AGENT,
            "run_id": os.path.basename(run_dir) if run_dir else "",
        }
        parsed = await llm_structured_call(
            prompt=prompt,
            schema=RiskOutput,
            metadata=call_meta,
        )
        span.set_attr("structured_mode", call_meta.get("structured_mode", "unknown"))
        raw = str(call_meta.get("raw_output", "") or "")
        try:
            validated = validate_risk_output(parsed)
            output = validated.model_dump(mode="python")
            output["risks"] = _attach_fallback_evidence(output.get("risks", []), evidence_hits)
            trace[_AGENT] = span.end(status="ok", output_chars=len(raw))
        except Exception as exc:
            raw_path = save_raw_agent_output(run_dir, _AGENT, raw) if run_dir and raw else ""
            output = RiskOutput().model_dump(mode="python")
            trace[_AGENT] = span.end(
                status="error",
                output_chars=len(raw),
                raw_output_path=raw_path,
                error_message=f"schema validation failed: {exc}",
            )

        return {"risks": output.get("risks", []), "trace": trace}

    except StructuredCallError as exc:
        raw = exc.raw_output or raw
        span.set_attr("structured_mode", exc.structured_mode)
        raw_path = save_raw_agent_output(run_dir, _AGENT, raw) if run_dir and raw else ""
        trace[_AGENT] = span.end(
            status="error",
            output_chars=len(raw),
            raw_output_path=raw_path,
            error_message=str(exc),
        )
        return {"risks": [], "trace": trace}

    except Exception as exc:
        raw_path = save_raw_agent_output(run_dir, _AGENT, raw) if run_dir and raw else ""
        trace[_AGENT] = span.end(
            status="error",
            output_chars=len(raw),
            raw_output_path=raw_path,
            error_message=str(exc),
        )
        return {"risks": [], "trace": trace}
