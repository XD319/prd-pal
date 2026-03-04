"""Minimal regression evaluator for requirement_review_v1 workflow.

Usage:
    python eval/run_eval.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from requirement_review_v1.workflow import build_review_graph

REQUIRED_TRACE_AGENTS = ("parser", "planner", "risk", "reviewer", "reporter")
REQUIRED_TRACE_FIELDS = (
    "start",
    "end",
    "duration_ms",
    "model",
    "status",
    "input_chars",
    "output_chars",
    "prompt_version",
    "raw_output_path",
    "error_message",
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run minimal workflow regression eval")
    parser.add_argument(
        "--cases",
        type=Path,
        default=Path("eval/cases/prd_test_inputs.jsonl"),
        help="Path to eval case jsonl",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("eval/eval_report.json"),
        help="Path to aggregated eval report",
    )
    parser.add_argument(
        "--runs-dir",
        type=Path,
        default=Path("eval/runs"),
        help="Directory to store per-case workflow outputs",
    )
    return parser.parse_args()


def _load_cases(cases_path: Path) -> list[dict[str, Any]]:
    if not cases_path.exists():
        raise FileNotFoundError(f"Cases file not found: {cases_path}")

    cases: list[dict[str, Any]] = []
    for index, line in enumerate(cases_path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            item = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL at line {index}: {exc}") from exc
        if not isinstance(item, dict):
            raise ValueError(f"Case at line {index} must be a JSON object")
        case_id = item.get("case_id")
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError(f"Missing or invalid case_id at line {index}")
        cases.append(item)
    return cases


def _case_to_requirement_doc(case: dict[str, Any]) -> str:
    # Feed the workflow with a deterministic text representation of each case.
    return json.dumps(case, ensure_ascii=False, indent=2)


def _resolve_model_provider(result: dict[str, Any]) -> tuple[str, str]:
    model = "unknown"
    provider = "unknown"
    try:
        from gpt_researcher.config.config import Config as _Cfg

        cfg = _Cfg()
        model = cfg.smart_llm_model or "unknown"
        provider = cfg.smart_llm_provider or "unknown"
    except Exception:
        trace = result.get("trace", {})
        if isinstance(trace, dict):
            for agent_name in ("parser", "reviewer"):
                span = trace.get(agent_name, {})
                if isinstance(span, dict):
                    maybe_model = span.get("model", "")
                    if isinstance(maybe_model, str) and maybe_model and maybe_model not in ("unknown", "none"):
                        model = maybe_model
                        break
    return model, provider


def _build_report_json(result: dict[str, Any], run_id: str) -> dict[str, Any]:
    model, provider = _resolve_model_provider(result)
    report_data: dict[str, Any] = {
        "schema_version": "v1.1",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "provider": provider,
        "project": "requirement_review_v1",
    }
    report_data.update(result)
    return report_data


def _check_report_json_valid(report_data: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    required_top_keys = (
        "schema_version",
        "run_id",
        "created_at",
        "model",
        "provider",
        "project",
        "trace",
        "metrics",
    )
    for key in required_top_keys:
        if key not in report_data:
            errors.append(f"missing key: {key}")

    trace = report_data.get("trace")
    if not isinstance(trace, dict):
        errors.append("trace must be an object")

    metrics = report_data.get("metrics")
    if not isinstance(metrics, dict):
        errors.append("metrics must be an object")

    return len(errors) == 0, errors


def _check_trace_complete(trace: Any) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not isinstance(trace, dict):
        return False, ["trace is not an object"]

    for agent in REQUIRED_TRACE_AGENTS:
        span = trace.get(agent)
        if not isinstance(span, dict):
            errors.append(f"missing agent trace: {agent}")
            continue
        for field in REQUIRED_TRACE_FIELDS:
            if field not in span:
                errors.append(f"{agent}: missing field {field}")
    return len(errors) == 0, errors


def _check_coverage_ratio(report_data: dict[str, Any]) -> tuple[bool, list[str], float | None]:
    errors: list[str] = []
    ratio_value: float | None = None

    metrics = report_data.get("metrics")
    if not isinstance(metrics, dict):
        return False, ["metrics is not an object"], None

    raw_ratio = metrics.get("coverage_ratio")
    if isinstance(raw_ratio, (int, float)):
        ratio_value = float(raw_ratio)
        if ratio_value < 0 or ratio_value > 1:
            errors.append("coverage_ratio must be between 0 and 1")
    else:
        errors.append("coverage_ratio missing or not numeric")

    return len(errors) == 0, errors, ratio_value


async def _run_case(
    graph: Any,
    case: dict[str, Any],
    runs_dir: Path,
) -> dict[str, Any]:
    case_id = str(case.get("case_id"))
    started_at = datetime.now(timezone.utc)
    run_id = f"{case_id}_{started_at.strftime('%Y%m%dT%H%M%SZ')}"
    run_dir = runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    try:
        result = await graph.ainvoke(
            {
                "requirement_doc": _case_to_requirement_doc(case),
                "run_dir": str(run_dir),
            }
        )
        if not isinstance(result, dict):
            raise ValueError("workflow result must be an object")

        report_data = _build_report_json(result, run_id)
        final_report = result.get("final_report", "")
        trace = result.get("trace", {})

        (run_dir / "report.md").write_text(str(final_report), encoding="utf-8")
        (run_dir / "report.json").write_text(
            json.dumps(report_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (run_dir / "run_trace.json").write_text(
            json.dumps(trace, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        report_ok, report_errors = _check_report_json_valid(report_data)
        trace_ok, trace_errors = _check_trace_complete(trace)
        coverage_ok, coverage_errors, coverage_ratio = _check_coverage_ratio(report_data)

        checks = {
            "report_json_valid": {"passed": report_ok, "errors": report_errors},
            "trace_complete": {"passed": trace_ok, "errors": trace_errors},
            "coverage_ratio_present": {"passed": coverage_ok, "errors": coverage_errors},
        }
        all_ok = all(item["passed"] for item in checks.values())

        return {
            "case_id": case_id,
            "title": case.get("title"),
            "scenario_type": case.get("scenario_type"),
            "run_id": run_id,
            "run_dir": str(run_dir),
            "status": "passed" if all_ok else "failed",
            "checks": checks,
            "coverage_ratio": coverage_ratio,
            "trace_status": {
                agent: (trace.get(agent, {}) if isinstance(trace, dict) else {}).get("status")
                for agent in REQUIRED_TRACE_AGENTS
            },
            "started_at": started_at.isoformat(),
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        return {
            "case_id": case_id,
            "title": case.get("title"),
            "scenario_type": case.get("scenario_type"),
            "run_id": run_id,
            "run_dir": str(run_dir),
            "status": "error",
            "checks": {
                "report_json_valid": {"passed": False, "errors": ["workflow failed before report validation"]},
                "trace_complete": {"passed": False, "errors": ["workflow failed before trace validation"]},
                "coverage_ratio_present": {"passed": False, "errors": ["workflow failed before coverage validation"]},
            },
            "coverage_ratio": None,
            "trace_status": {},
            "error": str(exc),
            "started_at": started_at.isoformat(),
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }


async def _amain() -> int:
    load_dotenv()
    args = _parse_args()

    cases = _load_cases(args.cases)
    args.runs_dir.mkdir(parents=True, exist_ok=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)

    graph = build_review_graph()
    case_results: list[dict[str, Any]] = []

    for idx, case in enumerate(cases, start=1):
        case_id = case.get("case_id", f"case_{idx}")
        print(f"[{idx}/{len(cases)}] Running case: {case_id}")
        case_result = await _run_case(graph, case, args.runs_dir)
        case_results.append(case_result)
        print(f"  -> {case_result['status']}")

    total = len(case_results)
    passed = sum(1 for item in case_results if item.get("status") == "passed")
    failed = sum(1 for item in case_results if item.get("status") == "failed")
    errored = sum(1 for item in case_results if item.get("status") == "error")

    eval_report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cases_file": str(args.cases),
        "runs_dir": str(args.runs_dir),
        "summary": {
            "total_cases": total,
            "passed_cases": passed,
            "failed_cases": failed,
            "error_cases": errored,
        },
        "cases": case_results,
    }

    args.out.write_text(json.dumps(eval_report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Eval report written to: {args.out}")

    # Non-zero on failed/error to support CI usage.
    return 0 if (failed == 0 and errored == 0) else 1


def main() -> None:
    raise SystemExit(asyncio.run(_amain()))


if __name__ == "__main__":
    main()
