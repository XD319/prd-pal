from __future__ import annotations

import pytest

from requirement_review_v1.monitoring import read_audit_events
from requirement_review_v1.notifications import (
    BaseNotifier,
    NotificationType,
    build_notification_record,
    dispatch_notification,
    read_notification_records,
)


@pytest.mark.parametrize(
    "notification_type",
    [
        NotificationType.approval_requested,
        NotificationType.blocked_by_risk,
        NotificationType.executor_handoff_created,
        NotificationType.execution_completed,
        NotificationType.execution_failed,
    ],
)
def test_dispatch_notification_supports_all_notification_types(tmp_path, notification_type: NotificationType) -> None:
    result = dispatch_notification(
        tmp_path,
        notification_type=notification_type,
        title=f"Notification: {notification_type.value}",
        summary="dry-run notification",
        run_id="20260308T060708Z",
        bundle_id="bundle-20260308T060708Z",
        task_id="bundle-20260308T060708Z:implementation_pack",
        metadata={"severity": "info"},
        audit_context={
            "actor": "workflow-bot",
            "source": "mcp",
            "tool_name": "test_tool",
            "client_metadata": {"request_id": "req-1"},
        },
    )

    records = read_notification_records(tmp_path)
    audit_events = read_audit_events(tmp_path)

    assert result.status == "dispatched"
    assert len(result.dispatches) == 2
    assert len(records) == 2
    assert len(audit_events) == 2
    assert {record["channel"] for record in records} == {"feishu", "wecom"}
    assert {record["event_type"] for record in records} == {notification_type.value}
    assert {record["notification_id"] for record in records} == {result.notification_id}
    assert {record["dispatch_status"] for record in records} == {"dispatched"}
    assert all(record["created_at"] for record in records)
    assert all(record["dispatched_at"] for record in records)
    assert records[0]["metadata"]["actor"] == "workflow-bot"
    assert records[0]["metadata"]["tool_name"] == "test_tool"
    assert records[0]["metadata"]["client_metadata"]["request_id"] == "req-1"
    assert all(record["payload"]["dry_run"] is True for record in records)
    assert [event["operation"] for event in audit_events] == ["notification_dispatch", "notification_dispatch"]
    assert {event["status"] for event in audit_events} == {"dispatched"}


def test_build_notification_record_captures_dispatch_fields() -> None:
    record = build_notification_record(
        notification_type=NotificationType.execution_failed,
        title="Execution failed: bundle-1:implementation_pack",
        summary="Validation failed in dry-run mode.",
        run_id="20260308T060709Z",
        bundle_id="bundle-20260308T060709Z",
        task_id="bundle-20260308T060709Z:implementation_pack",
        metadata={"actor": "codex-worker-1"},
        audit_context={
            "source": "mcp",
            "tool_name": "update_execution_task",
        },
        channel="feishu",
        payload={"dry_run": True, "channel": "feishu"},
        dispatch_status="dispatched",
        dispatched_at="2026-03-08T06:07:10+00:00",
    )

    assert record.event_type == NotificationType.execution_failed
    assert record.channel == "feishu"
    assert record.dispatch_status == "dispatched"
    assert record.payload["dry_run"] is True
    assert record.metadata["actor"] == "codex-worker-1"
    assert record.metadata["source"] == "mcp"
    assert record.metadata["tool_name"] == "update_execution_task"
    assert record.dispatched_at == "2026-03-08T06:07:10+00:00"


class _BrokenNotifier(BaseNotifier):
    channel = "broken"
    description = "Always fail when building a payload."

    def build_payload(self, event):
        raise RuntimeError(f"cannot render {event.event_type}")


def test_dispatch_notification_persists_failed_dispatches_without_silencing_errors(tmp_path) -> None:
    result = dispatch_notification(
        tmp_path,
        notification_type=NotificationType.blocked_by_risk,
        title="Bundle blocked by risk",
        summary="Critical dependency risk remains unresolved.",
        run_id="20260308T060710Z",
        bundle_id="bundle-20260308T060710Z",
        notifiers=[_BrokenNotifier()],
        audit_context={"tool_name": "approve_handoff", "source": "mcp"},
    )

    records = read_notification_records(tmp_path)
    audit_events = read_audit_events(tmp_path)

    assert result.status == "failed"
    assert len(records) == 1
    assert records[0]["event_type"] == "blocked_by_risk"
    assert records[0]["channel"] == "broken"
    assert records[0]["dispatch_status"] == "failed"
    assert records[0]["error_message"] == "cannot render blocked_by_risk"
    assert records[0]["payload"] == {}
    assert len(audit_events) == 1
    assert audit_events[0]["operation"] == "notification_dispatch"
    assert audit_events[0]["status"] == "failed"
    assert audit_events[0]["details"]["error_message"] == "cannot render blocked_by_risk"
