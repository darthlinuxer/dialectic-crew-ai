## Plan: CrewAI YAML Config Refactor Roadmap

## Status

- Drafted on 2026-03-11.
- Scope: refactor the repository toward stronger CrewAI project conventions by moving stable agent/task definitions into `config/*.yaml` while preserving Flow-first orchestration, persistence, guardrails, structured outputs, memory, knowledge sources, and vision isolation in Python.
- Primary goal: make core files leaner without regressing advanced CrewAI-native runtime behavior already present in the codebase.
- Secondary goal: reduce custom inline prompt wiring and move closer to documented CrewAI project structure where it fits naturally.

This roadmap is designed for phased execution by an LLM coding agent. Each phase has a narrow objective, concrete file targets, explicit checklists, and verification gates. The plan deliberately distinguishes between what CrewAI already supports natively in YAML-backed crews and what must remain in Python because it depends on Flow control, runtime state, callables, or project-specific safety constraints.

## CrewAI alignment summary

### Already aligned well

- `Flow` orchestration in `src/dialectic/prd_flow.py` and `src/execution/task_flow.py`
- `@persist()` state persistence and resume patterns
- `output_pydantic` structured outputs
- task guardrails
- `Memory` namespacing
- knowledge sources via `TextFileKnowledgeSource`
- MCP integration in `src/dialectic/agents.py`
- LLM hooks in `src/dialectic/hooks.py`

### Gaps this roadmap closes

- inline agent persona definitions in `src/dialectic/agents.py`
- inline task definitions in planning, PRD, execution, prioritization, and verification surfaces
- no `config/agents.yaml` or `config/tasks.yaml` organization in the application code
- inconsistent separation between declarative Crew definitions and runtime orchestration

### Important rule for implementation

Prefer documented CrewAI patterns first:
- Use YAML-backed agent/task config where the framework already supports it.
- Keep `Flow` classes in Python.
- Add only thin Python glue for features that YAML does not natively represent in this repository, such as `output_pydantic`, Python guardrails, memory wiring, knowledge sources, MCP/tool bundles, and dynamic state-dependent prompt sections.

## Non-goals

- Do not convert every module into `CrewBase` just for stylistic symmetry.
- Do not move `@start`, `@listen`, `@router`, persistence, retry logic, or artifact export into YAML.
- Do not weaken `VisionContext.PROJECT` vs `VisionContext.SELF` isolation.
- Do not replace fresh-per-run agent factories with cached singleton agents.
- Do not invent a large custom meta-framework around YAML.

## Target architecture

### Declarative layer in YAML

Use CrewAI-style config files in domain-local config folders:

- `src/dialectic/config/agents.yaml`
- `src/dialectic/config/tasks_prd.yaml`
- `src/planning/config/agents.yaml`
- `src/planning/config/tasks.yaml`
- `src/execution/config/tasks_dialectic.yaml`
- optional later:
  - `src/dialectic/config/tasks_prioritize.yaml`
  - `src/execution/config/tasks_verify.yaml`
  - `src/execution/config/agents_verify.yaml`

### Runtime layer in Python

Keep these responsibilities in Python:

- agent factory creation with fresh instances
- LLM tier binding
- tool and MCP bundle resolution
- `VisionContext` selection and `vision_label` interpolation
- `Memory` and `knowledge_sources` wiring
- schema binding for `output_pydantic`
- guardrail callable binding
- `Task.context` resolution from symbolic names to actual task objects
- Flow orchestration and persistence
- retry/stateful prompt augmentation
- artifact export and CLI contracts

## Suggested YAML schema

### `agents.yaml`

Each agent entry should support:

- `role`
- `goal`
- `backstory`
- optional runtime metadata interpreted by Python:
  - `llm_tier`
  - `tool_bundle`
  - `mcp_bundle`
  - `reasoning`
  - `max_reasoning_attempts`
  - `verbose`
  - `allow_delegation`

Placeholders are allowed where runtime values are known at kickoff time, for example:
- `{vision_label}`
- `{feature_objective}`
- `{user_story_title}`

### `tasks.yaml`

Each task entry should support:

- `description`
- `expected_output`
- `agent`
- optional CrewAI-compatible fields where appropriate:
  - `output_file`
  - `markdown`
- thin-adapter metadata for this repository:
  - `context`
  - `output_schema`
  - `guardrail`
  - `guardrail_max_retries`

## Phase-by-phase roadmap

### Phase 0 — foundation and safety rails

**Goal:** create the minimum config/runtime infrastructure needed to support YAML-backed definitions without breaking current behavior.

**Target files**
- `src/dialectic/agents.py`
- new loader/builder module under `src/dialectic/`
- new config folder under `src/dialectic/config/`
- tests for config loading and binding

**Checklist**
- [ ] Audit existing inline agent/task definitions and map each one to a future YAML key.
- [ ] Define a minimal runtime adapter for loading YAML config from package-local `config/` folders.
- [ ] Add symbolic registries for:
  - [ ] schema name → Pydantic class
  - [ ] guardrail name → Python callable
  - [ ] tool bundle name → tool list
  - [ ] MCP bundle name → MCP list
  - [ ] LLM tier name → configured LLM instance
- [ ] Decide on a placeholder interpolation strategy that works with CrewAI-style YAML values and runtime-provided inputs.
- [ ] Keep the adapter intentionally small and avoid embedding orchestration logic into it.

**CrewAI gap check**
- [ ] Re-check whether native CrewAI `config=` loading can cover enough of the use case before adding custom adapter behavior.
- [ ] Treat native CrewAI `Agent(config=...)`, `Task(config=...)`, YAML placeholders, `context`, `output_pydantic`, and guardrail support as the default path; add custom glue only for repo-specific runtime behavior that cannot stay declarative.
- [ ] Only keep custom registry behavior for repo-specific needs not covered by native YAML config.

**Verification gate**
- [ ] Add tests that prove YAML can be loaded, placeholders can be resolved, and symbolic schema/guardrail names can be bound safely.
- [ ] Verify no existing runtime behavior changes yet.

### Phase 1 — shared agent YAML migration

**Goal:** move static persona definitions out of `src/dialectic/agents.py` while preserving fresh factory semantics and runtime wiring.

**Target files**
- `src/dialectic/agents.py`
- `src/dialectic/config/agents.yaml`
- tests covering agent config loading and runtime binding

**Checklist**
- [ ] Move static fields for the following factories into YAML:
  - [ ] `create_visionario`
  - [ ] `create_critico_socratico`
  - [ ] `create_sintetizador`
  - [ ] `create_validador_macro`
  - [ ] `create_implementer`
- [ ] Keep Python responsible for:
  - [ ] `vision_label` interpolation
  - [ ] LLM tier selection
  - [ ] tool bundle resolution
  - [ ] MCP fallback behavior
  - [ ] fresh `Agent(...)` creation
- [ ] Preserve current knowledge-source and memory conventions unchanged.

**CrewAI gap check**
- [ ] Confirm that the resulting design still looks like a standard CrewAI YAML-backed agent config, not a parallel custom system.
- [ ] Confirm that YAML adds maintainability without making agent factories less explicit or less safe.

**Verification gate**
- [ ] Add tests proving each factory still returns a fresh agent instance.
- [ ] Add tests proving config-driven values are applied correctly.
- [ ] Re-run existing agent-focused tests.

### Phase 2 — planning crew migration

**Goal:** make `src/planning/flow.py` a thin orchestrator and move planning-specific agents/tasks into CrewAI-style YAML config.

**Target files**
- `src/planning/flow.py`
- new `src/planning/crew.py` or `src/planning/runtime.py`
- `src/planning/config/agents.yaml`
- `src/planning/config/tasks.yaml`
- `tests/test_planning_helpers.py`
- new planning builder/config tests

**Checklist**
- [ ] Create planning-specific agent YAML entries for:
  - [ ] visionary
  - [ ] critic
  - [ ] synthesizer
  - [ ] validator
- [ ] Move the following task templates into YAML:
  - [ ] thesis
  - [ ] antithesis
  - [ ] synthesis
  - [ ] validation
- [ ] Add a thin planning builder that:
  - [ ] loads YAML config
  - [ ] injects runtime values like PRD context, user story context, and `vision_label`
  - [ ] resolves `Task.context` dependencies
  - [ ] attaches `output_pydantic=UserStoryExecutionPlan`
  - [ ] attaches `_plan_guardrail`
  - [ ] assembles the crew with `planning=True`, `planning_llm=llm_planning`, memory, and knowledge sources
- [ ] Keep `run_user_story_planning()` responsible for:
  - [ ] PRD loading
  - [ ] user story resolution
  - [ ] retry loop
  - [ ] acceptance-check normalization
  - [ ] artifact export
  - [ ] public return contract

**CrewAI gap check**
- [ ] Re-check whether planning is now stable enough to look like a CrewAI YAML-configured crew without forcing a Flow migration.
- [ ] Re-check whether planning can reuse shared agent config plus planning-specific task YAML before introducing duplicated planning-only agent personas.
- [ ] Confirm no custom adapter behavior is doing work CrewAI placeholders could do directly.

**Verification gate**
- [ ] Keep `tests/test_planning_helpers.py` passing.
- [ ] Add planning config/builder tests for interpolation, context chaining, and validator binding.
- [ ] Re-run downstream tests that patch or call `run_user_story_planning()`.

### Phase 3 — PRD flow task migration

**Goal:** keep `DialecticFlow` Flow-first while moving stable task definitions into YAML.

**Target files**
- `src/dialectic/prd_flow.py`
- `src/dialectic/config/tasks_prd.yaml`
- tests for PRD flow wiring and guardrails

**Checklist**
- [ ] Move the following PRD task templates into YAML:
  - [ ] `task_vision`
  - [ ] `task_critica`
  - [ ] `task_sintese`
  - [ ] `task_validacao`
- [ ] Keep the following in Python:
  - [ ] `DialecticFlow`
  - [ ] `_build_retry_feedback_context`
  - [ ] `_extract_prd_from_result`
  - [ ] `_guardrail_success_output`
  - [ ] `_prd_guardrail`
  - [ ] persistence/resume
  - [ ] hook scope and metrics
  - [ ] optional file attachments
  - [ ] artifact export
- [ ] Ensure the builder can inject retry feedback blocks or knowledge-source references without making YAML conditional logic too clever.

**CrewAI gap check**
- [ ] Confirm the final design still follows the documented production pattern: Flow in Python, Crew as the focused unit of work.
- [ ] Re-check whether any YAML fields can be passed through native `config=` support directly instead of custom mapping.

**Verification gate**
- [ ] Re-run focused PRD flow tests.
- [ ] Re-run guardrail-related regressions.
- [ ] Verify persisted state/resume behavior is unchanged.

### Phase 4 — execution dialectic task migration

**Goal:** externalize the stable dialectic execution tasks in `src/execution/task_flow.py` while keeping the state machine intact.

**Target files**
- `src/execution/task_flow.py`
- `src/execution/config/tasks_dialectic.yaml`
- tests for task-flow wiring and validation behavior

**Checklist**
- [ ] Move the following dialectic task templates into YAML:
  - [ ] implement/thesis task
  - [ ] critique task
  - [ ] synthesis task
  - [ ] validation task
- [ ] Keep the following in Python:
  - [ ] `TaskExecutionFlow`
  - [ ] retry loop and `synthesis_for_retry`
  - [ ] verification branching
  - [ ] reimplementation branching
  - [ ] state mutation and scoring
  - [ ] memory and knowledge-source wiring
- [ ] Ensure task templates still receive runtime values such as `task_id`, `task_title`, `task_description`, `context_str`, `vision_label`, and retry synthesis text.

**CrewAI gap check**
- [ ] Confirm this remains a Flow-first execution design rather than drifting into an over-abstracted config engine.
- [ ] Re-check whether documented CrewAI task YAML patterns can cover any newly introduced fields before extending the adapter.

**Verification gate**
- [ ] Re-run focused task-flow state and execution regressions.
- [ ] Verify validation and retry semantics remain unchanged.

### Phase 5 — prioritization crew migration

**Goal:** move the stable prioritization crew toward stronger CrewAI project-style organization.

**Target files**
- `src/dialectic/prioritize.py`
- `src/dialectic/config/tasks_prioritize.yaml`
- optionally split or extend `src/dialectic/config/agents.yaml`

**Checklist**
- [ ] Move inline prioritization agents to YAML-backed definitions.
- [ ] Move inline prioritization tasks to YAML-backed definitions.
- [ ] Keep extraction, fallback sort, ranking application, and failure degradation in Python.
- [ ] Decide whether this module is a good candidate for a later `CrewBase` migration once YAML wiring is stable.

**CrewAI gap check**
- [ ] Re-check whether this is the right place to adopt `CrewBase` after the core migration pattern is proven.

**Verification gate**
- [ ] Re-run prioritization-related tests.
- [ ] Verify graceful degradation still works when Crew execution fails.

### Phase 6 — verification and override patterns

**Goal:** migrate standalone verification surfaces only after the config/runtime layer supports narrow runtime overrides cleanly.

**Target files**
- `src/execution/verify.py`
- optional `src/execution/config/tasks_verify.yaml`
- optional `src/execution/config/agents_verify.yaml`

**Checklist**
- [ ] Move verification task text into YAML if the adapter can bind `ValidationOutput` cleanly.
- [ ] Decide how to represent narrow tool overrides on top of `create_validador_macro(ctx)` without duplicating agent definitions.
- [ ] Keep plan lookup, artifact reading, and verification result extraction in Python.

**CrewAI gap check**
- [ ] Confirm whether CrewAI-native config plus small Python overrides is sufficient.
- [ ] Prefer shared validator config plus task-level or builder-level tool overrides before adding a separate `agents_verify.yaml`.
- [ ] Avoid creating a second agent definition just to support one specialized tool list unless the reuse boundary is genuinely cleaner.

**Verification gate**
- [ ] Re-run verification-focused tests.
- [ ] Verify no drift in CLI verification behavior.

### Phase 7 — docs and cleanup

**Goal:** document the new architecture so future contributors extend the YAML/config pattern consistently.

**Target files**
- `docs/flows.md`
- `docs/architecture.md`
- `docs/agents.md`
- `docs/cli.md` if user-visible behavior changed

**Checklist**
- [ ] Document which surfaces are Flow-first and which are stable crews.
- [ ] Document where static prompts now live.
- [ ] Document what still must remain in Python.
- [ ] Document the adapter’s intentionally narrow responsibilities.
- [ ] Document any future `CrewBase` candidates and why they were deferred.

**CrewAI gap check**
- [ ] Verify the docs explain the architecture in CrewAI-native terms, not custom jargon.

**Verification gate**
- [ ] Ensure docs do not claim features that the codebase does not yet implement.

## Implementation execution checklist for an LLM agent

Use this checklist at the start of each phase:

- [ ] Re-read the phase scope and non-goals.
- [ ] Check current CrewAI docs before introducing any custom config/runtime behavior.
- [ ] Confirm whether the framework already supports the desired pattern.
- [ ] Prefer native CrewAI YAML config fields before extending the adapter.
- [ ] Make one narrow migration slice at a time.
- [ ] Preserve public entrypoint contracts.
- [ ] Re-run the smallest relevant regression suite before moving on.
- [ ] Update docs only after the phase behavior is confirmed.

## Recommended phase order

1. Phase 0 — foundation and safety rails
2. Phase 1 — shared agent YAML migration
3. Phase 2 — planning crew migration
4. Phase 3 — PRD flow task migration
5. Phase 4 — execution dialectic task migration
6. Phase 5 — prioritization crew migration
7. Phase 6 — verification and override patterns
8. Phase 7 — docs and cleanup

## Success criteria

The roadmap is successful when:

- stable agent/task definitions are stored in domain-local YAML config files
- core flow/orchestrator files are visibly leaner
- CrewAI-native features already in the repo remain intact
- no public entrypoint contracts regress
- Flow orchestration remains explicit and testable in Python
- dynamic prompt/state behavior remains understandable and auditable
- future contributors can extend config without reintroducing large inline prompt blocks

## Final implementation decisions captured in this plan

- Use real CrewAI-style YAML config where possible.
- Keep Flow classes in Python.
- Use thin Python glue only for repo-specific needs not fully represented in YAML.
- Do not force `CrewBase` into the core Flow modules.
- Revisit `CrewBase` only for stable, non-Flow crew surfaces after the YAML migration pattern proves itself.

## Appendix A — file matrix and YAML key map

This appendix is intended to make execution more mechanical for an LLM agent. It maps each current inline surface to a future config location and clarifies what should remain Python-owned.

### Phase 1 file matrix — shared agents

| Current file | Current surface | Future YAML file | Future YAML key | Must remain in Python |
|---|---|---|---|---|
| `src/dialectic/agents.py` | `create_visionario` | `src/dialectic/config/agents.yaml` | `visionario` | fresh agent creation, `vision_label` interpolation, `llm_reasoning`, tool/MCP binding |
| `src/dialectic/agents.py` | `create_critico_socratico` | `src/dialectic/config/agents.yaml` | `critico_socratico` | fresh agent creation, `llm_complex`, MCP binding |
| `src/dialectic/agents.py` | `create_sintetizador` | `src/dialectic/config/agents.yaml` | `sintetizador` | fresh agent creation, `llm_complex`, MCP binding |
| `src/dialectic/agents.py` | `create_validador_macro` | `src/dialectic/config/agents.yaml` | `validador_macro` | fresh agent creation, `llm_simple`, tool binding |
| `src/dialectic/agents.py` | `create_implementer` | `src/dialectic/config/agents.yaml` | `implementer` | fresh agent creation, `llm_complex`, tool/MCP binding |

### Phase 2 file matrix — planning

| Current file | Current surface | Future YAML file | Future YAML key | Must remain in Python |
|---|---|---|---|---|
| `src/planning/flow.py` | planning visionary config | `src/planning/config/agents.yaml` | `planning_visionary` | runtime interpolation, live `Agent(...)` build |
| `src/planning/flow.py` | planning critic config | `src/planning/config/agents.yaml` | `planning_critic` | runtime interpolation, live `Agent(...)` build |
| `src/planning/flow.py` | planning synthesizer config | `src/planning/config/agents.yaml` | `planning_synthesizer` | runtime interpolation, live `Agent(...)` build |
| `src/planning/flow.py` | planning validator config | `src/planning/config/agents.yaml` | `planning_validator` | runtime interpolation, live `Agent(...)` build |
| `src/planning/flow.py` | thesis task | `src/planning/config/tasks.yaml` | `thesis_plan` | `Task.context` resolution, `output_pydantic`, guardrail binding |
| `src/planning/flow.py` | antithesis task | `src/planning/config/tasks.yaml` | `antithesis_plan` | `Task.context` resolution |
| `src/planning/flow.py` | synthesis task | `src/planning/config/tasks.yaml` | `synthesis_plan` | `Task.context` resolution |
| `src/planning/flow.py` | validation task | `src/planning/config/tasks.yaml` | `validation_plan` | `output_pydantic=UserStoryExecutionPlan`, `_plan_guardrail` |

### Phase 3 file matrix — PRD flow

| Current file | Current surface | Future YAML file | Future YAML key | Must remain in Python |
|---|---|---|---|---|
| `src/dialectic/prd_flow.py` | `task_vision` | `src/dialectic/config/tasks_prd.yaml` | `prd_thesis` | retry feedback assembly, runtime state injection |
| `src/dialectic/prd_flow.py` | `task_critica` | `src/dialectic/config/tasks_prd.yaml` | `prd_antithesis` | `Task.context` resolution |
| `src/dialectic/prd_flow.py` | `task_sintese` | `src/dialectic/config/tasks_prd.yaml` | `prd_synthesis` | `Task.context` resolution |
| `src/dialectic/prd_flow.py` | `task_validacao` | `src/dialectic/config/tasks_prd.yaml` | `prd_validation` | `output_pydantic=PRDSchema`, `_prd_guardrail`, persistence, export |

### Phase 4 file matrix — execution task flow

| Current file | Current surface | Future YAML file | Future YAML key | Must remain in Python |
|---|---|---|---|---|
| `src/execution/task_flow.py` | implement/thesis task | `src/execution/config/tasks_dialectic.yaml` | `execute_task_thesis` | retry loop, runtime state injection |
| `src/execution/task_flow.py` | critique task | `src/execution/config/tasks_dialectic.yaml` | `execute_task_antithesis` | `Task.context` resolution |
| `src/execution/task_flow.py` | synthesis task | `src/execution/config/tasks_dialectic.yaml` | `execute_task_synthesis` | `Task.context` resolution |
| `src/execution/task_flow.py` | validation task | `src/execution/config/tasks_dialectic.yaml` | `execute_task_validation` | `output_pydantic=ValidationOutput`, `_quality_guardrail` |
| `src/execution/task_flow.py` | independent verifier agent/task | deferred | deferred | verification branching, runtime checks text, `VerificationResult` binding |
| `src/execution/task_flow.py` | independent reimplementer agent/task | deferred | deferred | failed-check injection, revalidation branching |

### Phase 5 file matrix — prioritization

| Current file | Current surface | Future YAML file | Future YAML key | Must remain in Python |
|---|---|---|---|---|
| `src/dialectic/prioritize.py` | analyst | `src/dialectic/config/agents.yaml` or dedicated prioritize agent YAML | `prioritize_analyst` | live agent instantiation |
| `src/dialectic/prioritize.py` | critic | same | `prioritize_critic` | live agent instantiation |
| `src/dialectic/prioritize.py` | ranker | same | `prioritize_ranker` | live agent instantiation |
| `src/dialectic/prioritize.py` | analysis task | `src/dialectic/config/tasks_prioritize.yaml` | `prioritize_analysis` | fallback sort logic |
| `src/dialectic/prioritize.py` | critique task | `src/dialectic/config/tasks_prioritize.yaml` | `prioritize_critique` | `Task.context` resolution |
| `src/dialectic/prioritize.py` | rank task | `src/dialectic/config/tasks_prioritize.yaml` | `prioritize_rank` | `output_pydantic=PrioritizationResult`, `_prioritization_guardrail`, graceful degradation |

### Phase 6 file matrix — standalone verification

| Current file | Current surface | Future YAML file | Future YAML key | Must remain in Python |
|---|---|---|---|---|
| `src/execution/verify.py` | verification task | `src/execution/config/tasks_verify.yaml` | `verify_single_task` | task lookup, acceptance-criteria assembly, result extraction |
| `src/execution/verify.py` | validator override pattern | optional `src/execution/config/agents_verify.yaml` | `validator_read_only` | tool override support on top of shared validator factory |

## Appendix B — execution roadmap by task slice

This section breaks the work into LLM-friendly slices. Each slice should be completed, verified, and documented before moving to the next one.

### Slice 1 — add config infrastructure

- [ ] Create domain config folders if missing.
- [ ] Add minimal YAML loader support.
- [ ] Add schema registry.
- [ ] Add guardrail registry.
- [ ] Add tool/MCP/LLM bundle registries.
- [ ] Add tests for config parsing and symbol resolution.

### Slice 2 — migrate shared agents

- [ ] Create `src/dialectic/config/agents.yaml`.
- [ ] Move shared agent metadata into YAML.
- [ ] Update `src/dialectic/agents.py` factories to read YAML.
- [ ] Verify factories still create fresh instances.

### Slice 3 — migrate planning

- [ ] Create `src/planning/config/agents.yaml`.
- [ ] Create `src/planning/config/tasks.yaml`.
- [ ] Add planning builder/runtime module.
- [ ] Replace inline planning task construction with builder calls.
- [ ] Preserve `run_user_story_planning()` contract.
- [ ] Run planning helper and downstream self-improve regressions.

### Slice 4 — migrate PRD flow tasks

- [ ] Create `src/dialectic/config/tasks_prd.yaml`.
- [ ] Replace inline PRD task construction with builder calls.
- [ ] Preserve guardrail, structured-output, persistence, and export behavior.
- [ ] Run PRD flow and guardrail regressions.

### Slice 5 — migrate execution dialectic tasks

- [ ] Create `src/execution/config/tasks_dialectic.yaml`.
- [ ] Replace inline dialectic task construction with builder calls.
- [ ] Preserve task-flow retry and branching semantics.
- [ ] Run task-flow and execution regressions.

### Slice 6 — migrate prioritization

- [ ] Create prioritization task YAML.
- [ ] Move prioritization agents/tasks to config-backed builders.
- [ ] Preserve graceful degradation fallback behavior.
- [ ] Run prioritization regressions.

### Slice 7 — migrate verification overrides

- [ ] Create verification task YAML if justified.
- [ ] Add narrow override support for validator tool sets.
- [ ] Preserve CLI verification behavior.
- [ ] Run verification regressions.

### Slice 8 — docs cleanup

- [ ] Update `docs/flows.md`.
- [ ] Update `docs/architecture.md` and `docs/agents.md` as needed.
- [ ] Confirm docs describe current behavior only.

## Appendix C — phase review questions for the implementing LLM

Before closing any phase, answer all of these:

- [ ] Did I use native CrewAI YAML/config behavior where it already exists?
- [ ] Did I avoid moving orchestration logic into YAML?
- [ ] Did I preserve `VisionContext` separation?
- [ ] Did I preserve `output_pydantic` and guardrail semantics?
- [ ] Did I preserve fresh-per-run agent creation?
- [ ] Did I keep the adapter thinner than the code it replaces?
- [ ] Did I verify the narrowest relevant regression suite before moving on?

## Appendix D — recommended pytest commands by phase

Use `uv run pytest ... -q` as the default verification style for this roadmap. Run the narrowest suite that covers the changed surface before widening to downstream consumers.

### Phase 0 — foundation and safety rails

Required:

- `uv run pytest tests/test_agents.py tests/test_config.py tests/test_dialectic_config.py tests/test_crewai_runtime.py -q`

Recommended addition once the config runtime exists:

- `uv run pytest tests/test_yaml_config_runtime.py -q`

Notes:

- This phase should prove YAML loading, placeholder resolution, symbolic binding, and failure behavior for unknown schema or guardrail names.
- If new config-runtime helpers are shared across planning, PRD, and execution, add a dedicated foundational test file such as `tests/test_yaml_config_runtime.py`.

### Phase 1 — shared agent YAML migration

Required:

- `uv run pytest tests/test_agents.py -q`

Recommended broader check:

- `uv run pytest tests/test_agents.py tests/test_integration_agents.py -q`

Notes:

- Verify each factory in `src/dialectic/agents.py` still returns fresh agent instances.
- Verify YAML-backed fields are applied without changing vision-aware memory, knowledge, MCP fallback, or LLM-tier behavior.

### Phase 2 — planning crew migration

Required:

- `uv run pytest tests/test_planning_helpers.py -q`

Recommended downstream check:

- `uv run pytest tests/test_planning_helpers.py tests/test_self_improve.py tests/test_self_improve_lineage.py -q`

Notes:

- Planning is consumed by self-improve, so a downstream check is warranted after the planning builder or runtime is introduced.
- If a dedicated planning builder test file is added, include it in the required command.

### Phase 3 — PRD flow task migration

Required:

- `uv run pytest tests/test_prd_flow.py tests/test_flow_wiring.py tests/test_guardrails.py -q`

Recommended broader regression:

- `uv run pytest tests/test_prd_flow.py tests/test_guardrails.py tests/test_self_improve.py tests/test_self_improve_lineage.py -q`

Notes:

- Keep `tests/test_flow_wiring.py` in scope to protect the current CrewAI Flow decorator wiring while task creation moves out of `src/dialectic/prd_flow.py`.
- Resume and persistence semantics must remain unchanged.

### Phase 4 — execution dialectic task migration

Required:

- `uv run pytest tests/test_task_flow_state.py tests/test_flow_wiring.py tests/test_guardrails.py tests/test_dialectic_execution_resume.py -q`

Recommended broader regression:

- `uv run pytest tests/test_dialectic_execution_resume.py tests/test_flow_wiring.py tests/test_task_flow_state.py tests/test_self_improve.py tests/test_self_improve_lineage.py tests/test_cli_runtime.py -q`

Notes:

- This phase must preserve both task-flow behavior and execution resume or checkpoint semantics.
- If a dedicated execution YAML-builder test file is added, include it in the required command.

### Phase 5 — prioritization crew migration

Required:

- `uv run pytest tests/test_prioritize.py -q`

Recommended downstream check:

- `uv run pytest tests/test_prioritize.py tests/test_self_improve.py -q`

Notes:

- Prioritization is not isolated in practice; self-improve depends on it.
- Graceful degradation behavior must remain intact when crew execution fails.

### Phase 6 — verification and override patterns

Required:

- `uv run pytest tests/test_verify_ops.py tests/test_guardrails.py -q`

Recommended broader regression:

- `uv run pytest tests/test_verify_ops.py tests/test_guardrails.py tests/test_cli_runtime.py -q`

Optional live-LLM check:

- `uv run pytest tests/test_integration_verification.py -m llm -q`

Notes:

- Prefer shared validator config plus small runtime overrides before introducing separate verification-only agent YAML.
- Treat the LLM-backed verification run as optional and credential-gated.

### Phase 7 — docs and cleanup

Required:

- No pytest is required for docs-only updates.

If behavior or examples changed:

- `uv run pytest tests/test_cli_runtime.py -q`

Notes:

- Documentation must describe implemented behavior only.

### Global verification rule

- If a phase changes shared config or runtime builder behavior, rerun the smallest downstream suite that exercises the changed path.
