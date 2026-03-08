from __future__ import annotations

import pytest

from requirement_review_v1.notifications import (
    NotificationType,
    build_notification_record,
    read_notification_records,
    record_dry_run_notification,
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
def test_record_dry_run_notification_supports_all_notification_types(tmp_path, notification_type: NotificationType) -> None:
    path, record = record_dry_run_notification(
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

    assert path.name == "notifications.jsonl"
    assert record["notification_type"] == notification_type.value
    assert record["status"] == "dry_run"
    assert set(record["payloads"]) == {"feishu", "wecom"}
    assert record["metadata"]["actor"] == "workflow-bot"
    assert record["metadata"]["tool_name"] == "test_tool"
    assert record["metadata"]["client_metadata"]["request_id"] == "req-1"

    persisted = read_notification_records(tmp_path)
    assert len(persisted) == 1
    assert persisted[0]["notification_type"] == notification_type.value


def test_build_notification_record_renders_channel_specific_dry_run_payloads() -> None:
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
    )

    assert record.notification_type == NotificationType.execution_failed
    assert record.channels == ["feishu", "wecom"]
    assert record.metadata["actor"] == "codex-worker-1"
    assert record.metadata["source"] == "mcp"
    assert record.metadata["tool_name"] == "update_execution_task"

    feishu_payload = record.payloads["feishu"]
    wecom_payload = record.payloads["wecom"]

    assert feishu_payload["dry_run"] is True
    assert feishu_payload["msg_type"] == "interactive"
    assert feishu_payload["card"]["header"]["title"]["content"] == record.title

    assert wecom_payload["dry_run"] is True
    assert wecom_payload["msgtype"] == "markdown"
    assert "Execution failed" in wecom_payload["markdown"]["content"]
