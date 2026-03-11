# Architecture

This document describes the current architecture of Dialectic Crew AI as shipped in the repository.

## System overview

```mermaid
graph TB
    subgraph CLI[src/main/cli.py]
        PRD[prd]
        PLAN[plan]
        EXEC[execute]
        STATUS[status / verify-story]
        MANUAL[mark / verify]
        SELF[self-improve]
    end

    subgraph Core[src/dialectic]
        AGENTS[agents.py]
        YAMLCFG[yaml_config.py]
        PRDFLOW[prd_flow.py]
        PRDRT[prd_runtime.py]
        EXPORT[export.py]
        STATE[state.py]
        HOOKS[hooks.py]
        METRICS[metrics.py]
        INTRO[introspect.py]
        PRIOR[prioritize.py]
        PRIORRT[prioritize_runtime.py]
        VISION[vision.py]
    end

    subgraph Planning[src/planning]
        PFLOW[flow.py]
        PRT[runtime.py]
    end

    subgraph Execution[src/execution]
        ORCH[dialectic_execution.py]
        TFLOW[task_flow.py]
        TRT[runtime.py]
        VERIFY[verify.py]
        VRT[verify_runtime.py]
        RUNNER[runner.py]
    end

    subgraph MCP[src/mcp]
        SKIDX[skills_index.py]
        SKMCP[skills_mcp.py]
        SKILLS[skills/]
    end

    subgraph Models[src/schemas.py]
        SCHEMAS[Pydantic schemas]
    end

    PRD --> PRDFLOW
    PLAN --> PFLOW
    EXEC --> ORCH
    STATUS --> VERIFY
    MANUAL --> VERIFY
    SELF --> INTRO
    SELF --> PRIOR
    SELF --> PRDFLOW
    SELF --> PFLOW
    SELF --> ORCH

    PRDFLOW --> AGENTS
    PRDFLOW --> PRDRT
    PFLOW --> AGENTS
    PFLOW --> PRT
    TFLOW --> AGENTS
    TFLOW --> TRT
    VERIFY --> VRT
    AGENTS --> SKMCP
    SKMCP --> SKIDX
    SKIDX --> SKILLS

    PRDFLOW --> EXPORT
    PRDFLOW --> STATE
    PRDFLOW --> METRICS
    TFLOW --> METRICS
    INTRO --> METRICS
    SELF --> HOOKS

    PRDFLOW --> SCHEMAS
    PFLOW --> SCHEMAS
    TFLOW --> SCHEMAS
    ORCH --> SCHEMAS
    INTRO --> SCHEMAS
```

## Module responsibilities

### `src/dialectic/`

| File | Responsibility |
|---|---|
| `agents.py` | Core agent factories, LLM tier setup, MCP wiring, `vision_knowledge()` |
| `yaml_config.py` | Shared YAML config loader, placeholder rendering, and symbolic schema/guardrail resolution |
| `prd_flow.py` | PRD dialectic flow with retry, export, hooks, and persistence |
| `prd_runtime.py` | YAML-backed PRD crew builder used by `prd_flow.py` |
| `flow_persistence.py` | Shared CrewAI flow persistence backend selection (`.dialectic/flows.db` by default) |
| `state.py` | Flow state for PRD generation |
| `export.py` | JSON/Markdown export helpers |
| `config.py` | Export configuration loader |
| `hooks.py` | HookScope, token budgets, protected-path enforcement, cost tracking |
| `metrics.py` | SQLite-backed metrics store, defaulting to `.dialectic/metrics.db` |
| `introspect.py` | Four-lens introspection engine |
| `prioritize.py` | Dialectic prioritization for improvement opportunities, plus graceful-degradation fallback |
| `prioritize_runtime.py` | YAML-backed prioritization crew builder kept separate from fallback orchestration |
| `vision.py` | Vision context resolution and project-root helpers |
| `tools.py` | Shared CrewAI tool setup |
| `config/*.yaml` | Shared declarative agent/task templates for core dialectic crews |

### `src/planning/`

| File | Responsibility |
|---|---|
| `flow.py` | User-story planning dialectic with plan export and score thresholding |
| `runtime.py` | YAML-backed planning crew builder |
| `config/agents.yaml` | Declarative planning-specific agent personas |
| `config/tasks.yaml` | Declarative planning task templates |

### `src/execution/`

| File | Responsibility |
|---|---|
| `dialectic_execution.py` | Orchestrates task execution, dependency ordering, post-verification, and final reporting |
| `task_flow.py` | Per-task dialectic → verify → reimplement pipeline |
| `runtime.py` | YAML-backed task dialectic crew builder |
| `verify.py` | Shared task/story verification and status persistence |
| `task_reimplement_runtime.py` | YAML-backed independent reimplementation task builder used inside `task_flow.py` |
| `task_verify_runtime.py` | YAML-backed independent verifier task builder used inside `task_flow.py` |
| `verify_runtime.py` | YAML-backed standalone verification crew builder with read-only validator override |
| `runner.py` | Static spec generation (`--spec-only`) |
| `config/*.yaml` | Declarative execution and verification task templates |

The architecture now distinguishes two SQLite stores under `.dialectic/` by default:

- `.dialectic/flows.db` for CrewAI resumable flow state (`DIALECTIC_FLOW_DB` overrides it)
- `.dialectic/metrics.db` for passive telemetry (`DIALECTIC_METRICS_DB` overrides it)

### `src/mcp/`

| File | Responsibility |
|---|---|
| `skills_index.py` | Filesystem-backed index of discoverable `SKILL.md` files |
| `skills_mcp.py` | FastMCP server exposing skill listing, fetch, search, and resources |
| `skills/` | Project-local skill library |

## Key design choices

### 1. Dual vision contexts

The system does not hardcode a single vision file.

- `VisionContext.PROJECT` → `knowledge/VISION.md`
- `VisionContext.SELF` → `internal/SELF_VISION.md`

That context is resolved once and then attached as a CrewAI knowledge source for the relevant flow.

### 2. Fresh agents, persistent connectors

LLM connectors are module-level singletons, but agents themselves are factory-created per run. This avoids cross-run memory contamination while keeping configuration centralized.

Static agent and task text now lives in package-local YAML files where the content is stable. Thin runtime builder modules bind those templates to live CrewAI objects, knowledge sources, memory scopes, schema classes, guardrails, and runtime-only overrides.

Prioritization intentionally remains on this runtime-builder pattern rather than migrating to `CrewBase` today. The current split keeps the debate crew small and declarative while leaving failure handling and fallback ordering explicit in `src/dialectic/prioritize.py`.

### 3. Execution distrusts execution

Task execution is intentionally skeptical:

1. dialectic run produces an implementation
2. independent verifier checks actual files
3. fresh reimplementer tries to repair failed checks
4. orchestrator performs story-level verification again against PRD acceptance criteria

In other words, the codebase has trust issues, and honestly, good for it.

### 4. Hook-scoped safety

`HookScope` wraps expensive or risky flows to enforce:

- token budgets
- iteration caps
- protected-path write blocking
- cost and token metrics emission

This is especially important in `self-improve`, where the system must not casually rewrite its own safety rails.

### 5. Metrics without repo dirt

Runtime metrics are stored in `.dialectic/metrics.db` by default, not in a tracked top-level artifact. The path can be overridden with `DIALECTIC_METRICS_DB`.

### 6. MCP as optional enrichment

External MCP servers are loaded only when prerequisites are present. Missing Docker or missing API keys should reduce capability, not crash the entire run.

The local `skills_mcp` server is treated differently: it is a project capability and is wired directly into four core agents.

### 7. YAML-backed crews, Python-owned orchestration

The repository now follows a clearer split:

- YAML holds stable prompt and persona text
- runtime builder modules instantiate live CrewAI `Agent`, `Task`, and `Crew` objects
- Flow classes and orchestrators remain in Python, along with persistence, retries, result extraction, and safety logic

That keeps core orchestration explicit while making prompt-heavy modules much leaner.

## Self-improve architecture

`src/main/self_improve.py` is an orchestrator, not a CrewAI Flow class. It composes existing subsystems.

```mermaid
flowchart TD
    A[Baseline tests] --> B[Introspection]
    B --> C[Dialectic prioritization]
    C --> D[Create branch]
    D --> E[Generate PRD]
    E --> F[Plan user story]
    F --> G[Execute plan]
    G --> H[Run tests]
    H --> I[Check metric retention]
    I --> J[Create PR if gh is available]
```

Important current behavior:

- refuses to run without `git`
- refuses to run on a dirty worktree
- prefers `uv run pytest`, but falls back to `python -m pytest`
- preserves exact PRD/plan/execution artifact paths in the cycle record and PR body
- stores resumable cycle snapshots in `.dialectic/self_improve/<cycle-id>.json`
- resumes from the next unfinished stage using persisted PRD flow IDs, plan artifacts, and execution checkpoints
- prints a short resume summary describing the last failure, next stage, and reused artifacts/checkpoints
- creates a PR only when `gh` is available; otherwise it keeps the branch for manual review

## Technology stack

| Concern | Technology |
|---|---|
| Runtime | Python 3.10–3.13 |
| Orchestration | CrewAI Flows, Crews, Tasks, Agents |
| Validation | Pydantic v2 |
| Persistence | SQLite + CrewAI SQLiteFlowPersistence |
| Hooks / token counting | custom hooks + `tiktoken` |
| MCP | CrewAI MCP adapters + FastMCP |
| Packaging | setuptools + `pyproject.toml` |
| Recommended package manager | `uv` |

## Where to read next

- [`flows.md`](flows.md) for the routing behavior
- [`agents.md`](agents.md) for agent and MCP specifics
- [`configuration.md`](configuration.md) for runtime knobs