"""Source connector abstractions and shared schemas."""

from .base import BaseConnector
from .local_file import LocalFileConnector
from .registry import ConnectorRegistry
from .schemas import SourceDocument, SourceMetadata, SourceType
from .url import URLConnector

__all__ = [
    "BaseConnector",
    "ConnectorRegistry",
    "LocalFileConnector",
    "SourceDocument",
    "SourceMetadata",
    "SourceType",
    "URLConnector",
]
