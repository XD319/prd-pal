"""Minimal approval state machine for DeliveryBundle."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from requirement_review_v1.packs.delivery_bundle import ApprovalEvent, BundleStatus, DeliveryBundle


class InvalidTransitionError(ValueError):
    """Raised when a bundle transition is not allowed."""


VALID_TRANSITIONS: dict[BundleStatus, set[BundleStatus]] = {
    BundleStatus.draft: {
        BundleStatus.need_more_info,
        BundleStatus.approved,
        BundleStatus.blocked_by_risk,
    },
    BundleStatus.need_more_info: {
        BundleStatus.draft,
        BundleStatus.blocked_by_risk,
    },
    BundleStatus.blocked_by_risk: {
        BundleStatus.draft,
    },
    BundleStatus.approved: set(),
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _transition(bundle: DeliveryBundle, to_status: BundleStatus, reviewer: str, comment: str) -> DeliveryBundle:
    from_status = BundleStatus(bundle.status)
    if to_status not in VALID_TRANSITIONS.get(from_status, set()):
        raise InvalidTransitionError(f"invalid bundle transition: {from_status} -> {to_status}")

    history = list(bundle.approval_history)
    history.append(
        ApprovalEvent(
            event_id=f"approval-{uuid4().hex}",
            timestamp=_utc_now_iso(),
            from_status=from_status,
            to_status=to_status,
            reviewer=reviewer,
            comment=comment,
        )
    )
    return bundle.model_copy(update={"status": to_status, "approval_history": history}, deep=True)


def approve_bundle(bundle: DeliveryBundle, reviewer: str, comment: str) -> DeliveryBundle:
    return _transition(bundle, BundleStatus.approved, reviewer, comment)


def request_more_info(bundle: DeliveryBundle, reviewer: str, comment: str) -> DeliveryBundle:
    return _transition(bundle, BundleStatus.need_more_info, reviewer, comment)


def block_by_risk(bundle: DeliveryBundle, reviewer: str, comment: str) -> DeliveryBundle:
    return _transition(bundle, BundleStatus.blocked_by_risk, reviewer, comment)


def reset_to_draft(bundle: DeliveryBundle, reviewer: str, comment: str) -> DeliveryBundle:
    return _transition(bundle, BundleStatus.draft, reviewer, comment)
