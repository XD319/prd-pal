"""Source connector abstractions and shared schemas."""

from .auth import ConnectorAuthConfig, ConnectorAuthType
from .base import BaseConnector
from .errors import ConnectorErrorCode, ConnectorErrorPayload, get_connector_error_payload
from .feishu import FeishuConnector
from .local_file import LocalFileConnector
from .registry import ConnectorRegistry
from .schemas import SourceDocument, SourceMetadata, SourceType
from .url import URLConnector

__all__ = [
    "BaseConnector",
    "ConnectorAuthConfig",
    "ConnectorAuthType",
    "ConnectorErrorCode",
    "ConnectorErrorPayload",
    "ConnectorRegistry",
    "FeishuConnector",
    "LocalFileConnector",
    "SourceDocument",
    "SourceMetadata",
    "SourceType",
    "URLConnector",
    "get_connector_error_payload",
]
