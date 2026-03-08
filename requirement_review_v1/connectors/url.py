"""Connector placeholder for URL-based requirement sources."""

from __future__ import annotations

from urllib.parse import urlparse

from requirement_review_v1.connectors.base import BaseConnector
from requirement_review_v1.connectors.schemas import SourceDocument


class URLConnector(BaseConnector):
    """Validate HTTP(S) URLs and reserve the fetch implementation for later."""

    SUPPORTED_SCHEMES = {"http", "https"}

    def can_handle(self, source: str) -> bool:
        try:
            parsed = urlparse(source)
        except ValueError:
            return False
        return parsed.scheme in self.SUPPORTED_SCHEMES and bool(parsed.netloc)

    def get_content(self, source: str) -> SourceDocument:
        if not self.can_handle(source):
            raise ValueError(f"Unsupported URL source: {source}")
        raise NotImplementedError("URL connector fetching is not implemented in this version.")
