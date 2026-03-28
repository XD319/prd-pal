"""CLI entry point for the V1 requirement-review workflow.

Usage:
    python -m requirement_review_v1.main --input docs/prd.md
"""

import argparse
import asyncio

from dotenv import load_dotenv

from .service.review_service import review_prd_text_async
from .utils.logging import setup_logging


def _parse_args():
    parser = argparse.ArgumentParser(description="Requirement Review V1")
    parser.add_argument("--input", type=str, required=True, help="Path to the requirement document")
    return parser.parse_args()


async def main():
    load_dotenv()
    setup_logging()
    args = _parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        doc = f.read()

    summary = await review_prd_text_async(doc, config_overrides={"outputs_root": "outputs"})
    report_path = summary.report_md_path
    state_path = summary.report_json_path
    trace_path = summary.run_trace_path

    print(f"Report : {report_path}")
    print(f"State  : {state_path}")
    print(f"Trace  : {trace_path}")


if __name__ == "__main__":
    asyncio.run(main())
