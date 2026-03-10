# Plan: Fix Vision Context Drift and Tracing 401

## TL;DR

The three problems stem from two root causes: **(A)** agent prompts hardcode "VISION.md" in 14+ task descriptions and 5 agent backstories, causing confusion when running `self-improve` (where the RAG knowledge source correctly loads `SELF_VISION.md` but agents are told to consult "VISION.md"); **(B)** CrewAI's built-in tracing subsystem sends telemetry to CrewAI's cloud and gets a 401 because no API key is configured — the suppression only applies during `self-improve` today.

**Key insight for Problem 2:** The RAG plumbing is **already correct** — `vision_knowledge(VisionContext.SELF)` loads `internal/SELF_VISION.md` and all Crew instances pass `knowledge_sources=[vision_knowledge(VisionContext(self.state.vision_context))]`. The real issue is that the **prompt text** misleads agents into looking for "VISION.md" by name, which conflicts with the actual RAG content during self-improve.

---

## Steps

### 1. Add `_vision_label()` helper in `src/dialectic/agents.py`

Create a function (around line 100) that resolves the human-readable document name from `VisionContext` → `"VISION.md"` or `"SELF_VISION.md"` (using the existing `_VISION_PATHS` mapping from `src/dialectic/vision.py` lines 22–25).

### 2. Add optional `vision_context` parameter to all 5 agent factory functions

In `src/dialectic/agents.py`:

- `create_visionario(vision_context=VisionContext.PROJECT)`
- `create_critico_socratico(vision_context=VisionContext.PROJECT)`
- `create_sintetizador(vision_context=VisionContext.PROJECT)`
- `create_validador_macro(vision_context=VisionContext.PROJECT)`
- `create_implementer(vision_context=VisionContext.PROJECT)`

Interpolate `_vision_label(vision_context)` into each backstory where "VISION.md" is currently hardcoded (lines 127, 157, 210, 224, 236, 239–240). Default `VisionContext.PROJECT` preserves backward compatibility with existing tests and callers.

### 3. Update all 14 task description strings across 4 files

Replace hardcoded "VISION.md" with a dynamic reference using the vision context available in each scope:

| File | Lines | Context source |
|------|-------|----------------|
| `src/dialectic/prd_flow.py` | 98, 116, 136, 155 | `self.state.vision_context` |
| `src/planning/flow.py` | 190, 206, 228, 253 | `vision_context` parameter |
| `src/execution/task_flow.py` | 220, 230, 247, 261, 273, 415 | `self.state.vision_context` |
| `src/dialectic/prioritize.py` | 121, 175 | `vision_context` parameter |

### 4. Pass `vision_context` to agent factory calls at every call site

All flow methods and functions already have access to the context:

| Call site | File | Vision context source |
|-----------|------|-----------------------|
| `rodar_rodada_dialetica` | `src/dialectic/prd_flow.py` (line ~86) | `VisionContext(self.state.vision_context)` |
| `_build_planning_crew` | `src/planning/flow.py` (line ~184) | `vision_context` parameter |
| `run_dialectic` | `src/execution/task_flow.py` (line ~200) | `VisionContext(self.state.vision_context)` |
| `independent_reimplement` | `src/execution/task_flow.py` (line ~410) | `VisionContext(self.state.vision_context)` |
| `verify_task_implementation` | `src/execution/verify.py` (line ~260) | `ctx` parameter |
| `dialectic_prioritize` | `src/dialectic/prioritize.py` (line ~109) | `vision_context` parameter |

### 5. Suppress CrewAI tracing globally

- Move `os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")` from `src/main/self_improve.py` (line 45) into the CLI entry point at `src/main/cli.py` `main()` function so it applies to all commands (`prd`, `plan`, `execute`, `self-improve`).
- Keep it in `self_improve.py` as well for direct invocations.
- Update `.env.example` to document `CREWAI_DISABLE_TELEMETRY=true` and explain the 401 warning.

### 6. Run tests

```bash
.venv/bin/python -m pytest tests/test_agents.py tests/test_prioritize.py tests/test_self_improve.py tests/test_self_improve_git_safety.py tests/test_self_improve_lineage.py -q
```

---

## Verification

- Run the unit test suite above (101 tests should still pass)
- Run `grep -rn "VISION\.md is available" src/` and confirm **zero results** (all references now dynamic)
- Run `grep -rn "VISION\.md, available via" src/` and confirm **zero results** in backstories
- Manual smoke test: run `python -m main.cli self-improve --dry-run` and verify no "VISION.md" references appear in agent prompts, and no 401 tracing warning appears

---

## Decisions

| Decision | Rationale |
|----------|-----------|
| **Optional parameter with default over mandatory** | All agent factory functions get `vision_context=VisionContext.PROJECT` as the default, avoiding breaking changes to existing callers and tests that use `create_visionario()` without args |
| **Dynamic interpolation over generic phrasing** | Using the actual document name (e.g., "SELF_VISION.md") in prompts rather than a generic term like "the macro vision document" — this gives agents clearer guidance about which specific file they're working with |
| **Global telemetry suppression** | The 401 is not an MCP issue — it's CrewAI's built-in tracing trying to phone home without credentials. Suppressing it globally in the CLI entry point is the cleanest fix since the project doesn't use CrewAI Cloud |

---

## Files to Modify

1. `src/dialectic/agents.py` — add `_vision_label` helper, add `vision_context` param to 5 factories
2. `src/dialectic/prd_flow.py` — interpolate vision label in 4 task descriptions, pass ctx to agent factories
3. `src/planning/flow.py` — interpolate vision label in 4 task descriptions, pass ctx to agent factories
4. `src/execution/task_flow.py` — interpolate vision label in 6 task descriptions, pass ctx to agent factories
5. `src/execution/verify.py` — pass ctx to agent factories
6. `src/dialectic/prioritize.py` — interpolate vision label in 2 references, pass ctx to agent factories
7. `src/main/cli.py` — add global telemetry suppression in `main()`
8. `.env.example` — document `CREWAI_DISABLE_TELEMETRY=true`
