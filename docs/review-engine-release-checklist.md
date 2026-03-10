# Review Engine Release Checklist

This checklist is scoped to the review engine only.

It intentionally excludes approval-loop, execution orchestration, and delivery-management rollout work.

## 1. Entry-Point Smoke Checks

Run:

```bash
D:\venvs\marrdp\Scripts\python.exe eval/smoke_review_engine.py
```

Verify:

- CLI smoke passes and prints report, state, and trace artifact paths.
- FastAPI smoke passes for review submission, status lookup, and result retrieval.
- `eval/smoke_report.json` exists and records `passed: true`.

## 2. Regression Eval

Run:

```bash
D:\venvs\marrdp\Scripts\python.exe eval/run_eval.py
```

Verify:

- `eval/eval_report.json` is refreshed.
- `summary.failed_cases == 0` and `summary.error_cases == 0`.
- `runtime_summary.cases_with_failed_spans` is empty, or any non-empty entries are explicitly reviewed before release.
- `runtime_summary.slowest_case_span` and `duration_summary.slowest_cases_top_3` do not show unexpected regressions compared with the last accepted release run.

## 3. Automated Test Gate

Run:

```bash
D:\venvs\marrdp\Scripts\python.exe -m pytest -q
```

Verify:

- The test suite passes completely.
- Any warnings are known and accepted for this release.

## 4. Completed-Run Artifact Review

Inspect one fresh completed review run from the eval or smoke artifacts.

Verify:

- `report.md` renders a coherent review report.
- `report.json` includes `metrics.total_latency_ms`, cache counters, and the slowest-span fields.
- `run_trace.json` includes the expected core nodes: `parser`, `planner`, `risk`, `reviewer`, `reporter`.
- Review outputs remain review-engine focused and do not surface approval or orchestration features as part of this release phase.

## 5. FastAPI Shared-Environment Check

If releasing the HTTP surface, verify environment configuration:

- auth is configured or explicitly opted out for local-only environments
- submission rate limiting is configured for shared environments
- clients know how to use the current review endpoints only

## 6. Release Notes / Handoff

Before handoff or tagging:

- record the exact eval command used
- record the exact pytest command used
- link the refreshed `eval/eval_report.json` and `eval/smoke_report.json`
- call out any known non-blocking warnings or environment caveats
