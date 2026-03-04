"""Unified structured LLM call helper for requirement_review_v1 agents.

Primary path:
- provider tools / function calling / structured output -> dict

Fallback path:
- plain-text JSON response -> json_repair -> dict
"""

from __future__ import annotations

import json
from typing import Any

import json_repair
from langchain_community.adapters.openai import convert_openai_messages
from langchain_core.utils.json import parse_json_markdown
from pydantic import BaseModel

from gpt_researcher.config.config import Config
from gpt_researcher.utils.llm import create_chat_completion, get_llm


class StructuredCallError(RuntimeError):
    """Raised when structured call cannot produce a valid dict output."""

    def __init__(
        self,
        message: str,
        *,
        raw_output: str = "",
        structured_mode: str = "unknown",
    ) -> None:
        super().__init__(message)
        self.raw_output = raw_output
        self.structured_mode = structured_mode


def _schema_dict(schema: type[BaseModel] | dict[str, Any]) -> dict[str, Any]:
    if isinstance(schema, dict):
        return schema
    if isinstance(schema, type) and issubclass(schema, BaseModel):
        return schema.model_json_schema()
    raise TypeError("schema must be a pydantic model class or a JSON schema dict")


def _provider_supports_tools(provider: str | None) -> bool:
    if not provider:
        return False
    # Best-effort allow-list for providers that commonly support OpenAI-style
    # tool/function calling through LangChain chat models.
    supported = {
        "openai",
        "azure_openai",
        "openrouter",
        "deepseek",
        "vllm_openai",
        "dashscope",
        "aimlapi",
    }
    return provider in supported


def _extract_dict_output(output: Any) -> dict[str, Any]:
    if isinstance(output, BaseModel):
        return output.model_dump(mode="python", by_alias=True)
    if isinstance(output, dict):
        return output
    if isinstance(output, str):
        parsed = parse_json_markdown(output, parser=json_repair.loads)
        if isinstance(parsed, dict):
            return parsed
    raise TypeError(f"structured output is not a dict-like object: {type(output)}")


def _fallback_prompt(prompt: str, schema: type[BaseModel] | dict[str, Any]) -> str:
    schema_json = json.dumps(_schema_dict(schema), ensure_ascii=False, indent=2)
    return (
        f"{prompt}\n\n"
        "Return valid JSON only. Do not wrap with markdown fences.\n"
        "The output MUST follow this JSON schema:\n"
        f"{schema_json}\n"
    )


async def llm_structured_call(
    *,
    prompt: str,
    schema: type[BaseModel] | dict[str, Any],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    """Call LLM and return schema-shaped dict output.

    Args:
        prompt: Full instruction text.
        schema: Pydantic model class or JSON schema dict.
        metadata: Mutable metadata dict with at least ``agent_name`` / ``run_id``.
            This function writes:
            - ``structured_mode``: ``tools`` or ``fallback``
            - ``raw_output``: raw model output text (best effort)
    """
    cfg = Config()
    provider = cfg.smart_llm_provider
    model = cfg.smart_llm_model
    llm_kwargs = dict(cfg.llm_kwargs or {})

    metadata.setdefault("agent_name", "unknown")
    metadata.setdefault("run_id", "")
    metadata["structured_mode"] = "fallback"
    metadata["raw_output"] = ""

    if _provider_supports_tools(provider):
        try:
            provider_kwargs: dict[str, Any] = {"model": model}
            provider_kwargs.update(llm_kwargs)
            provider_obj = get_llm(provider, **provider_kwargs)

            llm = provider_obj.llm
            schema_for_tools: Any = schema
            if isinstance(schema, dict):
                schema_for_tools = {
                    "name": f"{metadata['agent_name']}_output",
                    "description": f"Structured output for {metadata['agent_name']}",
                    "parameters": schema,
                }

            try:
                structured_llm = llm.with_structured_output(
                    schema_for_tools,
                    method="function_calling",
                )
            except TypeError:
                structured_llm = llm.with_structured_output(schema_for_tools)

            result = await structured_llm.ainvoke(prompt)
            output = _extract_dict_output(result)
            metadata["structured_mode"] = "tools"
            metadata["raw_output"] = json.dumps(output, ensure_ascii=False, indent=2)
            return output
        except Exception:
            # Any capability/runtime issue falls back to text JSON path.
            pass

    try:
        fallback_prompt = _fallback_prompt(prompt, schema)
        messages = convert_openai_messages([{"role": "user", "content": fallback_prompt}])
        raw = await create_chat_completion(
            model=model,
            messages=messages,
            temperature=0,
            llm_provider=provider,
            llm_kwargs=llm_kwargs,
        )
        metadata["structured_mode"] = "fallback"
        metadata["raw_output"] = raw or ""
        parsed = parse_json_markdown(raw, parser=json_repair.loads)
        if not isinstance(parsed, dict):
            raise StructuredCallError(
                "fallback parsed JSON is not an object",
                raw_output=raw or "",
                structured_mode="fallback",
            )
        return parsed
    except StructuredCallError:
        raise
    except Exception as exc:
        raise StructuredCallError(
            f"structured call failed: {exc}",
            raw_output=str(metadata.get("raw_output", "") or ""),
            structured_mode=str(metadata.get("structured_mode", "unknown")),
        ) from exc
