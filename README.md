# Dialectic Crew AI

> CrewAI-powered dialectic PRD generation, user-story planning, execution, verification, and self-improvement.

[![Python](https://img.shields.io/badge/Python-3.10--3.13-blue.svg)](https://www.python.org/)
[![CrewAI](https://img.shields.io/badge/CrewAI-1.10+-purple.svg)](https://crewai.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## Overview

Dialectic Crew AI applies the same structured pattern across product definition and delivery:

$$
\text{Thesis} \rightarrow \text{Antithesis} \rightarrow \text{Synthesis} \rightarrow \text{Validation}
$$

It can:

- generate PRDs from a feature request
- plan implementation for a selected user story
- execute tasks with dialectic review, independent verification, and reimplementation
- track task and story status in plan artifacts
- run a guarded `self-improve` cycle against the app's own roadmap
- expose local agent skills through a built-in MCP server wired into core agents

## Current state

This repository is **beta / pre-production** and already ships the end-to-end engine:

- dual-vision architecture:
  - `knowledge/VISION.md` for the user's project
  - `internal/SELF_VISION.md` for the app's own evolution
- PRD, planning, execution, verification, and status commands
- passive metrics in `.dialectic/metrics.db` by default
- four-lens introspection plus dialectic prioritization for self-improvement
- guarded self-improvement with git cleanliness checks, test gates, metric gates, token budgets, and optional PR creation via `gh`
- built-in `skills_mcp` server for local `SKILL.md` discovery

The broader roadmap still lives in [`internal/SELF_VISION.md`](internal/SELF_VISION.md), but the codebase is already more than a PRD generator—it is a dialectic delivery loop with observability and self-reflection.

## Core capabilities

- **Five persistent agent factories** in `src/dialectic/agents.py`
- **Planning and memory enabled** on dialectic crews
- **Pydantic-first outputs** with guardrails and fallbacks
- **Semantic vision retrieval** through CrewAI `TextFileKnowledgeSource`
- **Execution pipeline**: dialectic → verify → reimplement
- **Story-level verification** via `verify-story`
- **Hook-based safety** for token budgets, cost tracking, and protected paths
- **Artifact lineage** across self-improve PRD/plan/execution stages
- **Conditional MCP loading** for Context7, Brave Search, Sequential Thinking, plus local skills MCP

## Installation

### Using `uv` (recommended)

```bash
git clone <repo-url>
cd dialectic-crew-ai
uv sync
source .venv/bin/activate
cp .env.example .env
```

### Using `pip`

```bash
git clone <repo-url>
cd dialectic-crew-ai
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

Then add at least one API key to `.env`:

```env
OPENAI_API_KEY=sk-...
```

## Quick start

### 1. Generate a PRD

```bash
uv run dialectic-crew prd "Login with 2FA"
uv run dialectic-crew prd "Dashboard redesign" --files wireframe.png spec.pdf
```

### 2. Plan a user story

```bash
uv run dialectic-crew plan
uv run dialectic-crew plan prd_output/PRD_20260308_164012.json US1
```

### 3. Execute the plan

```bash
uv run dialectic-crew execute
uv run dialectic-crew execute prd_output/exec_US1_20260308_175030.json
uv run dialectic-crew execute --spec-only
```

### 4. Inspect or re-verify status

```bash
uv run dialectic-crew status
uv run dialectic-crew verify-story
uv run dialectic-crew verify T0
uv run dialectic-crew mark T0 completed
```

### 5. Run self-improvement

```bash
uv run dialectic-crew self-improve --dry-run
uv run dialectic-crew self-improve
uv run dialectic-crew self-improve --max 3
```

## Self-improvement workflow

`self-improve` targets `internal/SELF_VISION.md` and runs:

1. baseline test snapshot
2. introspection across vision gaps, metrics, code health, and failure patterns
3. dialectic prioritization of opportunities
4. PRD generation with `VisionContext.SELF`
5. planning with explicit PRD artifact handoff
6. execution with exact artifact lineage capture
7. validation with tests + metric retention
8. optional PR creation through `gh`

Safety rails currently enforced by code:

- clean git worktree required before branch creation
- isolated `self-improve/<timestamp>` branches
- immutable protected files during hook-scoped execution
- token budget via `SELF_IMPROVE_TOKEN_BUDGET`
- per-agent iteration cap via `SELF_IMPROVE_MAX_ITERATIONS`
- pytest suite timeout via `SELF_IMPROVE_TEST_TIMEOUT`
- metrics retention gate via `MIN_METRIC_RETENTION`
- `uv run pytest` when available, with Python fallback when `uv` is absent
- baseline and post-run validation print captured pytest output when they fail

## MCP and skills integration

`src/dialectic/agents.py` conditionally wires external MCP servers and always attempts to start the local skills server:

- **Context7** — optional HTTP MCP, requires `CONTEXT7_API_KEY`
- **Brave Search** — optional stdio MCP, requires `BRAVE_API_KEY` and Docker
- **Sequential Thinking** — optional stdio MCP, requires Docker
- **skills_mcp** — local stdio MCP backed by `src/mcp/skills_mcp.py`

The built-in skills server indexes `SKILL.md` files from:

- `src/mcp/skills`
- `~/.agents/skills`
- `~/.cursor/skills-cursor`

It exposes:

- `skills_list_skills`
- `skills_get_skill`
- `skills_search_skills`
- `skills://{skill_id}` resources

Current agent wiring:

- `create_visionario()` → Context7, Brave, Skills
- `create_critico_socratico()` → Sequential Thinking, Skills
- `create_sintetizador()` → Context7, Skills
- `create_implementer()` → Context7, Brave, Skills
- `create_validador_macro()` → no MCP servers

## Configuration highlights

| Variable | Default | Purpose |
|---|---|---|
| `LLM_MODEL_SIMPLE` | `gpt-4o-mini` | Validator model |
| `LLM_MODEL_COMPLEX` | `gpt-4o` | Critic, Synthesizer, Implementer |
| `LLM_MODEL_REASONING` | `o3-mini` | Visionary model |
| `LLM_MODEL_PLANNING` | same as reasoning | CrewAI planning step |
| `PRD_OUTPUT_FORMAT` | `both` | `json`, `md`, or `both` |
| `PRD_OUTPUT_DIR` | `prd_output` | PRD and plan export directory |
| `MIN_PLAN_SCORE` | `7.5` | Planning approval threshold |
| `MIN_QUALITY_SCORE` | `7.5` | Task execution approval threshold |
| `DIALECTIC_METRICS_DB` | `.dialectic/metrics.db` | Metrics database path override |
| `SELF_IMPROVE_TOKEN_BUDGET` | `500000` | Self-improve token budget |
| `SELF_IMPROVE_MAX_ITERATIONS` | `25` | Self-improve per-agent iteration cap |
| `MIN_METRIC_RETENTION` | `0.95` | Metric regression gate |
| `SKILLS_MCP_TRANSPORT` | `stdio` | Skills MCP transport |
| `SKILLS_MCP_PORT` | `8001` | Skills MCP HTTP port when enabled |

For the full list, see [`docs/configuration.md`](docs/configuration.md).

## Repository layout

```text
dialectic-crew-ai/
├── main.py
├── pyproject.toml
├── README.md
├── internal/
│   └── SELF_VISION.md
├── knowledge/
│   └── VISION.md
├── docs/
├── exec_output/
├── prd_output/
├── src/
│   ├── schemas.py
│   ├── dialectic/
│   │   ├── agents.py
│   │   ├── config.py
│   │   ├── export.py
│   │   ├── hooks.py
│   │   ├── introspect.py
│   │   ├── metrics.py
│   │   ├── prd_flow.py
│   │   ├── prd_output.py
│   │   ├── prioritize.py
│   │   ├── state.py
│   │   ├── tools.py
│   │   └── vision.py
│   ├── execution/
│   │   ├── dialectic_execution.py
│   │   ├── runner.py
│   │   ├── task_flow.py
│   │   └── verify.py
│   ├── main/
│   │   ├── cli.py
│   │   └── self_improve.py
│   ├── mcp/
│   │   ├── skills_index.py
│   │   ├── skills_mcp.py
│   │   └── skills/
│   └── planning/
│       └── flow.py
└── tests/
```

## Tests

```bash
uv run pytest --tb=short -q
```

Real LLM integration tests are marked separately in the test suite and may require configured provider credentials.

## Documentation

- [`docs/getting-started.md`](docs/getting-started.md) — setup and first workflow
- [`docs/architecture.md`](docs/architecture.md) — system design and module boundaries
- [`docs/flows.md`](docs/flows.md) — PRD, planning, execution, and self-improve orchestration
- [`docs/agents.md`](docs/agents.md) — agent roles, tools, and MCP wiring
- [`docs/cli.md`](docs/cli.md) — full CLI reference
- [`docs/configuration.md`](docs/configuration.md) — environment variables and runtime knobs
- [`docs/export.md`](docs/export.md) — JSON/Markdown export behavior
- [`docs/schemas.md`](docs/schemas.md) — Pydantic schema reference