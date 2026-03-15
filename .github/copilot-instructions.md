# Copilot Instructions — Dialectic Crew AI

## What this project is

A CrewAI-powered dialectic engine that generates PRDs, plans user stories, executes tasks with independent verification, and runs guarded self-improvement cycles. The dialectic loop is: **Thesis → Antithesis → Synthesis → Validation**.

The current product surface is still **CLI-first**, but it already includes persisted PRD flows, resumable execution runs, resumable self-improve cycles, vision-aware agent memory, local MCP-backed skills discovery, and guarded self-evolution workflows. The long-term target remains the vision in `internal/SELF_VISION.md`: API-first architecture, project-aware vision management, structured traceable logging, and a web experience built on CrewAI-native capabilities whenever possible.

## Architecture (key paths)

| Layer | Path | Purpose |
|-------|------|---------|
| CLI | `src/main/cli.py` | Manual `sys.argv` dispatch (no Click/Typer). Entry point: `dialectic-crew` |
| Agents | `src/dialectic/agents.py` | 5 agent factories (`create_visionario`, `create_critico_socratico`, `create_sintetizador`, `create_validador_macro`, `create_implementer`) |
| PRD flow | `src/dialectic/prd_flow.py` | `DialecticFlow(Flow[DialecticState])` — CrewAI Flow with `@start`/`@listen`/`@router` decorators |
| Planning | `src/planning/flow.py` | User-story planning dialectic crew with retry/validation/export helpers |
| Execution | `src/execution/` | `dialectic_execution.py` orchestrates story execution and checkpoints; `task_flow.py` runs per-task dialectic→verify→reimplement |
| Schemas | `src/schemas.py` | All Pydantic models (PRDSchema, UserStory, ImplementationTask, etc.) — the single source of truth |
| Self-improve | `src/main/self_improve.py` | Orchestrator (not a Flow): introspect → prioritize → PRD → plan → execute → test → PR |
| MCP skills | `src/mcp/skills_mcp.py` | FastMCP server for local `SKILL.md` discovery |
| Runtime | `src/dialectic/crewai_runtime.py` | CrewAI runtime defaults, telemetry suppression, and tracing prompt controls |
| Persistence | `src/dialectic/flow_persistence.py` | Shared SQLite persistence helpers for CrewAI flows and resume support |
| Vision | `src/dialectic/vision.py` | Vision resolution, project-root selection, and runtime CWD preparation |
| Hooks | `src/dialectic/hooks.py` | HookScope guardrails for token budgets, iteration limits, protected paths, and tool-call accounting |
| Metrics | `src/dialectic/metrics.py` | SQLite store at `.dialectic/metrics.db` (override: `DIALECTIC_METRICS_DB`) |

## Dual vision system

Two vision files drive agent alignment — never mix them:
- `knowledge/VISION.md` → `VisionContext.PROJECT` (user's project)
- `internal/SELF_VISION.md` → `VisionContext.SELF` (this app's own evolution)

Vision is resolved by `src/dialectic/vision.py`. `prepare_vision_runtime()` **changes CWD** to the project root — this is intentional for CrewAI's relative-path knowledge sources.

Agents, crews, exported artifacts, and memory namespaces must stay aligned with the active vision context. Self-improve work is always anchored to `VisionContext.SELF`; project work is anchored to `VisionContext.PROJECT`. If a change weakens that separation, it is a bug, not a feature.

## Critical conventions

### Agent factories always create fresh instances
LLM connectors are module-level singletons, but agents are re-created per run to avoid memory contamination. Every agent backstory embeds `{vision_label}` (filename of the active vision) for traceability.

Agents also rely on CrewAI-native building blocks already present in the codebase: `TextFileKnowledgeSource` for vision ingestion, memory namespacing by vision context, and configured planning/reasoning tiers. Prefer strengthening those patterns over inventing parallel abstractions.

### LLM tiers via env vars
- `LLM_MODEL_SIMPLE` (default `gpt-4o-mini`) — validator
- `LLM_MODEL_COMPLEX` (default `gpt-4o`) — critic, synthesizer, implementer
- `LLM_MODEL_REASONING` (default `o3-mini`) — visionary
- `LLM_MODEL_PLANNING` — defaults to reasoning model

### MCP wiring is fault-tolerant
`_make_mcp()` returns `None` when prerequisites are missing. Agent tool lists filter out `None` via list comprehension. External MCP failures reduce capability, never crash.

### HookScope guards expensive flows
`src/dialectic/hooks.py` — a context manager that enforces token budgets, iteration caps, protected-path blocking, and cost metrics. Used especially in self-improve (`self_improve.py` has a hardcoded `frozenset` of paths that must never be modified).

### Metrics never raise
`emit()` is fire-and-forget; all exceptions are swallowed at DEBUG level. Metrics are passive telemetry and must never break the main flow.

### Resume and persistence are first-class features
PRD generation, execution, and self-improve all support persistence/resume behavior. Preserve flow IDs, checkpoints, lineage metadata, and resumable snapshots when changing these surfaces.

### Runtime defaults are intentional
CrewAI telemetry is disabled by default and tracing prompts are suppressed unless explicitly enabled. Do not re-enable noisy runtime behavior casually.

## Current capabilities to preserve

- CLI commands already support core workflows: `prd`, `plan`, `execute`, `status`, `mark`, `verify`, `verify-story`, `self-improve`, and `help`.
- `prd` and `execute` support resume flows, and `self-improve` supports resumable cycles and resumable-cycle listing.
- `--self` routes supported workflows to `VisionContext.SELF` and `internal/SELF_VISION.md`.
- PRD generation persists structured outputs to JSON and Markdown and uses CrewAI Flow persistence.
- Execution uses checkpointed task runs and post-verification against PRD acceptance criteria.
- Self-improve is a guarded orchestrator with git safety checks, prioritization, execution, validation, and recovery paths.
- Local skills are exposed through the FastMCP server in `src/mcp/skills_mcp.py`, and optional MCP integrations must fail soft.

## Vision alignment rules

`internal/SELF_VISION.md` is the product direction for this repository. Keep the instructions and implementation aligned with its framework-first priorities:

- Prefer CrewAI native capabilities before custom infrastructure: Memory, Knowledge, Flows, planning, reasoning, hooks, event listeners, human feedback, training, testing, and MCP integrations.
- Treat API, web UI, active external project management, structured logging, and broader observability as **target architecture** unless and until the codebase actually ships them.
- When documenting or implementing roadmap work, clearly distinguish **implemented behavior** from **planned direction**. No speculative docs, no imaginary features, no “coming soon” disguised as present tense.

## Developer workflows

```bash
# Install (uv preferred)
uv sync && cp .env.example .env

# Run the CLI
uv run dialectic-crew prd "Login with 2FA"
uv run dialectic-crew plan
uv run dialectic-crew execute
uv run dialectic-crew self-improve --dry-run

# Run tests (unit only — no API keys needed)
uv run pytest -q

# Run with coverage
uv run pytest --cov=src --cov-report=term-missing

# Real LLM integration tests (require API keys, slow, costly)
uv run pytest -m llm

# Focused self-improve regressions
uv run pytest tests/test_self_improve.py tests/test_self_improve_git_safety.py tests/test_self_improve_lineage.py -q
```

Tests marked `@pytest.mark.llm` are auto-skipped when no API key is present (see `tests/conftest.py`). The `conftest.py` provides factory helpers (`make_prd()`, `make_task()`, `make_plan()`) — call them with keyword overrides, not fixtures.

## CrewAI reference — always consult docs

This project is built on **CrewAI**. Before implementing new features, fixing bugs, or modifying agent/flow/crew behavior, **always** fetch the latest CrewAI documentation using Context7:

**Strong rule:** new code and refactored code should first try to solve the problem with documented CrewAI patterns already supported by the framework. Do **not** reinvent the wheel with custom orchestration, memory, knowledge, routing, or observability layers unless CrewAI clearly cannot support the requirement. If you are about to invent infrastructure, stop and re-check the docs first.

| Topic | Context7 library ID | When to consult |
|-------|---------------------|-----------------|
| Flows, Agents, Crews, Tasks, Memory, Knowledge, Guardrails | `/crewaiinc/crewai` | Any change to `src/dialectic/`, `src/planning/`, `src/execution/` |
| CrewAI website docs (tutorials, guides, concepts) | `/websites/crewai_en` | Architecture decisions, new flow patterns, decorator usage |
| CrewAI Tools (MCP adapters, file tools, search) | `/crewaiinc/crewai-tools` | Adding or modifying agent tools in `agents.py` or `tools.py` |

Key CrewAI patterns used in this codebase:
- `Flow[StateClass]` with `@start`/`@listen`/`@router`/`or_` decorators → `prd_flow.py`, `task_flow.py`
- `Crew(agents, tasks, process=Process.sequential)` with `planning=True` and `memory=True`
- `TextFileKnowledgeSource` for vision file injection into crews
- `SQLiteFlowPersistence` for state checkpointing
- Guardrail functions returning `(bool, result_or_error)` tuples
- Hook-based runtime guardrails for token/cost/protected-path enforcement
- MCP server adapters via `crewai_tools` — see `_make_mcp()` in `agents.py`

## Skills-first workflow (using-superpowers)

**Before every planning session, task execution, or implementation**, invoke the `using-superpowers` skill from `~/.agents/skills/using-superpowers/SKILL.md`. This is the project's meta-skill that routes to the correct specialized skill:

| Situation | Skill(s) to invoke |
|-----------|-------------------|
| Planning a complex multi-file change | `writing-plans` → `subagent-driven-development` |
| Implementing a feature or bugfix | `test-driven-development` (uses `senior-software-developer` patterns) |
| Architecture/refactor only | `senior-software-developer` directly |
| Debugging a failure | `systematic-debugging` |
| About to claim work is done | `verification-before-completion` |
| Exploring an unfamiliar area | `brainstorming` first, then implementation |

The skills library lives at `src/mcp/skills/` (also discoverable at `~/.agents/skills/`). Key skills for this Python/CrewAI project:
- `python-patterns` — Python-specific best practices
- `testing-patterns` — test structure and mocking strategies
- `clean-code` — pragmatic coding standards
- `code-review-checklist` — pre-PR quality checks

**Rule**: if there is even a 1% chance a skill applies to the current task, read it first. Skills tell you HOW to explore, plan, and implement — invoke them before starting work, not after.

## Patterns to follow when editing

1. **Schemas go in `src/schemas.py`** — all Pydantic models live there, nowhere else.
2. **New agents** must follow the `create_<name>(vision_context: VisionContext) -> Agent` factory pattern in `agents.py`.
3. **New CLI commands** are added as `cmd_<name>(args)` functions in `cli.py` and wired into the `sys.argv` dispatch in `main()`. Update `_command_requires_api()` and `_command_requires_vision()` if the command has special gate requirements.
4. **Follow Python best practices** — use type hints, small focused functions, clear names, cohesive modules, and tests that verify behavior rather than implementation trivia.
5. **Apply SOLID and established design patterns** where they simplify the design. Prefer composition, explicit interfaces/protocols, and narrow responsibilities over large multipurpose classes.
6. **Keep classes small and cohesive** — aim to keep classes under roughly 400 lines when practical. If a class starts turning into a novella, split responsibilities before it becomes literature.
7. **Prefer one class per file** unless colocating multiple tiny, tightly coupled classes is clearly the cleaner design.
8. **IMPORTANT!!!****Use CrewAI-native solutions first** — before adding custom abstractions, confirm that Flows, Crews, Tasks, Knowledge, Memory, Hooks, MCP adapters, Event Listeners or other CrewAI-native components do not already solve the problem.
9. **Test files** go in `tests/` and follow `test_<module>.py` naming. No global LLM mocking — mock per-test as needed.
10. **Metrics**: use `emit(metric_type, value, **context)` from `dialectic.metrics`. Never catch or suppress metric errors at the call site.
11. **Protected paths in self-improve**: if adding safety-critical files, add them to the `frozenset` in `self_improve.py`.
12. **Preserve persistence semantics** — when changing PRD, execution, or self-improve flows, keep resume/checkpoint metadata compatible unless a deliberate migration is part of the task.
13. **Git conventions**: conventional commits (`feat(scope): subject`), imperative mood, max 50 chars subject.
14. **CrewAI telemetry** is disabled by default (`CREWAI_DISABLE_TELEMETRY=true` set in `cli.py:main()`).
15. **Structured logging, API, active-project support, and UI work are roadmap areas** aligned with `internal/SELF_VISION.md`; document and implement them carefully as future-facing features until the code exists.
16. **Verification after meaningful changes is mandatory** — after non-trivial edits, and especially after refactors or import/package changes, verify the touched surface with relevant `pytest`, `ruff`, `mypy`, `pyright`, and editor diagnostics/Pylance on the touched files. Run `pylint` on touched Python files when imports, packaging, public exports, or module boundaries changed. Do not claim completion until these checks are green or any remaining issue is explicitly explained.
17. **Do not use dynamic imports to hide package/export problems** — if a test or module only works with `import_module(...)` or similar runtime indirection, prefer fixing the package surface instead (for example: canonical import path, missing `__init__.py`, or explicit package exports). Static tooling, runtime imports, and editor diagnostics must agree on the import contract.
18. **Use authoritative final verification** — for final sign-off, prefer a fresh foreground command with a clear exit result. Do not rely on ambiguous background-terminal output, stale shared-shell state, or partially interrupted command logs.
19. **Treat import/export refactors as dual-surface changes** — when touching imports, package boundaries, or public exports, verify both runtime importability and editor/static-analysis resolution. Keep smoke tests like `tests/test_package_exports.py` aligned with the canonical package surface rather than patching around failures.
20. **When in doubt, consult the vision** — if you are unsure about how to implement something, or whether a change fits the project direction, consult `internal/SELF_VISION.md` first. If the vision does not clarify the question, consider whether the vision itself needs clarification or expansion — and if so, propose that change before proceeding with implementation.
21. **When in doubt, consult the docs** — if you are unsure about how to use a CrewAI feature or whether it can solve a problem, consult the official CrewAI documentation first. The docs are the source of truth for how to leverage the framework effectively and avoid unnecessary custom infrastructure.
22. **new code should be covered by tests** — when adding new features or modifying existing behavior, add tests that verify the expected outcomes. Tests should focus on behavior and edge cases rather than implementation details. Use `pytest` fixtures and parameterization to keep tests clean and maintainable.
23. **When modifying existing code, preserve existing tests and add new ones as needed** — when changing existing functionality, ensure that existing tests still pass and add new tests to cover any new behavior or edge cases introduced by the change. Do not remove or weaken tests without a compelling reason, and if you do, document that reason in the commit message and code comments.
24. **Use descriptive commit messages** — when committing changes, use clear and descriptive commit messages that explain the what and why of the change. Follow conventional commit format (`feat(scope): subject`) and keep the subject line concise (max 50 characters). Use the body of the commit message to provide additional context, rationale, and any relevant details about the change.
25. **When in doubt, ask** — if you are unsure about any aspect of the codebase, project direction, implementation approach, or testing strategy, do not hesitate to ask for clarification from the team. It is better to ask questions and get alignment than to make assumptions that could lead to misaligned implementation or technical debt. Use team communication channels, code review comments, or direct messages to seek clarification as needed.
26. **Respect the existing code style and conventions** — when adding or modifying code, follow the existing code style and conventions used in the project. This includes naming conventions, formatting, and architectural patterns. Consistency in code style helps maintain readability and makes it easier for all team members to understand and contribute to the codebase.
27. **When in doubt, prioritize simplicity and clarity** — when making design decisions or implementing features, prioritize simplicity and clarity over complexity. Aim for straightforward solutions that are easy to understand and maintain, rather than over-engineered approaches that may be more powerful but harder to grasp. Simple code is more likely to be correct, easier to debug, and more accessible to new contributors.  
28. **When in doubt, prioritize safety and robustness** — especially in self-improve workflows, prioritize safety and robustness over speed or convenience. Implement guardrails, validation checks, and recovery paths to minimize the risk of catastrophic failures. When making changes that could impact critical paths, consider the potential failure modes and implement appropriate safeguards.
29. **New code** — if new code is project-related, it should be created using deep-modules and placed inside the `src` folder. If the new code is a test, it should be placed in the `tests` folder. Avoid adding new top-level folders without a clear and justified reason.
