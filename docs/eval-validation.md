# Eval Validation Guide

Use the smoke profile for day-to-day development when you need a fast regression signal on the core cases.

```bash
python eval/run_eval.py --profile smoke --workers 1
```

Use bounded parallel execution to shorten smoke/full eval wall time when cases are independent.

```bash
python eval/run_eval.py --profile smoke --workers 2
python eval/run_eval.py --workers 2
```

Use the full profile before release to run the complete case set and generate the full latency breakdown.

```bash
python eval/run_eval.py
```

Both commands write the aggregated report to `eval/eval_report.json` and refresh per-case artifacts under `eval/runs/`.

The current skill cache is process-local in-memory TTL cache. Eval parallelism in `run_eval.py` does not provide cross-process cache sharing, and separate CLI runs should not be treated as cache-hit evidence.

Use the review-mode comparison script when you want a minimal A/B validation of the parallel-review enhancement on at least two PRDs with different complexity levels.

```bash
python eval/compare_review_modes.py
```

The default comparison runs `single_review` and `parallel_review` against `prd_case_08` and `prd_case_11`, then writes the summary report to `eval/review_mode_comparison.json` and per-run artifacts under `eval/review_mode_comparison_runs/`.

If you need to choose specific PRDs, repeat `--case-id` and provide at least two ids:

```bash
python eval/compare_review_modes.py --case-id prd_case_08 --case-id prd_case_11
```

The comparison report records these metrics for each mode: `findings_count`, `open_questions_count`, `risk_items_count`, `conflicts_count`, and `duration_ms`. Stable token accounting is currently recorded as `not available`.
