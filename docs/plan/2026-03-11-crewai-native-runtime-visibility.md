# CrewAI-Native Runtime Visibility Implementation Plan

> **Note:** This plan should be executed task-by-task with verification at each step.

**Goal:** Add production-grade runtime visibility so operators can see exactly what the system is doing during execution, which flow/task/agent/tool is active, what state the system is in, and where any error occurred.

**Architecture:** Use CrewAI native observability as the backbone: `BaseEventListener` for lifecycle events, CrewAI tracing for deep timelines, execution hooks for guardrail/LLM/tool interception, and flow-state breadcrumbs for exact `Flow` node position. Add an explicit compatibility layer for the exact CrewAI event classes available in the installed version, cover both Flow-based and non-Flow orchestrators (`planning` retries and `self_improve` stages), and persist the resulting normalized runtime events in a repo-owned structured sink with redaction, truncation, and retention controls while keeping metrics as a separate telemetry plane.

**Tech Stack:** Python 3.10–3.13, CrewAI Flows/Crews/Tasks/Agents, CrewAI Event Listeners, CrewAI tracing, CrewAI execution hooks, pytest.

**Prerequisites:** Existing test environment (`uv sync`, `.venv`), familiarity with `src/dialectic/crewai_runtime.py`, `src/dialectic/hooks.py`, `src/dialectic/prd_flow.py`, `src/planning/flow.py`, `src/execution/task_flow.py`, and `src/main/self_improve.py`.

---

### Task 0: Inventory the exact CrewAI observability contract

**Files:**
- Create: `/home/darthlinuxer/dialectic-crew-ai/src/dialectic/runtime_contract.py`
- Test: `/home/darthlinuxer/dialectic-crew-ai/tests/test_runtime_contract.py`
- Test: `/home/darthlinuxer/dialectic-crew-ai/tests/test_crewai_runtime.py`

**Step 1: Write the failing test**
- Add tests that lock the observability contract to the CrewAI version currently installed.
- Cover:
  - which native event classes are importable
  - which fields are available on those event objects
  - graceful fallback behavior when optional tracing/event classes are unavailable
  - idempotent listener registration behavior

**Step 2: Run test to verify it fails**
Run: `uv run pytest tests/test_runtime_contract.py tests/test_crewai_runtime.py -q`
Expected: FAIL because the compatibility/normalization layer does not yet exist.

**Step 3: Write minimal implementation**
- Create `runtime_contract.py` to centralize:
  - the set of supported CrewAI event classes
  - event-field extraction helpers
  - feature-detection helpers for tracing and listener availability
- Do not scatter version-specific imports and field assumptions across the listener implementation.

**Step 4: Run test to verify it passes**
Run: `uv run pytest tests/test_runtime_contract.py tests/test_crewai_runtime.py -q`
Expected: PASS.

**Step 5: Commit**
- Commit message: `feat(observability): add runtime contract adapter`

---

### Task 1: Define the runtime event model and storage seam

**Files:**
- Create: `/home/darthlinuxer/dialectic-crew-ai/src/dialectic/runtime_events.py`
- Modify: `/home/darthlinuxer/dialectic-crew-ai/src/dialectic/__init__.py`
- Test: `/home/darthlinuxer/dialectic-crew-ai/tests/test_runtime_events.py`

**Step 1: Write the failing test**
- Add tests for a normalized runtime event model that requires fields for:
  - `event_type`
  - `timestamp`
  - `correlation_id`
  - optional `flow_id`
  - optional `run_id`
  - optional `task_id`
  - optional `story_id`
  - optional `agent_role`
  - optional `tool_name`
  - `phase`
  - `success`
  - optional `error_type`
  - optional `error_message`
  - optional `stage`
  - `payload`
  - Include tests verifying event serialization is JSON-safe and payload redaction helpers can safely sanitize known sensitive keys.

**Step 2: Run test to verify it fails**
Run: `uv run pytest tests/test_runtime_events.py -q`
Expected: FAIL because `runtime_events.py` does not yet exist.

**Step 3: Write minimal implementation**
- Create a small Pydantic model or dataclass-based event schema in `src/dialectic/runtime_events.py`.
- Add helper constructors for:
  - lifecycle events
  - error events
  - breadcrumb events
- Add explicit support for non-Flow stage events (for example planning attempts and self-improve stages) so the schema does not overfit only `Flow` nodes.
- Export the public symbols from `src/dialectic/__init__.py` only if they are intended to be package-level API.

**Step 4: Run test to verify it passes**
Run: `uv run pytest tests/test_runtime_events.py -q`
Expected: PASS.

**Step 5: Commit**
- Commit message: `feat(observability): add runtime event model`

---

### Task 2: Add a repo-owned runtime event sink

**Files:**
- Create: `/home/darthlinuxer/dialectic-crew-ai/src/dialectic/runtime_event_sink.py`
- Modify: `/home/darthlinuxer/dialectic-crew-ai/src/dialectic/config.py`
- Modify: `/home/darthlinuxer/dialectic-crew-ai/docs/configuration.md`
- Test: `/home/darthlinuxer/dialectic-crew-ai/tests/test_runtime_event_sink.py`

**Step 1: Write the failing test**
- Add tests for an append-only structured event sink that:
  - writes JSON lines safely
  - creates parent directories if needed
  - never raises on best-effort logging failures
  - uses configurable output paths
  - applies payload truncation and secret redaction rules
  - rotates or segments files according to configured retention limits

**Step 2: Run test to verify it fails**
Run: `uv run pytest tests/test_runtime_event_sink.py -q`
Expected: FAIL because the sink does not exist yet.

**Step 3: Write minimal implementation**
- Create a sink that writes normalized runtime events to a path under `.dialectic/` by default.
- Add config/env support for path override, enable/disable behavior, redaction/truncation, and retention or rotation limits.
- Keep this separate from `src/dialectic/metrics.py`; do not merge the two concerns.

**Step 4: Run test to verify it passes**
Run: `uv run pytest tests/test_runtime_event_sink.py -q`
Expected: PASS.

**Step 5: Commit**
- Commit message: `feat(observability): add runtime event sink`

---

### Task 3: Bootstrap run correlation at the CLI boundary

**Files:**
- Modify: `/home/darthlinuxer/dialectic-crew-ai/src/main/cli.py`
- Modify: `/home/darthlinuxer/dialectic-crew-ai/src/main/cli_commands.py`
- Create: `/home/darthlinuxer/dialectic-crew-ai/src/dialectic/runtime_context.py`
- Test: `/home/darthlinuxer/dialectic-crew-ai/tests/test_cli_runtime.py`

**Step 1: Write the failing test**
- Add tests proving a command invocation creates a correlation context.
- Add coverage for resumed commands so the active correlation includes both the new command correlation and the persisted identifier (`flow_id`, `resume_run_id`, or `resume_cycle_id`).

**Step 2: Run test to verify it fails**
Run: `uv run pytest tests/test_cli_runtime.py -k correlation -q`
Expected: FAIL because correlation context is not currently created or propagated.

**Step 3: Write minimal implementation**
- Add `runtime_context.py` with helpers to:
  - create a run correlation ID
  - attach structured context
  - read the current runtime context from anywhere in the process
- Initialize context in `src/main/cli.py:main` before command dispatch.
- Thread relevant IDs into command handlers in `src/main/cli_commands.py`.

**Step 4: Run test to verify it passes**
Run: `uv run pytest tests/test_cli_runtime.py -k correlation -q`
Expected: PASS.

**Step 5: Commit**
- Commit message: `feat(observability): add cli runtime correlation`

---

### Task 4: Implement a CrewAI BaseEventListener for lifecycle visibility

**Files:**
- Create: `/home/darthlinuxer/dialectic-crew-ai/src/dialectic/runtime_listener.py`
- Modify: `/home/darthlinuxer/dialectic-crew-ai/src/dialectic/crewai_runtime.py`
- Test: `/home/darthlinuxer/dialectic-crew-ai/tests/test_runtime_listener.py`

**Step 1: Write the failing test**
- Add tests for event normalization from native CrewAI events into the runtime event schema.
- Cover at least these event families:
  - crew start/completion
  - task start/completion
  - agent execution start/completion
  - tool usage start/finish
  - LLM call start/completion
  - memory query completion
- Add coverage proving the listener degrades gracefully when an event class from Task 0 is not available in the current CrewAI build.

**Step 2: Run test to verify it fails**
Run: `uv run pytest tests/test_runtime_listener.py -q`
Expected: FAIL because the listener is not implemented.

**Step 3: Write minimal implementation**
- Create a `BaseEventListener` subclass.
- Subscribe only to the needed CrewAI events through the Task 0 compatibility layer.
- Normalize each event into the shared runtime event schema.
- Write each event to the runtime event sink.
- Keep the listener lightweight and defensive; handler failures must never crash execution.

**Step 4: Run test to verify it passes**
Run: `uv run pytest tests/test_runtime_listener.py -q`
Expected: PASS.

**Step 5: Commit**
- Commit message: `feat(observability): add crewai runtime listener`

---

### Task 5: Evolve CrewAI runtime setup to support tracing and listener registration

**Files:**
- Modify: `/home/darthlinuxer/dialectic-crew-ai/src/dialectic/crewai_runtime.py`
- Modify: `/home/darthlinuxer/dialectic-crew-ai/docs/configuration.md`
- Test: `/home/darthlinuxer/dialectic-crew-ai/tests/test_crewai_runtime.py`

**Step 1: Write the failing test**
- Add tests for new runtime configuration behavior:
  - event listener registration occurs once
  - tracing remains disabled by default unless configured
  - tracing can be deliberately enabled for diagnostics
  - the current prompt-suppression logic remains intact
  - the runtime operates in a supported degraded mode when tracing/event utilities are unavailable

**Step 2: Run test to verify it fails**
Run: `uv run pytest tests/test_crewai_runtime.py -q`
Expected: FAIL because there is no listener-aware runtime bootstrap yet.

**Step 3: Write minimal implementation**
- Refactor `configure_crewai_runtime()` to:
  - preserve existing safe defaults
  - register the runtime listener layer
  - expose clear env-driven tracing control
- Keep native tracing control separate from the repo-owned event sink so operators can enable one without implicitly forcing the other.
- Do not force full tracing on for every run initially.

**Step 4: Run test to verify it passes**
Run: `uv run pytest tests/test_crewai_runtime.py -q`
Expected: PASS.

**Step 5: Commit**
- Commit message: `feat(observability): wire crewai runtime observability`

---

### Task 6: Instrument hooks for guardrail, tool, and low-level LLM visibility

**Files:**
- Modify: `/home/darthlinuxer/dialectic-crew-ai/src/dialectic/hooks.py`
- Test: `/home/darthlinuxer/dialectic-crew-ai/tests/test_hooks.py`

**Step 1: Write the failing test**
- Add or extend tests so hook executions emit structured runtime events for:
  - before-LLM call
  - after-LLM call
  - before-tool call
  - after-tool call
  - token budget exceeded
  - iteration limit exceeded
  - protected-path block
  - hook scope enter/exit summary

**Step 2: Run test to verify it fails**
Run: `uv run pytest tests/test_hooks.py -q`
Expected: FAIL because hooks currently only emit metrics and plain logs.

**Step 3: Write minimal implementation**
- Emit normalized runtime events in each hook and in `HookScope.__enter__` / `HookScope.__exit__`.
- Include current correlation context, label, task/tool/agent metadata, durations, and policy outcomes.
- Keep all hook-side observability best-effort.

**Step 4: Run test to verify it passes**
Run: `uv run pytest tests/test_hooks.py -q`
Expected: PASS.

**Step 5: Commit**
- Commit message: `feat(observability): instrument runtime hooks`

---

### Task 7: Add explicit flow-node and orchestrator-stage breadcrumbs

**Files:**
- Modify: `/home/darthlinuxer/dialectic-crew-ai/src/dialectic/prd_flow.py`
- Modify: `/home/darthlinuxer/dialectic-crew-ai/src/planning/flow.py`
- Modify: `/home/darthlinuxer/dialectic-crew-ai/src/execution/task_flow.py`
- Modify: `/home/darthlinuxer/dialectic-crew-ai/src/main/self_improve.py`
- Test: `/home/darthlinuxer/dialectic-crew-ai/tests/test_prd_flow.py`
- Test: `/home/darthlinuxer/dialectic-crew-ai/tests/test_planning_runtime.py`
- Test: `/home/darthlinuxer/dialectic-crew-ai/tests/test_task_flow_state.py`
- Test: `/home/darthlinuxer/dialectic-crew-ai/tests/test_self_improve.py`

**Step 1: Write the failing test**
- Add tests proving each major flow updates breadcrumb state and emits corresponding runtime events:
  - PRD flow node entry (`iniciar_dialetica`, `rodar_rodada_dialetica`, `avaliar`, `salvar_prd_final`)
  - planning entry/retry/approval paths as stage-style breadcrumbs (planning is not a `Flow` class)
  - execution dialectic/verify/reimplement/completed/failed paths
  - self-improve stage entry/exit for baseline tests, introspection, prioritization, PRD, planning, execution, validation, and PR creation paths

**Step 2: Run test to verify it fails**
Run:
- `uv run pytest tests/test_prd_flow.py -q`
- `uv run pytest tests/test_task_flow_state.py -q`
- `uv run pytest tests/test_self_improve.py -k observability -q`
Expected: FAIL because flow-node breadcrumb events are not emitted consistently yet.

**Step 3: Write minimal implementation**
- Add helper calls that update the current node/phase and emit breadcrumb runtime events.
- Reuse existing state where available (for example `current_phase`, `phases_executed` in execution).
- For non-Flow orchestrators, emit explicit stage events instead of pretending there are native `Flow` nodes.
- Avoid changing business logic or retry behavior.

**Step 4: Run test to verify it passes**
Run:
- `uv run pytest tests/test_prd_flow.py -q`
- `uv run pytest tests/test_task_flow_state.py -q`
- `uv run pytest tests/test_self_improve.py -k observability -q`
Expected: PASS.

**Step 5: Commit**
- Commit message: `feat(observability): add flow breadcrumbs`

---

### Task 8: Add failure localization in terminal error paths

**Files:**
- Modify: `/home/darthlinuxer/dialectic-crew-ai/src/execution/task_flow.py`
- Modify: `/home/darthlinuxer/dialectic-crew-ai/src/main/self_improve.py`
- Modify: `/home/darthlinuxer/dialectic-crew-ai/src/dialectic/prd_flow.py`
- Modify: `/home/darthlinuxer/dialectic-crew-ai/src/planning/flow.py`
- Test: `/home/darthlinuxer/dialectic-crew-ai/tests/test_self_improve.py`
- Test: `/home/darthlinuxer/dialectic-crew-ai/tests/test_task_flow_state.py`

**Step 1: Write the failing test**
- Add tests proving failure events capture:
  - nearest flow node
  - task ID/story ID if known
  - agent/tool if known
  - exception type/message
  - correlation identity
- Include one self-improve stage failure case and one task flow failure case.

**Step 2: Run test to verify it fails**
Run:
- `uv run pytest tests/test_self_improve.py -k observability -q`
- `uv run pytest tests/test_task_flow_state.py -k failed -q`
Expected: FAIL because structured failure localization is not yet implemented.

**Step 3: Write minimal implementation**
- Emit explicit failure events in terminal failure paths.
- Preserve exception-chain context when available.
- Ensure observability failures remain non-fatal.

**Step 4: Run test to verify it passes**
Run:
- `uv run pytest tests/test_self_improve.py -k observability -q`
- `uv run pytest tests/test_task_flow_state.py -k failed -q`
Expected: PASS.

**Step 5: Commit**
- Commit message: `feat(observability): localize runtime failures`

---

### Task 9: Add end-to-end observability regression coverage

**Files:**
- Create: `/home/darthlinuxer/dialectic-crew-ai/tests/test_runtime_observability.py`
- Modify: `/home/darthlinuxer/dialectic-crew-ai/tests/test_cli_runtime.py`
- Modify: `/home/darthlinuxer/dialectic-crew-ai/tests/test_prd_flow.py`
- Modify: `/home/darthlinuxer/dialectic-crew-ai/tests/test_self_improve.py`

**Step 1: Write the failing test**
- Add integration-style tests proving one invocation yields an observable chain:
  - command start
  - correlation creation
  - flow breadcrumb(s)
  - lifecycle events from listener/hook layers
  - terminal success or failure event
- Add resume-specific coverage for:
  - `prd --resume`
  - `execute --resume-run`
  - `self-improve --resume`

**Step 2: Run test to verify it fails**
Run: `uv run pytest tests/test_runtime_observability.py -q`
Expected: FAIL because end-to-end correlation is not wired yet.

**Step 3: Write minimal implementation**
- Fill any remaining gaps in event propagation or sink writes.
- Keep the implementation minimal and avoid adding a second orchestration layer.

**Step 4: Run test to verify it passes**
Run: `uv run pytest tests/test_runtime_observability.py -q`
Expected: PASS.

**Step 5: Commit**
- Commit message: `test(observability): add runtime visibility regressions`

---

### Task 10: Run focused verification and document the feature

**Files:**
- Modify: `/home/darthlinuxer/dialectic-crew-ai/README.md`
- Modify: `/home/darthlinuxer/dialectic-crew-ai/docs/configuration.md`
- Modify: `/home/darthlinuxer/dialectic-crew-ai/docs/architecture.md`
- Create: `/home/darthlinuxer/dialectic-crew-ai/docs/plan/2026-03-11-crewai-native-runtime-visibility.md`

**Step 1: Update documentation**
- Document:
  - what native CrewAI observability layers are now used
  - how to enable tracing
  - where runtime event files are written
  - how to interpret correlation IDs and breadcrumb events
  - how redaction, truncation, and retention work
  - what degraded mode looks like when optional tracing/event features are missing
  - what remains intentionally out of scope for the first milestone

**Step 2: Run focused verification suites**
Run:
- `uv run pytest tests/test_runtime_events.py tests/test_runtime_event_sink.py tests/test_runtime_listener.py tests/test_hooks.py tests/test_crewai_runtime.py tests/test_runtime_observability.py -q`
- `uv run pytest tests/test_prd_flow.py tests/test_task_flow_state.py tests/test_self_improve.py tests/test_cli_runtime.py -q`
Expected: PASS.

**Step 3: Run broader regression floor**
Run: `uv run pytest --tb=short -q`
Expected: PASS, or only unrelated pre-existing failures if explicitly documented.

**Step 4: Commit**
- Commit message: `docs(observability): document runtime visibility`

---

## Architecture decisions

1. **Primary signal source:** CrewAI Event Listeners are the main runtime timeline.
2. **Deep diagnostics:** CrewAI tracing is enabled by configuration, not forced globally on day one.
3. **Guardrail layer:** CrewAI execution hooks remain the place for LLM/tool budgets, aborts, and protected-path policy events.
4. **Compatibility first:** Event imports and field extraction are centralized so CrewAI version drift does not leak through the entire implementation.
5. **Exact runtime position:** Explicit flow-node and orchestrator-stage breadcrumbs are required because lifecycle events alone do not fully answer “which method or stage is running right now?”.
6. **Storage:** Runtime event sink is separate from metrics storage and must enforce redaction/truncation/retention rules.
7. **Failure model:** Observability must never become a new source of runtime failure.

## Scope boundaries

**Included:**
- Runtime visibility for flows, tasks, agents, tools, LLM calls, retries, and failures
- Correlation IDs and resume continuity
- Repo-owned structured persistence of native observability signals
- Documentation and focused test coverage

**Excluded for this milestone:**
- API/WebSocket streaming layer
- External SaaS observability backends
- Multi-tenant auth concerns
- UI dashboards
- Database-backed event storage

## Suggested execution order

0. CrewAI observability contract adapter
1. Runtime event model
2. Event sink
3. CLI correlation context
4. BaseEventListener layer
5. CrewAI runtime wiring
6. Hook instrumentation
7. Flow and orchestrator breadcrumbs
8. Failure localization
9. End-to-end regression tests
10. Documentation and final verification

## Recommended handoff filename

`/home/darthlinuxer/dialectic-crew-ai/docs/plan/2026-03-11-crewai-native-runtime-visibility.md`

## Execution options

**1. Interactive execution** — Implement task-by-task with verification after each commit.

**2. Automated execution** — Implement in batched phases with checkpoints after Tasks 4, 7, and 10.

**3. Manual execution** — Use this document as a guide for self-directed implementation with the same test/commit cadence.
