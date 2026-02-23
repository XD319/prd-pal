"""Reviewer agent — LangGraph node that evaluates each parsed requirement
on clarity, testability, and ambiguity.

parsed_items  →  review_results
"""

from __future__ import annotations

import json
from typing import Any

import json_repair
from langchain_community.adapters.openai import convert_openai_messages
from langchain_core.utils.json import parse_json_markdown

from gpt_researcher.config.config import Config
from gpt_researcher.utils.llm import create_chat_completion

from ..prompts import REVIEWER_SYSTEM_PROMPT, REVIEWER_USER_PROMPT
from ..state import ReviewState
from ..utils.io import save_raw_agent_output
from ..utils.trace import trace_start

_AGENT = "reviewer"


async def run(state: ReviewState) -> ReviewState:
    """Review every item in *parsed_items* and produce *review_results*.

    Each result contains ``is_clear``, ``is_testable``, ``is_ambiguous``,
    a list of concrete ``issues``, and actionable ``suggestions``.

    Returns a partial state update with *review_results* and *trace*.
    On failure the results list is empty and the trace carries the error.
    """
    parsed_items: list[dict] = state.get("parsed_items", [])
    trace: dict[str, Any] = dict(state.get("trace", {}))
    run_dir: str = state.get("run_dir", "")
    raw = ""

    if not parsed_items:
        span = trace_start(_AGENT, model="none", input_chars=0)
        trace[_AGENT] = span.end(
            status="error",
            error_message="parsed_items is empty — nothing to review",
        )
        return {"review_results": [], "trace": trace}

    items_json = json.dumps(parsed_items, ensure_ascii=False, indent=2)
    span = trace_start(_AGENT, input_chars=len(items_json))

    messages = convert_openai_messages([
        {"role": "system", "content": REVIEWER_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": REVIEWER_USER_PROMPT.format(items_json=items_json),
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
        review_results: list[dict] = parsed.get("review_results", [])

        if "review_results" not in parsed:
            raw_path = save_raw_agent_output(run_dir, _AGENT, raw) if run_dir and raw else ""
            trace[_AGENT] = span.end(
                status="error",
                output_chars=len(raw),
                raw_output_path=raw_path,
                error_message="key 'review_results' missing after json repair",
            )
        else:
            trace[_AGENT] = span.end(status="ok", output_chars=len(raw))

        return {"review_results": review_results, "trace": trace}

    except Exception as exc:
        raw_path = save_raw_agent_output(run_dir, _AGENT, raw) if run_dir and raw else ""
        trace[_AGENT] = span.end(
            status="error",
            output_chars=len(raw),
            raw_output_path=raw_path,
            error_message=str(exc),
        )
        return {"review_results": [], "trace": trace}
