"""Feishu dry-run payload renderer."""

from __future__ import annotations

from requirement_review_v1.notifications.base import BaseNotifier
from requirement_review_v1.notifications.models import NotificationEvent


class FeishuNotifier(BaseNotifier):
    channel = "feishu"
    description = "Render a Feishu interactive-card dry-run payload."

    def build_payload(self, event: NotificationEvent) -> dict[str, object]:
        metadata = event.metadata or {}
        lines = [
            f"Event Type: {event.event_type}",
            f"Run ID: {event.run_id or '-'}",
            f"Bundle ID: {event.bundle_id or '-'}",
            f"Task ID: {event.task_id or '-'}",
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
                    "title": {"tag": "plain_text", "content": event.title},
                    "template": "orange",
                },
                "elements": [
                    {"tag": "div", "text": {"tag": "lark_md", "content": event.summary or event.title}},
                    {"tag": "note", "elements": [{"tag": "plain_text", "content": " | ".join(lines)}]},
                ],
            },
        }
