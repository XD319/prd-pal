"""Shared helpers and annotated types for schema validation."""

from typing import Annotated, Any

from pydantic import BeforeValidator


def normalize_bool(v: Any) -> bool:
    """Coerce ``"true"`` / ``"false"`` strings (case-insensitive) to *bool*.

    Accepted truthy strings: ``"true"``, ``"1"``, ``"yes"``.
    Everything else maps to ``False`` (for str inputs) or falls through to
    ``bool(v)`` for other types.
    """
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "yes")
    return bool(v)


def safe_list(v: Any) -> list:
    """Guarantee a list value: ``None`` → ``[]``, bare scalar → ``[scalar]``."""
    if v is None:
        return []
    if isinstance(v, list):
        return v
    return [v]


NormalizedBool = Annotated[bool, BeforeValidator(normalize_bool)]
"""``bool`` that also accepts ``"true"`` / ``"false"`` strings."""

SafeStrList = Annotated[list[str], BeforeValidator(safe_list)]
"""``list[str]`` that coerces ``None`` → ``[]``."""
