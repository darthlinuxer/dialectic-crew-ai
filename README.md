# Dialectic Crew AI

> Automated PRD generation using Socratic/Hegelian dialectics with CrewAI.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![CrewAI](https://img.shields.io/badge/CrewAI-1.10+-purple.svg)](https://crewai.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## Project Status

**This is a pre-production, self-evolving application.** The system is currently using its own dialectic pipeline to implement the features defined in [`knowledge/VISION.md`](knowledge/VISION.md). In other words, the app generates PRDs for its own roadmap items, plans user stories, and produces execution artifacts to build itself.

The goal is to first implement and test all features from the vision document. Once the full feature set is stable and verified, the application will be transformed into a **general-purpose dialectic platform** that works like an advanced REPL loop with full observability — capable of ingesting any external project, generating PRDs, planning implementation, and executing tasks against it.

**Current phase:** Phase 1 (core engine) is complete. The system is bootstrapping Phases 2-6 through self-evolution.

## What is it?

**Dialectic Crew AI** generates high-quality PRDs (Product Requirement Documents) through a dialectic process:

```
THESIS -> ANTITHESIS -> SYNTHESIS -> VALIDATION -> (RETRY UNTIL 9.0)
```

- **Thesis (Visionary)**: Proposes the initial solution
- **Antithesis (Critic)**: Challenges the proposal with rigorous critique
- **Synthesis (Synthesizer)**: Merges ideas into a superior version
- **Validation (Gate)**: Approves if score >= 9.0

## Features

- 5 AI agents as factory functions (fresh per flow, no cross-run contamination)
- Automatic retry until quality score reaches 9.0
- Pydantic validation with native CrewAI `output_pydantic`
- Task Guardrails for automatic output validation
- RAG-based vision access via CrewAI `TextFileKnowledgeSource` (semantic retrieval from `knowledge/VISION.md`)
- Anti-drift: all agents consult the macro vision via knowledge sources before acting
- Planning flow with retry loop and quality gate
- Task tracking: status, LLM-based verification, acceptance criteria
- Three-phase execution pipeline: Dialectic -> Verify (A+B) -> Reimplement (C) via `@router`
- Dual export: JSON + Markdown with YAML frontmatter
- SQLite persistence with lazy initialization for flow state recovery
- Dependency-aware task ordering via topological sort
- Conditional MCP server loading (Context7, Brave Search, Sequential Thinking)

## Installation

```bash
git clone <repo-url>
cd dialectic-crew-ai
uv sync

# Configure API key
cp .env.example .env
# Edit .env and add OPENAI_API_KEY=sk-...
```

## Usage (CLI)

### Generate PRD

```bash
uv run dialectic-crew prd "Login with 2FA"
# or: python main.py prd "Login with 2FA"

# With reference files
uv run dialectic-crew prd "Dashboard redesign" --files wireframe.png spec.pdf
```

### Plan user story execution

```bash
# Latest PRD, first user story
uv run dialectic-crew plan

# Specific PRD and user story
uv run dialectic-crew plan prd_output/PRD_20260308_164012.json US1
```

### Execute plan with dialectic

```bash
# Uses the latest plan
uv run dialectic-crew execute

# Specific plan
uv run dialectic-crew execute prd_output/exec_US1_20260308_175030.json

# Generate spec Markdown only (no LLM)
uv run dialectic-crew execute --spec-only
```

### Check task status

```bash
# Status of all tasks from the latest plan
uv run dialectic-crew status

# Specific plan
uv run dialectic-crew status prd_output/exec_US1_20260308_175030.json
```

### Manually mark a task

```bash
uv run dialectic-crew mark T0 completed
uv run dialectic-crew mark T3 failed prd_output/exec_US1_20260308_175030.json
```

### Verify task with LLM agent

```bash
# Verify if a task was implemented correctly
uv run dialectic-crew verify T0

# With PRD to check acceptance criteria
uv run dialectic-crew verify T2 --prd prd_output/PRD_20260308_164012.json
```

## Configuration (.env)

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | (required) |
| `LLM_MODEL_SIMPLE` | Model for lightweight tasks (validation) | `gpt-4o-mini` |
| `LLM_MODEL_COMPLEX` | Model for complex tasks (implementation, critique) | `gpt-4o` |
| `LLM_MODEL_REASONING` | Model for architecture and macro decisions | `o3-mini` |
| `LLM_REQUEST_TIMEOUT` | Timeout per LLM request (seconds) | `900` |
| `PRD_OUTPUT_FORMAT` | PRD export format: `json`, `md`, `both` | `json` |
| `PRD_OUTPUT_DIR` | PRD output directory | `prd_output` |
| `MAX_RETRIES_PER_TASK` | Retries per task in dialectic cycle | `3` |
| `MIN_QUALITY_SCORE` | Minimum score to approve a task (0-10) | `7.5` |

## Execution Pipeline

Each task runs through a CrewAI Flow (`TaskExecutionFlow`) with conditional routing:

```
@start() run_dialectic
    |
    v
@router evaluate_dialectic
    +-- "verify"  -> verify_implementation (Phase A + B)
    |                    |
    |              @router evaluate_verification
    |                    +-- "completed" -> done
    |                    +-- "reimplement" -> independent_reimplement (Phase C)
    |                                        +-- "completed"
    |                                        +-- "failed"
    +-- "failed" -> done
```

## Exported Markdown Format

Generated Markdown includes YAML frontmatter with audit metadata:

```yaml
---
quality_score: 9.2
validation_status: approved
generated_at: 2026-03-08T20:00:00Z
vision_hash: a1b2c3d4...  # SHA-256 of knowledge/VISION.md
---
```

Body sections: `# Objective`, `## Macro Impact`, `## User Stories`, `## Anti-Drift Questions`

## Project Structure

```
dialectic-crew-ai/
+-- main.py                        # Bootstrap entry point
+-- pyproject.toml                 # Project config (uv/pip, package-dir=src)
+-- knowledge/
|   +-- VISION.md                  # System macro vision (accessed via TextFileKnowledgeSource)
+-- .env                           # API keys and config (not committed)
+-- tests/                         # Unit tests
|   +-- test_*.py
+-- docs/                          # Full documentation
+-- src/                           # All packages
    +-- schemas.py                 # Pydantic models (PRD, tasks, execution)
    +-- dialectic/                 # Dialectic core
    |   +-- agents.py              # Agent factory functions + vision_knowledge()
    |   +-- prd_flow.py            # Main flow (thesis->antithesis->synthesis->validation)
    |   +-- state.py               # Flow state
    |   +-- export.py              # Dual exporter (JSON+MD) with atomicity
    |   +-- config.py              # Export configuration
    |   +-- tools.py               # CrewAI tools (FileRead, FileWrite)
    +-- planning/                  # User story planning
    |   +-- flow.py                # Dialectic planning flow with retry loop
    +-- execution/                 # Plan execution
    |   +-- dialectic_execution.py # Orchestrator with dependency propagation
    |   +-- task_flow.py           # Per-task CrewAI Flow
    |   +-- runner.py              # Spec Markdown generation
    |   +-- verify.py              # Task tracking and LLM verification
    +-- main/                      # CLI
        +-- cli.py                 # Full CLI (prd, plan, execute, status, mark, verify)
```

## Self-Evolution Roadmap

The application is currently working through its own roadmap (see [`knowledge/VISION.md`](knowledge/VISION.md) for the full vision):

- **Phase 1** (complete): Core dialectic engine, planning, execution, CLI
- **Phase 2** (next): CrewAI feature adoption (Memory, Reasoning, Planning, Conditional Tasks, LLM Hooks)
- **Phase 3**: Self-improvement via Training (`crew.train()`) and Testing (`crewai test`)
- **Phase 4**: REST API with Event Listeners, PostgreSQL, background workers
- **Phase 5**: Web UI with live dialectic visualization and review workflows
- **Phase 6**: External integrations (GitHub, Jira, Slack) and multi-tenant scale

Once all phases are implemented and battle-tested through self-evolution, the platform will be generalized to accept any external project as input — functioning as an advanced REPL loop with full observability for automated PRD generation, planning, and execution.

## Tests

```bash
# Run all unit tests
uv run python -m pytest tests/ -v --ignore=tests/test_llm_tooling.py

# Run tool calling test (requires API key)
uv run python tests/test_llm_tooling.py
```

## Documentation

Full documentation is available in the [`docs/`](docs/) directory:

- [Getting Started](docs/getting-started.md) — Installation, prerequisites, first run
- [Architecture](docs/architecture.md) — System design, module layout, design decisions
- [Flows](docs/flows.md) — CrewAI Flow pipelines with diagrams
- [Agents](docs/agents.md) — Agent definitions, LLM tiers, MCP servers
- [Data Models](docs/schemas.md) — Pydantic schemas and data flow
- [CLI Reference](docs/cli.md) — All commands and usage examples
- [Configuration](docs/configuration.md) — Environment variables and export settings
- [Export System](docs/export.md) — Dual export (JSON + Markdown), validation, rollback
