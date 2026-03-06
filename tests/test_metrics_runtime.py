from requirement_review_v1.metrics import compute_runtime_metrics


def test_compute_runtime_metrics_aggregates_latency_cache_and_parallel_flags():
    trace = {
        "parser": {
            "start": "2026-03-06T10:00:00+00:00",
            "end": "2026-03-06T10:00:02+00:00",
            "duration_ms": 2000,
        },
        "planner": {
            "start": "2026-03-06T10:00:02+00:00",
            "end": "2026-03-06T10:00:05+00:00",
            "duration_ms": 3000,
        },
        "risk": {
            "start": "2026-03-06T10:00:02.500000+00:00",
            "end": "2026-03-06T10:00:06+00:00",
            "duration_ms": 3500,
        },
        "planner_risk_parallel": {
            "start": "2026-03-06T10:00:02+00:00",
            "end": "2026-03-06T10:00:06+00:00",
            "parallelized": True,
        },
        "risk_catalog.search": {
            "start": "2026-03-06T10:00:02.600000+00:00",
            "end": "2026-03-06T10:00:02.700000+00:00",
            "duration_ms": 100,
            "cache_hit": True,
        },
        "other_skill": {
            "start": "2026-03-06T10:00:03+00:00",
            "end": "2026-03-06T10:00:03.100000+00:00",
            "duration_ms": 100,
            "cache_hit": False,
        },
    }

    metrics = compute_runtime_metrics(trace)

    assert metrics["total_latency_ms"] == 6000
    assert metrics["planner_latency_ms"] == 3000
    assert metrics["risk_latency_ms"] == 3500
    assert metrics["cache_hit_count"] == 1
    assert metrics["cache_miss_count"] == 1
    assert metrics["parallel_enabled"] is True
