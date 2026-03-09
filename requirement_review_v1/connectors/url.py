"""Connector for controlled HTTP(S) text-page ingestion."""

from __future__ import annotations

import ipaddress
import socket
from html.parser import HTMLParser
from pathlib import PurePosixPath
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from requirement_review_v1.connectors.base import BaseConnector
from requirement_review_v1.connectors.schemas import SourceDocument, SourceMetadata, SourceType


class _URLOpener(Protocol):
    def __call__(self, request: Request, timeout: float = ...) -> Any: ...


class _HTMLTextExtractor(HTMLParser):
    """Convert simple HTML pages into readable plain text for review ingestion."""

    BLOCK_TAGS = {
        "article",
        "br",
        "div",
        "footer",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "li",
        "main",
        "ol",
        "p",
        "section",
        "table",
        "tr",
        "ul",
    }
    SKIP_TAGS = {"script", "style"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._title_parts: list[str] = []
        self._text_parts: list[str] = []
        self._tag_stack: list[str] = []

    @property
    def title(self) -> str:
        return " ".join(part.strip() for part in self._title_parts if part.strip()).strip()

    @property
    def text(self) -> str:
        return "".join(self._text_parts).strip()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        normalized = tag.lower()
        self._tag_stack.append(normalized)
        if normalized in self.BLOCK_TAGS:
            self._append_break()

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.lower()
        if normalized in self.BLOCK_TAGS:
            self._append_break()
        for index in range(len(self._tag_stack) - 1, -1, -1):
            if self._tag_stack[index] == normalized:
                del self._tag_stack[index]
                break

    def handle_data(self, data: str) -> None:
        if not data:
            return
        active_tags = set(self._tag_stack)
        if active_tags & self.SKIP_TAGS:
            return
        normalized = " ".join(data.split())
        if not normalized:
            return
        if "title" in active_tags:
            self._title_parts.append(normalized)
            return
        if self._text_parts and not self._text_parts[-1].endswith(("\n", " ")):
            self._text_parts.append(" ")
        self._text_parts.append(normalized)

    def _append_break(self) -> None:
        if not self._text_parts:
            return
        if self._text_parts[-1].endswith("\n\n"):
            return
        if self._text_parts[-1].endswith("\n"):
            self._text_parts.append("\n")
        else:
            self._text_parts.append("\n\n")


class URLConnector(BaseConnector):
    """Fetch public HTTP(S) text pages and normalize them into ``SourceDocument``."""

    SUPPORTED_SCHEMES = {"http", "https"}
    SUPPORTED_MIME_TYPES = {
        "application/xhtml+xml",
        "text/html",
        "text/markdown",
        "text/plain",
        "text/x-markdown",
    }
    MAX_RESPONSE_BYTES = 1_000_000
    DEFAULT_TIMEOUT_SECONDS = 10.0
    USER_AGENT = "marrdp-requirement-review/1.0"

    def __init__(
        self,
        *,
        opener: _URLOpener | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_response_bytes: int = MAX_RESPONSE_BYTES,
    ) -> None:
        self._opener = opener or urlopen
        self._timeout_seconds = timeout_seconds
        self._max_response_bytes = max_response_bytes

    def can_handle(self, source: str) -> bool:
        try:
            parsed = urlparse(str(source or "").strip())
        except ValueError:
            return False
        return parsed.scheme in self.SUPPORTED_SCHEMES and bool(parsed.netloc)

    def get_content(self, source: str) -> SourceDocument:
        normalized_source = str(source or "").strip()
        parsed = self._parse_supported_url(normalized_source)
        self._assert_public_host(parsed.hostname or "")

        request = Request(
            normalized_source,
            headers={
                "Accept": "text/markdown, text/html, text/plain;q=0.9, text/*;q=0.8",
                "User-Agent": self.USER_AGENT,
            },
            method="GET",
        )

        try:
            response = self._opener(request, timeout=self._timeout_seconds)
        except HTTPError as exc:
            raise ConnectionError(
                f"Failed to fetch URL source '{normalized_source}': HTTP {exc.code}"
            ) from exc
        except URLError as exc:
            raise ConnectionError(
                f"Network unavailable while fetching URL source '{normalized_source}': {self._format_network_reason(exc.reason)}"
            ) from exc
        except TimeoutError as exc:
            raise ConnectionError(
                f"Network unavailable while fetching URL source '{normalized_source}': request timed out"
            ) from exc

        with response:
            final_url = getattr(response, "geturl", lambda: normalized_source)()
            final_parsed = self._parse_supported_url(str(final_url or normalized_source).strip())
            self._assert_public_host(final_parsed.hostname or "")

            headers = getattr(response, "headers", None)
            content_type = self._resolve_content_type(headers)
            if not self._is_supported_content_type(content_type):
                raise ValueError(
                    "Unsupported URL content type: "
                    f"{content_type or '<missing>'}. Only text/plain, text/markdown, text/html, and other text/* pages are supported."
                )

            charset = self._resolve_charset(headers)
            raw_content = self._read_body(response, content_type=content_type)
            decoded_content = self._decode_body(raw_content, charset=charset)
            title, content_markdown = self._normalize_content(decoded_content, content_type, final_parsed.path)

        metadata = SourceMetadata(
            mime_type=content_type,
            encoding=charset,
            size_bytes=len(raw_content),
            extra={
                "requested_url": normalized_source,
                "final_url": final_parsed.geturl(),
            },
        )
        return SourceDocument(
            source_type=SourceType.url,
            source=final_parsed.geturl(),
            title=title,
            content_markdown=content_markdown,
            metadata=metadata,
        )

    def _parse_supported_url(self, source: str):
        if not self.can_handle(source):
            raise ValueError(f"Unsupported URL source: {source}")
        parsed = urlparse(source)
        if parsed.username or parsed.password:
            raise ValueError("URL sources with embedded credentials are not supported")
        return parsed

    def _assert_public_host(self, hostname: str) -> None:
        normalized_host = str(hostname or "").strip().strip(".").lower()
        if not normalized_host:
            raise ValueError("URL source is missing a hostname")
        if normalized_host in {"localhost", "0.0.0.0"} or normalized_host.endswith(".local"):
            raise ValueError(f"URL source must be publicly reachable: {hostname}")

        try:
            addresses = socket.getaddrinfo(normalized_host, None, proto=socket.IPPROTO_TCP)
        except socket.gaierror as exc:
            raise ConnectionError(
                f"Network unavailable while validating URL source '{hostname}': {exc.strerror or exc}"
            ) from exc

        for _family, _socktype, _proto, _canonname, sockaddr in addresses:
            ip_value = sockaddr[0]
            ip = ipaddress.ip_address(ip_value)
            if any(
                (
                    ip.is_private,
                    ip.is_loopback,
                    ip.is_link_local,
                    ip.is_multicast,
                    ip.is_reserved,
                    ip.is_unspecified,
                )
            ):
                raise ValueError(f"URL source must be publicly reachable: {hostname}")

    def _resolve_content_type(self, headers: Any) -> str:
        if headers is None:
            return ""
        content_type_getter = getattr(headers, "get_content_type", None)
        if callable(content_type_getter):
            return str(content_type_getter()).lower()
        getter = getattr(headers, "get", None)
        if callable(getter):
            return str(getter("Content-Type", "") or "").split(";", 1)[0].strip().lower()
        return ""

    def _resolve_charset(self, headers: Any) -> str:
        if headers is None:
            return "utf-8"
        charset_getter = getattr(headers, "get_content_charset", None)
        if callable(charset_getter):
            return str(charset_getter() or "utf-8")
        return "utf-8"

    def _is_supported_content_type(self, content_type: str) -> bool:
        normalized = str(content_type or "").strip().lower()
        return normalized.startswith("text/") or normalized in self.SUPPORTED_MIME_TYPES

    def _read_body(self, response: Any, *, content_type: str) -> bytes:
        declared_length = self._resolve_declared_length(getattr(response, "headers", None))
        if declared_length is not None and declared_length > self._max_response_bytes:
            raise ValueError(
                f"URL content too large to ingest safely: {declared_length} bytes exceeds {self._max_response_bytes} bytes"
            )

        raw_content = response.read(self._max_response_bytes + 1)
        if len(raw_content) > self._max_response_bytes:
            raise ValueError(
                f"URL content too large to ingest safely: exceeds {self._max_response_bytes} bytes for {content_type or 'unknown content'}"
            )
        return raw_content

    def _resolve_declared_length(self, headers: Any) -> int | None:
        if headers is None:
            return None
        getter = getattr(headers, "get", None)
        if not callable(getter):
            return None
        raw_value = getter("Content-Length")
        if raw_value in (None, ""):
            return None
        try:
            return int(str(raw_value))
        except (TypeError, ValueError):
            return None

    def _decode_body(self, raw_content: bytes, *, charset: str) -> str:
        try:
            return raw_content.decode(charset or "utf-8")
        except LookupError:
            return raw_content.decode("utf-8", errors="replace")
        except UnicodeDecodeError:
            return raw_content.decode(charset or "utf-8", errors="replace")

    def _normalize_content(self, content: str, content_type: str, path: str) -> tuple[str, str]:
        normalized_type = str(content_type or "").strip().lower()
        if normalized_type in {"text/html", "application/xhtml+xml"}:
            parser = _HTMLTextExtractor()
            parser.feed(content)
            parser.close()
            fallback_title = self._derive_title_from_path(path)
            title = parser.title or fallback_title
            text_content = parser.text or content.strip()
            return title, text_content
        return self._derive_title_from_path(path), content.strip()

    def _derive_title_from_path(self, path: str) -> str:
        normalized_path = str(path or "").strip() or "/"
        name = PurePosixPath(normalized_path).name
        if not name:
            return "remote-document"
        return PurePosixPath(name).stem or name

    def _format_network_reason(self, reason: object) -> str:
        if isinstance(reason, socket.timeout):
            return "request timed out"
        if isinstance(reason, socket.gaierror):
            return reason.strerror or str(reason)
        return str(reason or "unknown network error")
