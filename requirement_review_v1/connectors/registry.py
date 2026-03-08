"""Connector registry for resolving normalized source handlers."""

from __future__ import annotations

from requirement_review_v1.connectors.base import BaseConnector
from requirement_review_v1.connectors.feishu import FeishuConnector
from requirement_review_v1.connectors.local_file import LocalFileConnector
from requirement_review_v1.connectors.url import URLConnector


class ConnectorRegistry:
    """Resolve a source string to the first connector that supports it."""

    def __init__(self, connectors: list[BaseConnector] | None = None) -> None:
        self._connectors = connectors or [FeishuConnector(), URLConnector(), LocalFileConnector()]

    def resolve(self, source: str) -> BaseConnector:
        for connector in self._connectors:
            if connector.can_handle(source):
                return connector
        raise ValueError(f"No connector available for source: {source}")
