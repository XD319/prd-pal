# Review Engine Positioning

## Purpose

This document defines the repository's first-layer architecture.

The system should be positioned as a requirement review engine whose primary output is a review result, not as an execution orchestration platform.

## First-Layer Architecture

The main architecture is:

`source input -> review mode gating -> normalizer -> parallel reviewers -> aggregator -> review artifacts`

Each stage has a clear role:

1. `source input`
   - Accept requirement content from `prd_text`, `prd_path`, or connector-backed `source`.
   - Normalize the ingestion path without changing the review objective.

2. `review mode gating`
   - Decide whether the requirement should use `single_review` or `parallel_review`.
   - Keep low-complexity inputs on a simpler path and reserve multi-reviewer cost for more complex inputs.

3. `normalizer`
   - Extract structured requirement context.
   - Produce reviewer-specific slices for product, engineering, QA, and security perspectives.

4. `parallel reviewers`
   - Run the reviewer set concurrently when gating selects the parallel mode.
   - Preserve a single-review fallback for simpler cases.

5. `aggregator`
   - Merge findings, risks, open questions, reviewer summaries, and conflicts.
   - Deduplicate overlapping reviewer output into a unified review result.

6. `review artifacts`
   - Persist the aggregated review into markdown and JSON artifacts that humans and downstream systems can consume.

## What Belongs To The Extension Layer

The following capabilities are kept in the repository but belong to the extension layer rather than the first-layer definition:

- delivery bundle generation
- approval loop and review workspace persistence
- handoff packs and coding-agent prompts
- execution routing and task lifecycle
- traceability maps
- notifications
- governance helpers such as audit query and retry operations

These capabilities can remain implemented, tested, and documented. They should simply be described as downstream or platform extensions built on top of the review result.

## Documentation Rule

When documenting the repository:

- Lead with review-only architecture and review artifacts.
- Place orchestration capabilities in extension sections.
- Do not describe retained extension code as deprecated unless it has actually been removed.

## Practical Interpretation

For users evaluating the project quickly, the shortest accurate description is:

`A multi-agent requirement review engine that can optionally expand into bundle approval, handoff, and execution orchestration.`
