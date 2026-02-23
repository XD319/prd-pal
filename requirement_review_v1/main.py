"""CLI entry point for the V1 requirement-review workflow.

Usage:
    python -m requirement_review_v1.main --input docs/prd.md
"""

import argparse
import asyncio
import json
import os
from datetime import datetime, timezone

from dotenv import load_dotenv

from .workflow import build_review_graph


def _parse_args():
    parser = argparse.ArgumentParser(description="Requirement Review V1")
    parser.add_argument("--input", type=str, required=True, help="Path to the requirement document")
    return parser.parse_args()


async def main():
    load_dotenv()
    args = _parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        doc = f.read()

    # ── prepare output directory before graph runs ──────────────────
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = os.path.join("outputs", run_id)
    os.makedirs(out_dir, exist_ok=True)

    graph = build_review_graph()
    result = await graph.ainvoke({"requirement_doc": doc, "run_dir": out_dir})

    report_path = os.path.join(out_dir, "report.md")
    state_path = os.path.join(out_dir, "report.json")
    trace_path = os.path.join(out_dir, "run_trace.json")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(result.get("final_report", ""))

    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    with open(trace_path, "w", encoding="utf-8") as f:
        json.dump(result.get("trace", {}), f, ensure_ascii=False, indent=2)

    print(f"Report : {report_path}")
    print(f"State  : {state_path}")
    print(f"Trace  : {trace_path}")


if __name__ == "__main__":
    asyncio.run(main())
