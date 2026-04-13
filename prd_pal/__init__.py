"""Stable public package namespace for prd-pal.

The implementation still lives in ``requirement_review_v1`` for now.
This package provides forward-looking entrypoints without forcing a
one-shot internal module rename.
"""

from importlib import import_module

__all__ = ["main", "run_cli"]


def __getattr__(name: str):
    if name == "main":
        return import_module("prd_pal.main")
    if name == "run_cli":
        return import_module("requirement_review_v1.main").run_cli
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
