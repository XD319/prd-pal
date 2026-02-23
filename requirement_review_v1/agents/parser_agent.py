"""Parser agent — LangGraph node that decomposes a requirement document
into structured items.

requirement_doc  →  parsed_items
"""

from __future__ import annotations

from typing import Any

import json_repair
from langchain_community.adapters.openai import convert_openai_messages
from langchain_core.utils.json import parse_json_markdown

from gpt_researcher.config.config import Config
from gpt_researcher.utils.llm import create_chat_completion

from ..prompts import PARSER_SYSTEM_PROMPT, PARSER_USER_PROMPT
from ..state import ReviewState
from ..utils.io import save_raw_agent_output
from ..utils.trace import trace_start

_AGENT = "parser"


async def run(state: ReviewState) -> ReviewState:
    """Parse *requirement_doc* into a list of structured requirement items.

    Returns a partial state update containing *parsed_items* and *trace*.
    On any failure the items list is empty and the trace carries the error.
    """
    requirement_doc: str = state.get("requirement_doc", "")
    trace: dict[str, Any] = dict(state.get("trace", {}))
    run_dir: str = state.get("run_dir", "")
    raw = ""

    span = trace_start(_AGENT, input_chars=len(requirement_doc))

    messages = convert_openai_messages([
        {"role": "system", "content": PARSER_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": PARSER_USER_PROMPT.format(requirement_doc=requirement_doc),
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
        parsed_items: list[dict] = parsed.get("parsed_items", [])

        if "parsed_items" not in parsed:
            raw_path = save_raw_agent_output(run_dir, _AGENT, raw) if run_dir and raw else ""
            trace[_AGENT] = span.end(
                status="error",
                output_chars=len(raw),
                raw_output_path=raw_path,
                error_message="key 'parsed_items' missing after json repair",
            )
        else:
            trace[_AGENT] = span.end(status="ok", output_chars=len(raw))

        return {"parsed_items": parsed_items, "trace": trace}

    except Exception as exc:
        raw_path = save_raw_agent_output(run_dir, _AGENT, raw) if run_dir and raw else ""
        trace[_AGENT] = span.end(
            status="error",
            output_chars=len(raw),
            raw_output_path=raw_path,
            error_message=str(exc),
        )
        return {"parsed_items": [], "trace": trace}
