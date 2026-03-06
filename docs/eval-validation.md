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
