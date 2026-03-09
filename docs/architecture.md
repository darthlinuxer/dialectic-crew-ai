# Architecture

This document describes the system architecture of Dialectic Crew AI, how modules connect, and the key design decisions.

---

## System Overview

```mermaid
graph TB
    subgraph CLI["CLI Layer (src/main/cli.py)"]
        CMD_PRD["prd command"]
        CMD_PLAN["plan command"]
        CMD_EXEC["execute command<br/>(auto-verify + story status)"]
        CMD_STATUS["status / verify-story"]
        CMD_OVERRIDES["mark / verify<br/>(manual overrides)"]
    end

    subgraph Core["Dialectic Core (src/dialectic/)"]
        AGENTS["agents.py<br/>5 AI Agents"]
        PRD_FLOW["prd_flow.py<br/>DialecticFlow"]
        STATE["state.py<br/>DialecticState"]
        EXPORT["export.py<br/>PRDExporter"]
        CONFIG["config.py<br/>ExportConfig"]
        TOOLS["tools.py<br/>FileRead/Write"]
    end

    subgraph Planning["Planning (src/planning/)"]
        PLAN_FLOW["flow.py<br/>User Story Planning"]
    end

    subgraph Execution["Execution (src/execution/)"]
        DIAL_EXEC["dialectic_execution.py<br/>Orchestrator"]
        TASK_FLOW["task_flow.py<br/>TaskExecutionFlow"]
        RUNNER["runner.py<br/>Spec Generator"]
        VERIFY["verify.py<br/>Task Tracking"]
    end

    subgraph Schemas["Data Models (src/schemas.py)"]
        PRD_S["PRDSchema"]
        PLAN_S["UserStoryExecutionPlan"]
        TASK_S["ImplementationTask"]
        EXEC_S["ExecutionReport"]
    end

    CMD_PRD --> PRD_FLOW
    CMD_PLAN --> PLAN_FLOW
    CMD_EXEC --> DIAL_EXEC
    CMD_STATUS --> VERIFY

    PRD_FLOW --> AGENTS
    PRD_FLOW --> STATE
    PRD_FLOW --> EXPORT
    PLAN_FLOW --> AGENTS
    DIAL_EXEC --> TASK_FLOW
    TASK_FLOW --> AGENTS
    TASK_FLOW --> TOOLS
    DIAL_EXEC --> VERIFY

    EXPORT --> CONFIG
    PRD_FLOW --> PRD_S
    PLAN_FLOW --> PLAN_S
    TASK_FLOW --> TASK_S
    DIAL_EXEC --> EXEC_S

    style CLI fill:#4A90D9,stroke:#2C5F8A,color:#fff
    style Core fill:#E8A838,stroke:#B8862D,color:#fff
    style Planning fill:#00B894,stroke:#00896B,color:#fff
    style Execution fill:#E17055,stroke:#D63031,color:#fff
    style Schemas fill:#6C5CE7,stroke:#4834D4,color:#fff
```

---

## Module Responsibilities

### `src/schemas.py` — Source of Truth

All Pydantic data models live here. Every module imports from this single file, ensuring consistent data structures throughout the system.

### `src/dialectic/` — Core Engine

| File | Responsibility |
|------|---------------|
| `agents.py` | Agent factory functions (5 agents with LLM tiers, MCP servers, tools) + `vision_knowledge()` for RAG-based VISION.md access |
| `prd_flow.py` | Main `DialecticFlow` (CrewAI Flow) for PRD generation with retry and lazy SQLite persistence |
| `state.py` | `DialecticState` Pydantic model for flow state management (feature objective, file attachments) |
| `config.py` | `ExportConfig` loader with pydantic-settings + fallback |
| `export.py` | `PRDExporter` (JSON+MD), markdown rendering, consistency validation |
| `tools.py` | CrewAI tools (FileRead, FileWrite, DirectoryRead, JSONSearch, CodeDocs) used by agents |

### `src/planning/` — User Story Planning

| File | Responsibility |
|------|---------------|
| `flow.py` | Dialectic cycle for producing `UserStoryExecutionPlan` from a PRD user story |

### `src/execution/` — Plan Execution

| File | Responsibility |
|------|---------------|
| `dialectic_execution.py` | Orchestrates `TaskExecutionFlow` per task with topological sort and dependency failure propagation, runs post-execution PRD verification, computes and persists user story status |
| `task_flow.py` | Per-task CrewAI Flow: dialectic → verify → reimplement |
| `runner.py` | Generates spec Markdown from a plan (no LLM, static) |
| `verify.py` | Task/story status tracking and display, reusable LLM verification core (`_run_verification`), story-level verification (`verify_user_story`), manual overrides (`mark_task`, `verify_task`) |

### `src/main/cli.py` — Command-Line Interface

Parses CLI arguments and dispatches to the appropriate module. Primary commands: `prd`, `plan`, `execute`, `status`, `verify-story`. Manual overrides: `mark`, `verify`.

---

## Data Flow

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant DialecticFlow
    participant PlanningFlow
    participant ExecutionOrchestrator
    participant TaskFlow
    participant FileSystem

    User->>CLI: dialectic-crew prd "Feature X"
    CLI->>CLI: Check knowledge/VISION.md exists
    CLI->>DialecticFlow: kickoff(feature)
    Note over DialecticFlow: Crews access VISION.md via TextFileKnowledgeSource
    loop Until score ≥ 9.0 or max retries
        DialecticFlow->>DialecticFlow: Thesis → Antithesis → Synthesis → Validation
    end
    DialecticFlow->>FileSystem: Export PRD (JSON + MD)
    FileSystem-->>User: prd_output/PRD_*.json + .md

    User->>CLI: dialectic-crew plan
    CLI->>PlanningFlow: run(prd, user_story)
    loop Until score ≥ 7.0 or max retries
        PlanningFlow->>PlanningFlow: Dialectic cycle for plan
    end
    PlanningFlow->>FileSystem: Export plan (JSON + MD)
    FileSystem-->>User: prd_output/exec_*.json + .md

    User->>CLI: dialectic-crew execute
    CLI->>ExecutionOrchestrator: run(plan)
    ExecutionOrchestrator->>FileSystem: Mark story in_progress
    loop For each task (topological order)
        ExecutionOrchestrator->>TaskFlow: kickoff(task)
        TaskFlow->>TaskFlow: Dialectic → Verify → Reimplement
        TaskFlow-->>ExecutionOrchestrator: TaskExecutionResult
        ExecutionOrchestrator->>FileSystem: Update task status
    end
    Note over ExecutionOrchestrator: Post-execution verification phase
    loop For each completed task
        ExecutionOrchestrator->>ExecutionOrchestrator: _run_verification(task, PRD criteria)
        ExecutionOrchestrator->>FileSystem: Update task status (verified/failed)
    end
    ExecutionOrchestrator->>FileSystem: Compute + persist story status
    ExecutionOrchestrator->>FileSystem: Save report + spec
    FileSystem-->>User: exec_output/run_id/report.json
```

---

## Design Decisions

### 1. Dialectics as Core Pattern

Every generative step (PRD, planning, execution) follows the same four-phase pattern. This isn't optional — the Validator agent is the sole approval gate, and proposals loop until they reach the quality threshold.

### 2. Anti-Drift Mechanism

```mermaid
graph LR
    VISION["knowledge/VISION.md"] --> KS["TextFileKnowledgeSource<br/>(semantic chunking + RAG)"]
    KS --> CREW["Crew knowledge_sources"]
    CREW --> A1["Visionary queries it"]
    CREW --> A2["Critic checks alignment"]
    CREW --> A3["Synthesizer respects it"]
    CREW --> A4["Validator gates against it"]
    A4 --> ADQ["Anti-Drift Questions<br/>(mandatory in PRD)"]
    A4 --> VH["vision_hash<br/>(SHA-256 in MD frontmatter)"]

    style VISION fill:#FF6B6B,stroke:#C0392B,color:#fff
    style KS fill:#DDA0DD,stroke:#9B59B6,color:#fff
    style ADQ fill:#74B9FF,stroke:#0984E3,color:#fff
    style VH fill:#74B9FF,stroke:#0984E3,color:#fff
```

All agents access `knowledge/VISION.md` via CrewAI's `TextFileKnowledgeSource`, which provides semantic chunking and vector retrieval. Relevant sections of the vision are automatically surfaced to agents based on query context, rather than injecting the full document text. Anti-drift questions are mandatory in every PRD. The exported Markdown includes a SHA-256 hash of the vision file, enabling automated drift detection.

### 3. Tiered LLM Strategy

```mermaid
graph TD
    subgraph Reasoning["Reasoning Tier (o3-mini)"]
        V["Visionary Architect"]
    end
    subgraph Complex["Complex Tier (gpt-4o)"]
        CR["Socratic Critic"]
        SY["Synthesizer"]
        IM["Implementer"]
    end
    subgraph Simple["Simple Tier (gpt-4o-mini)"]
        VA["Macro Validator"]
    end

    V -->|"Architecture<br/>decisions"| Reasoning
    CR -->|"Critique &<br/>synthesis"| Complex
    IM -->|"Implementation"| Complex
    VA -->|"Structured<br/>scoring"| Simple

    style Reasoning fill:#6C5CE7,stroke:#4834D4,color:#fff
    style Complex fill:#E8A838,stroke:#B8862D,color:#fff
    style Simple fill:#00B894,stroke:#00896B,color:#fff
```

Expensive reasoning models handle architecture; mid-tier handles implementation and critique; cheap models handle structured validation. This optimizes cost while maintaining quality.

### 4. Atomic Export with Rollback

When exporting "both" formats, JSON is written first (safe for pipelines). If Markdown writing fails, the JSON file is automatically rolled back (deleted) and an exception is raised.

### 5. Conditional MCP Loading

MCP (Model Context Protocol) servers are loaded only when their prerequisites are met. The `_make_mcp()` helper checks for required environment variables and system commands (e.g., Docker) before instantiation. Missing prerequisites cause the server to be `None`, which is filtered from agent `mcps=` lists. This prevents runtime errors when API keys or Docker are unavailable.

### 6. Graceful Degradation

If CrewAI's `output_pydantic` fails to produce structured output, the system falls back to regex-based JSON extraction from raw text. If that also fails, placeholder objects are created and the flow continues.

### 7. SQLite Flow Persistence (Lazy)

Both `DialecticFlow` and `TaskExecutionFlow` use `SQLiteFlowPersistence` from CrewAI. Persistence is lazily initialized on first use (not at module import) to avoid side effects during imports or testing. Flow state is persisted to a local SQLite database, enabling recovery after interruptions and providing an audit trail of dialectic iterations.

### 8. Crew Planning and Memory

Crews are configured with `planning=True` and `memory=True`. CrewAI's built-in planning step (using `LLM_MODEL_PLANNING`) generates a plan before agents execute, improving task coordination. Memory enables agents to learn from earlier interactions within a crew run.

### 9. Topological Sort with Dependency Propagation

Tasks with dependencies are ordered using a topological sort algorithm. If cycles are detected (invalid state), the system falls back to ordering by the `order` field. Tasks whose dependencies have failed are automatically skipped and marked as failed, preventing cascading wasted LLM calls.

### 10. Automated Post-Execution Verification

The execution flow does not trust its own dialectic score as the final word. After all tasks complete, an independent post-execution verification phase re-checks each completed task against PRD acceptance criteria using a separate LLM agent with file-reading tools. This provides a "second opinion" that catches cases where the dialectic cycle approved work that doesn't actually meet the acceptance criteria in the codebase. The verification core (`_run_verification`) is shared between the automated flow and the manual CLI commands (`verify`, `verify-story`), ensuring consistent behavior.

### 11. User Story-Level Status Tracking

User story status is computed automatically from task verification results and persisted in the plan JSON alongside task-level statuses. This closes the tracking loop: the plan file is the single source of truth for both task and story completion, eliminating the need to cross-reference separate report files. CLI commands (`status`, `verify-story`) and the execution flow all read and write status through the same `verify.py` functions.

### 12. Agent Factory Functions

Agents are defined as factory functions (`create_visionario()`, `create_critico_socratico()`, etc.) rather than module-level singletons. Each call returns a fresh `Agent` instance, preventing cross-flow memory contamination when `memory=True`. The `vision_knowledge()` factory creates a `TextFileKnowledgeSource` pointing to `knowledge/VISION.md` via CrewAI's standard knowledge directory convention.

### 13. RAG-Based Vision Access

Instead of injecting the full `VISION.md` text into every task description (which was repeated 4 times per dialectic round), the system uses CrewAI's `TextFileKnowledgeSource` for semantic chunking and vector retrieval. Each Crew is configured with `knowledge_sources=[vision_knowledge()]`, and agents receive only the vision sections relevant to their current query context.

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Runtime | Python 3.10–3.13 |
| Agent Framework | CrewAI (Flow API, Crew, Tasks, Agents) |
| Tool Integration | MCP (Model Context Protocol) via `crewai.mcp` |
| Data Validation | Pydantic v2 |
| LLM Integration | LiteLLM (via CrewAI) |
| State Persistence | SQLite (via CrewAI `SQLiteFlowPersistence`) |
| Configuration | pydantic-settings + python-dotenv |
| Build System | setuptools + pyproject.toml |
| Package Manager | uv (recommended) |
| Container Runtime | Docker (optional, for MCP Stdio servers) |
