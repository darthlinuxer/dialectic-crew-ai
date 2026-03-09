# Architecture

This document describes the system architecture of Dialectic Crew AI, how modules connect, and the key design decisions.

---

## System Overview

```mermaid
graph TB
    subgraph CLI["CLI Layer (src/main/cli.py)"]
        CMD_PRD["prd command"]
        CMD_PLAN["plan command"]
        CMD_EXEC["execute command"]
        CMD_STATUS["status / mark / verify"]
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
| `agents.py` | Defines 5 CrewAI agents with LLM tier assignments |
| `prd_flow.py` | Main `DialecticFlow` (CrewAI Flow) for PRD generation with retry |
| `state.py` | `DialecticState` Pydantic model for flow state management |
| `config.py` | `ExportConfig` loader with pydantic-settings + fallback |
| `export.py` | `PRDExporter` (JSON+MD), markdown rendering, consistency validation |
| `tools.py` | CrewAI tools (FileRead, FileWrite, JSONSearch) used by agents |

### `src/planning/` — User Story Planning

| File | Responsibility |
|------|---------------|
| `flow.py` | Dialectic cycle for producing `UserStoryExecutionPlan` from a PRD user story |

### `src/execution/` — Plan Execution

| File | Responsibility |
|------|---------------|
| `dialectic_execution.py` | Orchestrates `TaskExecutionFlow` per task with topological sort |
| `task_flow.py` | Per-task CrewAI Flow: dialectic → verify → reimplement |
| `runner.py` | Generates spec Markdown from a plan (no LLM, static) |
| `verify.py` | Task status tracking, display, manual marking, LLM verification |

### `src/main/cli.py` — Command-Line Interface

Parses CLI arguments and dispatches to the appropriate module. Six commands: `prd`, `plan`, `execute`, `status`, `mark`, `verify`.

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
    CLI->>CLI: Read VISION.md
    CLI->>DialecticFlow: kickoff(feature, vision)
    loop Until score ≥ 9.0 or max retries
        DialecticFlow->>DialecticFlow: Thesis → Antithesis → Synthesis → Validation
    end
    DialecticFlow->>FileSystem: Export PRD (JSON + MD)
    FileSystem-->>User: prd_output/PRD_*.json + .md

    User->>CLI: dialectic-crew plan
    CLI->>PlanningFlow: run(prd, user_story, vision)
    PlanningFlow->>PlanningFlow: Dialectic cycle for plan
    PlanningFlow->>FileSystem: Export plan (JSON + MD)
    FileSystem-->>User: prd_output/exec_*.json + .md

    User->>CLI: dialectic-crew execute
    CLI->>ExecutionOrchestrator: run(plan, vision)
    loop For each task (topological order)
        ExecutionOrchestrator->>TaskFlow: kickoff(task)
        TaskFlow->>TaskFlow: Dialectic → Verify → Reimplement
        TaskFlow-->>ExecutionOrchestrator: TaskExecutionResult
    end
    ExecutionOrchestrator->>FileSystem: Save report + spec
    FileSystem-->>User: exec_output/<run_id>/report.json
```

---

## Design Decisions

### 1. Dialectics as Core Pattern

Every generative step (PRD, planning, execution) follows the same four-phase pattern. This isn't optional — the Validator agent is the sole approval gate, and proposals loop until they reach the quality threshold.

### 2. Anti-Drift Mechanism

```mermaid
graph LR
    VISION["VISION.md"] --> A1["Visionary reads it"]
    VISION --> A2["Critic checks alignment"]
    VISION --> A3["Synthesizer respects it"]
    VISION --> A4["Validator gates against it"]
    A4 --> ADQ["Anti-Drift Questions<br/>(mandatory in PRD)"]
    A4 --> VH["vision_hash<br/>(SHA-256 in MD frontmatter)"]

    style VISION fill:#FF6B6B,stroke:#C0392B,color:#fff
    style ADQ fill:#74B9FF,stroke:#0984E3,color:#fff
    style VH fill:#74B9FF,stroke:#0984E3,color:#fff
```

All agents are instructed to read `VISION.md`. Anti-drift questions are mandatory in every PRD. The exported Markdown includes a SHA-256 hash of the vision file, enabling automated drift detection.

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

### 5. Graceful Degradation

If CrewAI's `output_pydantic` fails to produce structured output, the system falls back to regex-based JSON extraction from raw text. If that also fails, placeholder objects are created and the flow continues.

### 6. Topological Sort for Task Ordering

Tasks with dependencies are ordered using a topological sort algorithm. If cycles are detected (invalid state), the system falls back to ordering by the `order` field.

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Runtime | Python 3.10–3.13 |
| Agent Framework | CrewAI (Flow API, Crew, Tasks, Agents) |
| Data Validation | Pydantic v2 |
| LLM Integration | LiteLLM (via CrewAI) |
| Configuration | pydantic-settings + python-dotenv |
| Build System | setuptools + pyproject.toml |
| Package Manager | uv (recommended) |
