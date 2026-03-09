from __future__ import annotations

import pytest

from requirement_review_v1.connectors import ConnectorRegistry, NotionConnector, get_connector_error_payload
from requirement_review_v1.connectors.errors import ConnectorValidationError
from requirement_review_v1.connectors.notion import NotionAuthenticationError, NotionNotReadyError


NOTION_PAGE_ID = "0123456789abcdef0123456789abcdef"
NOTION_PAGE_URL = f"https://workspace.notion.site/Product-Spec-{NOTION_PAGE_ID}"


@pytest.fixture
def notion_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MARRDP_NOTION_TOKEN", "secret_notion_token")
    monkeypatch.setenv("MARRDP_NOTION_API_BASE_URL", "https://api.notion.example.test/v1")
    monkeypatch.setenv("MARRDP_NOTION_API_VERSION", "2022-06-28")


def test_notion_connector_can_handle_custom_scheme_and_notion_urls() -> None:
    connector = NotionConnector()

    assert connector.can_handle(f"notion://page/{NOTION_PAGE_ID}") is True
    assert connector.can_handle(NOTION_PAGE_URL) is True
    assert connector.can_handle("https://docs.example.com/spec") is False


def test_connector_registry_routes_notion_sources() -> None:
    connector = ConnectorRegistry().resolve(NOTION_PAGE_URL)

    assert isinstance(connector, NotionConnector)


def test_notion_connector_requires_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MARRDP_NOTION_TOKEN", raising=False)

    with pytest.raises(NotionAuthenticationError, match="authentication failed") as exc_info:
        NotionConnector().get_content(f"notion://page/{NOTION_PAGE_ID}")

    payload = get_connector_error_payload(exc_info.value)
    assert payload is not None
    assert payload.model_dump()["code"] == "authentication_failed"
    assert "MARRDP_NOTION_TOKEN" in payload.message


def test_notion_connector_validates_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MARRDP_NOTION_TOKEN", "secret_notion_token")
    monkeypatch.setenv("MARRDP_NOTION_API_BASE_URL", "not-a-url")

    with pytest.raises(ConnectorValidationError, match="MARRDP_NOTION_API_BASE_URL"):
        NotionConnector().get_content(NOTION_PAGE_URL)


def test_notion_connector_uses_shared_foundation_for_stubbed_not_ready_flow(notion_env: None) -> None:
    with pytest.raises(NotionNotReadyError, match="not implemented yet") as exc_info:
        NotionConnector().get_content(NOTION_PAGE_URL)

    payload = get_connector_error_payload(exc_info.value)
    assert payload is not None
    assert payload.model_dump()["code"] == "unsupported_source"
    assert payload.details == {
        "connector": "notion",
        "page_id": NOTION_PAGE_ID,
        "base_url": "https://api.notion.example.test/v1",
        "api_version": "2022-06-28",
    }
