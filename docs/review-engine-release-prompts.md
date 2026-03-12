# Review Engine Frontend And Release Gap Prompts

This document is a phased prompt set for the current repository direction:

- keep the mainline centered on the review engine
- add a lightweight frontend for review submission and report consumption
- close the highest-value release gaps that still block a more production-ready release

It is intentionally narrower than the older platform-expansion plans in this repository.

## Current Baseline

As of the current codebase:

- `README.md` is now positioned around the review engine rather than the retained extension layer.
- `frontend/` does not contain a real application yet. It currently only has `node_modules` and Vite log files.
- FastAPI already supports:
  - `POST /api/review`
  - `GET /api/review/{run_id}`
  - `GET /api/report/{run_id}?format=md|json`
- MCP already exposes `review_requirement`, `review_prd`, and `get_report`.
- The largest review-engine gaps are:
  - no actual frontend UI
  - no frontend-friendly review result API contract beyond file download
  - no shipped authenticated Feishu document adapter
  - no generalized foundation for authenticated private-source connectors
  - release hardening is still incomplete for a more formal public version

## Recommended Order

```text
Phase A  Frontend-ready review API
    ->
Phase B  Frontend MVP for submit / poll / inspect / download
    ->
Phase C  Real Feishu connector
    ->
Phase D  Authenticated source foundation
    ->
Phase E  Review-engine release hardening
```

Principles:

- keep every phase aligned with the review-engine mainline
- avoid re-centering the repo around approval or execution orchestration
- require tests for backend changes and build verification for frontend changes

## Environment Rule

All Python test and evaluation commands in this document must be run with:

- `D:\venvs\marrdp\Scripts\python.exe`

Use that interpreter for `pytest`, `eval`, and any Python-based smoke validation in every phase. Frontend build commands remain standard `npm` commands inside `frontend/`.

## Phase A: Frontend-ready Review API

Goal: make the current backend easier for a frontend to consume without changing the review-engine scope.

### Step A-1: Add a structured result endpoint

```text
You are working in the Multi-Agent-Requirement-Review-and-Delivery-Planning-System repository.
Create a new branch from main: `git checkout -b feature/review-ui-api`

Task:
1. Inspect the current FastAPI implementation in:
   - `requirement_review_v1/server/app.py`
   - `requirement_review_v1/service/review_service.py`

2. Add a frontend-friendly result endpoint:
   - `GET /api/review/{run_id}/result`

3. Requirements:
   - Read and return parsed `report.json`
   - Include stable artifact paths when present:
     - `report.md`
     - `report.json`
     - `run_trace.json`
     - `review_report.json`
     - `risk_items.json`
     - `open_questions.json`
     - `review_summary.md`
   - Return a controlled `404` when the run directory does not exist
   - Return a controlled `409` or equivalent when the run is still in progress and `report.json` is not ready yet
   - Keep the existing endpoints backward compatible

4. Add or update tests:
   - `tests/test_server_app_source_input.py`
   - add a new API-focused test if needed

5. Run:
   - `D:\venvs\marrdp\Scripts\python.exe -m pytest tests/test_server_app_source_input.py -v`
   - `D:\venvs\marrdp\Scripts\python.exe -m pytest -q`

6. Commit:
   `git commit -am "feat(api): add structured review result endpoint for frontend consumers"`
```

### Step A-2: Add a review run listing endpoint

```text
You are on `feature/review-ui-api`.

Task:
1. Add a lightweight endpoint:
   - `GET /api/runs`

2. Requirements:
   - Scan `outputs/` for run directories
   - Return the most recent runs first
   - For each run include:
     - `run_id`
     - `status`
     - `created_at`
     - `updated_at`
     - presence flags for core artifacts
   - Do not parse every large artifact eagerly
   - Keep the implementation file-based for now; do not introduce a database in this phase

3. Add tests covering:
   - empty outputs directory
   - one completed run
   - one in-progress run

4. Update `docs/v2-api.md` with the new endpoint contract.

5. Run `D:\venvs\marrdp\Scripts\python.exe -m pytest -q`

6. Commit:
   `git commit -am "feat(api): add review run listing endpoint for frontend history views"`
```


### Phase A Exit Gate

Before leaving Phase A, add a short phase-end assessment in your response:

1. Re-run the full Python test suite with `D:\venvs\marrdp\Scripts\python.exe -m pytest -q`.
2. Confirm the new API contract is documented and backward compatibility is intact.
3. Evaluate whether the phase branch is ready to merge and push:
   - if yes, state that it is merge-ready and push-ready
   - if no, list the blockers and do not recommend merge/push yet

## Phase B: Frontend MVP

Goal: ship a lightweight review workspace for technical and semi-technical users.

### Step B-1: Bootstrap the frontend

```text
You are working in the repository.
Create a branch from main after Phase A lands: `git checkout -b feature/review-frontend-mvp`

Task:
1. Inspect `frontend/`.
   - If it only contains logs or dependency cache, replace it with a real minimal app.

2. Build a small Vite + React frontend inside `frontend/` with at least:
   - `frontend/package.json`
   - `frontend/index.html`
   - `frontend/src/main.jsx`
   - `frontend/src/App.jsx`
   - `frontend/src/styles.css`

3. Product direction:
   - this is a review workspace, not a generic admin CRUD panel
   - prioritize clarity of review flow over platform-style menus
   - design for desktop first, but keep mobile readable

4. UI requirements:
   - a review submission form for:
     - `prd_text`
     - `prd_path`
     - `source`
   - a run status area
   - a result overview area

5. Styling requirements:
   - do not use a flat white dashboard with default tables everywhere
   - define CSS variables for color, spacing, and status tones
   - make the empty state and loading state feel intentional

6. Verification:
   - `npm run build`

7. Commit:
   `git commit -am "feat(frontend): bootstrap review workspace frontend"`
```

### Step B-2: Implement submit, poll, and result rendering

```text
You are on `feature/review-frontend-mvp`.

Task:
1. Connect the frontend to:
   - `POST /api/review`
   - `GET /api/review/{run_id}`
   - `GET /api/review/{run_id}/result`
   - `GET /api/report/{run_id}?format=md|json`

2. Build the following UI areas:
   - ReviewSubmitPanel
   - RunProgressCard
   - ReviewSummaryPanel
   - FindingsPanel
   - RisksPanel
   - OpenQuestionsPanel
   - ArtifactDownloadPanel

3. Behavior requirements:
   - submit starts a run and stores the returned `run_id`
   - poll until the run completes or fails
   - after completion, fetch and display the structured review result
   - allow downloading both Markdown and JSON report artifacts
   - show clear failure messaging if the run fails

4. Keep the codebase simple:
   - prefer a small local state model over adding a heavy state library
   - use modern React patterns and avoid premature optimization

5. Verification:
   - `npm run build`

6. Commit:
   `git commit -am "feat(frontend): add review submit, polling, and result inspection flow"`
```

### Step B-3: Add run history and responsive polish

```text
You are on `feature/review-frontend-mvp`.

Task:
1. Build a review history view backed by:
   - `GET /api/runs`

2. Show:
   - recent runs
   - run status
   - created time
   - quick links to open result details

3. Add:
   - loading states
   - error states
   - empty states
   - mobile layout adjustments

4. Keep the experience review-first:
   - do not add approval, execution, or orchestration UI in this phase

5. If a frontend test setup is lightweight to add, include a minimal test for one critical component.

6. Verification:
   - `npm run build`

7. Commit:
   `git commit -am "feat(frontend): add review history and responsive polish"`
```


### Phase B Exit Gate

Before leaving Phase B, add a short phase-end assessment in your response:

1. Re-run `npm run build` in `frontend/`.
2. Re-run `D:\venvs\marrdp\Scripts\python.exe -m pytest -q` if this phase changed any backend contract, API docs, or shared integration surface.
3. Evaluate whether the phase branch is ready to merge and push:
   - if yes, state that it is merge-ready and push-ready
   - if no, list the blockers and do not recommend merge/push yet

## Phase C: Real Feishu Connector

Goal: replace the current Feishu placeholder boundary with an actual authenticated document fetch path.

### Step C-1: Implement the Feishu document client

```text
You are working in the repository.
Create a branch from main after the frontend MVP stabilizes: `git checkout -b feature/feishu-review-source`

Task:
1. Inspect the current connector implementation:
   - `requirement_review_v1/connectors/feishu.py`
   - `requirement_review_v1/connectors/registry.py`
   - `tests/test_feishu_connector.py`

2. Upgrade `FeishuConnector` from a placeholder to a real authenticated connector.

3. Requirements:
   - keep the current source recognition logic
   - use `MARRDP_FEISHU_APP_ID`, `MARRDP_FEISHU_APP_SECRET`, and `MARRDP_FEISHU_OPEN_BASE_URL`
   - support controlled fetching for recognized document URLs and `feishu://...` sources
   - normalize the fetched content into `SourceDocument`
   - keep error mapping explicit for:
     - authentication failure
     - permission denied
     - document not found
     - unsupported document type

4. Implementation constraints:
   - do not hardcode live credentials
   - structure the HTTP client code so it can be mocked cleanly in tests
   - keep local-file and public-URL ingestion unchanged

5. Update tests to use mocked responses instead of real network calls.

6. Run `D:\venvs\marrdp\Scripts\python.exe -m pytest -q`

7. Commit:
   `git commit -am "feat(connectors): implement authenticated Feishu source fetching for review inputs"`
```

### Step C-2: Integrate Feishu behavior across API and MCP

```text
You are on `feature/feishu-review-source`.

Task:
1. Verify and update integration points:
   - `requirement_review_v1/service/review_service.py`
   - `requirement_review_v1/server/app.py`
   - `requirement_review_v1/mcp_server/server.py`

2. Requirements:
   - `source` inputs using Feishu should now enter the normal review flow
   - controlled connector errors must be surfaced consistently in FastAPI and MCP responses
   - source metadata should still be written into run artifacts where the codebase already supports it

3. Update documentation:
   - `README.md`
   - `docs/v2-api.md`
   - `docs/mcp.md`
   - `.env.example`

4. Run `D:\venvs\marrdp\Scripts\python.exe -m pytest -q`

5. Commit:
   `git commit -am "feat(connectors): wire Feishu review inputs through service, API, and MCP layers"`
```


### Phase C Exit Gate

Before leaving Phase C, add a short phase-end assessment in your response:

1. Re-run the full Python test suite with `D:\venvs\marrdp\Scripts\python.exe -m pytest -q`.
2. Confirm connector error mapping, docs, and environment-variable guidance are complete.
3. Evaluate whether the phase branch is ready to merge and push:
   - if yes, state that it is merge-ready and push-ready
   - if no, list the blockers and do not recommend merge/push yet

## Phase D: Authenticated Source Foundation

Goal: avoid making Feishu a one-off by introducing a reusable private-source connector foundation.

### Step D-1: Add connector auth and error abstractions

```text
You are working in the repository.
Create a branch from main after Phase C lands: `git checkout -b feature/review-source-auth-foundation`

Task:
1. Inspect the current connectors package and define a small shared foundation for authenticated sources.

2. Add or update:
   - connector auth config model
   - connector error taxonomy
   - reusable response normalization helpers

3. Requirements:
   - keep the API surface small
   - preserve compatibility with current local file and URL connectors
   - make future private-source integrations easier without forcing them all into the codebase now

4. Add tests that verify:
   - common error shapes
   - auth config validation
   - no regressions for existing connectors

5. Run `D:\venvs\marrdp\Scripts\python.exe -m pytest -q`

6. Commit:
   `git commit -am "refactor(connectors): add shared auth and error foundations for private review sources"`
```

### Step D-2: Add one more private-source stub the right way

```text
You are on `feature/review-source-auth-foundation`.

Task:
1. Add one additional private-source connector stub, such as `confluence.py` or `notion.py`.

2. Requirements:
   - source recognition
   - config validation
   - explicit controlled errors
   - registration in the connector registry
   - no live API calls yet

3. The purpose of this step is architectural validation:
   - prove the shared connector foundation is not Feishu-specific

4. Add focused tests.

5. Run `D:\venvs\marrdp\Scripts\python.exe -m pytest -q`

6. Commit:
   `git commit -am "feat(connectors): add private-source connector stub on shared auth foundation"`
```


### Phase D Exit Gate

Before leaving Phase D, add a short phase-end assessment in your response:

1. Re-run the full Python test suite with `D:\venvs\marrdp\Scripts\python.exe -m pytest -q`.
2. Confirm the shared private-source foundation does not regress existing local-file or URL behavior.
3. Evaluate whether the phase branch is ready to merge and push:
   - if yes, state that it is merge-ready and push-ready
   - if no, list the blockers and do not recommend merge/push yet

## Phase E: Review-engine Release Hardening

Goal: close the gap between a capable project and a more formal release candidate.

### Step E-1: Add a persistent cache backend

```text
You are working in the repository.
Create a branch from main after the source work stabilizes: `git checkout -b feature/review-release-hardening`

Task:
1. Inspect the existing in-process caching behavior and related tests.

2. Add an optional persistent cache backend for cross-process reuse.

3. Requirements:
   - start with SQLite or a file-based cache
   - keep the current in-memory behavior available as the default fallback
   - expose cache hit/miss metadata in a way that helps debugging
   - do not change core review outputs

4. Update tests for both in-memory and persistent modes.

5. Run `D:\venvs\marrdp\Scripts\python.exe -m pytest -q`

6. Commit:
   `git commit -am "feat(runtime): add optional persistent cache backend for review workloads"`
```

### Step E-2: Add API auth and rate limiting

```text
You are on `feature/review-release-hardening`.

Task:
1. Harden the FastAPI surface for shared-environment use.

2. Requirements:
   - add a simple API-key or bearer-token layer controlled by environment variables
   - add a basic rate-limit policy for review submission endpoints
   - keep local development ergonomic with an explicit opt-out
   - return controlled error responses instead of generic server failures

3. Update:
   - `requirement_review_v1/server/app.py`
   - relevant docs
   - `.env.example`

4. Add tests covering:
   - authorized request
   - unauthorized request
   - rate-limit behavior

5. Run `D:\venvs\marrdp\Scripts\python.exe -m pytest -q`

6. Commit:
   `git commit -am "feat(api): add basic auth and rate limiting for review endpoints"`
```

### Step E-3: Add release observability and smoke validation

```text
You are on `feature/review-release-hardening`.

Task:
1. Improve release confidence for the review engine.

2. Add:
   - a small smoke script for CLI and FastAPI review flow
   - better runtime metrics or trace summaries for completed runs
   - a release checklist document focused on the review engine

3. Keep scope tight:
   - do not reintroduce approval or orchestration work as part of this phase

4. Update:
   - `eval/`
   - `docs/`
   - any lightweight runtime metrics module if needed

5. Run:
   - `D:\venvs\marrdp\Scripts\python.exe eval/run_eval.py`
   - `D:\venvs\marrdp\Scripts\python.exe -m pytest -q`

6. Commit:
   `git commit -am "chore(release): add review-engine smoke validation and release checklist"`
```


### Phase E Exit Gate

Before leaving Phase E, add a short phase-end assessment in your response:

1. Re-run `D:\venvs\marrdp\Scripts\python.exe eval/run_eval.py`.
2. Re-run the full Python test suite with `D:\venvs\marrdp\Scripts\python.exe -m pytest -q`.
3. Confirm release docs, smoke validation, and hardening changes are complete.
4. Evaluate whether the phase branch is ready to merge and push:
   - if yes, state that it is merge-ready and push-ready
   - if no, list the blockers and do not recommend merge/push yet

## Suggested Execution Strategy

If you want the fastest visible payoff, do this first:

1. Phase A
2. Phase B
3. Phase C

If you want the strongest release-readiness path, do this first:

1. Phase C
2. Phase D
3. Phase E
4. Phase B

## Universal Rules For Every Prompt

Apply these constraints in every implementation step:

1. Read the existing code before changing it.
2. Keep the repository centered on review results.
3. Do not introduce extension-layer UI or workflow concepts into the mainline unless explicitly needed.
4. Add or update tests for backend changes.
5. Run build verification for frontend changes.
6. Update docs whenever a public contract changes.
7. At the end of each phase, explicitly assess whether the branch is ready to merge and push.
