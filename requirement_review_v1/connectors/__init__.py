"""Source connector abstractions and shared schemas."""

from .base import BaseConnector
from .schemas import SourceDocument, SourceMetadata, SourceType

__all__ = [
    "BaseConnector",
    "SourceDocument",
    "SourceMetadata",
    "SourceType",
]
