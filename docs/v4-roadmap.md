# v4 Roadmap

## v4 Goals

v4 expands the system from requirement review into delivery planning and coding-agent handoff.

The core v4 goals are:

1. Delivery Planning
2. Task Pack / Handoff Pack generation

## System Positioning

v4 is the upstream planning and orchestration layer for downstream coding agents.

- It analyzes requirements, decomposes work, and prepares structured implementation and testing handoff artifacts.
- It does not directly modify application repositories.
- It does not directly execute shell commands in target repositories.
- It does not directly perform CI/CD operations.

## Phase 1 Scope

The first v4 phase focuses on the minimum planning-to-handoff loop:

1. `implementation.plan` skill
2. `test.plan.generate` skill
3. Codex / Claude Code prompt generation
4. `ImplementationPack`
5. `TestPack`
6. `ExecutionPack`

## Deliverable Intent

- `ImplementationPack` captures task breakdown, constraints, touched areas, sequencing, and coding-agent implementation guidance.
- `TestPack` captures validation strategy, target test coverage, and test execution guidance for the coding agent.
- `ExecutionPack` packages the final handoff context so an external coding agent can execute with minimal ambiguity.

## Non-Goals

- Do not directly edit or patch the target repository.
- Do not directly execute shell commands in the target repository.
- Do not directly own or run CI/CD workflows.

## Acceptance Direction

The v4 phase 1 MVP should be considered successful when the system can:

- turn reviewed requirements into a structured delivery plan;
- generate implementation and test planning outputs through dedicated skills;
- produce coding-agent-ready prompts for Codex and Claude Code;
- emit consistent `ImplementationPack`, `TestPack`, and `ExecutionPack` artifacts without taking direct repository actions.

## Future Expansion

- Add richer orchestration for multi-agent delivery workflows.
- Add stronger validation and completeness checks for handoff packs.
- Add integration points for downstream execution systems while preserving the planning-layer boundary.
