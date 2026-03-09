from __future__ import annotations

import os

import pytest

from requirement_review_v1.connectors import ConnectorRegistry, FeishuConnector
from requirement_review_v1.connectors.feishu import FeishuIntegrationUnavailableError


def test_feishu_connector_can_handle_custom_scheme_and_lark_urls() -> None:
    connector = FeishuConnector()

    assert connector.can_handle("feishu://wiki/team-space/doc-token") is True
    assert connector.can_handle("https://tenant.feishu.cn/wiki/team-space/doc-token") is True
    assert connector.can_handle("https://tenant.larksuite.com/docx/doc-token") is True
    assert connector.can_handle("https://openai.com/spec") is False


def test_connector_registry_routes_feishu_sources() -> None:
    connector = ConnectorRegistry().resolve("feishu://wiki/team-space/doc-token")

    assert isinstance(connector, FeishuConnector)


def test_feishu_connector_raises_structured_unavailable_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MARRDP_FEISHU_APP_ID", "app-id")
    monkeypatch.delenv("MARRDP_FEISHU_APP_SECRET", raising=False)
    monkeypatch.setenv("MARRDP_FEISHU_OPEN_BASE_URL", "https://open.feishu.example.test")

    with pytest.raises(FeishuIntegrationUnavailableError) as exc_info:
        FeishuConnector().get_content("feishu://wiki/team-space/doc-token-1234")

    error = exc_info.value
    assert "intentionally unavailable" in str(error)
    assert "MARRDP_FEISHU_APP_ID" in str(error)
    assert error.metadata == {
        "source_type": "feishu",
        "source_kind": "feishu_scheme",
        "document_kind": "wiki",
        "document_token_hint": "doc-...1234",
        "wiki_space_hint": "team-space",
        "host": "feishu",
        "path": "/team-space/doc-token-1234",
        "app_id_configured": True,
        "app_secret_configured": False,
        "base_url": "https://open.feishu.example.test",
        "local_file_fallback_supported": True,
        "url_connector_unaffected": True,
    }


def test_feishu_connector_rejects_non_feishu_sources() -> None:
    with pytest.raises(ValueError, match="Unsupported Feishu source"):
        FeishuConnector().get_content("https://openai.com/spec")
