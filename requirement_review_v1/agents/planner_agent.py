"""Planner agent node that generates a delivery plan from parsed items."""

from __future__ import annotations

import json
import os
from typing import Any

from gpt_researcher.config.config import Config

from ..prompts import PLANNER_SYSTEM_PROMPT, PLANNER_USER_PROMPT
from ..schemas import PlannerOutput, validate_planner_output
from ..state import ReviewState
from ..utils.io import save_raw_agent_output
from ..utils.llm_structured_call import StructuredCallError, llm_structured_call
from ..utils.trace import trace_start

_AGENT = "planner"


async def run(state: ReviewState) -> ReviewState:
    """Produce a delivery plan from parsed requirement items."""

    parsed_items: list[dict] = state.get("parsed_items", [])
    trace: dict[str, Any] = dict(state.get("trace", {}))
    run_dir: str = state.get("run_dir", "")
    raw = ""

    if not parsed_items:
        span = trace_start(_AGENT, model="none", input_chars=0)
        trace[_AGENT] = span.end(status="error", error_message="parsed_items is empty - nothing to plan")
        return _empty_result(trace)

    items_json = json.dumps(parsed_items, ensure_ascii=False, indent=2)
    span = trace_start(_AGENT, input_chars=len(items_json))
    prompt = f"{PLANNER_SYSTEM_PROMPT}\n\n{PLANNER_USER_PROMPT.format(items_json=items_json)}"

    try:
        cfg = Config()
        span.model = cfg.smart_llm_model or "unknown"

        call_meta: dict[str, Any] = {
            "agent_name": _AGENT,
            "run_id": os.path.basename(run_dir) if run_dir else "",
        }
        parsed = await llm_structured_call(
            prompt=prompt,
            schema=PlannerOutput,
            metadata=call_meta,
        )
        span.set_attr("structured_mode", call_meta.get("structured_mode", "unknown"))
        raw = str(call_meta.get("raw_output", "") or "")
        try:
            validated = validate_planner_output(parsed)
            output = validated.model_dump(mode="python", by_alias=True)
            trace[_AGENT] = span.end(status="ok", output_chars=len(raw))
        except Exception as exc:
            raw_path = save_raw_agent_output(run_dir, _AGENT, raw) if run_dir and raw else ""
            output = PlannerOutput().model_dump(mode="python", by_alias=True)
            trace[_AGENT] = span.end(
                status="error",
                output_chars=len(raw),
                raw_output_path=raw_path,
                error_message=f"schema validation failed: {exc}",
            )

        return {
            "plan": {
                "tasks": output.get("tasks", []),
                "milestones": output.get("milestones", []),
                "dependencies": output.get("dependencies", []),
                "estimation": output.get("estimation", {}),
            },
            "trace": trace,
        }

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
        return _empty_result(trace)

    except Exception as exc:
        raw_path = save_raw_agent_output(run_dir, _AGENT, raw) if run_dir and raw else ""
        trace[_AGENT] = span.end(
            status="error",
            output_chars=len(raw),
            raw_output_path=raw_path,
            error_message=str(exc),
        )
        return _empty_result(trace)


def _empty_result(trace: dict[str, Any]) -> ReviewState:
    return {
        "plan": {"tasks": [], "milestones": [], "dependencies": [], "estimation": {}},
        "trace": trace,
    }
