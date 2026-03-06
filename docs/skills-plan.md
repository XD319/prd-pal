# Skills Execution Plan

## Cache strategy

- `requirement_review_v1.skills.executor.SkillExecutor` provides an in-memory TTL cache shared across skill executions in the current process.
- Cache is controlled by `SKILLS_CACHE_ENABLED`.
- Default: `true`.
- Accepted truthy values: `1`, `true`, `yes`, `on`.
- Any other explicit value disables cache.
- This is process-local only; separate CLI runs do not reuse cached entries.

## TTL behavior

- Default TTL is `300` seconds.
- A skill can override TTL via `SkillSpec.cache_ttl_sec`.
- If cache is disabled, or TTL is `0`, the handler always runs.
- On cache hit, the executor skips the handler but still validates cached output against `output_model` before returning it.
- Re-running `python -m requirement_review_v1.main` starts a new process and therefore starts with an empty cache.

## Cache key

Cache key hash is:

- `sha256(skill_name + normalized_input + skill_config_version)`

Where:

- `skill_name` is `SkillSpec.name`
- `normalized_input` is the canonical JSON generated from the validated `input_model` payload using `model_dump()` and sorted JSON keys
- `skill_config_version` is `SkillSpec.config_version`

## Trace fields

Each `SkillExecutor.execute()` call writes a trace entry under the skill name, for example `trace["risk_catalog.search"]`.

Trace includes:

- `cache_hit`
- `cache_key_hash`
- `ttl_sec`
- standard timing/status fields from `trace_start()`

## Current skill coverage

- `risk_catalog.search` uses TTL cache with `cache_ttl_sec=300`
- `risk_agent` consumes this skill trace and preserves the skill-level trace entry in `run_trace.json`

## Validation guidance

- Use unit tests that execute the same skill twice in the same `SkillExecutor` lifecycle to confirm `cache_hit=true` on the second call.
- For end-to-end validation, use a long-lived FastAPI or MCP process rather than two independent CLI invocations.

## Future work

- TODO: persistent cache backend for cross-process reuse, for example SQLite, file-based cache, or Redis.
