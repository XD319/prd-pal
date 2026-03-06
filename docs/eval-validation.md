# Eval Validation Guide

Use the smoke profile for day-to-day development when you need a fast regression signal on the core cases.

```bash
python eval/run_eval.py --profile smoke
```

Use the full profile before release to run the complete case set and generate the full latency breakdown.

```bash
python eval/run_eval.py
```

Both commands write the aggregated report to `eval/eval_report.json` and refresh per-case artifacts under `eval/runs/`.
