"""Reviewer agent — LangGraph node that evaluates each parsed requirement
on clarity, testability, and ambiguity.

parsed_items  →  review_results
"""

from __future__ import annotations

import json
import time
from typing import Any

import json_repair
from langchain_community.adapters.openai import convert_openai_messages
from langchain_core.utils.json import parse_json_markdown

from gpt_researcher.config.config import Config
from gpt_researcher.utils.llm import create_chat_completion

from ..prompts import REVIEWER_SYSTEM_PROMPT, REVIEWER_USER_PROMPT
from ..state import ReviewState


async def run(state: ReviewState) -> ReviewState:
    """Review every item in *parsed_items* and produce *review_results*.

    Each result contains ``is_clear``, ``is_testable``, ``is_ambiguous``,
    a list of concrete ``issues``, and actionable ``suggestions``.

    Returns a partial state update with *review_results* and *trace*.
    On failure the results list is empty and the trace carries the error.
    """
    start = time.time()
    parsed_items: list[dict] = state.get("parsed_items", [])
    trace: dict[str, Any] = dict(state.get("trace", {}))

    if not parsed_items:
        trace["reviewer"] = {
            "elapsed_seconds": 0.0,
            "error": "parsed_items is empty — nothing to review",
        }
        return {"review_results": [], "trace": trace}

    items_json = json.dumps(parsed_items, ensure_ascii=False, indent=2)

    messages = convert_openai_messages([
        {"role": "system", "content": REVIEWER_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": REVIEWER_USER_PROMPT.format(items_json=items_json),
        },
    ])

    try:
        cfg = Config()
        raw = await create_chat_completion(
            model=cfg.smart_llm_model,
            messages=messages,
            temperature=0,
            llm_provider=cfg.smart_llm_provider,
            llm_kwargs=cfg.llm_kwargs,
        )

        parsed: dict = parse_json_markdown(raw, parser=json_repair.loads)
        review_results: list[dict] = parsed.get("review_results", [])

        elapsed = round(time.time() - start, 3)
        trace["reviewer"] = {
            "elapsed_seconds": elapsed,
            "result_count": len(review_results),
        }
        return {"review_results": review_results, "trace": trace}

    except Exception as exc:
        elapsed = round(time.time() - start, 3)
        trace["reviewer"] = {
            "elapsed_seconds": elapsed,
            "error": str(exc),
        }
        return {"review_results": [], "trace": trace}
