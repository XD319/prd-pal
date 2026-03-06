"""Runtime metrics derived from workflow trace spans."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def _parse_iso(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _span_duration_ms(span: Any) -> int:
    if not isinstance(span, dict):
        return 0
    raw = span.get("duration_ms", 0)
    try:
        return max(0, int(raw or 0))
    except (TypeError, ValueError):
        return 0


def _total_latency_ms(trace: dict[str, Any]) -> int:
    starts: list[datetime] = []
    ends: list[datetime] = []
    for span in trace.values():
        if not isinstance(span, dict):
            continue
        start = _parse_iso(span.get("start"))
        end = _parse_iso(span.get("end"))
        if start is not None:
            starts.append(start)
        if end is not None:
            ends.append(end)
    if not starts or not ends:
        return 0
    return max(0, int((max(ends) - min(starts)).total_seconds() * 1000))


def compute_runtime_metrics(trace: dict[str, Any] | None) -> dict[str, Any]:
    """Return run-level latency/cache/parallel metrics from trace."""

    safe_trace = trace if isinstance(trace, dict) else {}
    cache_hit_count = 0
    cache_miss_count = 0

    for span in safe_trace.values():
        if not isinstance(span, dict):
            continue
        cache_hit = span.get("cache_hit")
        if cache_hit is True:
            cache_hit_count += 1
        elif cache_hit is False:
            cache_miss_count += 1

    parallel_span = safe_trace.get("planner_risk_parallel", {})
    parallel_enabled = False
    if isinstance(parallel_span, dict):
        parallel_enabled = bool(
            parallel_span.get("parallelized")
            or parallel_span.get("parallel_enabled")
            or parallel_span.get("fan_out") == "parser->planner+risk"
        )

    return {
        "total_latency_ms": _total_latency_ms(safe_trace),
        "planner_latency_ms": _span_duration_ms(safe_trace.get("planner")),
        "risk_latency_ms": _span_duration_ms(safe_trace.get("risk")),
        "cache_hit_count": cache_hit_count,
        "cache_miss_count": cache_miss_count,
        "parallel_enabled": parallel_enabled,
    }

