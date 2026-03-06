# Requirement Review Architecture Notes

## Current entrypoints

- CLI: `python -m requirement_review_v1.main --input docs/sample_prd.md`
- API: `python main.py` -> `requirement_review_v1.server.app:app`
- MCP: `python -m requirement_review_v1.mcp_server.server`
- Eval: `python eval/run_eval.py`

## Runtime stack

- Workflow orchestration: `requirement_review_v1/workflow.py`
- Shared LLM runtime: `review_runtime/utils/llm.py`
- Provider factory: `review_runtime/llm_provider/generic/base.py`
- Runtime config: `review_runtime/config/config.py`

## Main flow

`parser -> clarify (conditional) -> planner + risk -> reviewer -> route_decider -> reporter`

Each run writes:

- `outputs/<run_id>/report.md`
- `outputs/<run_id>/report.json`
- `outputs/<run_id>/run_trace.json`
