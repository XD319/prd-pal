"""Risk agent — LangGraph node that identifies delivery risks from the
planner's output.

tasks + milestones + dependencies + estimation  →  risks
"""

from __future__ import annotations

import json
from typing import Any

import json_repair
from langchain_community.adapters.openai import convert_openai_messages
from langchain_core.utils.json import parse_json_markdown

from gpt_researcher.config.config import Config
from gpt_researcher.utils.llm import create_chat_completion

from ..prompts import RISK_SYSTEM_PROMPT, RISK_USER_PROMPT
from ..schemas import RiskOutput, validate_risk_output
from ..state import ReviewState
from ..utils.io import save_raw_agent_output
from ..utils.trace import trace_start

_AGENT = "risk"


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

    messages = convert_openai_messages([
        {"role": "system", "content": RISK_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": RISK_USER_PROMPT.format(plan_json=plan_json),
        },
    ])

    try:
        cfg = Config()
        span.model = cfg.smart_llm_model or "unknown"

        raw = await create_chat_completion(
            model=cfg.smart_llm_model,
            messages=messages,
            temperature=0,
            llm_provider=cfg.smart_llm_provider,
            llm_kwargs=cfg.llm_kwargs,
        )

        parsed: dict = parse_json_markdown(raw, parser=json_repair.loads)
        try:
            validated = validate_risk_output(parsed)
            output = validated.model_dump(mode="python")
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

    except Exception as exc:
        raw_path = save_raw_agent_output(run_dir, _AGENT, raw) if run_dir and raw else ""
        trace[_AGENT] = span.end(
            status="error",
            output_chars=len(raw),
            raw_output_path=raw_path,
            error_message=str(exc),
        )
        return {"risks": [], "trace": trace}
