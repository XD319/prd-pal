"""Claude Code adapter request builder."""

from __future__ import annotations

from pathlib import Path

from prd_pal.execution.models import ExecutionTask
from prd_pal.handoff import render_claude_code_prompt
from prd_pal.packs.delivery_bundle import DeliveryBundle
from prd_pal.packs.schemas import ExecutionPack

from .base import BaseAdapter


class ClaudeCodeAdapter(BaseAdapter):
    """Build offline Claude Code execution requests."""

    adapter_name = "claude_code"
    display_name = "Claude Code"
    request_filename = "claude_code_request.json"
    request_type = "claude_code.run_pack"

    def _render_prompt(self, execution_pack: ExecutionPack) -> str:
        return render_claude_code_prompt(execution_pack)

    def _build_adapter_payload(
        self,
        *,
        task: ExecutionTask,
        bundle: DeliveryBundle,
        execution_pack: ExecutionPack,
        prompt: str,
        context_path: Path,
    ) -> dict[str, object]:
        test_pack = execution_pack.test_pack
        return {
            "input": {
                "prompt": prompt,
                "context_file": str(context_path),
                "workspace_root": str(bundle.metadata.get("workspace_root", "") or ""),
                "test_scope": test_pack.test_scope,
                "edge_cases": test_pack.edge_cases,
                "acceptance_criteria": test_pack.acceptance_criteria,
                "handoff_strategy": execution_pack.handoff_strategy,
            },
            "callback": {
                "type": "file",
                "mode": "deferred",
                "task_id": task.task_id,
                "context_file": str(context_path),
            },
        }
