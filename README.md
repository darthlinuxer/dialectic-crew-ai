# Dialectic Crew AI

> Automated PRD generation using Socratic/Hegelian dialectics with CrewAI.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![CrewAI](https://img.shields.io/badge/CrewAI-1.10+-purple.svg)](https://crewai.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## What is it?

**Dialectic Crew AI** generates high-quality PRDs (Product Requirement Documents) through a dialectic process:

```
THESIS → ANTITHESIS → SYNTHESIS → VALIDATION → (RETRY UNTIL 9.0)
```

- **Thesis (Visionary)**: Proposes the initial solution
- **Antithesis (Critic)**: Challenges the proposal with rigorous critique
- **Synthesis (Synthesizer)**: Merges ideas into a superior version
- **Validation (Gate)**: Approves if score >= 9.0

## Features

- 4 AI agents working in harmony (OpenAI models by tier)
- Automatic retry until quality score reaches 9.0
- Pydantic validation with native CrewAI `output_pydantic`
- Task Guardrails for automatic output validation
- Native timeout with `akickoff()` + `asyncio.wait_for()`
- Anti-drift: all agents read VISION.md before acting
- Task tracking: status, LLM-based verification, acceptance criteria
- Three-phase execution pipeline: Dialectic → Verify (A+B) → Reimplement (C) via `@router`
- Dual export: JSON + Markdown with YAML frontmatter

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
python main.py prd "Login with 2FA"
```

### Plan user story execution

```bash
# Latest PRD, first user story
python main.py plan

# Specific PRD and user story
python main.py plan prd_output/PRD_20260308_1640.json US1
```

### Execute plan with dialectic

```bash
# Uses the latest plan
python main.py execute

# Specific plan
python main.py execute prd_output/exec_US1_20260308_1750.json

# Generate spec Markdown only (no LLM)
python main.py execute --spec-only
```

### Check task status

```bash
# Status of all tasks from the latest plan
python main.py status

# Specific plan
python main.py status prd_output/exec_US1_20260308_1750.json
```

### Manually mark a task

```bash
python main.py mark T0 completed
python main.py mark T3 failed prd_output/exec_US1_20260308_1750.json
```

### Verify task with LLM agent

```bash
# Verify if a task was implemented correctly
python main.py verify T0

# With PRD to check acceptance criteria
python main.py verify T2 --prd prd_output/PRD_20260308_1640.json
```

### Alternative CLI (output format override)

```bash
python -m main.cli "Login with 2FA" --output-format both
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
| `CREW_KICKOFF_TIMEOUT` | Total timeout for crew.kickoff() (seconds) | `300` |

## Execution Pipeline

Each task runs through a CrewAI Flow (`TaskExecutionFlow`) with conditional routing:

```
@start() run_dialectic
    │
    ▼
@router evaluate_dialectic
    ├── "verify"  → verify_implementation (Phase A + B)
    │                    │
    │              @router evaluate_verification
    │                    ├── "completed" → done ✓
    │                    └── "reimplement" → independent_reimplement (Phase C)
    │                                        ├── "completed" ✓
    │                                        └── "failed" ✗
    └── "failed" → done ✗
```

## Exported Markdown Format

Generated Markdown includes YAML frontmatter with audit metadata:

```yaml
---
quality_score: 9.2
validation_status: approved
generated_at: 2026-03-08T20:00:00Z
vision_hash: a1b2c3d4...  # SHA-256 of VISION.md
---
```

Body sections: `# Objective`, `## Macro Impact`, `## User Stories`, `## Anti-Drift Questions`

## Project Structure

```
dialectic-crew-ai/
├── main.py                        # Bootstrap entry point
├── run_dialectic.py               # Convenience: full dialectic flow
├── run_simple.py                  # Convenience: single-pass (no retry)
├── run_user_story_dialectic.py    # Convenience: plan a user story
├── pyproject.toml                 # Project config (uv/pip, package-dir=src)
├── VISION.md                      # System macro vision
├── .env                           # API keys and config (not committed)
├── tests/                         # Unit tests (26 tests)
│   └── test_*.py
└── src/                           # All packages
    ├── schemas.py                 # Pydantic models (PRD, tasks, execution)
    ├── dialectic/                 # Dialectic core
    │   ├── agents.py              # CrewAI agents (model tiers)
    │   ├── prd_flow.py            # Main flow (thesis→antithesis→synthesis→validation)
    │   ├── state.py               # Flow state
    │   ├── export.py              # Dual exporter (JSON+MD) with atomicity
    │   ├── config.py              # Export configuration
    │   └── tools.py               # CrewAI tools (FileRead, FileWrite)
    ├── planning/                  # User story planning
    │   └── flow.py                # Dialectic cycle for execution plans
    ├── execution/                 # Plan execution
    │   ├── dialectic_execution.py # Orchestrator: runs TaskExecutionFlow per task
    │   ├── task_flow.py           # CrewAI Flow: dialectic→verify→reimplement
    │   ├── runner.py              # Spec Markdown generation
    │   └── verify.py              # Task tracking and LLM verification
    └── main/                      # CLI
        └── cli.py                 # Full CLI (prd, plan, execute, status, mark, verify)
```

## Tests

```bash
# Run all unit tests
uv run python -m pytest tests/ -v --ignore=tests/test_llm_tooling.py

# Run tool calling test (requires API key)
uv run python tests/test_llm_tooling.py
```
