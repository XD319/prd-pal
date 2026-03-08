"""Feishu dry-run payload renderer."""

from __future__ import annotations

from requirement_review_v1.notifications.base import BaseNotifier, NotificationRecord


class FeishuNotifier(BaseNotifier):
    channel = "feishu"
    description = "Render a Feishu interactive-card dry-run payload."

    def build_payload(self, record: NotificationRecord) -> dict[str, object]:
        metadata = record.metadata or {}
        lines = [
            f"Notification Type: {record.notification_type}",
            f"Run ID: {record.run_id or '-'}",
            f"Bundle ID: {record.bundle_id or '-'}",
            f"Task ID: {record.task_id or '-'}",
        ]
        actor = str(metadata.get("actor") or "").strip()
        if actor:
            lines.append(f"Actor: {actor}")
        tool_name = str(metadata.get("tool_name") or "").strip()
        if tool_name:
            lines.append(f"Source Tool: {tool_name}")

        return {
            "channel": self.channel,
            "dry_run": True,
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": record.title},
                    "template": "orange",
                },
                "elements": [
                    {"tag": "div", "text": {"tag": "lark_md", "content": record.summary or record.title}},
                    {"tag": "note", "elements": [{"tag": "plain_text", "content": " | ".join(lines)}]},
                ],
            },
        }
