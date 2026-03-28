"""Provider-agnostic LangChain chat model loader used by the review runtime.

Modified from GPT Researcher: https://github.com/assafelovic/gpt-researcher
Original license: Apache-2.0
This file has been adapted for this repository's review runtime.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import traceback
from enum import Enum
from typing import Any, Callable

import aiofiles
from colorama import Fore, Style, init

_SUPPORTED_PROVIDERS = {
    "aimlapi",
    "anthropic",
    "azure_openai",
    "bedrock",
    "cohere",
    "dashscope",
    "deepseek",
    "fireworks",
    "gigachat",
    "google_genai",
    "google_vertexai",
    "groq",
    "huggingface",
    "litellm",
    "mistralai",
    "netmind",
    "ollama",
    "openai",
    "openrouter",
    "together",
    "vllm_openai",
    "xai",
}

NO_SUPPORT_TEMPERATURE_MODELS = [
    "deepseek/deepseek-reasoner",
    "gpt-5",
    "gpt-5-mini",
    "o1",
    "o1-2024-12-17",
    "o1-mini",
    "o1-mini-2024-09-12",
    "o1-preview",
    "o3",
    "o3-2025-04-16",
    "o3-mini",
    "o3-mini-2025-01-31",
    "o4-mini",
    "o4-mini-2025-04-16",
]

SUPPORT_REASONING_EFFORT_MODELS = [
    "o3",
    "o3-2025-04-16",
    "o3-mini",
    "o3-mini-2025-01-31",
    "o4-mini",
    "o4-mini-2025-04-16",
]


class ReasoningEfforts(str, Enum):
    High = "high"
    Medium = "medium"
    Low = "low"


class ChatLogger:
    """Append request/response records to a JSONL file."""

    def __init__(self, path: str):
        self.path = path
        self._lock = asyncio.Lock()

    async def log_request(self, messages: Any, response: str) -> None:
        record = {
            "messages": messages,
            "response": response,
            "stacktrace": traceback.format_exc(),
        }
        async with self._lock:
            async with aiofiles.open(self.path, mode="a", encoding="utf-8") as handle:
                await handle.write(json.dumps(record, ensure_ascii=False) + "\n")


class GenericLLMProvider:
    """Thin wrapper around a LangChain chat model instance."""

    def __init__(self, llm: Any, *, chat_log: str | None = None, verbose: bool = True):
        self.llm = llm
        self.verbose = verbose
        self.chat_logger = ChatLogger(chat_log) if chat_log else None

    @classmethod
    def from_provider(
        cls,
        provider: str,
        chat_log: str | None = None,
        verbose: bool = True,
        **kwargs: Any,
    ) -> "GenericLLMProvider":
        try:
            factory = _provider_factories()[provider]
        except KeyError as exc:
            supported = ", ".join(sorted(_SUPPORTED_PROVIDERS))
            raise ValueError(f"Unsupported {provider}.\n\nSupported model providers are: {supported}") from exc
        llm = factory(dict(kwargs))
        return cls(llm, chat_log=chat_log, verbose=verbose)

    async def get_chat_response(
        self,
        messages: Any,
        stream: bool,
        websocket: Any | None = None,
        **kwargs: Any,
    ) -> str:
        if not stream:
            result = await self.llm.ainvoke(messages, **kwargs)
            text = _extract_text(result)
            if self.chat_logger:
                await self.chat_logger.log_request(messages, text)
            return text

        text_parts: list[str] = []
        init(autoreset=True)
        async for chunk in self.llm.astream(messages, **kwargs):
            fragment = _extract_text(chunk)
            if not fragment:
                continue
            text_parts.append(fragment)
            if websocket is not None:
                await websocket.send_json({"type": "stream", "output": fragment})
            elif self.verbose:
                print(Fore.GREEN + fragment, end="", flush=True)
        if self.verbose and text_parts and websocket is None:
            print(Style.RESET_ALL)
        final_text = "".join(text_parts)
        if self.chat_logger:
            await self.chat_logger.log_request(messages, final_text)
        return final_text


def _provider_factories() -> dict[str, Callable[[dict[str, Any]], Any]]:
    return {
        "aimlapi": _build_aimlapi,
        "anthropic": _build_anthropic,
        "azure_openai": _build_azure_openai,
        "bedrock": _build_bedrock,
        "cohere": _build_cohere,
        "dashscope": _build_dashscope,
        "deepseek": _build_deepseek,
        "fireworks": _build_fireworks,
        "gigachat": _build_gigachat,
        "google_genai": _build_google_genai,
        "google_vertexai": _build_google_vertexai,
        "groq": _build_groq,
        "huggingface": _build_huggingface,
        "litellm": _build_litellm,
        "mistralai": _build_mistralai,
        "netmind": _build_netmind,
        "ollama": _build_ollama,
        "openai": _build_openai,
        "openrouter": _build_openrouter,
        "together": _build_together,
        "vllm_openai": _build_vllm_openai,
        "xai": _build_xai,
    }


def _extract_text(payload: Any) -> str:
    content = getattr(payload, "content", payload)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if isinstance(item, dict):
                text_value = item.get("text")
                if isinstance(text_value, str):
                    parts.append(text_value)
                    continue
                nested_text = item.get("text", {}).get("value") if isinstance(item.get("text"), dict) else None
                if isinstance(nested_text, str):
                    parts.append(nested_text)
                    continue
            text_attr = getattr(item, "text", None)
            if isinstance(text_attr, str):
                parts.append(text_attr)
        return "".join(parts)
    return str(content or "")


def _check_pkg(package_name: str) -> None:
    if importlib.util.find_spec(package_name):
        return
    pip_name = package_name.replace("_", "-")
    raise ImportError(f"Unable to import {pip_name}. Please install with `pip install -U {pip_name}`")


def _build_openai(kwargs: dict[str, Any]) -> Any:
    _check_pkg("langchain_openai")
    from langchain_openai import ChatOpenAI

    kwargs.setdefault("openai_api_base", os.environ.get("OPENAI_BASE_URL"))
    kwargs = {key: value for key, value in kwargs.items() if value is not None}
    return ChatOpenAI(**kwargs)


def _build_anthropic(kwargs: dict[str, Any]) -> Any:
    _check_pkg("langchain_anthropic")
    from langchain_anthropic import ChatAnthropic

    return ChatAnthropic(**kwargs)


def _build_azure_openai(kwargs: dict[str, Any]) -> Any:
    _check_pkg("langchain_openai")
    from langchain_openai import AzureChatOpenAI

    model = kwargs.get("model")
    if model and "azure_deployment" not in kwargs:
        kwargs["azure_deployment"] = model
    return AzureChatOpenAI(**kwargs)


def _build_cohere(kwargs: dict[str, Any]) -> Any:
    _check_pkg("langchain_cohere")
    from langchain_cohere import ChatCohere

    return ChatCohere(**kwargs)


def _build_google_vertexai(kwargs: dict[str, Any]) -> Any:
    _check_pkg("langchain_google_vertexai")
    from langchain_google_vertexai import ChatVertexAI

    return ChatVertexAI(**kwargs)


def _build_google_genai(kwargs: dict[str, Any]) -> Any:
    _check_pkg("langchain_google_genai")
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(**kwargs)


def _build_fireworks(kwargs: dict[str, Any]) -> Any:
    _check_pkg("langchain_fireworks")
    from langchain_fireworks import ChatFireworks

    return ChatFireworks(**kwargs)


def _build_ollama(kwargs: dict[str, Any]) -> Any:
    _check_pkg("langchain_ollama")
    from langchain_ollama import ChatOllama

    base_url = os.environ.get("OLLAMA_BASE_URL")
    if base_url:
        kwargs.setdefault("base_url", base_url)
    return ChatOllama(**kwargs)


def _build_together(kwargs: dict[str, Any]) -> Any:
    _check_pkg("langchain_together")
    from langchain_together import ChatTogether

    return ChatTogether(**kwargs)


def _build_mistralai(kwargs: dict[str, Any]) -> Any:
    _check_pkg("langchain_mistralai")
    from langchain_mistralai import ChatMistralAI

    return ChatMistralAI(**kwargs)


def _build_huggingface(kwargs: dict[str, Any]) -> Any:
    _check_pkg("langchain_huggingface")
    from langchain_huggingface import ChatHuggingFace

    model_id = kwargs.pop("model", None) or kwargs.pop("model_name", None)
    if model_id is not None:
        kwargs["model_id"] = model_id
    return ChatHuggingFace(**kwargs)


def _build_groq(kwargs: dict[str, Any]) -> Any:
    _check_pkg("langchain_groq")
    from langchain_groq import ChatGroq

    return ChatGroq(**kwargs)


def _build_bedrock(kwargs: dict[str, Any]) -> Any:
    _check_pkg("langchain_aws")
    from langchain_aws import ChatBedrock

    model_id = kwargs.pop("model", None) or kwargs.pop("model_name", None)
    if model_id is not None:
        kwargs = {"model_id": model_id, "model_kwargs": kwargs}
    return ChatBedrock(**kwargs)


def _build_dashscope(kwargs: dict[str, Any]) -> Any:
    _check_pkg("langchain_openai")
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        openai_api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
        openai_api_key=os.environ["DASHSCOPE_API_KEY"],
        **kwargs,
    )


def _build_xai(kwargs: dict[str, Any]) -> Any:
    _check_pkg("langchain_xai")
    from langchain_xai import ChatXAI

    return ChatXAI(**kwargs)


def _build_deepseek(kwargs: dict[str, Any]) -> Any:
    _check_pkg("langchain_openai")
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        openai_api_base="https://api.deepseek.com",
        openai_api_key=os.environ["DEEPSEEK_API_KEY"],
        **kwargs,
    )


def _build_litellm(kwargs: dict[str, Any]) -> Any:
    _check_pkg("langchain_community")
    from langchain_community.chat_models.litellm import ChatLiteLLM

    return ChatLiteLLM(**kwargs)


def _build_gigachat(kwargs: dict[str, Any]) -> Any:
    _check_pkg("langchain_gigachat")
    from langchain_gigachat.chat_models import GigaChat

    kwargs.pop("model", None)
    return GigaChat(**kwargs)


def _build_openrouter(kwargs: dict[str, Any]) -> Any:
    _check_pkg("langchain_openai")
    from langchain_core.rate_limiters import InMemoryRateLimiter
    from langchain_openai import ChatOpenAI

    requests_per_second = float(os.environ.get("OPENROUTER_LIMIT_RPS", "1.0"))
    rate_limiter = InMemoryRateLimiter(
        requests_per_second=requests_per_second,
        check_every_n_seconds=0.1,
        max_bucket_size=10,
    )
    return ChatOpenAI(
        openai_api_base="https://openrouter.ai/api/v1",
        openai_api_key=os.environ["OPENROUTER_API_KEY"],
        request_timeout=180,
        rate_limiter=rate_limiter,
        **kwargs,
    )


def _build_vllm_openai(kwargs: dict[str, Any]) -> Any:
    _check_pkg("langchain_openai")
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        openai_api_base=os.environ["VLLM_OPENAI_API_BASE"],
        openai_api_key=os.environ["VLLM_OPENAI_API_KEY"],
        **kwargs,
    )


def _build_aimlapi(kwargs: dict[str, Any]) -> Any:
    _check_pkg("langchain_openai")
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        openai_api_base="https://api.aimlapi.com/v1",
        openai_api_key=os.environ["AIMLAPI_API_KEY"],
        **kwargs,
    )


def _build_netmind(kwargs: dict[str, Any]) -> Any:
    _check_pkg("langchain_netmind")
    from langchain_netmind import ChatNetmind

    return ChatNetmind(**kwargs)
