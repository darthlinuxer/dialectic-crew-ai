# CLI Reference

Dialectic Crew AI exposes the full lifecycle from one CLI:

- PRD generation
- user-story planning
- task execution
- status inspection and re-verification
- semi-autonomous self-improvement

## Entry points

```bash
uv run dialectic-crew <command> [arguments...]
python main.py <command> [arguments...]
```

## Command map

| Command | Purpose |
|---|---|
| `prd` | Generate a PRD through the dialectic cycle |
| `plan` | Build a `UserStoryExecutionPlan` for one user story |
| `execute` | Execute a plan or generate a static spec |
| `status` | Show story and task statuses |
| `verify-story` | Re-verify all completed tasks in a story |
| `verify` | Re-verify a single task |
| `mark` | Manually override a task status |
| `self-improve` | Run introspection → PRD → plan → execute → validate → PR |
| `help` | Show CLI help |

## `prd`

```bash
uv run dialectic-crew prd "your feature request" [--files file1 file2 ...] [--self]
```

- uses the main dialectic flow
- retries until the PRD reaches the approval threshold or the flow exhausts retries
- exports to `prd_output/`
- switches to `internal/SELF_VISION.md` when `--self` is provided

Examples:

```bash
uv run dialectic-crew prd "Login with two-factor authentication"
uv run dialectic-crew prd "Improve self-improvement safety gates" --self
```

## `plan`

```bash
uv run dialectic-crew plan [prd.json] [US-001|index] [--self]
```

- defaults to the latest PRD when no file is provided
- defaults to the first user story when no story reference is provided
- accepts flexible story references such as `US-001`, `US1`, or `1`
- exports plan JSON + Markdown into `prd_output/`

The planning threshold is controlled by `MIN_PLAN_SCORE` and defaults to `7.5`.

## `execute`

```bash
uv run dialectic-crew execute [plan.json|--latest] [--spec-only] [--self]
```

### Normal execution

Without `--spec-only`, the command:

1. loads a plan
2. executes each task in dependency order
3. runs dialectic → verify → reimplement per task
4. post-verifies completed tasks against PRD acceptance criteria
5. updates task and story status in the plan artifact
6. writes an execution report to `exec_output/`

### Spec-only execution

With `--spec-only`, the command skips LLM execution and emits a static Markdown spec through `src/execution/runner.py`.

## `status`

```bash
uv run dialectic-crew status [plan.json|--latest]
```

Reads the plan artifact and shows story + task state.

## `verify-story`

```bash
uv run dialectic-crew verify-story [plan.json] [--prd prd.json]
```

Re-runs verification for all completed tasks in the story and persists the resulting story status back into the plan.

Use this when manual edits happened after execution or when you want a clean second pass.

## `verify`

```bash
uv run dialectic-crew verify <task_id> [plan.json] [--prd prd.json]
```

Re-checks a single task and updates its stored status.

## `mark`

```bash
uv run dialectic-crew mark <task_id> <pending|in_progress|completed|failed> [plan.json]
```

Manual override for edge cases and human intervention.

## `self-improve`

```bash
uv run dialectic-crew self-improve [--dry-run] [--max N] [--stash-dirty]
```

### What it does

1. runs baseline tests
2. checks git availability and requires a clean worktree for real runs
3. introspects against `internal/SELF_VISION.md`
4. ranks opportunities through dialectic prioritization
5. creates an isolated git branch
6. generates a PRD, then a plan, then executes it
7. validates tests and metrics, then creates a PR if `gh` is installed

### Runtime requirements

- `git` is required
- the worktree must be clean
- interrupted runs on a `self-improve/*` branch are auto-cleaned before retrying
- on other branches, dirty worktrees abort with guidance unless `--stash-dirty` is used
- `gh` is optional
- metrics default to `.dialectic/metrics.db`
- CrewAI telemetry is disabled automatically during self-improve to prevent external exporter SSL noise from polluting logs
- with an API key configured, baseline validation runs the full pytest suite, including `@pytest.mark.llm` tests
- failed baseline or post-run validation prints the captured pytest stdout/stderr tail for faster diagnosis

### Self-improve controls

| Variable | Default | Purpose |
|---|---|---|
| `SELF_IMPROVE_TOKEN_BUDGET` | `500000` | cycle-wide token budget |
| `SELF_IMPROVE_MAX_ITERATIONS` | `25` | per-agent iteration cap |
| `SELF_IMPROVE_TEST_TIMEOUT` | `1800` | timeout for the full pytest validation subprocess |
| `MIN_METRIC_RETENTION` | `0.95` | post-run regression gate |
| `CREWAI_DISABLE_TELEMETRY` | `true` during self-improve | suppress CrewAI telemetry exporter requests during the cycle |

`--stash-dirty` stashes tracked and untracked changes from the current branch before self-improve continues. The stash is preserved in the stash stack so it can be reviewed or restored manually later.

## `--self` flag

Supported by:

- `prd`
- `plan`
- `execute`

It switches the active vision from `knowledge/VISION.md` to `internal/SELF_VISION.md`.

## Typical workflows

### Standard project workflow

```bash
uv run dialectic-crew prd "Feature X"
uv run dialectic-crew plan
uv run dialectic-crew execute
uv run dialectic-crew status
```

### Standard project workflow with re-verification

```bash
uv run dialectic-crew verify-story
uv run dialectic-crew verify T0
```

### Self-targeted workflow

```bash
uv run dialectic-crew prd "Add better roadmap observability" --self
uv run dialectic-crew plan --self
uv run dialectic-crew execute --self
```

### Fully automated self-improvement

```bash
uv run dialectic-crew self-improve --dry-run
uv run dialectic-crew self-improve
```