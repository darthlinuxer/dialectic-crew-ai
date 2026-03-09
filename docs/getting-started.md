# Getting Started

This guide covers installation, prerequisites, and running your first dialectic PRD generation.

---

## Prerequisites

- **Python 3.10–3.13**
- **An LLM API key** (OpenAI, Anthropic, Groq, or MiniMax)
- **`VISION.md`** in your project root (already included in the repository)

---

## Installation

### Option 1: Using uv (recommended)

```bash
git clone <repo-url>
cd dialectic-crew-ai
uv sync
source .venv/bin/activate
```

### Option 2: Using pip

```bash
git clone <repo-url>
cd dialectic-crew-ai
pip install -e .
```

### Option 3: Using pip with virtual environment

```bash
git clone <repo-url>
cd dialectic-crew-ai
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

---

## Configuration

1. Copy the example environment file:

```bash
cp .env.example .env
```

2. Edit `.env` and add your API key:

```env
OPENAI_API_KEY=sk-your-key-here
```

3. (Optional) Customize other settings:

```env
# Use different models
LLM_MODEL_SIMPLE=gpt-4o-mini
LLM_MODEL_COMPLEX=gpt-4o
LLM_MODEL_REASONING=o3-mini

# Export format: json, md, or both
PRD_OUTPUT_FORMAT=both
```

See [Configuration](configuration.md) for all available options.

---

## Your First PRD

### Step 1: Generate a PRD

```bash
uv run dialectic-crew prd "User authentication with two-factor authentication"
# or: python main.py prd "User authentication with two-factor authentication"
```

The system will:
1. Read `VISION.md` for context
2. Run the Visionary agent to propose an initial solution (thesis)
3. Run the Socratic Critic to challenge it (antithesis)
4. Run the Synthesizer to merge them (synthesis)
5. Run the Validator to score it (validation)
6. Repeat until the quality score reaches 9.0 (or max retries)

**Output:** `prd_output/PRD_YYYYMMDD_HHMM.json` and `.md`

### Step 2: Review the PRD

Open the generated Markdown file to review the PRD:

```bash
cat prd_output/PRD_*.md
```

The PRD includes:
- Feature name and objective
- Macro impact assessment
- User stories with acceptance criteria
- Anti-drift questions ensuring vision alignment
- Quality score and validation notes

### Step 3: Plan a User Story

Select a user story from the PRD and generate an implementation plan:

```bash
uv run dialectic-crew plan
# or: python main.py plan
```

This will:
1. Load the latest PRD
2. Select the first user story
3. Run a dialectic cycle to produce an implementation plan

**Output:** `prd_output/exec_US-001_YYYYMMDD_HHMM.json` and `.md`

### Step 4: Execute the Plan

Run the plan with full dialectic execution per task:

```bash
uv run dialectic-crew execute
# or: python main.py execute
```

Each task goes through:
1. **Dialectic cycle**: Implement → Critique → Synthesize → Validate (with retries)
2. **Verification**: Independent agent reads files to verify artifacts
3. **Reimplementation**: If verification fails, a fresh agent fixes the gaps

**Output:** `exec_output/<run_id>/report.json`

### Step 5: Check Status

```bash
uv run dialectic-crew status
# or: python main.py status
```

---

## End-to-End Workflow

```mermaid
flowchart TD
    START(["Start"]) --> PRD["dialectic-crew prd<br/>'Feature request'"]
    PRD --> REVIEW1["Review PRD<br/>(prd_output/*.md)"]
    REVIEW1 --> PLAN["dialectic-crew plan"]
    PLAN --> REVIEW2["Review plan<br/>(prd_output/exec_*.md)"]
    REVIEW2 --> DECIDE{Execute with LLM<br/>or spec only?}
    DECIDE -->|"Full execution"| EXEC["dialectic-crew execute"]
    DECIDE -->|"Spec only"| SPEC["dialectic-crew execute<br/>--spec-only"]
    EXEC --> STATUS["dialectic-crew status"]
    STATUS --> CHECK{All tasks<br/>completed?}
    CHECK -->|"Yes"| DONE(["Done!"])
    CHECK -->|"No"| FIX["dialectic-crew verify T-XXX<br/>dialectic-crew mark T-XXX completed"]
    FIX --> STATUS
    SPEC --> DONE2(["Manual implementation<br/>using spec"])

    style START fill:#4A90D9,stroke:#2C5F8A,color:#fff
    style PRD fill:#6C5CE7,stroke:#4834D4,color:#fff
    style PLAN fill:#00B894,stroke:#00896B,color:#fff
    style EXEC fill:#E17055,stroke:#D63031,color:#fff
    style DONE fill:#55EFC4,stroke:#00B894,color:#333
    style DONE2 fill:#55EFC4,stroke:#00B894,color:#333
```

---

## Convenience Scripts

For quick testing, the repository includes convenience scripts:

| Script | Equivalent | Description |
|--------|-----------|-------------|
| `python run_dialectic.py` | `uv run dialectic-crew prd "..."` | Full dialectic with hardcoded feature |
| `python run_simple.py` | `uv run dialectic-crew prd "..."` (single pass) | Single pass, no retry |
| `python run_user_story_dialectic.py` | `uv run dialectic-crew plan` | Plans a user story |

---

## Output Files

After running the full workflow, you'll have:

```
prd_output/
├── PRD_20260308_1640.json          # Structured PRD (machine-readable)
├── PRD_20260308_1640.md            # Narrative PRD (human-readable)
├── exec_US-001_20260308_1750.json  # Implementation plan
└── exec_US-001_20260308_1750.md    # Plan in Markdown

exec_output/
└── 20260308_1800/
    ├── report.json                 # Execution report with per-task results
    └── spec_US-001_20260308_1800.md  # Implementation spec
```

---

## Troubleshooting

### "VISION.md not found"

Make sure you're running from the project root directory where `VISION.md` exists.

### "Configure your API key first!"

Add at least one API key to your `.env` file. See [Configuration](configuration.md).

### Timeout errors

Increase the timeout values in `.env`:

```env
LLM_REQUEST_TIMEOUT=1800
CREW_KICKOFF_TIMEOUT=600
```

### Low quality scores

The system retries up to `MAX_RETRIES` (default: 5) times. If scores consistently stay below 9.0:
- Review `VISION.md` — agents use it as their primary reference
- Try a stronger reasoning model: `LLM_MODEL_REASONING=o3`
- Check that your feature request is clear and specific

---

## Next Steps

- Read the [Architecture](architecture.md) to understand the system design
- Explore the [Flow documentation](flows.md) for detailed pipeline diagrams
- Review [Agent definitions](agents.md) to understand each agent's role
- Check the [CLI Reference](cli.md) for all available commands
