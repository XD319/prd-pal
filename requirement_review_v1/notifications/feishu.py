"""Feishu notification renderer and sender."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from requirement_review_v1.notifications.base import BaseNotifier
from requirement_review_v1.notifications.models import (
    NotificationDeliveryResult,
    NotificationEvent,
    NotificationType,
)

_FALSE_VALUES = {"0", "false", "no", "off"}
_DETAIL_BASE_URL_ENVS = (
    "MARRDP_FEISHU_NOTIFICATION_DETAIL_BASE_URL",
    "MARRDP_PUBLIC_BASE_URL",
    "MARRDP_APP_BASE_URL",
)


@dataclass(frozen=True, slots=True)
class FeishuNotifierConfig:
    webhook_url: str = ""
    detail_base_url: str = ""
    dry_run: bool = True
    timeout_seconds: float = 10.0


@dataclass(frozen=True, slots=True)
class FeishuHTTPResponse:
    status_code: int
    json_body: dict[str, Any]


class _FeishuHTTPClient(Protocol):
    def post_json(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
        timeout_seconds: float = 10.0,
    ) -> FeishuHTTPResponse: ...


class _DefaultFeishuHTTPClient:
    USER_AGENT = "marrdp-feishu-notifier/1.0"

    def post_json(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
        timeout_seconds: float = 10.0,
    ) -> FeishuHTTPResponse:
        request_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": self.USER_AGENT,
        }
        if headers:
            request_headers.update(headers)

        request = Request(
            url,
            data=json.dumps(json_body or {}).encode("utf-8"),
            headers=request_headers,
            method="POST",
        )
        try:
            response = urlopen(request, timeout=timeout_seconds)
        except HTTPError as exc:
            return FeishuHTTPResponse(
                status_code=int(exc.code),
                json_body=_decode_json_body(exc.read()),
            )
        except URLError as exc:
            raise RuntimeError(f"Feishu notification delivery failed: {exc.reason or exc}") from exc
        except TimeoutError as exc:
            raise RuntimeError("Feishu notification delivery failed: request timed out") from exc

        with response:
            status_code_getter = getattr(response, "getcode", None)
            status_code = int(status_code_getter()) if callable(status_code_getter) else 200
            return FeishuHTTPResponse(
                status_code=status_code,
                json_body=_decode_json_body(response.read()),
            )


def _decode_json_body(raw_body: bytes) -> dict[str, Any]:
    normalized = bytes(raw_body or b"").strip()
    if not normalized:
        return {}
    try:
        decoded = json.loads(normalized.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"message": normalized.decode("utf-8", errors="replace")}
    return decoded if isinstance(decoded, dict) else {"data": decoded}


def _env_disabled(name: str, *, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in _FALSE_VALUES


def _env_float(name: str, *, default: float, minimum: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return max(minimum, float(raw.strip()))
    except ValueError:
        return default


def load_feishu_notifier_config() -> FeishuNotifierConfig:
    webhook_url = str(os.getenv("MARRDP_FEISHU_NOTIFICATION_WEBHOOK_URL", "") or "").strip()
    detail_base_url = ""
    for env_name in _DETAIL_BASE_URL_ENVS:
        candidate = str(os.getenv(env_name, "") or "").strip()
        if candidate:
            detail_base_url = candidate.rstrip("/")
            break
    return FeishuNotifierConfig(
        webhook_url=webhook_url,
        detail_base_url=detail_base_url,
        dry_run=_env_disabled("MARRDP_FEISHU_NOTIFICATION_DRY_RUN", default=True),
        timeout_seconds=_env_float("MARRDP_FEISHU_NOTIFICATION_TIMEOUT_SEC", default=10.0, minimum=1.0),
    )


def _normalize_review_status(event: NotificationEvent) -> str:
    metadata = event.metadata or {}
    status_from_metadata = str(metadata.get("review_run_status") or "").strip().lower()
    if status_from_metadata:
        return status_from_metadata

    mapping = {
        NotificationType.review_submitted: "submitted",
        NotificationType.review_running: "running",
        NotificationType.review_completed: "completed",
        NotificationType.review_failed: "failed",
        NotificationType.clarification_required: "clarification_required",
        NotificationType.execution_completed: "completed",
        NotificationType.execution_failed: "failed",
    }
    return mapping.get(event.event_type, "running")


def _status_label(status: str) -> str:
    mapping = {
        "submitted": "Submitted",
        "running": "Running",
        "completed": "Completed",
        "failed": "Failed",
        "clarification_required": "Clarification Required",
    }
    return mapping.get(status, status.replace("_", " ").title() or "Running")


def _status_template(status: str) -> str:
    mapping = {
        "submitted": "wathet",
        "running": "blue",
        "completed": "green",
        "failed": "red",
        "clarification_required": "orange",
    }
    return mapping.get(status, "blue")


class FeishuCardRenderer:
    def __init__(self, *, config: FeishuNotifierConfig | None = None) -> None:
        self._config = config or load_feishu_notifier_config()

    def render(self, event: NotificationEvent) -> dict[str, object]:
        status = _normalize_review_status(event)
        summary = str(event.summary or event.title or "").strip() or f"Review {status.replace('_', ' ')}."
        detail_url = self._resolve_detail_url(event)
        metadata = event.metadata or {}
        actor = str(metadata.get("actor") or "").strip()
        question_count = int(metadata.get("clarification_question_count", 0) or 0)

        note_segments = [f"Run ID: {event.run_id or '-'}", f"Status: {_status_label(status)}"]
        if actor:
            note_segments.append(f"Actor: {actor}")
        if question_count:
            note_segments.append(f"Questions: {question_count}")

        elements: list[dict[str, Any]] = [
            {
                "tag": "div",
                "fields": [
                    {
                        "is_short": True,
                        "text": {"tag": "lark_md", "content": f"**Run ID**\n`{event.run_id or '-'}`"},
                    },
                    {
                        "is_short": True,
                        "text": {"tag": "lark_md", "content": f"**Status**\n{_status_label(status)}"},
                    },
                ],
            },
            {"tag": "div", "text": {"tag": "lark_md", "content": summary}},
            {"tag": "note", "elements": [{"tag": "plain_text", "content": " | ".join(note_segments)}]},
        ]
        if detail_url:
            elements.append(
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "type": "primary",
                            "text": {"tag": "plain_text", "content": "查看详情"},
                            "url": detail_url,
                        }
                    ],
                }
            )

        return {
            "channel": "feishu",
            "dry_run": True,
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True, "enable_forward": True},
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": f"{_status_label(status)} | {event.run_id or event.title}",
                    },
                    "template": _status_template(status),
                },
                "elements": elements,
            },
        }

    def _resolve_detail_url(self, event: NotificationEvent) -> str:
        metadata = event.metadata or {}
        explicit_detail_url = str(metadata.get("detail_url") or "").strip()
        if explicit_detail_url:
            return explicit_detail_url
        run_id = str(event.run_id or "").strip()
        if not run_id:
            return ""
        base_url = self._config.detail_base_url
        if not base_url:
            return f"/run/{run_id}"
        return f"{base_url}/run/{run_id}"


class FeishuWebhookSender:
    def __init__(
        self,
        *,
        config: FeishuNotifierConfig | None = None,
        http_client: _FeishuHTTPClient | None = None,
    ) -> None:
        self._config = config or load_feishu_notifier_config()
        self._http_client = http_client or _DefaultFeishuHTTPClient()

    def send(self, event: NotificationEvent, payload: dict[str, object]) -> NotificationDeliveryResult:
        normalized_payload = dict(payload) if isinstance(payload, dict) else {}
        effective_dry_run = self._config.dry_run or not self._config.webhook_url
        normalized_payload["dry_run"] = effective_dry_run

        delivery_metadata = {
            "mode": "dry_run" if effective_dry_run else "webhook",
        }
        if self._config.webhook_url:
            parsed = urlparse(self._config.webhook_url)
            delivery_metadata["target_host"] = parsed.netloc

        if effective_dry_run:
            return NotificationDeliveryResult(
                payload=normalized_payload,
                delivery_metadata=delivery_metadata,
                dry_run=True,
            )

        response = self._http_client.post_json(
            self._config.webhook_url,
            json_body=normalized_payload,
            timeout_seconds=self._config.timeout_seconds,
        )
        if response.status_code < 200 or response.status_code >= 300:
            raise RuntimeError(
                f"Feishu notification delivery failed with HTTP {response.status_code}: {response.json_body!r}"
            )
        api_code = response.json_body.get("code")
        if api_code not in (None, 0):
            raise RuntimeError(f"Feishu notification delivery failed with code={api_code}: {response.json_body!r}")

        delivery_metadata["status_code"] = response.status_code
        return NotificationDeliveryResult(
            payload=normalized_payload,
            delivery_metadata=delivery_metadata,
            dry_run=False,
        )


class FeishuNotifier(BaseNotifier):
    channel = "feishu"
    description = "Render and optionally dispatch a Feishu interactive-card notification."

    def __init__(
        self,
        *,
        renderer: FeishuCardRenderer | None = None,
        sender: FeishuWebhookSender | None = None,
    ) -> None:
        self._renderer = renderer or FeishuCardRenderer()
        self._sender = sender or FeishuWebhookSender()

    def build_payload(self, event: NotificationEvent) -> dict[str, object]:
        payload = self._renderer.render(event)
        payload.setdefault("channel", self.channel)
        return payload

    def send_payload(
        self,
        event: NotificationEvent,
        payload: dict[str, object],
    ) -> NotificationDeliveryResult:
        return self._sender.send(event, payload)
