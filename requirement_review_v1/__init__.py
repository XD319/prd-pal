"""Backward-compatible import alias for the migrated prd_pal package."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path

__path__ = [str(Path(__file__).resolve().parent.parent / "prd_pal")]


def __getattr__(name: str):
    return getattr(import_module("prd_pal"), name)
