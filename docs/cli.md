# CLI Reference

Dialectic Crew AI provides a command-line interface with six commands covering the full PRD lifecycle.

**Entry points:**

```bash
uv run dialectic-crew <command> [arguments...]   # recommended (uses uv)
python main.py <command> [arguments...]           # alternative (direct Python)
```

> Throughout this document, examples show both forms. They are fully interchangeable — use whichever fits your setup.

---

## Command Overview

```mermaid
flowchart LR
    subgraph Commands
        PRD["prd"]
        PLAN["plan"]
        EXEC["execute"]
        STATUS["status"]
        MARK["mark"]
        VERIFY["verify"]
    end

    PRD -->|"Generates"| PRD_OUT["prd_output/<br/>PRD_*.json + .md"]
    PLAN -->|"Generates"| PLAN_OUT["prd_output/<br/>exec_*.json + .md"]
    EXEC -->|"Generates"| EXEC_OUT["exec_output/<br/>&lt;run_id&gt;/report.json"]
    STATUS -->|"Reads"| PLAN_OUT
    MARK -->|"Updates"| PLAN_OUT
    VERIFY -->|"Reads + Updates"| PLAN_OUT

    style PRD fill:#6C5CE7,stroke:#4834D4,color:#fff
    style PLAN fill:#00B894,stroke:#00896B,color:#fff
    style EXEC fill:#E17055,stroke:#D63031,color:#fff
    style STATUS fill:#FDCB6E,stroke:#E1A517,color:#333
    style MARK fill:#FDCB6E,stroke:#E1A517,color:#333
    style VERIFY fill:#FDCB6E,stroke:#E1A517,color:#333
```

---

## Commands

### `prd` — Generate a PRD

Generates a Product Requirement Document using the full dialectic method with automatic retries until the quality score reaches 9.0.

```bash
uv run dialectic-crew prd "your feature request"
# or: python main.py prd "your feature request"
```

**Requirements:**
- `VISION.md` in the current directory
- API key configured in `.env`

**Output:** `prd_output/PRD_YYYYMMDD_HHMM.json` and `.md`

**Example:**

```bash
uv run dialectic-crew prd "Login with two-factor authentication"
# or: python main.py prd "Login with two-factor authentication"
```

**Compatibility shortcut:** Passing a string without a command is equivalent to `prd`:

```bash
python main.py "Login with 2FA"
# Same as: python main.py prd "Login with 2FA"
```

---

### `plan` — Plan User Story Execution

Plans the execution of a specific user story from a PRD. Uses the dialectic method to produce a `UserStoryExecutionPlan` with implementation tasks.

```bash
uv run dialectic-crew plan [prd.json] [US-001|index]
# or: python main.py plan [prd.json] [US-001|index]
```

**Arguments:**

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `prd.json` | No | Latest PRD in `prd_output/` | Path to the PRD JSON file |
| `US-001` | No | First user story | User story reference (ID or index) |

**Output:** `prd_output/exec_<US>_<timestamp>.json` and `.md`

**Examples:**

```bash
# Plan the first user story from the latest PRD
uv run dialectic-crew plan

# Plan a specific user story from a specific PRD
uv run dialectic-crew plan prd_output/PRD_20260308_1640.json US-002

# Use numeric index (0-based)
uv run dialectic-crew plan prd_output/PRD_20260308_1640.json 1
```

**User story references are flexible:**
- `US-001`, `US001`, `US1`, `1` all resolve to the same story

---

### `execute` — Execute the Plan

Executes the plan with CrewAI, running a full dialectic cycle per task. Each task goes through: Dialectic → Verify → Reimplement (if needed).

```bash
uv run dialectic-crew execute [plan.json|--latest] [--spec-only]
# or: python main.py execute [plan.json|--latest] [--spec-only]
```

**Arguments:**

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `plan.json` | No | `--latest` | Path to the plan JSON or `--latest` |
| `--spec-only` | No | `false` | Generate only a Markdown spec (no LLM execution) |

**Output:** `exec_output/<run_id>/report.json` and `spec_*.md`

**Examples:**

```bash
# Execute the latest plan with full dialectic
uv run dialectic-crew execute

# Execute a specific plan
uv run dialectic-crew execute prd_output/exec_US-001_20260308_1200.json

# Generate only a static spec (no LLM calls)
uv run dialectic-crew execute --spec-only
```

---

### `status` — View Task Status

Displays the completion status of all tasks in a plan.

```bash
uv run dialectic-crew status [plan.json|--latest]
# or: python main.py status [plan.json|--latest]
```

**Output example:**

```
=================================================================
  US-001 — User Authentication
  Score: 9.2/10.0  |  Plan: prd_output/exec_US-001_20260308_1750.json
=================================================================
  [x] T-001 — Set up auth module  (2026-03-08T18:30:00)
  [~] T-002 — Implement login endpoint
  [ ] T-003 — Add 2FA support  (deps: T-002)
  [!] T-004 — Write integration tests  -- Score: 5.0/10

  Progress: 1/4 completed, 1 failed, 1 in progress
=================================================================
```

**Status icons:**

| Icon | Status |
|------|--------|
| `[ ]` | Pending |
| `[~]` | In progress |
| `[x]` | Completed |
| `[!]` | Failed |

---

### `mark` — Manually Set Task Status

Manually updates the status of a task in the plan.

```bash
uv run dialectic-crew mark <task_id> <status> [plan.json]
# or: python main.py mark <task_id> <status> [plan.json]
```

**Arguments:**

| Argument | Required | Description |
|----------|----------|-------------|
| `task_id` | Yes | Task ID (e.g., `T-001`) |
| `status` | Yes | `pending`, `in_progress`, `completed`, or `failed` |
| `plan.json` | No | Path to plan (default: latest) |

**Examples:**

```bash
uv run dialectic-crew mark T-001 completed
uv run dialectic-crew mark T-003 failed prd_output/exec_US-001_20260308_1750.json
```

---

### `verify` — LLM-Based Task Verification

Uses an LLM agent to verify whether a task was correctly implemented by reading the actual project files.

```bash
uv run dialectic-crew verify <task_id> [plan.json] [--prd prd.json]
# or: python main.py verify <task_id> [plan.json] [--prd prd.json]
```

**Arguments:**

| Argument | Required | Description |
|----------|----------|-------------|
| `task_id` | Yes | Task ID to verify |
| `plan.json` | No | Path to plan (default: latest) |
| `--prd prd.json` | No | PRD to load acceptance criteria from |

**What it does:**
1. Loads the task description and acceptance criteria (from the PRD if provided)
2. Creates a Validator agent with file-reading tools
3. Agent reads project files to verify artifacts exist and are correct
4. Updates task status to `completed` or `failed` based on results

**Examples:**

```bash
# Verify using latest plan
uv run dialectic-crew verify T-001

# Verify with PRD acceptance criteria
uv run dialectic-crew verify T-002 --prd prd_output/PRD_20260308_1640.json
```

---

### `help` — Show Help

```bash
uv run dialectic-crew help
# or: python main.py help
# or: python main.py -h / --help
```

---

## Typical Workflow

```mermaid
flowchart TD
    A["1. Generate PRD<br/>dialectic-crew prd 'Feature X'"] --> B["2. Review PRD<br/>(prd_output/PRD_*.md)"]
    B --> C["3. Plan user story<br/>dialectic-crew plan"]
    C --> D["4. Review plan<br/>(prd_output/exec_*.md)"]
    D --> E["5. Execute plan<br/>dialectic-crew execute"]
    E --> F["6. Check status<br/>dialectic-crew status"]
    F --> G{All tasks done?}
    G -->|No| H["7. Verify/fix tasks<br/>dialectic-crew verify T-001"]
    H --> F
    G -->|Yes| I["Done!<br/>(exec_output/report.json)"]

    style A fill:#6C5CE7,stroke:#4834D4,color:#fff
    style C fill:#00B894,stroke:#00896B,color:#fff
    style E fill:#E17055,stroke:#D63031,color:#fff
    style I fill:#55EFC4,stroke:#00B894,color:#333
```
