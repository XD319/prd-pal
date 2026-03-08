"""Dry-run notification primitives and persistence helpers."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from pydantic import Field

from requirement_review_v1.monitoring import (
    normalize_audit_context,
    resolve_audit_actor,
    resolve_audit_client_metadata,
    resolve_audit_source,
)
from requirement_review_v1.schemas.base import AgentSchemaModel

try:
    from enum import StrEnum
except ImportError:  # pragma: no cover - Python < 3.11 fallback
    from enum import Enum

    class StrEnum(str, Enum):
        pass


NOTIFICATIONS_FILENAME = "notifications.jsonl"


class NotificationType(StrEnum):
    approval_requested = "approval_requested"
    blocked_by_risk = "blocked_by_risk"
    executor_handoff_created = "executor_handoff_created"
    execution_completed = "execution_completed"
    execution_failed = "execution_failed"


class NotificationStatus(StrEnum):
    dry_run = "dry_run"


class NotificationRecord(AgentSchemaModel):
    notification_id: str
    timestamp: str
    notification_type: NotificationType
    run_id: str = ""
    bundle_id: str = ""
    task_id: str = ""
    title: str
    summary: str = ""
    status: NotificationStatus = NotificationStatus.dry_run
    channels: list[str] = Field(default_factory=list)
    payloads: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BaseNotifier(ABC):
    channel: str = ""
    description: str = ""

    @abstractmethod
    def build_payload(self, record: NotificationRecord) -> dict[str, Any]:
        """Return one dry-run payload for the notifier channel."""


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_notification_type(notification_type: NotificationType | str) -> NotificationType:
    try:
        return NotificationType(str(notification_type or "").strip())
    except ValueError as exc:
        allowed = ", ".join(item.value for item in NotificationType)
        raise ValueError(f"notification_type must be one of: {allowed}") from exc


def notifications_path(run_dir: str | Path) -> Path:
    return Path(run_dir) / NOTIFICATIONS_FILENAME


def _merge_notification_metadata(
    metadata: dict[str, Any] | None,
    audit_context: dict[str, Any] | None,
) -> dict[str, Any]:
    context = normalize_audit_context(audit_context)
    merged = dict(metadata) if isinstance(metadata, dict) else {}

    actor = resolve_audit_actor(context, default="")
    source = resolve_audit_source(context, default="service")
    tool_name = str(context.get("tool_name") or "").strip()
    client_metadata = resolve_audit_client_metadata(context)

    if actor and "actor" not in merged:
        merged["actor"] = actor
    if source and "source" not in merged:
        merged["source"] = source
    if tool_name and "tool_name" not in merged:
        merged["tool_name"] = tool_name

    existing_client_metadata = merged.get("client_metadata")
    merged_client_metadata = dict(client_metadata)
    if isinstance(existing_client_metadata, dict):
        merged_client_metadata.update(existing_client_metadata)
    if merged_client_metadata:
        merged["client_metadata"] = merged_client_metadata

    return merged


def _default_notifiers() -> tuple[BaseNotifier, ...]:
    from .feishu import FeishuNotifier
    from .wecom import WeComNotifier

    return (FeishuNotifier(), WeComNotifier())


def build_notification_record(
    *,
    notification_type: NotificationType | str,
    title: str,
    summary: str = "",
    run_id: str = "",
    bundle_id: str = "",
    task_id: str = "",
    metadata: dict[str, Any] | None = None,
    audit_context: dict[str, Any] | None = None,
    notifiers: Sequence[BaseNotifier] | None = None,
) -> NotificationRecord:
    resolved_type = _resolve_notification_type(notification_type)
    resolved_notifiers = tuple(notifiers) if notifiers is not None else _default_notifiers()
    merged_metadata = _merge_notification_metadata(metadata, audit_context)
    timestamp = _utc_now_iso()
    record = NotificationRecord(
        notification_id=f"notification:{resolved_type.value}:{run_id or bundle_id or task_id or timestamp}",
        timestamp=timestamp,
        notification_type=resolved_type,
        run_id=str(run_id or "").strip(),
        bundle_id=str(bundle_id or "").strip(),
        task_id=str(task_id or "").strip(),
        title=str(title or "").strip(),
        summary=str(summary or title or "").strip(),
        channels=[notifier.channel for notifier in resolved_notifiers if str(notifier.channel or "").strip()],
        metadata=merged_metadata,
    )
    payloads = {notifier.channel: notifier.build_payload(record) for notifier in resolved_notifiers if notifier.channel}
    return record.model_copy(update={"payloads": payloads}, deep=True)


def append_notification_record(run_dir: str | Path, record: NotificationRecord | dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    run_dir_path = Path(run_dir)
    run_dir_path.mkdir(parents=True, exist_ok=True)

    if isinstance(record, NotificationRecord):
        payload = record.model_dump(mode="python")
    elif isinstance(record, dict):
        payload = NotificationRecord.model_validate(record).model_dump(mode="python")
    else:
        raise TypeError("record must be a NotificationRecord or dict")

    path = notifications_path(run_dir_path)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return path, payload


def record_dry_run_notification(
    run_dir: str | Path,
    *,
    notification_type: NotificationType | str,
    title: str,
    summary: str = "",
    run_id: str = "",
    bundle_id: str = "",
    task_id: str = "",
    metadata: dict[str, Any] | None = None,
    audit_context: dict[str, Any] | None = None,
    notifiers: Sequence[BaseNotifier] | None = None,
) -> tuple[Path, dict[str, Any]]:
    record = build_notification_record(
        notification_type=notification_type,
        title=title,
        summary=summary,
        run_id=run_id,
        bundle_id=bundle_id,
        task_id=task_id,
        metadata=metadata,
        audit_context=audit_context,
        notifiers=notifiers,
    )
    return append_notification_record(run_dir, record)


def read_notification_records(run_dir: str | Path) -> list[dict[str, Any]]:
    path = notifications_path(run_dir)
    if not path.exists():
        return []

    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        payload = line.strip()
        if not payload:
            continue
        try:
            loaded = json.loads(payload)
        except json.JSONDecodeError:
            continue
        if isinstance(loaded, dict):
            records.append(loaded)
    return records
