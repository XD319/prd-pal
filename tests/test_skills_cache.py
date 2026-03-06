from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel, ConfigDict

from requirement_review_v1.skills.executor import SkillExecutor, SkillSpec


class SampleInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str


class SampleOutput(BaseModel):
    value: str


@pytest.fixture(autouse=True)
def clear_skill_cache():
    SkillExecutor.clear_cache()
    yield
    SkillExecutor.clear_cache()


def build_spec(*, handler: MagicMock, ttl_sec: int) -> SkillSpec:
    return SkillSpec(
        name="tests.sample_skill",
        input_model=SampleInput,
        output_model=SampleOutput,
        handler=handler,
        config_version="tests.sample_skill@v1",
        cache_ttl_sec=ttl_sec,
    )


@pytest.mark.asyncio
async def test_cache_disabled_calls_handler_on_every_execute():
    handler = MagicMock(side_effect=[{"value": "first"}, {"value": "second"}])
    spec = build_spec(handler=handler, ttl_sec=60)
    executor = SkillExecutor(cache_enabled=False)
    trace_first: dict = {}
    trace_second: dict = {}

    first = await executor.execute(spec, {"query": "same"}, trace=trace_first)
    second = await executor.execute(spec, {"query": "same"}, trace=trace_second)

    assert first.value == "first"
    assert second.value == "second"
    assert handler.call_count == 2
    assert trace_first["tests.sample_skill"]["cache_hit"] is False
    assert trace_second["tests.sample_skill"]["cache_hit"] is False


@pytest.mark.asyncio
async def test_cache_enabled_hits_cache_and_reports_cache_hit_to_trace_callback():
    handler = MagicMock(return_value={"value": "cached"})
    spec = build_spec(handler=handler, ttl_sec=60)
    executor = SkillExecutor(cache_enabled=True)
    trace = MagicMock()

    first = await executor.execute(spec, {"query": "same"}, trace=trace)
    second = await executor.execute(spec, {"query": "same"}, trace=trace)

    assert first.value == "cached"
    assert second.value == "cached"
    handler.assert_called_once()
    assert trace.call_count == 2
    first_name, first_trace = trace.call_args_list[0].args
    second_name, second_trace = trace.call_args_list[1].args
    assert first_name == "tests.sample_skill"
    assert second_name == "tests.sample_skill"
    assert first_trace["cache_hit"] is False
    assert second_trace["cache_hit"] is True
    assert second_trace["ttl_sec"] == 60


@pytest.mark.asyncio
async def test_ttl_expiry_reinvokes_handler_after_sleep():
    handler = MagicMock(side_effect=[{"value": "first"}, {"value": "second"}])
    spec = build_spec(handler=handler, ttl_sec=1)
    executor = SkillExecutor(cache_enabled=True)
    trace_first: dict = {}
    trace_second: dict = {}

    first = await executor.execute(spec, {"query": "same"}, trace=trace_first)
    time.sleep(1.1)
    second = await executor.execute(spec, {"query": "same"}, trace=trace_second)

    assert first.value == "first"
    assert second.value == "second"
    assert handler.call_count == 2
    assert trace_first["tests.sample_skill"]["cache_hit"] is False
    assert trace_second["tests.sample_skill"]["cache_hit"] is False


@pytest.mark.asyncio
async def test_cache_key_diff_payload_does_not_hit():
    handler = MagicMock(side_effect=[{"value": "alpha"}, {"value": "beta"}])
    spec = build_spec(handler=handler, ttl_sec=60)
    executor = SkillExecutor(cache_enabled=True)
    trace_first: dict = {}
    trace_second: dict = {}

    first = await executor.execute(spec, {"query": "alpha"}, trace=trace_first)
    second = await executor.execute(spec, {"query": "beta"}, trace=trace_second)

    assert first.value == "alpha"
    assert second.value == "beta"
    assert handler.call_count == 2
    assert trace_first["tests.sample_skill"]["cache_hit"] is False
    assert trace_second["tests.sample_skill"]["cache_hit"] is False
    assert (
        trace_first["tests.sample_skill"]["cache_key_hash"]
        != trace_second["tests.sample_skill"]["cache_key_hash"]
    )
