"""Minimal runtime configuration for the requirement review system."""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Any, Iterator

from review_runtime.llm_provider.generic.base import ReasoningEfforts, _SUPPORTED_PROVIDERS

DEFAULT_CONFIG: dict[str, Any] = {
    "FAST_LLM": "openai:gpt-5-nano",
    "SMART_LLM": "openai:gpt-5-nano",
    "STRATEGIC_LLM": "openai:gpt-5-nano",
    "FAST_TOKEN_LIMIT": 3000,
    "SMART_TOKEN_LIMIT": 6000,
    "STRATEGIC_TOKEN_LIMIT": 4000,
    "TEMPERATURE": 0.2,
    "REPORT_SOURCE": "web",
    "DOC_PATH": "./my-docs",
    "LLM_KWARGS": {},
    "VERBOSE": False,
    "REASONING_EFFORT": "medium",
}

_MISSING = object()
_RUNTIME_CONFIG_OVERRIDES: ContextVar[dict[str, Any]] = ContextVar(
    "review_runtime_config_overrides",
    default={},
)


@contextmanager
def runtime_config_overrides(overrides: dict[str, Any] | None = None) -> Iterator[None]:
    current = _RUNTIME_CONFIG_OVERRIDES.get({})
    merged = dict(current) if isinstance(current, dict) else {}
    if isinstance(overrides, dict):
        for key, value in overrides.items():
            if value is not None:
                merged[str(key)] = value
    token: Token = _RUNTIME_CONFIG_OVERRIDES.set(merged)
    try:
        yield
    finally:
        _RUNTIME_CONFIG_OVERRIDES.reset(token)


class Config:
    """Load runtime settings from env vars with sensible local defaults."""

    def __init__(self, config_path: str | None = None):
        self.config_path = config_path
        config = self._load_config(config_path)

        self.fast_llm = self._get_str("FAST_LLM", config)
        self.smart_llm = self._get_str("SMART_LLM", config)
        self.strategic_llm = self._get_str("STRATEGIC_LLM", config)
        self.fast_token_limit = self._get_int("FAST_TOKEN_LIMIT", config)
        self.smart_token_limit = self._get_int("SMART_TOKEN_LIMIT", config)
        self.strategic_token_limit = self._get_int("STRATEGIC_TOKEN_LIMIT", config)
        self.temperature = self._get_float("TEMPERATURE", config)
        self.verbose = self._get_bool("VERBOSE", config)
        self.report_source = self._get_str("REPORT_SOURCE", config)
        self.doc_path = self._get_str("DOC_PATH", config)
        self.llm_kwargs = self._get_dict("LLM_KWARGS", config)
        self.reasoning_effort = self.parse_reasoning_effort(self._get_str("REASONING_EFFORT", config) or None)

        self.fast_llm_provider, self.fast_llm_model = self.parse_llm(self.fast_llm)
        self.smart_llm_provider, self.smart_llm_model = self.parse_llm(self.smart_llm)
        self.strategic_llm_provider, self.strategic_llm_model = self.parse_llm(self.strategic_llm)

        if self.report_source != "web" and self.doc_path:
            os.makedirs(self.doc_path, exist_ok=True)

    @staticmethod
    def _load_config(config_path: str | None) -> dict[str, Any]:
        if not config_path:
            return dict(DEFAULT_CONFIG)
        if not os.path.exists(config_path):
            return dict(DEFAULT_CONFIG)

        with open(config_path, "r", encoding="utf-8") as handle:
            loaded = json.load(handle)
        merged = dict(DEFAULT_CONFIG)
        if isinstance(loaded, dict):
            merged.update(loaded)
        return merged

    @staticmethod
    def _get_runtime_override(key: str) -> Any:
        overrides = _RUNTIME_CONFIG_OVERRIDES.get({})
        if isinstance(overrides, dict) and key in overrides:
            return overrides[key]
        return _MISSING

    @classmethod
    def _get_str(cls, key: str, config: dict[str, Any]) -> str:
        override = cls._get_runtime_override(key)
        if override is not _MISSING:
            return str(override) if override is not None else ""
        value = os.getenv(key, config.get(key))
        return str(value) if value is not None else ""

    @classmethod
    def _get_int(cls, key: str, config: dict[str, Any]) -> int:
        override = cls._get_runtime_override(key)
        if override is not _MISSING:
            return int(override)
        value = os.getenv(key)
        if value is None:
            return int(config.get(key, 0))
        return int(value)

    @classmethod
    def _get_float(cls, key: str, config: dict[str, Any]) -> float:
        override = cls._get_runtime_override(key)
        if override is not _MISSING:
            return float(override)
        value = os.getenv(key)
        if value is None:
            return float(config.get(key, 0.0))
        return float(value)

    @classmethod
    def _get_bool(cls, key: str, config: dict[str, Any]) -> bool:
        override = cls._get_runtime_override(key)
        if override is not _MISSING:
            if isinstance(override, bool):
                return override
            return str(override).strip().lower() in {"1", "true", "yes", "on"}
        value = os.getenv(key)
        if value is None:
            return bool(config.get(key, False))
        return value.strip().lower() in {"1", "true", "yes", "on"}

    @classmethod
    def _get_dict(cls, key: str, config: dict[str, Any]) -> dict[str, Any]:
        override = cls._get_runtime_override(key)
        if override is not _MISSING:
            if isinstance(override, dict):
                return dict(override)
            if isinstance(override, str):
                try:
                    parsed = json.loads(override)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{key} must be valid JSON") from exc
                if not isinstance(parsed, dict):
                    raise ValueError(f"{key} must be a JSON object")
                return parsed
            raise ValueError(f"{key} must be a JSON object")
        value = os.getenv(key)
        if value is None:
            loaded = config.get(key, {})
            return dict(loaded) if isinstance(loaded, dict) else {}
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{key} must be valid JSON") from exc
        if not isinstance(parsed, dict):
            raise ValueError(f"{key} must be a JSON object")
        return parsed

    @staticmethod
    def parse_llm(llm_str: str | None) -> tuple[str | None, str | None]:
        if llm_str is None:
            return None, None
        try:
            provider, model = llm_str.split(":", 1)
        except ValueError as exc:
            raise ValueError(
                "Set SMART_LLM or FAST_LLM as '<provider>:<model>', for example 'openai:gpt-4.1'"
            ) from exc
        if provider not in _SUPPORTED_PROVIDERS:
            raise ValueError(
                f"Unsupported {provider}. Supported providers: {', '.join(sorted(_SUPPORTED_PROVIDERS))}"
            )
        return provider, model

    @staticmethod
    def parse_reasoning_effort(reasoning_effort_str: str | None) -> str:
        if reasoning_effort_str is None:
            return ReasoningEfforts.Medium.value
        valid = {effort.value for effort in ReasoningEfforts}
        if reasoning_effort_str not in valid:
            raise ValueError(
                f"Invalid reasoning effort: {reasoning_effort_str}. Valid options: {', '.join(sorted(valid))}"
            )
        return reasoning_effort_str
