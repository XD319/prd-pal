"""Adapter abstractions for downstream execution payload builders."""

from __future__ import annotations

from .base import BaseAdapter
from .claude_code import ClaudeCodeAdapter
from .codex import CodexAdapter

ADAPTER_REGISTRY = {
    "codex": CodexAdapter,
    "claude_code": ClaudeCodeAdapter,
}


def get_adapter(name: str) -> BaseAdapter:
    """Instantiate an adapter by executor name."""

    normalized = str(name or "").strip()
    try:
        return ADAPTER_REGISTRY[normalized]()
    except KeyError as exc:
        available = ", ".join(sorted(ADAPTER_REGISTRY))
        raise ValueError(f"unknown adapter '{normalized}'. Available: {available}") from exc


__all__ = [
    "ADAPTER_REGISTRY",
    "BaseAdapter",
    "ClaudeCodeAdapter",
    "CodexAdapter",
    "get_adapter",
]
