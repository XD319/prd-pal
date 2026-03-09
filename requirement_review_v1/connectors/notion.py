"""Authenticated Notion connector stub built on the shared auth foundation."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from urllib.parse import urlparse

from requirement_review_v1.connectors.auth import ConnectorAuthConfig, ConnectorAuthType
from requirement_review_v1.connectors.base import BaseConnector
from requirement_review_v1.connectors.errors import (
    ConnectorAuthError,
    ConnectorPermissionError,
    ConnectorUnsupportedSourceError,
    ConnectorValidationError,
)
from requirement_review_v1.connectors.schemas import SourceDocument


@dataclass(frozen=True, slots=True)
class NotionSourceRef:
    raw_source: str
    source_kind: str
    host: str
    path: str
    page_id: str


@dataclass(frozen=True, slots=True)
class NotionConfig:
    auth: ConnectorAuthConfig
    base_url: str
    api_version: str


class NotionAuthenticationError(ConnectorAuthError):
    """Raised when Notion credentials are missing or rejected."""


class NotionPermissionDeniedError(ConnectorPermissionError):
    """Raised when a Notion integration lacks access to a recognized page."""


class NotionNotReadyError(ConnectorUnsupportedSourceError):
    """Raised while the Notion connector is intentionally stubbed without live fetch support."""


class NotionConnector(BaseConnector):
    """Recognize Notion sources and validate config without performing live API calls yet."""

    NOTION_SCHEME = "notion"
    NOTION_HOST_KEYWORDS = ("notion.so", "notion.site")
    TOKEN_ENV = "MARRDP_NOTION_TOKEN"
    BASE_URL_ENV = "MARRDP_NOTION_API_BASE_URL"
    API_VERSION_ENV = "MARRDP_NOTION_API_VERSION"
    DEFAULT_BASE_URL = "https://api.notion.com/v1"
    DEFAULT_API_VERSION = "2022-06-28"
    _NOTION_ID_PATTERN = re.compile(r"([0-9a-fA-F]{32})")

    def can_handle(self, source: str) -> bool:
        normalized = str(source or "").strip()
        if not normalized:
            return False
        if normalized.lower().startswith(f"{self.NOTION_SCHEME}://"):
            return True

        try:
            parsed = urlparse(normalized)
        except ValueError:
            return False

        if parsed.scheme in {"http", "https"}:
            host = (parsed.netloc or "").lower()
            return any(keyword in host for keyword in self.NOTION_HOST_KEYWORDS)
        return False

    def get_content(self, source: str) -> SourceDocument:
        source_ref = self._parse_source(source)
        config = self._read_config()
        self._ensure_authenticated(config=config, source_ref=source_ref)
        raise NotionNotReadyError(
            f"Notion source '{source_ref.raw_source}' was recognized, but live Notion API fetching is not implemented yet.",
            source=source_ref.raw_source,
            details={
                "connector": "notion",
                "page_id": source_ref.page_id,
                "base_url": config.base_url,
                "api_version": config.api_version,
            },
        )

    def _parse_source(self, source: str) -> NotionSourceRef:
        normalized = str(source or "").strip()
        if not self.can_handle(normalized):
            raise ConnectorUnsupportedSourceError(
                f"Unsupported Notion source: {source}",
                source=str(source),
                details={"connector": "notion"},
            )

        parsed = urlparse(normalized)
        is_custom_scheme = parsed.scheme.lower() == self.NOTION_SCHEME
        host = (parsed.netloc or "").strip().lower()
        path = parsed.path or ""
        page_id = self._extract_page_id(path)
        if not page_id:
            raise ConnectorValidationError(
                f"Notion source is missing a recognizable page identifier: {normalized}",
                source=normalized,
                details={"connector": "notion", "path": path},
            )
        return NotionSourceRef(
            raw_source=normalized,
            source_kind="notion_scheme" if is_custom_scheme else "https_url",
            host=self.NOTION_SCHEME if is_custom_scheme else host,
            path=path,
            page_id=page_id,
        )

    def _read_config(self) -> NotionConfig:
        raw_base_url = str(os.getenv(self.BASE_URL_ENV, self.DEFAULT_BASE_URL) or self.DEFAULT_BASE_URL).strip()
        parsed_base_url = urlparse(raw_base_url)
        if parsed_base_url.scheme not in {"http", "https"} or not parsed_base_url.netloc:
            raise ConnectorValidationError(
                f"{self.BASE_URL_ENV} must be an absolute http(s) URL, got: {raw_base_url or '<empty>'}",
                details={"connector": "notion", "base_url_env": self.BASE_URL_ENV},
            )

        token = str(os.getenv(self.TOKEN_ENV, "") or "").strip()
        if token:
            auth = ConnectorAuthConfig(
                auth_type=ConnectorAuthType.bearer_token,
                token=token,
                extra={"token_env": self.TOKEN_ENV},
            )
        else:
            auth = ConnectorAuthConfig(extra={"expected_auth_type": "bearer_token", "token_env": self.TOKEN_ENV})

        return NotionConfig(
            auth=auth,
            base_url=raw_base_url.rstrip("/"),
            api_version=str(os.getenv(self.API_VERSION_ENV, self.DEFAULT_API_VERSION) or self.DEFAULT_API_VERSION).strip(),
        )

    def _ensure_authenticated(self, *, config: NotionConfig, source_ref: NotionSourceRef) -> None:
        if config.auth.auth_type != ConnectorAuthType.bearer_token:
            raise NotionAuthenticationError(
                "Notion authentication failed because an integration token is missing. "
                f"Set {self.TOKEN_ENV} before fetching '{source_ref.raw_source}'.",
                source=source_ref.raw_source,
                details={"connector": "notion", "auth_type": str(config.auth.auth_type)},
            )

    def _extract_page_id(self, path: str) -> str:
        segments = [segment for segment in str(path or "").split("/") if segment]
        if not segments:
            return ""

        last_segment = segments[-1]
        for token in reversed(last_segment.split("-")):
            candidate = str(token or "").strip().lower()
            if re.fullmatch(r"[0-9a-f]{32}", candidate):
                return candidate

        normalized_path = str(path or "").replace("-", "")
        matches = self._NOTION_ID_PATTERN.findall(normalized_path)
        return matches[-1].lower() if matches else ""

