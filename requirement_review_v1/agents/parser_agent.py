"""Parser agent — LangGraph node that decomposes a requirement document
into structured items.

requirement_doc  →  parsed_items
"""

from __future__ import annotations

import os
from typing import Any

from gpt_researcher.config.config import Config

from ..prompts import (
    CLARIFY_PARSER_SYSTEM_PROMPT,
    CLARIFY_PARSER_USER_PROMPT,
    PARSER_SYSTEM_PROMPT,
    PARSER_USER_PROMPT,
)
from ..schemas import ParserOutput, validate_parser_output
from ..state import ReviewState
from ..utils.io import save_raw_agent_output
from ..utils.llm_structured_call import StructuredCallError, llm_structured_call
from ..utils.trace import trace_start

_AGENT = "parser"
_DEFAULT_PROMPT_VERSION = "v1.1"
_CLARIFY_PROMPT_VERSION = "v1.1-clarify"


async def run(state: ReviewState) -> ReviewState:
    """Parse *requirement_doc* into a list of structured requirement items.

    Returns a partial state update containing *parsed_items* and *trace*.
    On any failure the items list is empty and the trace carries the error.
    """
    requirement_doc: str = state.get("requirement_doc", "")
    trace: dict[str, Any] = dict(state.get("trace", {}))
    run_dir: str = state.get("run_dir", "")
    raw = ""
    prompt_version = str(state.get("parser_prompt_version", _DEFAULT_PROMPT_VERSION) or _DEFAULT_PROMPT_VERSION)

    span = trace_start(_AGENT, input_chars=len(requirement_doc))
    span.set_attr("prompt_version", prompt_version)

    if prompt_version == _CLARIFY_PROMPT_VERSION:
        system_prompt = CLARIFY_PARSER_SYSTEM_PROMPT
        user_prompt = CLARIFY_PARSER_USER_PROMPT
    else:
        system_prompt = PARSER_SYSTEM_PROMPT
        user_prompt = PARSER_USER_PROMPT

    prompt = (
        f"{system_prompt}\n\n"
        f"{user_prompt.format(requirement_doc=requirement_doc)}"
    )

    try:
        cfg = Config()
        span.model = cfg.smart_llm_model or "unknown"

        call_meta: dict[str, Any] = {
            "agent_name": _AGENT,
            "run_id": os.path.basename(run_dir) if run_dir else "",
        }
        parsed = await llm_structured_call(
            prompt=prompt,
            schema=ParserOutput,
            metadata=call_meta,
        )
        span.set_attr("structured_mode", call_meta.get("structured_mode", "unknown"))
        raw = str(call_meta.get("raw_output", "") or "")
        try:
            validated = validate_parser_output(parsed)
            output = validated.model_dump(mode="python")
            trace[_AGENT] = span.end(status="ok", output_chars=len(raw))
        except Exception as exc:
            raw_path = save_raw_agent_output(run_dir, _AGENT, raw) if run_dir and raw else ""
            output = ParserOutput().model_dump(mode="python")
            trace[_AGENT] = span.end(
                status="error",
                output_chars=len(raw),
                raw_output_path=raw_path,
                error_message=f"schema validation failed: {exc}",
            )

        return {"parsed_items": output.get("parsed_items", []), "trace": trace}

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
        return {"parsed_items": [], "trace": trace}

    except Exception as exc:
        raw_path = save_raw_agent_output(run_dir, _AGENT, raw) if run_dir and raw else ""
        trace[_AGENT] = span.end(
            status="error",
            output_chars=len(raw),
            raw_output_path=raw_path,
            error_message=str(exc),
        )
        return {"parsed_items": [], "trace": trace}
