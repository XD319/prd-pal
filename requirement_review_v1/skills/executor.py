"""Skill executor with in-memory TTL caching and trace metadata."""

from __future__ import annotations

import hashlib
import inspect
import json
import os
import threading
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from pydantic import BaseModel, ValidationError

from ..utils.trace import trace_start

_DEFAULT_CACHE_TTL_SEC = 300
_CACHE_ENABLED_ENV = "SKILLS_CACHE_ENABLED"
_TRUE_VALUES = {"1", "true", "yes", "on"}

SkillHandler = Callable[[BaseModel], Any] | Callable[[BaseModel], Awaitable[Any]]
TraceSink = dict[str, Any] | Callable[[str, dict[str, Any]], None]


class SkillExecutionError(RuntimeError):
    """Raised when skill execution or validation fails."""


@dataclass(frozen=True)
class SkillSpec:
    """Runtime contract for an executable skill."""

    name: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    handler: SkillHandler
    config_version: str = "v1"
    cache_ttl_sec: int | None = None

    @property
    def ttl_sec(self) -> int:
        return self.cache_ttl_sec if self.cache_ttl_sec is not None else _DEFAULT_CACHE_TTL_SEC


class SkillExecutor:
    """Execute skills with optional TTL caching and per-call trace output."""

    _cache: dict[str, tuple[float, Any]] = {}
    _cache_lock = threading.Lock()

    def __init__(self, *, cache_enabled: bool | None = None) -> None:
        self._cache_enabled_override = cache_enabled

    async def execute(
        self,
        spec: SkillSpec,
        payload: dict[str, Any] | BaseModel,
        *,
        trace: TraceSink | None = None,
    ) -> BaseModel:
        validated_input = spec.input_model.model_validate(payload)
        cache_key_hash = _build_cache_key_hash(spec, validated_input)
        ttl_sec = max(0, spec.ttl_sec)
        cache_enabled = self._cache_enabled()
        span = trace_start(spec.name, model="none", input_chars=len(_canonical_input_json(validated_input)))

        cache_hit = False
        if cache_enabled and ttl_sec > 0:
            cached_output = self._get_cached_output(cache_key_hash, ttl_sec)
            if cached_output is not None:
                cache_hit = True
                output_model = _validate_output(spec, cached_output)
                trace_data = span.end(status="ok")
                trace_data.update(
                    {
                        "cache_hit": True,
                        "cache_key_hash": cache_key_hash,
                        "ttl_sec": ttl_sec,
                    }
                )
                _write_trace(trace, spec.name, trace_data)
                return output_model

        try:
            raw_output = spec.handler(validated_input)
            if inspect.isawaitable(raw_output):
                raw_output = await raw_output
            output_model = _validate_output(spec, raw_output)
        except ValidationError as exc:
            trace_data = span.end(status="error", error_message=str(exc))
            trace_data.update(
                {
                    "cache_hit": cache_hit,
                    "cache_key_hash": cache_key_hash,
                    "ttl_sec": ttl_sec,
                }
            )
            _write_trace(trace, spec.name, trace_data)
            raise SkillExecutionError(str(exc)) from exc
        except Exception as exc:
            trace_data = span.end(status="error", error_message=str(exc))
            trace_data.update(
                {
                    "cache_hit": cache_hit,
                    "cache_key_hash": cache_key_hash,
                    "ttl_sec": ttl_sec,
                }
            )
            _write_trace(trace, spec.name, trace_data)
            raise

        if cache_enabled and ttl_sec > 0:
            self._store_cached_output(cache_key_hash, output_model.model_dump(mode="python"))

        trace_data = span.end(status="ok")
        trace_data.update(
            {
                "cache_hit": False,
                "cache_key_hash": cache_key_hash,
                "ttl_sec": ttl_sec,
            }
        )
        _write_trace(trace, spec.name, trace_data)
        return output_model

    @classmethod
    def clear_cache(cls) -> None:
        with cls._cache_lock:
            cls._cache.clear()

    def _cache_enabled(self) -> bool:
        if self._cache_enabled_override is not None:
            return self._cache_enabled_override
        return _env_enabled(_CACHE_ENABLED_ENV, default=True)

    @classmethod
    def _get_cached_output(cls, cache_key_hash: str, ttl_sec: int) -> Any | None:
        now = time.time()
        with cls._cache_lock:
            cached = cls._cache.get(cache_key_hash)
            if cached is None:
                return None
            timestamp, output_data = cached
            if now - timestamp > ttl_sec:
                cls._cache.pop(cache_key_hash, None)
                return None
            return output_data

    @classmethod
    def _store_cached_output(cls, cache_key_hash: str, output_data: Any) -> None:
        with cls._cache_lock:
            cls._cache[cache_key_hash] = (time.time(), output_data)


def _env_enabled(name: str, *, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in _TRUE_VALUES


def _canonical_input_json(payload: BaseModel) -> str:
    dumped = payload.model_dump()
    return json.dumps(dumped, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _build_cache_key_hash(spec: SkillSpec, payload: BaseModel) -> str:
    material = "||".join((spec.name, _canonical_input_json(payload), spec.config_version))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _validate_output(spec: SkillSpec, raw_output: Any) -> BaseModel:
    try:
        return spec.output_model.model_validate(raw_output)
    except ValidationError as exc:
        raise SkillExecutionError(str(exc)) from exc


def _write_trace(trace: TraceSink | None, name: str, trace_data: dict[str, Any]) -> None:
    if trace is None:
        return
    if callable(trace):
        trace(name, trace_data)
        return
    trace[name] = trace_data
