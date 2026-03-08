"""Reviewer agent node that evaluates requirements and plan coverage."""

from __future__ import annotations

import json
import os
from typing import Any

from review_runtime.config.config import Config

from ..prompts import REVIEWER_SYSTEM_PROMPT, REVIEWER_USER_PROMPT
from ..schemas import ReviewerOutput, validate_reviewer_output
from ..state import ReviewState, plan_from_state
from ..templates.registry import REVIEWER_REVIEW_PROMPT
from ..utils.io import save_raw_agent_output
from ..utils.llm_structured_call import StructuredCallError, llm_structured_call
from ..utils.trace import trace_start

_AGENT = "reviewer"
_VAGUE_TERMS = (
    "fast",
    "quick",
    "quickly",
    "timely",
    "reliable",
    "scalable",
    "user-friendly",
    "significant",
    "dramatic",
    "highly secure",
    "real time",
    "real-time",
    "fairness",
    "fair",
    "transparent",
    "transparency",
    "personalized",
    "improve outcomes",
    "from day one",
    "no manual intervention",
    "good",
    "better",
)


def _is_high_risk(result: dict[str, Any]) -> bool:
    flags = sum(
        [
            not result.get("is_clear", True),
            not result.get("is_testable", True),
            result.get("is_ambiguous", False),
        ]
    )
    return flags >= 2


def _compute_high_risk_ratio(review_results: list[dict[str, Any]]) -> float:
    total = len(review_results)
    if total == 0:
        return 0.0
    high_count = sum(1 for item in review_results if _is_high_risk(item))
    return high_count / total


def _compute_ambiguity_ratio(parsed_items: list[dict[str, Any]]) -> float:
    total = len(parsed_items)
    if total == 0:
        return 0.0

    high_count = 0
    for item in parsed_items:
        text_parts = [str(item.get("description", ""))]
        text_parts.extend(str(x) for x in item.get("acceptance_criteria", []))
        lowered = " ".join(text_parts).lower()
        if any(term in lowered for term in _VAGUE_TERMS):
            high_count += 1
    return high_count / total


async def run(state: ReviewState) -> ReviewState:
    """Review parsed items and cross-check them against the delivery plan."""

    parsed_items: list[dict] = state.get("parsed_items", [])
    trace: dict[str, Any] = dict(state.get("trace", {}))
    run_dir: str = state.get("run_dir", "")
    raw = ""

    if not parsed_items:
        span = trace_start(_AGENT, model="none", input_chars=0)
        trace[_AGENT] = span.end(status="error", error_message="parsed_items is empty - nothing to review")
        return {
            "review_results": [],
            "plan_review": {},
            "high_risk_ratio": 0.0,
            "trace": trace,
        }

    items_json = json.dumps(parsed_items, ensure_ascii=False, indent=2)
    plan = plan_from_state(state)
    plan_data = {
        "tasks": plan.get("tasks", []),
        "milestones": plan.get("milestones", []),
        "estimation": plan.get("estimation", {}),
    }
    plan_json = json.dumps(plan_data, ensure_ascii=False, indent=2)

    input_chars = len(items_json) + len(plan_json)
    span = trace_start(_AGENT, input_chars=input_chars)
    span.set_template(REVIEWER_REVIEW_PROMPT)
    prompt = f"{REVIEWER_SYSTEM_PROMPT}\n\n{REVIEWER_USER_PROMPT.format(items_json=items_json, plan_json=plan_json)}"

    try:
        cfg = Config()
        span.model = cfg.smart_llm_model or "unknown"

        call_meta: dict[str, Any] = {
            "agent_name": _AGENT,
            "run_id": os.path.basename(run_dir) if run_dir else "",
        }
        parsed = await llm_structured_call(
            prompt=prompt,
            schema=ReviewerOutput,
            metadata=call_meta,
        )
        span.set_attr("structured_mode", call_meta.get("structured_mode", "unknown"))
        raw = str(call_meta.get("raw_output", "") or "")
        try:
            validated = validate_reviewer_output(parsed)
            output = validated.model_dump(mode="python")
            trace[_AGENT] = span.end(status="ok", output_chars=len(raw))
        except Exception as exc:
            raw_path = save_raw_agent_output(run_dir, _AGENT, raw) if run_dir and raw else ""
            output = ReviewerOutput().model_dump(mode="python")
            trace[_AGENT] = span.end(
                status="error",
                output_chars=len(raw),
                raw_output_path=raw_path,
                error_message=f"schema validation failed: {exc}",
            )

        high_risk_ratio = _compute_high_risk_ratio(output.get("review_results", []))
        ambiguity_ratio = _compute_ambiguity_ratio(parsed_items)
        high_risk_ratio = max(high_risk_ratio, ambiguity_ratio)
        span.set_attr("high_risk_ratio", round(high_risk_ratio, 4))
        span.set_attr("ambiguity_ratio", round(ambiguity_ratio, 4))
        span.set_attr("revision_round", int(state.get("revision_round", 0) or 0))

        return {
            "review_results": output.get("review_results", []),
            "plan_review": output.get("plan_review", {}),
            "high_risk_ratio": high_risk_ratio,
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
        return {
            "review_results": [],
            "plan_review": {},
            "high_risk_ratio": 0.0,
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
        return {
            "review_results": [],
            "plan_review": {},
            "high_risk_ratio": 0.0,
            "trace": trace,
        }
