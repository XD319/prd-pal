"""WeCom dry-run payload renderer."""

from __future__ import annotations

from requirement_review_v1.notifications.base import BaseNotifier, NotificationRecord


class WeComNotifier(BaseNotifier):
    channel = "wecom"
    description = "Render a WeCom markdown-message dry-run payload."

    def build_payload(self, record: NotificationRecord) -> dict[str, object]:
        metadata = record.metadata or {}
        detail_lines = [
            f"> Notification Type: `{record.notification_type}`",
            f"> Run ID: `{record.run_id or '-'}`",
            f"> Bundle ID: `{record.bundle_id or '-'}`",
            f"> Task ID: `{record.task_id or '-'}`",
        ]
        actor = str(metadata.get("actor") or "").strip()
        if actor:
            detail_lines.append(f"> Actor: `{actor}`")
        tool_name = str(metadata.get("tool_name") or "").strip()
        if tool_name:
            detail_lines.append(f"> Source Tool: `{tool_name}`")

        return {
            "channel": self.channel,
            "dry_run": True,
            "msgtype": "markdown",
            "markdown": {
                "content": "\n".join([f"**{record.title}**", record.summary or record.title, *detail_lines]),
            },
        }
