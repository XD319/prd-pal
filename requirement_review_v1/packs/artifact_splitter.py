"""Split the combined review output into standalone delivery artifacts."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from requirement_review_v1.packs.delivery_bundle import ArtifactRef
from requirement_review_v1.templates import DeliveryArtifactTemplate, get_delivery_artifact_template


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ArtifactSplitter:
    """Split review outputs into independent markdown artifacts."""

    TEMPLATE_IDS = {
        "prd_review_report": "delivery_artifact.prd_review_report",
        "open_questions": "delivery_artifact.open_questions",
        "scope_boundary": "delivery_artifact.scope_boundary",
        "tech_design_draft": "delivery_artifact.tech_design_draft",
        "test_checklist": "delivery_artifact.test_checklist",
    }

    def templates(self) -> dict[str, DeliveryArtifactTemplate]:
        return {
            artifact_type: get_delivery_artifact_template(template_id)
            for artifact_type, template_id in self.TEMPLATE_IDS.items()
        }

    def template_trace(self) -> dict[str, dict[str, str]]:
        return {
            artifact_type: template.trace_metadata()
            for artifact_type, template in self.templates().items()
        }

    def split(self, review_result: dict[str, Any], run_dir: Path) -> dict[str, ArtifactRef]:
        run_dir.mkdir(parents=True, exist_ok=True)
        generated_at = _utc_now_iso()
        refs: dict[str, ArtifactRef] = {}

        for artifact_type, template in self.templates().items():
            content = template.renderer(review_result)
            path = run_dir / template.file_name
            path.write_text(content, encoding="utf-8")
            refs[artifact_type] = ArtifactRef(
                artifact_type=artifact_type,
                path=str(path),
                content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
                generated_at=generated_at,
            )
        return refs
