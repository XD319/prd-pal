"""Notification dispatch abstractions and persistence helpers."""

from .base import BaseNotifier, default_notifiers, resolve_notifiers
from .dispatcher import (
    NOTIFICATIONS_FILENAME,
    append_notification_record,
    build_notification_event,
    build_notification_record,
    dispatch_notification,
    notifications_path,
    read_notification_records,
    record_dry_run_notification,
)
from .feishu import FeishuNotifier
from .models import (
    DispatchStatus,
    NotificationDispatchRecord,
    NotificationDispatchResult,
    NotificationEvent,
    NotificationStatus,
    NotificationType,
)
from .wecom import WeComNotifier

__all__ = [
    "NOTIFICATIONS_FILENAME",
    "BaseNotifier",
    "DispatchStatus",
    "FeishuNotifier",
    "NotificationDispatchRecord",
    "NotificationDispatchResult",
    "NotificationEvent",
    "NotificationStatus",
    "NotificationType",
    "WeComNotifier",
    "append_notification_record",
    "build_notification_event",
    "build_notification_record",
    "default_notifiers",
    "dispatch_notification",
    "notifications_path",
    "read_notification_records",
    "record_dry_run_notification",
    "resolve_notifiers",
]
