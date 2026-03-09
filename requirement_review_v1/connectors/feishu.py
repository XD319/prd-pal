"""Controlled placeholder connector for Feishu-based sources."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from requirement_review_v1.connectors.base import BaseConnector
from requirement_review_v1.connectors.schemas import SourceDocument


@dataclass(frozen=True, slots=True)
class FeishuSourceRef:
    raw_source: str
    source_kind: str
    host: str
    path: str
    document_kind: str
    document_token: str
    wiki_space: str


@dataclass(frozen=True, slots=True)
class FeishuConfig:
    app_id: str
    app_secret: str
    base_url: str


class FeishuIntegrationUnavailableError(NotImplementedError):
    """Raised when a Feishu source is recognized but runtime integration is unavailable."""

    def __init__(self, message: str, *, metadata: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.metadata = dict(metadata or {})


class FeishuConnector(BaseConnector):
    """Recognize Feishu inputs and fail fast with explicit integration-boundary guidance."""

    FEISHU_SCHEME = "feishu"
    FEISHU_HOST_KEYWORDS = ("feishu.cn", "larksuite.com")
    APP_ID_ENV = "MARRDP_FEISHU_APP_ID"
    APP_SECRET_ENV = "MARRDP_FEISHU_APP_SECRET"
    BASE_URL_ENV = "MARRDP_FEISHU_OPEN_BASE_URL"
    DEFAULT_BASE_URL = "https://open.feishu.cn"

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
        source_ref = self._parse_source(source)
        config = self._read_config()
        metadata = self._build_unavailable_metadata(source_ref=source_ref, config=config)
        raise FeishuIntegrationUnavailableError(
            self._build_unavailable_message(source_ref=source_ref, config=config),
            metadata=metadata,
        )

    def _parse_source(self, source: str) -> FeishuSourceRef:
        normalized = str(source or "").strip()
        if not self.can_handle(normalized):
            raise ValueError(f"Unsupported Feishu source: {source}")

        parsed = urlparse(normalized)
        is_custom_scheme = parsed.scheme.lower() == self.FEISHU_SCHEME
        host = (parsed.netloc or "").strip().lower()
        path = parsed.path or ""
        segments = [segment for segment in path.split("/") if segment]

        if is_custom_scheme:
            source_kind = "feishu_scheme"
            document_kind = host or (segments[0] if segments else "unknown")
            wiki_space = segments[0] if document_kind == "wiki" and segments else ""
            document_token = segments[-1] if segments else ""
            resolved_host = self.FEISHU_SCHEME
        else:
            source_kind = "https_url"
            document_kind = self._detect_document_kind(segments)
            wiki_space = self._detect_wiki_space(document_kind=document_kind, segments=segments)
            document_token = segments[-1] if segments else ""
            resolved_host = host

        return FeishuSourceRef(
            raw_source=normalized,
            source_kind=source_kind,
            host=resolved_host,
            path=path,
            document_kind=document_kind,
            document_token=document_token,
            wiki_space=wiki_space,
        )

    def _read_config(self) -> FeishuConfig:
        return FeishuConfig(
            app_id=str(os.getenv(self.APP_ID_ENV, "") or "").strip(),
            app_secret=str(os.getenv(self.APP_SECRET_ENV, "") or "").strip(),
            base_url=str(os.getenv(self.BASE_URL_ENV, self.DEFAULT_BASE_URL) or self.DEFAULT_BASE_URL).strip(),
        )

    def _build_unavailable_message(self, *, source_ref: FeishuSourceRef, config: FeishuConfig) -> str:
        return (
            "Feishu connector fetching is intentionally unavailable in this repository build. "
            f"Recognized source '{source_ref.raw_source}' as a Feishu {source_ref.document_kind or 'document'} input. "
            f"Reserved optional integration env vars are {self.APP_ID_ENV}, {self.APP_SECRET_ENV}, and {self.BASE_URL_ENV}; "
            f"current config status: app_id={'set' if config.app_id else 'missing'}, app_secret={'set' if config.app_secret else 'missing'}. "
            "This open-source build does not ship an authenticated Feishu document client, so export the document locally or provide prd_text instead. "
            "Local file and public URL connectors remain the supported ingestion path and are not affected by Feishu integration state."
        )

    def _build_unavailable_metadata(self, *, source_ref: FeishuSourceRef, config: FeishuConfig) -> dict[str, Any]:
        return {
            "source_type": "feishu",
            "source_kind": source_ref.source_kind,
            "document_kind": source_ref.document_kind,
            "document_token_hint": self._mask_token(source_ref.document_token),
            "wiki_space_hint": source_ref.wiki_space,
            "host": source_ref.host,
            "path": source_ref.path,
            "app_id_configured": bool(config.app_id),
            "app_secret_configured": bool(config.app_secret),
            "base_url": config.base_url,
            "local_file_fallback_supported": True,
            "url_connector_unaffected": True,
        }

    def _detect_document_kind(self, segments: list[str]) -> str:
        for kind in ("wiki", "docx", "docs", "sheet", "base"):
            if kind in segments:
                return kind
        return "unknown"

    def _detect_wiki_space(self, *, document_kind: str, segments: list[str]) -> str:
        if document_kind != "wiki":
            return ""
        try:
            wiki_index = segments.index("wiki")
        except ValueError:
            return ""
        space_index = wiki_index + 1
        return segments[space_index] if len(segments) > space_index else ""

    def _mask_token(self, token: str) -> str:
        normalized = str(token or "").strip()
        if not normalized:
            return ""
        if len(normalized) <= 8:
            return "*" * len(normalized)
        return f"{normalized[:4]}...{normalized[-4:]}"
