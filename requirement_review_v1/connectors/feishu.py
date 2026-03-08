"""Controlled placeholder connector for Feishu-based sources."""

from __future__ import annotations

from urllib.parse import urlparse

from requirement_review_v1.connectors.base import BaseConnector
from requirement_review_v1.connectors.schemas import SourceDocument


class FeishuConnector(BaseConnector):
    """Recognize Feishu tokens and URLs without performing network calls."""

    FEISHU_SCHEME = "feishu"
    FEISHU_HOST_KEYWORDS = ("feishu.cn", "larksuite.com")

    def can_handle(self, source: str) -> bool:
        normalized = str(source or "").strip()
        if not normalized:
            return False

        if normalized.lower().startswith(f"{self.FEISHU_SCHEME}://"):
            return True

        try:
            parsed = urlparse(normalized)
        except ValueError:
            return False

        if parsed.scheme in {"http", "https"}:
            host = (parsed.netloc or "").lower()
            return any(keyword in host for keyword in self.FEISHU_HOST_KEYWORDS)
        return False

    def get_content(self, source: str) -> SourceDocument:
        if not self.can_handle(source):
            raise ValueError(f"Unsupported Feishu source: {source}")
        raise NotImplementedError(
            "Feishu connector fetching is not implemented in this version. "
            "Export the document locally or provide prd_text for now."
        )
