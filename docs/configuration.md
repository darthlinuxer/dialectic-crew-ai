# Configuration

Dialectic Crew AI is configured primarily through environment variables loaded from `.env`.

## Loading behavior

- `python-dotenv` loads `.env`
- `pydantic-settings` is used when available for export config validation
- empty strings are treated as missing values
- most optional subsystems degrade gracefully when unset

## API keys

At least one provider key must be configured for LLM-backed commands:

| Variable |
|---|
| `OPENAI_API_KEY` |
| `ANTHROPIC_API_KEY` |
| `GROQ_API_KEY` |

## Model selection

| Variable | Default | Used by |
|---|---|---|
| `LLM_MODEL_SIMPLE` | `gpt-4o-mini` | Validator and lightweight checks |
| `LLM_MODEL_COMPLEX` | `gpt-4o` | Critic, Synthesizer, Implementer |
| `LLM_MODEL_REASONING` | `o3-mini` | Visionary |
| `LLM_MODEL_PLANNING` | same as reasoning | CrewAI planning stage |
| `LLM_REQUEST_TIMEOUT` | `900` | Per-request LLM timeout |

## Output and project paths

| Variable | Default | Purpose |
|---|---|---|
| `PRD_OUTPUT_FORMAT` | `json` | PRD/plan export format: `json`, `md`, `both` |
| `PRD_OUTPUT_DIR` | `prd_output` | Export directory for PRDs and plans |
| `DIALECTIC_PROJECT_ROOT` | auto-detected | Override project-root discovery |
| `DIALECTIC_METRICS_DB` | `.dialectic/metrics.db` | Override runtime metrics database path |

## Planning and execution thresholds

| Variable | Default | Purpose |
|---|---|---|
| `MIN_PLAN_SCORE` | `7.5` | Minimum plan approval score |
| `MAX_RETRIES_PER_TASK` | `3` | Max execution retries per task |
| `MIN_QUALITY_SCORE` | `7.5` | Minimum dialectic task score |
| `CREW_KICKOFF_TIMEOUT` | `300` | Crew kickoff timeout in seconds |

## Hook, budget, and validation controls

| Variable | Default | Purpose |
|---|---|---|
| `TOKEN_BUDGET` | `0` | Generic HookScope token budget (`0` = unlimited) |
| `MAX_LLM_ITERATIONS` | `25` | Generic HookScope LLM iteration cap |
| `SELF_IMPROVE_TOKEN_BUDGET` | `500000` | Self-improve cycle token budget |
| `SELF_IMPROVE_MAX_ITERATIONS` | `25` | Self-improve per-agent iteration cap |
| `SELF_IMPROVE_TEST_TIMEOUT` | `1800` | Timeout for full-suite pytest validation during self-improve |
| `MIN_METRIC_RETENTION` | `0.95` | Minimum post-run metric retention ratio |
| `COST_PER_INPUT_TOKEN` | `0.0000025` | Estimated input-token cost used in tracking |
| `COST_PER_OUTPUT_TOKEN` | `0.00001` | Estimated output-token cost used in tracking |

## MCP configuration

### External MCP servers

| Variable | Needed for | Notes |
|---|---|---|
| `CONTEXT7_API_KEY` | Context7 MCP | Enables live library/framework docs via HTTP MCP |
| `BRAVE_API_KEY` | Brave Search MCP | Requires Docker in addition to the key |

Sequential Thinking requires Docker but no API key.

### Skills MCP server

The local skills server is implemented in `src/mcp/skills_mcp.py` and is launched through Python.

| Variable | Default | Purpose |
|---|---|---|
| `SKILLS_MCP_TRANSPORT` | `stdio` | `stdio` or `streamable_http` |
| `SKILLS_MCP_PORT` | `8001` | Port for HTTP transport |

Skills are indexed from:

- `src/mcp/skills`
- `~/.agents/skills`
- `~/.cursor/skills-cursor`

## Vision contexts

The active vision is selected by runtime context, not by an environment variable:

| Context | File | Activated by |
|---|---|---|
| Project | `knowledge/VISION.md` | normal commands |
| Self | `internal/SELF_VISION.md` | `--self` or `self-improve` |

## Example `.env`

```env
OPENAI_API_KEY=sk-your-key-here

LLM_MODEL_SIMPLE=gpt-4o-mini
LLM_MODEL_COMPLEX=gpt-4o
LLM_MODEL_REASONING=o3-mini
LLM_MODEL_PLANNING=o3-mini
LLM_REQUEST_TIMEOUT=900

PRD_OUTPUT_FORMAT=both
PRD_OUTPUT_DIR=prd_output

MIN_PLAN_SCORE=7.5
MAX_RETRIES_PER_TASK=3
MIN_QUALITY_SCORE=7.5
CREW_KICKOFF_TIMEOUT=300

DIALECTIC_METRICS_DB=.dialectic/metrics.db
SELF_IMPROVE_TOKEN_BUDGET=500000
SELF_IMPROVE_MAX_ITERATIONS=25
MIN_METRIC_RETENTION=0.95

CONTEXT7_API_KEY=ctx7sk-...
BRAVE_API_KEY=...
SKILLS_MCP_TRANSPORT=stdio
```

## Notes

- If Docker is missing, Brave Search and Sequential Thinking MCP servers are skipped rather than crashing startup.
- If `gh` is missing, `self-improve` can still run; only PR creation is skipped.
- If `uv` is missing, `self-improve` falls back to `python -m pytest` for validation.
- When an API key is configured, `self-improve` validates against the full pytest suite, including tests marked `llm`.
- `self-improve` runs pytest with `--reruns 1` to tolerate a single transient LLM-test failure during baseline and post-run validation.
- If baseline or post-run validation fails, `self-improve` prints the captured pytest stdout/stderr tail before aborting.