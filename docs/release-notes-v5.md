# Release Notes v5

## Summary

v5 standardizes delivery artifacts around a canonical `delivery_bundle.json` and introduces the minimum approval loop needed for human gating before downstream handoff.

## New capabilities

- `DeliveryBundle` schema with explicit artifact references, metadata, status, and approval history
- Standalone artifact generation for:
  - `prd_review_report.md`
  - `open_questions.md`
  - `scope_boundary.md`
  - `tech_design_draft.md`
  - `test_checklist.md`
- `DeliveryBundleBuilder` to assemble a unified `delivery_bundle.json`
- Minimal approval state machine with statuses:
  - `draft`
  - `need_more_info`
  - `approved`
  - `blocked_by_risk`
- MCP tools:
  - `generate_delivery_bundle`
  - `approve_handoff`
- Main-flow integration in `review_service` with non-blocking bundle generation trace

## Artifact inventory

- `prd_review_report.md`: normalized review-report artifact derived from the final review report
- `open_questions.md`: items that require clarification before delivery approval
- `scope_boundary.md`: in-scope requirements, planned work, and explicit scope boundary reminder
- `tech_design_draft.md`: first-pass technical design draft from planning output
- `test_checklist.md`: consolidated test scope, edge cases, regression focus, and review-driven checks
- `delivery_bundle.json`: canonical manifest carrying all artifact references plus approval state

## Approval flow

State transitions in v5:

- `draft -> need_more_info`
- `draft -> approved`
- `draft -> blocked_by_risk`
- `need_more_info -> draft`
- `need_more_info -> blocked_by_risk`
- `blocked_by_risk -> draft`

`approved` is terminal in v5.

Example usage through MCP:

```text
generate_delivery_bundle(run_id="20260307T010203Z")
approve_handoff(bundle_id="bundle-20260307T010203Z", action="approve", reviewer="alice")
```

## Difference from v4

v4 produced useful review outputs and handoff packs, but the outputs were still effectively a combined result set without a formal approval-ready source of truth.

v5 changes that by:

- splitting review output into named standalone artifacts
- introducing `delivery_bundle.json` as the canonical handoff manifest
- attaching a minimum approval lifecycle to the bundle
- exposing bundle generation and approval as MCP operations

## Known limitations

- Bundle persistence is still file-system based only
- No database-backed approval history or audit query layer exists yet
- No notification mechanism exists for reviewers or downstream executors
- No execution orchestration or task routing is included in v5
