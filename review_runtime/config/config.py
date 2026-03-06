"""Minimal runtime configuration for the requirement review system."""

from __future__ import annotations

import json
import os
from typing import Any

from review_runtime.llm_provider.generic.base import ReasoningEfforts, _SUPPORTED_PROVIDERS

DEFAULT_CONFIG: dict[str, Any] = {
    "FAST_LLM": "openai:gpt-4o-mini",
    "SMART_LLM": "openai:gpt-4.1",
    "STRATEGIC_LLM": "openai:o4-mini",
    "FAST_TOKEN_LIMIT": 3000,
    "SMART_TOKEN_LIMIT": 6000,
    "STRATEGIC_TOKEN_LIMIT": 4000,
    "TEMPERATURE": 0.4,
    "REPORT_SOURCE": "web",
    "DOC_PATH": "./my-docs",
    "LLM_KWARGS": {},
    "VERBOSE": False,
    "REASONING_EFFORT": "medium",
}


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
        self.reasoning_effort = self.parse_reasoning_effort(os.getenv("REASONING_EFFORT"))

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
    def _get_str(key: str, config: dict[str, Any]) -> str:
        value = os.getenv(key, config.get(key))
        return str(value) if value is not None else ""

    @staticmethod
    def _get_int(key: str, config: dict[str, Any]) -> int:
        value = os.getenv(key)
        if value is None:
            return int(config.get(key, 0))
        return int(value)

    @staticmethod
    def _get_float(key: str, config: dict[str, Any]) -> float:
        value = os.getenv(key)
        if value is None:
            return float(config.get(key, 0.0))
        return float(value)

    @staticmethod
    def _get_bool(key: str, config: dict[str, Any]) -> bool:
        value = os.getenv(key)
        if value is None:
            return bool(config.get(key, False))
        return value.strip().lower() in {"1", "true", "yes", "on"}

    @staticmethod
    def _get_dict(key: str, config: dict[str, Any]) -> dict[str, Any]:
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
