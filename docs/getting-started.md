# Getting Started

This guide walks through the current end-to-end workflow: install, configure, generate a PRD, plan it, execute it, verify it, and optionally run self-improvement.

## Prerequisites

- Python 3.10–3.13
- at least one supported LLM API key
- `knowledge/VISION.md` customized for your project
- Docker only if you want Brave Search or Sequential Thinking MCP support
- `git` if you plan to use `self-improve`

## Install

### Option 1: `uv` (recommended)

```bash
git clone <repo-url>
cd dialectic-crew-ai
uv sync
source .venv/bin/activate
```

### Option 2: `pip`

```bash
git clone <repo-url>
cd dialectic-crew-ai
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Configure `.env`

```bash
cp .env.example .env
```

Minimum example:

```env
OPENAI_API_KEY=sk-your-key-here
```

Useful optional settings:

```env
PRD_OUTPUT_FORMAT=both
MIN_PLAN_SCORE=7.5
MIN_QUALITY_SCORE=7.5
DIALECTIC_METRICS_DB=.dialectic/metrics.db
SELF_IMPROVE_TOKEN_BUDGET=500000
```

## First workflow

### Generate a PRD

```bash
uv run dialectic-crew prd "User authentication with two-factor authentication"
```

With reference files:

```bash
uv run dialectic-crew prd "Dashboard redesign" --files wireframe.png spec.pdf
```

What happens:

1. the active vision is loaded as a CrewAI knowledge source
2. the Visionary proposes a thesis
3. the Critic challenges it
4. the Synthesizer improves it
5. the Validator scores it
6. the flow retries until approval or retry exhaustion

Artifacts land in `prd_output/`.

### Plan a user story

```bash
uv run dialectic-crew plan
```

This selects the latest PRD and the first user story by default.

### Execute the plan

```bash
uv run dialectic-crew execute
```

Each task runs through dialectic → verify → reimplement, and the orchestrator then performs post-verification against PRD acceptance criteria.

### Check status or re-verify

```bash
uv run dialectic-crew status
uv run dialectic-crew verify-story
```

For targeted checks:

```bash
uv run dialectic-crew verify T0
uv run dialectic-crew mark T0 completed
```

## Self-targeted runs

Use `--self` when you want the same flows to target the app's own roadmap in `internal/SELF_VISION.md`:

```bash
uv run dialectic-crew prd "Improve self-improve branch summaries" --self
uv run dialectic-crew plan --self
uv run dialectic-crew execute --self
```

## Automated self-improvement

```bash
uv run dialectic-crew self-improve --simulate
uv run dialectic-crew self-improve
```

Current runtime behavior:

- requires `git`
- refuses to start on a dirty worktree
- `--simulate` runs on a disposable `self-improve/simulate` branch with temporary runtime artifacts, then cleans it up
- real runs create isolated long-lived self-improve branches
- validates tests after execution
- checks metrics for regression
- creates a PR only when `gh` is installed

## Built-in skills MCP

The repository ships a local skills MCP server. Core agents can use it to discover and load `SKILL.md` guidance from project and user skill directories.

You normally do not need to configure anything extra for stdio mode, but you can tune it with:

```env
SKILLS_MCP_TRANSPORT=stdio
SKILLS_MCP_PORT=8001
```

## Troubleshooting

### Vision document not found

- normal runs require `knowledge/VISION.md`
- `--self` and `self-improve` require `internal/SELF_VISION.md`

### API key missing

Set at least one of:

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `GROQ_API_KEY`

### Docker missing

The app still runs, but Brave Search and Sequential Thinking MCP servers are skipped.

### `self-improve` refuses to start

Check for:

- uncommitted git changes
- missing `git`
- failing baseline tests

## Next reads

- [`architecture.md`](architecture.md)
- [`agents.md`](agents.md)
- [`cli.md`](cli.md)
- [`configuration.md`](configuration.md)