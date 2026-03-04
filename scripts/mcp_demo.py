#!/usr/bin/env python
"""End-to-end MCP demo client for requirement_review_v1.

Flow:
1. Start local MCP server via stdio (`python -m requirement_review_v1.mcp_server.server`)
2. Call `review_prd`
3. Call `get_report` with returned `run_id`
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import timedelta
from pathlib import Path
from typing import Any

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run MCP demo: review_prd -> get_report")
    parser.add_argument("--prd-file", type=Path, help="Path to PRD markdown/text file")
    parser.add_argument("--prd-text", type=str, help="Inline PRD text")
    parser.add_argument("--outputs-root", type=str, default="outputs", help="Outputs root for run artifacts")
    parser.add_argument("--run-id", type=str, default="", help="Optional run_id override")
    parser.add_argument("--report-format", choices=["md", "json"], default="md", help="get_report format")
    parser.add_argument("--report-offset", type=int, default=0, help="get_report offset")
    parser.add_argument("--report-limit", type=int, default=1200, help="get_report limit")
    parser.add_argument("--timeout-seconds", type=int, default=600, help="Timeout for each tool call")
    parser.add_argument("--python", type=str, default=sys.executable, help="Python executable used to start MCP server")
    parser.add_argument(
        "--server-module",
        type=str,
        default="requirement_review_v1.mcp_server.server",
        help="MCP server module path",
    )
    return parser


def _resolve_prd_text(args: argparse.Namespace) -> str:
    if args.prd_text and args.prd_text.strip():
        return args.prd_text

    if args.prd_file:
        if not args.prd_file.exists():
            raise FileNotFoundError(f"PRD file not found: {args.prd_file}")
        return args.prd_file.read_text(encoding="utf-8")

    return (
        "# PRD Demo\n"
        "## 背景\n"
        "构建一个任务列表应用，支持创建、编辑、完成任务。\n"
        "## 核心功能\n"
        "1. 用户可新增任务并设置截止日期。\n"
        "2. 用户可按状态筛选任务。\n"
        "3. 任务完成后可归档。\n"
        "## 非功能需求\n"
        "- 页面首屏加载时间 < 2s。\n"
        "- 支持并发 1000 在线用户。\n"
    )


def _result_to_payload(result: Any) -> Any:
    structured = getattr(result, "structuredContent", None)
    if structured is not None:
        return structured

    contents = getattr(result, "content", None)
    if not contents:
        return None

    if len(contents) == 1:
        first = contents[0]
        text = getattr(first, "text", None)
        if isinstance(text, str):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return text
        if hasattr(first, "model_dump"):
            return first.model_dump()
        return str(first)

    normalized: list[Any] = []
    for item in contents:
        text = getattr(item, "text", None)
        if isinstance(text, str):
            normalized.append(text)
        elif hasattr(item, "model_dump"):
            normalized.append(item.model_dump())
        else:
            normalized.append(str(item))
    return normalized


async def _run_demo(args: argparse.Namespace) -> int:
    repo_root = Path(__file__).resolve().parents[1]
    prd_text = _resolve_prd_text(args)

    server_params = StdioServerParameters(
        command=args.python,
        args=["-m", args.server_module],
        cwd=repo_root,
        env=os.environ.copy(),
    )

    timeout = timedelta(seconds=args.timeout_seconds)

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            tool_names = [tool.name for tool in tools_result.tools]
            print(f"Available tools: {tool_names}")

            review_args: dict[str, Any] = {
                "prd_text": prd_text,
                "options": {"outputs_root": args.outputs_root},
            }
            if args.run_id:
                review_args["options"]["run_id"] = args.run_id

            print("\nCalling tool: review_prd")
            review_result = await session.call_tool(
                "review_prd",
                review_args,
                read_timeout_seconds=timeout,
            )
            review_payload = _result_to_payload(review_result)
            print(json.dumps(review_payload, ensure_ascii=False, indent=2))

            if not isinstance(review_payload, dict):
                print("review_prd returned non-object payload; cannot continue")
                return 1

            error = review_payload.get("error")
            if isinstance(error, dict):
                print("review_prd returned error, skip get_report")
                return 1

            run_id = str(review_payload.get("run_id", "")).strip()
            if not run_id:
                print("review_prd did not return run_id")
                return 1

            get_report_args = {
                "run_id": run_id,
                "format": args.report_format,
                "offset": args.report_offset,
                "limit": args.report_limit,
                "options": {"outputs_root": args.outputs_root},
            }

            print("\nCalling tool: get_report")
            report_result = await session.call_tool(
                "get_report",
                get_report_args,
                read_timeout_seconds=timeout,
            )
            report_payload = _result_to_payload(report_result)
            print(json.dumps(report_payload, ensure_ascii=False, indent=2))

    return 0


def main() -> int:
    args = _build_parser().parse_args()
    try:
        return asyncio.run(_run_demo(args))
    except KeyboardInterrupt:
        print("Interrupted by user")
        return 130
    except Exception as exc:
        print(f"Demo failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
