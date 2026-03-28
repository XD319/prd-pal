from __future__ import annotations

from pathlib import Path


def test_local_prd_review_skill_hardens_storage_and_source_usage() -> None:
    skill_path = Path("skills/prd-review-agent/SKILL.md")
    yaml_path = Path("skills/prd-review-agent/agents/openai.yaml")

    skill = skill_path.read_text(encoding="utf-8")
    ui_yaml = yaml_path.read_text(encoding="utf-8")

    assert "[TODO" not in skill
    assert "outputs/_skill/current_prd.md" in skill
    assert "Do not use connector-backed `--source`" in skill
    assert "Do not paste the full PRD or the full report JSON" in skill
    assert "$prd-review-agent" in ui_yaml


def test_remote_prd_review_service_skill_targets_http_flow() -> None:
    skill_path = Path("skills/prd-review-service/SKILL.md")
    yaml_path = Path("skills/prd-review-service/agents/openai.yaml")

    skill = skill_path.read_text(encoding="utf-8")
    ui_yaml = yaml_path.read_text(encoding="utf-8")

    assert "[TODO" not in skill
    assert "GET <base-url>/health" in skill
    assert "POST <base-url>/api/review" in skill
    assert "GET <base-url>/api/review/<run_id>/result" in skill
    assert "Never reveal API keys" in skill
    assert "$prd-review-service" in ui_yaml
