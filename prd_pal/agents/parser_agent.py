"""Parser agent LangGraph node that decomposes a requirement document into structured items.

requirement_doc -> parsed_items
"""

from __future__ import annotations

import os
from typing import Any

from review_runtime.config.config import Config

from ..prompt_quality.context_trimmer import trim_context_for_node
from ..prompt_registry import load_prompt_template
from ..prompts import (
    CLARIFY_PARSER_SYSTEM_PROMPT,
    CLARIFY_PARSER_USER_PROMPT,
    PARSER_SYSTEM_PROMPT,
    PARSER_USER_PROMPT,
)
from ..schemas import ParserOutput, validate_parser_output
from ..state import ReviewState
from ..templates.registry import CLARIFY_PARSER_REVIEW_PROMPT, PARSER_REVIEW_PROMPT
from ..utils.io import save_raw_agent_output
from ..utils.llm_structured_call import StructuredCallError, llm_structured_call
from ..utils.logging import get_logger
from ..utils.trace import trace_start

_AGENT = "parser"
_DEFAULT_PROMPT_VERSION = PARSER_REVIEW_PROMPT.version
_CLARIFY_PROMPT_VERSION = CLARIFY_PARSER_REVIEW_PROMPT.version
log = get_logger(_AGENT)


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
    log.info("开始解析", extra={"node": _AGENT})

    span = trace_start(_AGENT, input_chars=len(requirement_doc))

    if prompt_version == _CLARIFY_PROMPT_VERSION:
        prompt_template = CLARIFY_PARSER_REVIEW_PROMPT
        system_prompt = CLARIFY_PARSER_SYSTEM_PROMPT
        user_prompt = CLARIFY_PARSER_USER_PROMPT
    else:
        prompt_template = PARSER_REVIEW_PROMPT
        try:
            record = load_prompt_template(_AGENT)
            system_prompt = record.system_prompt
            user_prompt = record.user_prompt_template.replace("{input_text}", "{requirement_doc}")
        except Exception:
            system_prompt = PARSER_SYSTEM_PROMPT
            user_prompt = PARSER_USER_PROMPT
    span.set_template(prompt_template)

    trimmed_context = trim_context_for_node(_AGENT, requirement_doc)
    if trimmed_context.was_trimmed:
        span.set_attr("trimmed_context", True)
        span.set_attr("original_input_chars", trimmed_context.original_chars)
        span.set_attr("trimmed_input_chars", trimmed_context.trimmed_chars)
        requirement_doc = trimmed_context.text

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

        parsed_items = output.get("parsed_items", [])
        log.info("解析完成, %s 条需求", len(parsed_items), extra={"node": _AGENT})
        return {"parsed_items": parsed_items, "trace": trace}

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
        log.warning("解析完成, %s 条需求", 0, extra={"node": _AGENT})
        return {"parsed_items": [], "trace": trace}

    except Exception as exc:
        raw_path = save_raw_agent_output(run_dir, _AGENT, raw) if run_dir and raw else ""
        trace[_AGENT] = span.end(
            status="error",
            output_chars=len(raw),
            raw_output_path=raw_path,
            error_message=str(exc),
        )
        log.warning("解析完成, %s 条需求", 0, extra={"node": _AGENT})
        return {"parsed_items": [], "trace": trace}
