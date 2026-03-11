# Deep-Modules Refactoring Plan — Dialectic Crew AI

## Current State Summary

This codebase is a CrewAI-powered dialectic engine structured across 5 packages under `src/` (~4,500 lines of Python) with 30+ test files. The mental model is sound — `dialectic/`, `execution/`, `planning/`, `main/`, `mcp/` — but several modules have grown beyond their cohesion boundary.

**Main problems:**
- 3 files exceed 400 lines (one is 798 lines)
- Classes mix with loose functions in the same file
- Helper patterns repeat across runtime modules
- `_find_latest_plan` is duplicated 3 times
- Several functions lack input validation on arguments

---

## Fast Feedback Loop

```bash
# After each refactoring step:
uv run pytest -q                                      # ~30s, unit-only, no API keys
uv run pytest --cov=src --cov-report=term-missing      # coverage check
uv run python -c "from dialectic import DialecticFlow"  # import smoke test
```

Run after each step below. If any test breaks, fix before continuing.

---

## Module Map (current state)

| Module | Key Files | Lines | Classes | Coupling Risks |
|--------|-----------|-------|---------|----------------|
| **dialectic/** | 17 `.py` files | ~2,700 | `DialecticState` (27L), `DialecticFlow` (173L class body), `TokenBudgetTracker` (100L), `HookScope` (80L), `MetricsStore` (95L), `PRDExporter` (75L), `ExportConfig` (dataclass) | `prd_flow.py` (473L), `export.py` (504L), `hooks.py` (516L) all exceed 400L. `agents.py` (215L) mixes LLM singletons + MCP config + agent factories + bundles + knowledge helpers |
| **execution/** | 7 `.py` files | ~1,500 | `TaskFlowState` (35L), `TaskExecutionFlow` (200L) | `dialectic_execution.py` (471L) exceeds 400L. `_find_latest_plan` duplicated in `runner.py`, `verify.py`, and `dialectic_execution.py`. `verify.py` (419L) nearly exceeds limit |
| **planning/** | 3 `.py` files | ~350 | none | Clean but `flow.py` mixes guardrail + helpers + main function |
| **main/** | 2 `.py` files | ~1,316 | `_CycleAbort` (trivial) | `self_improve.py` (798L!) is the worst offender. `cli.py` (518L) exceeds 400L with manual arg parsing |
| **mcp/** | 2 `.py` files | ~500 | `SkillIndex` (95L), 3 Pydantic input models | Clean. `skills_mcp.py` (365L) fine |
| **schemas.py** | 1 file | ~160 | 13 Pydantic models | Single-file design is correct per project conventions |

---

## Dialectic Method Cohesion Findings

A structured review of the Thesis → Antithesis → Synthesis → Validation loop across all three surfaces (PRD, planning, execution) identified the following actionable concerns. Items that can be naturally addressed during a refactoring phase are tagged with that phase.

| ID | Finding | Severity | Affected Files | Phase |
|----|---------|----------|----------------|-------|
| DC-1 | **Validator context inconsistency**: PRD validator sees only synthesis (`context=[task_sintese]`), while planning and execution validators see all three phases. The PRD validator cannot verify that critiques were actually addressed. | Medium | `src/dialectic/prd_runtime.py` | Phase 6 |
| DC-2 | **Planning retries lack feedback propagation**: `run_user_story_planning` rebuilds the crew from scratch each retry with no validator feedback. PRD and execution retries both propagate feedback (retry_feedback_block / synthesis_for_retry). Planning may repeat the same mistakes across retries. | High | `src/planning/flow.py` | Phase 9 |
| DC-3 | **Reimplementation loses dialectic context**: When task verification fails and `independent_reimplement` triggers, the reimplementation crew receives only `failed_checks` + `verification_notes`. Original dialectic reasoning (critic insights, synthesis rationale) is not carried forward. | Low | `src/execution/task_flow.py` | Phase 8 |
| DC-4 | **Validator uses weakest LLM tier**: All validators use `llm_tier: simple`. Score calibration is critical (determines retry vs approve), and simpler models may not reliably distinguish quality levels. Guardrails partially compensate for schema compliance but not for scoring accuracy. | Low | `src/dialectic/config/agents.yaml`, `src/planning/config/agents.yaml` | Config-only (no structural change) |

---

## Proposed Deep Modules + Interface Specs

### Module 1: `dialectic/` — Core dialectic engine

**Split plan:**

| Current File | Problem | Target Files |
|---|---|---|
| `agents.py` (215L) | Mixes LLM singletons, MCP config, tool bundles, knowledge, memory, and agent factories | `llm.py` (LLM singletons + tier registry), `mcp_config.py` (MCP server setup + bundles), `tool_bundles.py` (tool bundle registry), `knowledge.py` (vision knowledge + crew memory), `agents.py` (only agent factories + `_build_agent`) |
| `prd_flow.py` (473L) | Flow class + guardrails + retry feedback builder + JSON parsing helpers + `run_dialectic_flow()` | `prd_flow.py` (only `DialecticFlow` class + `run_dialectic_flow`), `prd_guardrails.py` (guardrail + extraction helpers) |
| `export.py` (504L) | `PRDExporter` class + `render_markdown` + `prd_to_markdown` + `execution_plan_to_markdown` + `validate_consistency` + frontmatter parsing | `prd_exporter.py` (only `PRDExporter` class), `markdown_renderers.py` (all `*_to_markdown` + `render_markdown` functions), `export_validation.py` (`validate_consistency` + `_parse_frontmatter`) |
| `hooks.py` (516L) | `TokenBudgetTracker` class + `HookScope` class + 4 hook functions + token counting helpers | `token_tracker.py` (`TokenBudgetTracker` class + `count_tokens` + `count_messages_tokens`), `hooks.py` (`HookScope` class + 4 hook functions) |
| `metrics.py` (~200L) | OK as-is | No split needed |

### Module 2: `execution/` — Task execution engine

**Split plan:**

| Current File | Problem | Target Files |
|---|---|---|
| `dialectic_execution.py` (471L) | Main orchestrator + topological sort + context builder + checkpoint I/O + plan loading (duplicated) | `dialectic_execution.py` (~300L, only `run_dialectic_execution`), `checkpoint.py` (checkpoint save/load/upsert), `plan_loader.py` (shared `_find_latest_plan` + `_load_plan` — **replaces all 3 copies**), `topological_sort.py` (`_topological_sort`), `context_builder.py` (`_build_task_context`) |
| `verify.py` (419L) | Plan I/O + status display + mark + update + verification logic | `verify.py` (verification-only: `_run_verification`, `verify_task`, `verify_user_story`), `status.py` (`show_status`, `_STATUS_ICONS`, `mark_task`, `update_task_status`, `update_user_story_status`) |
| `runner.py` | Duplicates `_find_latest_plan` + `_load_plan` | Uses shared `plan_loader.py` instead |
| `task_flow.py` (415L) | Technically within 400L for class body, but mixes guardrails with the flow class | `task_flow.py` (only `TaskFlowState` + `TaskExecutionFlow`), move `_quality_guardrail` + `_verification_guardrail` to `task_guardrails.py` |

### Module 3: `main/` — CLI + self-improve

**Split plan:**

| Current File | Problem | Target Files |
|---|---|---|
| `self_improve.py` (798L!) | **Worst offender.** Mixes git helpers, test runners, metrics comparison, PR creation, record persistence, cycle listing, resume logic, print formatting, and the main orchestrator | `self_improve.py` (~350L, only `run_self_improve` + `_CycleAbort`), `git_helpers.py` (all `_git_*` functions + `_recover_stale_self_improve_worktree` + `_dirty_worktree_guidance`), `test_runner.py` (`_snapshot_tests`, `_pytest_command`, `_emit_test_failure_details`), `metrics_comparison.py` (`_metrics_stable`), `self_improve_persistence.py` (record save/load/list + `_record_*_artifacts` + `_require_artifact` + `_summarize_resume_state`), `pr_builder.py` (`_create_pr` + `_build_pr_body` + `_print_report`) |
| `cli.py` (518L) | Manual arg parsing bloat | `cli.py` (~300L, dispatch + gates), `cli_commands.py` (all `cmd_*` functions) |

### Module 4: `planning/` — No changes needed

At ~350L total with clean separation already. Leave as-is.

### Module 5: `mcp/` — No changes needed

At ~500L total with clean separation. Leave as-is.

---

## Identified Function Call Gaps

These should be addressed during the refactor:

| Location | Gap | Fix |
|---|---|---|
| `prd_flow.py` `_materialize_plain_data` | No type guard on input; silently returns `None` for unexpected types | Add explicit `Any` return path or raise `TypeError` |
| `dialectic_execution.py` `_topological_sort` | Does not validate that task dependencies reference existing task IDs | Add check: warn/log on unknown dependency IDs before fallback |
| `verify.py` `_find_task` | Normalizes to `upper()` for comparison but task IDs might have more complex patterns | Document normalization contract or use `casefold()` |
| `planning/flow.py` `_normalize_us_ref` | No validation that input is a string; would crash on `None` with `.strip()` | The caller passes `str \| None` but `_normalize_us_ref` doesn't guard `None` |
| `self_improve.py` `_run_cmd` | `timeout` param not validated; negative values would cause `subprocess` errors | Add `max(timeout, 1)` guard |
| `agents.py` `_get_agent_config` | Accepts `vision_context` param but never uses it | Remove unused parameter |
| `export.py` `execution_plan_to_markdown` | Accepts `dict` but doesn't validate it has required keys before `model_validate` | Wrap in try/except with meaningful error |
| `cli.py` `cmd_prd` | `feature_request` can be `None` even when `resume_id` is `None` — passed to `run_dialectic_flow` which would raise | Add early guard matching the if-block in `main()` |
| `prd_runtime.py` `build_prd_crew` | Validation task context is `[task_sintese]` (synthesis only), unlike planning/execution which pass all 3 phases — validator cannot verify critique incorporation (DC-1) | Change to `context=[task_vision, task_critica, task_sintese]` for consistency |
| `planning/flow.py` `run_user_story_planning` | Retry loop rebuilds crew from scratch with no feedback from previous validator rejection (DC-2) | Propagate `final_validation_notes` from failed attempt into next crew as retry context, mirroring PRD's `retry_feedback_block` pattern |
| `execution/task_flow.py` `independent_reimplement` | Reimplementation crew receives only verification failure data, losing original dialectic reasoning (DC-3) | Pass condensed dialectic summary (`dialectic_notes` + `impl_output` snippet) as additional context to `build_task_flow_reimplementation_crew` |

---

## Boundary Enforcement

1. **`__init__.py` as public API**: each package's `__init__.py` exports only the public interface. Imports from outside the package must go through `__init__.py`, not reach into internal files.

2. **Naming convention**: files prefixed with `_` are explicitly internal (e.g. `_git_helpers.py`). However, since CrewAI's yaml_config references guardrail names by string, guardrail files must remain importable by the registry.

3. **Shared helpers**: create `src/execution/plan_loader.py` as the single source of truth for `_find_latest_plan()` and `_load_plan()`. Delete all 3 current copies.

4. **No cross-module private access**: `main/` should never import `_`-prefixed functions from `dialectic/` or `execution/` — use the public interface.

---

## Testing Strategy

1. **Contract tests first**: before moving code, write boundary tests for each new helper module's public functions:
   - `test_plan_loader.py` — test `find_latest_plan()` and `load_plan()` against fixtures
   - `test_git_helpers.py` — test git helper functions (already partially covered in `test_self_improve_git_safety.py`)
   - `test_token_tracker.py` — extract from existing `test_hooks.py`

2. **Existing tests remain**: current test files map to current source files. After split, update imports but keep the same assertions. Existing `test_self_improve.py`, `test_hooks.py`, `test_export_helpers.py`, `test_prd_flow.py` etc. continue to work with updated import paths.

3. **No new LLM-dependent tests**: all new boundary tests should be pure-unit (mock where needed).

---

## Incremental Migration Steps

### Phase 1 — Extract shared helpers (low risk, highest deduplication payoff) ✅ Completed 2026-03-11

1. Create `src/execution/plan_loader.py` with `find_latest_plan()` + `load_plan()`
2. Update `runner.py`, `verify.py`, `dialectic_execution.py` to import from `plan_loader`
3. Delete all 3 `_find_latest_plan` / `_load_plan` copies
4. Run tests ✓

Completed with shared helpers in `src/execution/plan_loader.py` plus focused regression coverage in `tests/test_plan_loader.py`.

### Phase 2 — Split `self_improve.py` (798L → 6 files)

1. Extract `git_helpers.py` (all `_git_*` + recovery + worktree)
2. Extract `test_runner.py` (`_snapshot_tests`, `_pytest_command`, `_emit_test_failure_details`)
3. Extract `self_improve_persistence.py` (record I/O + resume helpers + listing)
4. Extract `pr_builder.py` (`_create_pr`, `_build_pr_body`, `_print_report`)
5. Extract `metrics_comparison.py` (`_metrics_stable`)
6. Slim `self_improve.py` to only `run_self_improve()` + `_CycleAbort`
7. Run tests ✓ (especially `test_self_improve.py`, `test_self_improve_git_safety.py`, `test_self_improve_lineage.py`)

Status: steps 1-2 completed on 2026-03-11 via `src/main/git_helpers.py` and `src/main/test_runner.py`; focused self-improve regressions passed after each extraction.

### Phase 3 — Split `agents.py` (mixed concerns → 5 focused files)

1. Extract `llm.py` (LLM singletons + `_LLM_BY_TIER`)
2. Extract `mcp_config.py` (MCP server instances + `_MCP_BUNDLES`)
3. Extract `tool_bundles.py` (`_TOOL_BUNDLES`)
4. Extract `knowledge.py` (`vision_knowledge`, `crew_memory`, `_vision_label`)
5. Slim `agents.py` to agent factories only
6. Run tests ✓

### Phase 4 — Split `hooks.py` (516L → 2 files)

1. Extract `token_tracker.py` (`TokenBudgetTracker` + `count_tokens` + `count_messages_tokens`)
2. Keep `hooks.py` with `HookScope` + 4 hook functions (imports from `token_tracker`)
3. Run tests ✓

### Phase 5 — Split `export.py` (504L → 3 files)

1. Extract `prd_exporter.py` (`PRDExporter` class)
2. Extract `markdown_renderers.py` (all `*_to_markdown` + `render_markdown`)
3. Extract `export_validation.py` (`validate_consistency` + `_parse_frontmatter`)
4. Run tests ✓

### Phase 6 — Split `prd_flow.py` (473L → 2 files)

1. Extract `prd_guardrails.py` (`_prd_guardrail`, `_extract_prd_from_result`, `_guardrail_success_output`, `_build_retry_feedback_context`, `_materialize_plain_data`)
2. Slim `prd_flow.py` to `DialecticFlow` class + `run_dialectic_flow()`
3. **Address DC-1**: In `prd_runtime.py`, update `task_validacao` context from `[task_sintese]` to `[task_vision, task_critica, task_sintese]` for cross-surface consistency
4. Run tests ✓

### Phase 7 — Split `cli.py` (518L → 2 files) + `dialectic_execution.py` (471L → 4 files)

1. Extract `cli_commands.py` (all `cmd_*` functions)
2. Extract `checkpoint.py`, `topological_sort.py`, `context_builder.py` from `dialectic_execution.py`
3. Run tests ✓

### Phase 8 — Split `verify.py` (419L → 2 files) + `task_flow.py` guardrails

1. Extract `status.py` from `verify.py`
2. Extract `task_guardrails.py` from `task_flow.py`
3. **Address DC-3**: In `task_flow.py` `independent_reimplement`, pass condensed dialectic context (`dialectic_notes` + truncated `impl_output`) into the reimplementation crew so design insights from the original dialectic survive verification failure
4. Run tests ✓

### Phase 9 — Fix function call gaps + dialectic cohesion

1. Address all 11 gaps from the table above (original 8 + DC-1 through DC-3)
2. **Address DC-2**: In `planning/flow.py` `run_user_story_planning`, propagate `final_validation_notes` from failed attempts into the next planning crew as retry context, mirroring the PRD flow's `retry_feedback_block` pattern
3. **(Optional) Evaluate DC-4**: Consider upgrading validator `llm_tier` from `simple` to `complex` in `agents.yaml` / `planning/config/agents.yaml` — config-only change, no structural impact
4. Run full test suite ✓

### Phase 10 — Update `__init__.py` public APIs

1. Update all 5 package `__init__.py` files to re-export from new file locations
2. Ensure all external imports still work
3. Run full test suite ✓

---

## Verification

```bash
# After each phase:
uv run pytest -q

# After all phases complete:
uv run pytest --cov=src --cov-report=term-missing

# Confirm: no coverage regression, all imports resolve, no circular imports
python -c "from dialectic import DialecticFlow; from execution import run_dialectic_execution; from main.self_improve import run_self_improve"
```

---

## Decisions

- **`schemas.py` stays as single file**: 160 lines with 13 models is well within limits and follows project convention
- **`planning/` and `mcp/` untouched**: both under 400L per file with clean cohesion
- **Strangler pattern**: all moves use import-forwarding in the original location during transition, deleted only after all consumers are migrated
- **No new abstractions**: splits create smaller files with the same functions — no new base classes, protocols, or registries
- **`_find_latest_plan` deduplication is Phase 1**: highest-value, lowest-risk change to validate the workflow

---

## File Count Summary

| Package | Before | After | Net change |
|---------|--------|-------|------------|
| `dialectic/` | 17 | 25 | +8 |
| `execution/` | 7 | 14 | +7 |
| `main/` | 2 | 8 | +6 |
| `planning/` | 3 | 3 | 0 |
| `mcp/` | 2 | 2 | 0 |
| `src/` (root) | 1 | 1 | 0 |
| **Total** | **32** | **53** | **+21** |

Every file after the refactor will be under 400 lines, with one class per file (where classes exist) and functions grouped into cohesive helper modules.
