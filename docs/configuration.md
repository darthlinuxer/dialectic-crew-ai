# Configuration

Dialectic Crew AI is configured through environment variables, loaded from a `.env` file via `python-dotenv` and optionally validated by `pydantic-settings`.

---

## Configuration Flow

```mermaid
flowchart LR
    ENV[".env file"] --> DOTENV["python-dotenv<br/>load_dotenv()"]
    DOTENV --> PSETTINGS{"pydantic-settings<br/>available?"}
    PSETTINGS -->|Yes| BASESETS["BaseSettings<br/>validates + coerces"]
    PSETTINGS -->|No| OSENV["os.environ<br/>direct read"]
    BASESETS --> CONFIG["ExportConfig<br/>(dataclass)"]
    OSENV --> CONFIG

    style ENV fill:#4A90D9,stroke:#2C5F8A,color:#fff
    style CONFIG fill:#55EFC4,stroke:#00B894,color:#333
```

The configuration system is resilient:
- If `pydantic-settings` is not installed, falls back to `os.environ`
- Invalid values fall back to safe defaults with logged warnings
- Empty strings are treated as absent

---

## Environment Variables

### API Keys

At least one API key must be set. The system checks for any of these:

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `MINIMAX_API_KEY` | MiniMax API key |
| `GROQ_API_KEY` | Groq API key |

### LLM Model Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_MODEL_SIMPLE` | `gpt-4o-mini` | Model for the Validator agent (Simple tier) |
| `LLM_MODEL_COMPLEX` | `gpt-4o` | Model for Critic, Synthesizer, Implementer (Complex tier) |
| `LLM_MODEL_REASONING` | `o3-mini` | Model for the Visionary Architect (Reasoning tier) |
| `LLM_REQUEST_TIMEOUT` | `900` | Per-request LLM timeout in seconds |

### Export Configuration

| Variable | Default | Valid Values | Description |
|----------|---------|-------------|-------------|
| `PRD_OUTPUT_FORMAT` | `json` | `md`, `json`, `both` | Export format for PRDs |
| `PRD_OUTPUT_DIR` | `prd_output` | Any path | Output directory for PRDs and plans |

### Execution Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_RETRIES_PER_TASK` | `3` | Maximum dialectic retries per task during execution |
| `MIN_QUALITY_SCORE` | `7.5` | Minimum score for a task to pass during execution |
| `CREW_KICKOFF_TIMEOUT` | `300` | Total timeout for a crew kickoff in seconds |

---

## Configuration Hierarchy

```mermaid
graph TD
    CLI["CLI Arguments<br/>(plan path, task_id, etc.)"] --> RUNTIME["Runtime Values"]
    ENVVARS["Environment Variables<br/>(.env file)"] --> DEFAULTS["Module Defaults"]
    DEFAULTS --> RUNTIME
    HARDCODED["Hardcoded Defaults<br/>(in source code)"] --> DEFAULTS

    style CLI fill:#E17055,stroke:#D63031,color:#fff
    style ENVVARS fill:#FDCB6E,stroke:#E1A517,color:#333
    style HARDCODED fill:#DFE6E9,stroke:#B2BEC3,color:#333
    style RUNTIME fill:#55EFC4,stroke:#00B894,color:#333
```

CLI arguments override environment variables, which override hardcoded defaults.

---

## Export Config Details

The `ExportConfig` dataclass (`src/dialectic/config.py`) manages export settings:

```mermaid
classDiagram
    class ExportConfig {
        +Literal output_format [md|json|both]
        +Path output_dir
        +__post_init__() validates and normalizes
    }
```

### Validation Rules

| Scenario | Behavior |
|----------|----------|
| `PRD_OUTPUT_FORMAT` absent or empty | Falls back to `"json"`, logs warning |
| `PRD_OUTPUT_FORMAT` invalid value | Falls back to `"json"`, logs warning |
| `PRD_OUTPUT_FORMAT` mixed case (e.g., `Both`) | Normalized to lowercase (`both`) |
| `PRD_OUTPUT_DIR` absent | Falls back to `Path("prd_output")` |
| `pydantic-settings` not installed | Falls back to `os.environ`, logs warning |
| `pydantic-settings` fails at runtime | Falls back to `os.environ`, logs warning |

---

## Example `.env` File

```env
# Required: at least one API key
OPENAI_API_KEY=sk-your-key-here

# Optional: LLM model overrides
LLM_MODEL_SIMPLE=gpt-4o-mini
LLM_MODEL_COMPLEX=gpt-4o
LLM_MODEL_REASONING=o3-mini
LLM_REQUEST_TIMEOUT=900

# Optional: export settings
PRD_OUTPUT_FORMAT=both
PRD_OUTPUT_DIR=prd_output

# Optional: execution settings
MAX_RETRIES_PER_TASK=3
MIN_QUALITY_SCORE=7.5
CREW_KICKOFF_TIMEOUT=300
```

---

## Where Configuration Is Used

```mermaid
flowchart TD
    subgraph ENV["Environment Variables"]
        API["API Keys"]
        LLM["LLM Models"]
        EXPORT["Export Settings"]
        EXEC["Execution Settings"]
    end

    API --> AGENTS["src/dialectic/agents.py<br/>Agent LLM configuration"]
    LLM --> AGENTS
    EXPORT --> CONFIG_MOD["src/dialectic/config.py<br/>ExportConfig loader"]
    CONFIG_MOD --> EXPORTER["src/dialectic/export.py<br/>PRDExporter"]
    EXEC --> TASK_FLOW["src/execution/task_flow.py<br/>TaskExecutionFlow"]
    EXEC --> DIAL_EXEC["src/execution/dialectic_execution.py<br/>Orchestrator"]
    EXEC --> PLAN_FLOW["src/planning/flow.py<br/>Planning timeout"]

    style ENV fill:#4A90D9,stroke:#2C5F8A,color:#fff
```
