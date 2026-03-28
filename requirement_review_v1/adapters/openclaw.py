"""OpenClaw adapter request builder."""

from __future__ import annotations

from pathlib import Path

from requirement_review_v1.execution.models import ExecutionTask
from requirement_review_v1.handoff import render_openclaw_prompt
from requirement_review_v1.packs.delivery_bundle import DeliveryBundle
from requirement_review_v1.packs.schemas import ExecutionPack

from .base import BaseAdapter


class OpenClawAdapter(BaseAdapter):
    """Build offline OpenClaw execution requests."""

    adapter_name = "openclaw"
    display_name = "OpenClaw"
    request_filename = "openclaw_request.json"
    request_type = "openclaw.run_pack"

    def _render_prompt(self, execution_pack: ExecutionPack) -> str:
        return render_openclaw_prompt(execution_pack)

    def _build_adapter_payload(
        self,
        *,
        task: ExecutionTask,
        bundle: DeliveryBundle,
        execution_pack: ExecutionPack,
        prompt: str,
        context_path: Path,
    ) -> dict[str, object]:
        implementation_pack = execution_pack.implementation_pack
        test_pack = execution_pack.test_pack
        return {
            "input": {
                "prompt": prompt,
                "context_file": str(context_path),
                "workspace_root": str(bundle.metadata.get("workspace_root", "") or ""),
                "target_modules": implementation_pack.target_modules,
                "implementation_steps": implementation_pack.implementation_steps,
                "acceptance_criteria": implementation_pack.acceptance_criteria,
                "constraints": implementation_pack.constraints,
                "verification_scope": test_pack.test_scope,
                "edge_cases": test_pack.edge_cases,
                "handoff_strategy": execution_pack.handoff_strategy,
            },
            "callback": {
                "type": "file",
                "mode": "deferred",
                "task_id": task.task_id,
                "context_file": str(context_path),
            },
        }
