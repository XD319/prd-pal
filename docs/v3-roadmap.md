# v3 Roadmap

## v3 Goals

v3 focuses on three capabilities:

1. Reusable Subflow
2. Parallelization
3. Tool Result Caching

## MVP Deliverables

1. Define a reusable subflow mechanism so repeated review and planning steps can be composed once and invoked across flows.
2. Add parallel execution for independent review tasks to reduce end-to-end latency without changing the existing v2 business behavior.
3. Introduce tool result caching for deterministic tool calls, including cache hit/miss visibility and invalidation rules for local development and evaluation runs.

## Non-Goals

- Do not rewrite the v2 schema.
- Do not introduce a distributed queue or other distributed execution infrastructure.
- Do not expand scope into broad workflow redesign beyond subflow reuse, parallel task execution, and tool result caching.

## Acceptance Gates

The v3 MVP is accepted only when all of the following gates pass:

- `sample_prd` runs successfully against the v3 flow.
- `run_eval` completes successfully with expected evaluation output.
- `pytest` passes for the relevant repository test suite.
