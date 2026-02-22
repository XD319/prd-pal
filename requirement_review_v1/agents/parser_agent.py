"""Parser agent — LangGraph node that decomposes a requirement document
into structured items.

requirement_doc  →  parsed_items
"""

from __future__ import annotations

import time
from typing import Any

import json_repair
from langchain_community.adapters.openai import convert_openai_messages
from langchain_core.utils.json import parse_json_markdown

from gpt_researcher.config.config import Config
from gpt_researcher.utils.llm import create_chat_completion

from ..prompts import PARSER_SYSTEM_PROMPT, PARSER_USER_PROMPT
from ..state import ReviewState


async def run(state: ReviewState) -> ReviewState:
    """Parse *requirement_doc* into a list of structured requirement items.

    Returns a partial state update containing *parsed_items* and *trace*.
    On any failure the items list is empty and the trace carries the error.
    """
    start = time.time()
    requirement_doc: str = state.get("requirement_doc", "")
    trace: dict[str, Any] = dict(state.get("trace", {}))

    messages = convert_openai_messages([
        {"role": "system", "content": PARSER_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": PARSER_USER_PROMPT.format(requirement_doc=requirement_doc),
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
        parsed_items: list[dict] = parsed.get("parsed_items", [])

        elapsed = round(time.time() - start, 3)
        trace["parser"] = {
            "elapsed_seconds": elapsed,
            "item_count": len(parsed_items),
        }
        return {"parsed_items": parsed_items, "trace": trace}

    except Exception as exc:
        elapsed = round(time.time() - start, 3)
        trace["parser"] = {
            "elapsed_seconds": elapsed,
            "error": str(exc),
        }
        return {"parsed_items": [], "trace": trace}
