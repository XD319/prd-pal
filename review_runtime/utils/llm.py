"""Shared LLM helpers for the requirement review workflow."""

from __future__ import annotations

import logging
import os
from typing import Any

from review_runtime.llm_provider.generic.base import (
    NO_SUPPORT_TEMPERATURE_MODELS,
    SUPPORT_REASONING_EFFORT_MODELS,
    ReasoningEfforts,
)


def get_llm(llm_provider: str, **kwargs):
    from review_runtime.llm_provider import GenericLLMProvider

    return GenericLLMProvider.from_provider(llm_provider, **kwargs)


async def create_chat_completion(
    messages: list[dict[str, str]],
    model: str | None = None,
    temperature: float | None = 0.4,
    max_tokens: int | None = 4000,
    llm_provider: str | None = None,
    stream: bool = False,
    websocket: Any | None = None,
    llm_kwargs: dict[str, Any] | None = None,
    reasoning_effort: str | None = ReasoningEfforts.Medium.value,
    **kwargs,
) -> str:
    if model is None:
        raise ValueError("Model cannot be None")
    if max_tokens is not None and max_tokens > 32001:
        raise ValueError(f"Max tokens cannot be more than 32,000, but got {max_tokens}")

    provider_kwargs: dict[str, Any] = {"model": model}
    if llm_kwargs:
        provider_kwargs.update(llm_kwargs)

    if model in SUPPORT_REASONING_EFFORT_MODELS:
        provider_kwargs["reasoning_effort"] = reasoning_effort

    if model not in NO_SUPPORT_TEMPERATURE_MODELS:
        provider_kwargs["temperature"] = temperature
        provider_kwargs["max_tokens"] = max_tokens
    else:
        provider_kwargs["temperature"] = None
        provider_kwargs["max_tokens"] = None

    if llm_provider == "openai":
        base_url = os.environ.get("OPENAI_BASE_URL")
        if base_url:
            provider_kwargs["openai_api_base"] = base_url

    provider = get_llm(llm_provider, **provider_kwargs)
    for _ in range(10):
        return await provider.get_chat_response(messages, stream, websocket, **kwargs)

    logging.error("Failed to get response from %s API", llm_provider)
    raise RuntimeError(f"Failed to get response from {llm_provider} API")
