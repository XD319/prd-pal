from __future__ import annotations

from prd_pal.review.ingress_normalization import normalize_ingress_request
from prd_pal.review.profile_router import load_profile_pack, route_review_profile


def test_profile_router_selects_data_sensitive_for_security_signals() -> None:
    canonical = normalize_ingress_request(
        run_id="20260414T112300Z",
        requirement_doc="Add OAuth login and encrypt PII export for admin approval.",
        prd_text="Add OAuth login and encrypt PII export for admin approval.",
        audit_context={"source": "web"},
    )

    routed = route_review_profile(canonical)

    assert routed.selected_profile == "data_sensitive"
    assert routed.confidence >= 0.6
    assert "Selected data_sensitive" in routed.reason


def test_profile_router_fallbacks_to_default_when_ambiguous() -> None:
    canonical = normalize_ingress_request(
        run_id="20260414T112301Z",
        requirement_doc="Polish wording and improve experience.",
        audit_context={"source": "cli"},
    )

    routed = route_review_profile(canonical)

    assert routed.selected_profile == "default"
    assert "fallback to default" in routed.reason.lower()


def test_load_profile_pack_returns_profile_paths() -> None:
    pack = load_profile_pack("approval_workflow")

    assert pack["profile"] == "approval_workflow"
    assert pack["checklist_path"].endswith("approval_workflow/checklist.md")
    assert pack["rules_path"].endswith("approval_workflow/rules.md")
    assert "approval" in pack["checklist"].lower()
