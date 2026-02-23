"""Planner agent — LangGraph node that generates a delivery plan from parsed
requirement items.

parsed_items  →  tasks, milestones, dependencies, estimation
"""

from __future__ import annotations

import json
from typing import Any

import json_repair
from langchain_community.adapters.openai import convert_openai_messages
from langchain_core.utils.json import parse_json_markdown

from gpt_researcher.config.config import Config
from gpt_researcher.utils.llm import create_chat_completion

from ..prompts import PLANNER_SYSTEM_PROMPT, PLANNER_USER_PROMPT
from ..state import ReviewState
from ..utils.io import save_raw_agent_output
from ..utils.trace import trace_start

_AGENT = "planner"

_EXPECTED_KEYS = ("tasks", "milestones", "dependencies", "estimation")


async def run(state: ReviewState) -> ReviewState:
    """Produce a delivery plan from *parsed_items*.

    Returns a partial state update with *tasks*, *milestones*,
    *dependencies*, *estimation*, and *trace*.
    On failure every output list/dict is empty and the trace carries the error.
    """
    parsed_items: list[dict] = state.get("parsed_items", [])
    trace: dict[str, Any] = dict(state.get("trace", {}))
    run_dir: str = state.get("run_dir", "")
    raw = ""

    if not parsed_items:
        span = trace_start(_AGENT, model="none", input_chars=0)
        trace[_AGENT] = span.end(
            status="error",
            error_message="parsed_items is empty — nothing to plan",
        )
        return _empty_result(trace)

    items_json = json.dumps(parsed_items, ensure_ascii=False, indent=2)
    span = trace_start(_AGENT, input_chars=len(items_json))

    messages = convert_openai_messages([
        {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": PLANNER_USER_PROMPT.format(items_json=items_json),
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

        missing = [k for k in _EXPECTED_KEYS if k not in parsed]
        if missing:
            raw_path = save_raw_agent_output(run_dir, _AGENT, raw) if run_dir and raw else ""
            trace[_AGENT] = span.end(
                status="error",
                output_chars=len(raw),
                raw_output_path=raw_path,
                error_message=f"keys missing after json repair: {missing}",
            )
        else:
            trace[_AGENT] = span.end(status="ok", output_chars=len(raw))

        return {
            "tasks": parsed.get("tasks", []),
            "milestones": parsed.get("milestones", []),
            "dependencies": parsed.get("dependencies", []),
            "estimation": parsed.get("estimation", {}),
            "trace": trace,
        }

    except Exception as exc:
        raw_path = save_raw_agent_output(run_dir, _AGENT, raw) if run_dir and raw else ""
        trace[_AGENT] = span.end(
            status="error",
            output_chars=len(raw),
            raw_output_path=raw_path,
            error_message=str(exc),
        )
        return _empty_result(trace)


def _empty_result(trace: dict) -> ReviewState:
    return {
        "tasks": [],
        "milestones": [],
        "dependencies": [],
        "estimation": {},
        "trace": trace,
    }
