"""CLI entry point for the V1 requirement-review workflow.

Usage:
    python -m requirement_review_v1.main --input docs/prd.md
"""

import argparse
import asyncio

from dotenv import load_dotenv

from .run_review import run_review


def _parse_args():
    parser = argparse.ArgumentParser(description="Requirement Review V1")
    parser.add_argument("--input", type=str, required=True, help="Path to the requirement document")
    return parser.parse_args()


async def main():
    load_dotenv()
    args = _parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        doc = f.read()

    run_output = await run_review(doc, outputs_root="outputs")
    report_path = run_output["report_paths"]["report_md"]
    state_path = run_output["report_paths"]["report_json"]
    trace_path = run_output["report_paths"]["run_trace"]

    print(f"Report : {report_path}")
    print(f"State  : {state_path}")
    print(f"Trace  : {trace_path}")


if __name__ == "__main__":
    asyncio.run(main())
