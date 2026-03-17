# SELF_VISION.md — System Self-Evolution Vision

## About the Project

**Dialectic Crew AI** is itself the product: a CLI-first application that uses the **dialectic method** (thesis → antithesis → synthesis → validation) to generate high-quality PRDs (Product Requirement Documents), turn approved user stories into execution plans, and execute those plans through guarded verification loops. The system self-orients by this vision to prevent drift and to evolve toward its vocation.

**Intent:** Be the best dialectic-method **platform** for the full lifecycle already present in the codebase: generating PRDs in **Markdown** and **JSON**, producing validated user-story execution plans, executing those plans with dialectic + verification + reimplementation safeguards, maintaining explicit alignment to the correct macro vision (`internal/SELF_VISION.md` for self-evolution and `knowledge/VISION.md` for project work), and using its own dialectic process to evolve itself. The platform leverages CrewAI's native capabilities where they fit today and continues moving toward deeper adoption of Memory, Knowledge, Event Listeners, Human Feedback, Training, and Reasoning while minimizing unnecessary custom infrastructure.

**Vocation:**
- **Core:** Generate structured PRDs (objective, macro_impact, user_stories, anti_drift_questions) in **two formats** — `.md` (readable, versionable, collaborative) and `.json` (machine-friendly, integrations, APIs) — then derive executable user-story plans and tracked execution artifacts from those approved PRDs.
- **Method:** Ensure proposals and plans go through contradiction (antithesis) and synthesis before approval, and ensure execution runs through dialectic implementation, verification, and reimplementation when needed.
- **Evolution:** Extend the same dialectic method to additional artifacts and lifecycle phases without weakening the already-shipped PRD → plan → execute workflow.

---

## Business Objectives

1. **PRDs in Markdown and JSON** — Every approved PRD must be persisted in `prd_output/` as both `.md` (narrative document, human-ready) and `.json` (validated schema, tool-ready).
2. **Plans from approved PRDs** — Approved PRDs must support user-story planning that produces structured `UserStoryExecutionPlan` artifacts in scoped `prd_output/` directories, with both machine-readable and human-readable outputs.
3. **Execution from approved plans** — Approved execution plans must be runnable through the execution pipeline, producing tracked outputs in scoped `exec_output/` directories, including verification outcomes and resumable checkpoints.
4. **Quality through dialectics** — Maintain the Thesis → Antithesis → Synthesis → Validation loop with retry until score >= 9.0 for PRDs, while preserving the planning and execution quality gates already present in the system.
5. **Anti-drift** — For self-evolution flows (e.g. `self-improve`), all agents MUST ingest `internal/SELF_VISION.md` via `VisionContext.SELF`. For external projects, all agents MUST ingest the active project vision via `VisionContext.PROJECT`, resolving to `knowledge/target/<target-slug>/VISION.md` when a target checkout is selected and falling back to `knowledge/VISION.md` otherwise. Anti-drift questions and validation ensure continuous alignment with the correct macro vision.
6. **Self-improvement** — This file (`internal/SELF_VISION.md`) defines the macro vision for Dialectic Crew AI itself. Self-evolution behavior or scope changes must be consistent with this document, and self-improve cycles MUST never substitute a project vision (`knowledge/VISION.md`) in place of this self vision.
7. **API-first architecture** — Expose all capabilities (PRD creation, planning, execution, verification) through a REST API backed by CrewAI Event Listeners for real-time progress streaming, enabling programmatic integration and a web frontend.
8. **Web experience** — Provide a web UI for PRD creation, browsing, review workflows (powered by CrewAI's `@human_feedback` decorator), user story boards, and live dialectic visualization — making the tool accessible to non-technical stakeholders.
9. **Self-evolution** — The system uses its own dialectic pipeline to generate PRDs for its own features. `internal/SELF_VISION.md` defines the target; the app generates the PRDs to get there, plans the user stories, and produces execution artifacts exclusively against this repository when running in self-improve mode. CrewAI Training (`crew.train()`) captures human feedback to permanently improve agent behavior. Human review remains the final gate.
10. **Framework-first** — Before building custom solutions, leverage CrewAI's native features: Memory for cross-session learning, Knowledge for semantic document access, Event Listeners for observability, Human Feedback for review workflows, Training for self-improvement, Reasoning for deeper agent thinking, and Conditional Tasks for efficient flow control.
11. **Structured logging and traceability** — Provide first-class structured logging that emits JSON-structured, rotating log files with correlation IDs for each CrewAI flow, agent, and tool call, while also emitting concise human-readable console logs by default when verbose mode is not enabled. Logs must be rich enough for both humans and LLM agents to reconstruct an end-to-end flow “stacktrace” during debugging.

---

## System Scope

### Main Modules / Components

| Component       | Description |
|-----------------|-------------|
| **dialectic**   | Dialectic core: agents (Visionary, Socratic Critic, Synthesizer, Validator), tools, state, DialecticFlow (PRD with retry), export (PRD and plan to Markdown). |
| **planning**    | Execution planning: per user story, produces UserStoryExecutionPlan (thesis → antithesis → synthesis → validation). |
| **execution**   | Approved plan execution: consumes UserStoryExecutionPlan and generates artifacts (spec/draft in Markdown; extensible to code or integrations). Three-phase pipeline: Dialectic → Verify (A+B) → Reimplement (C) via @router. |
| **schemas**     | Source of truth for PRDs and plans: PRDSchema, UserStory, MacroImpact, AntiDriftQuestion; UserStoryExecutionPlan, ImplementationTask, VerificationResult. |
| **main / CLI**  | Commands: `prd "feature"` (PRD with dialectics), `plan [prd] [US]` (plan per user story), `execute [plan]` (execution artifact), `status`, `mark`, `verify`,  `self-improve`. In addition, the CLI MUST support: (a) setting an **active project directory** that points to a local checkout of a remote repo, and (b) project-scoped commands that operate only on that active project. |
| **api** (planned) | FastAPI REST + WebSocket layer. CrewAI Event Listeners feed real-time progress to connected clients. Background workers for long-running LLM flows. JWT/OAuth2 auth with multi-tenant isolation. |
| **db** (planned) | PostgreSQL persistence for PRDs, plans, executions, reviews, and LLM usage. Version history with diffs. Replaces flat-file storage as the primary store. |
| **frontend** (planned) | Next.js web application: PRD creator with live dialectic visualization, `@human_feedback`-powered review workflow, story board, analytics dashboard. |
| **observability** (planned) | CrewAI Event Listeners + LLM Hooks for cost tracking, token usage, latency metrics, and integration with the structured logging system. Pluggable into Langfuse, OpenLIT, or Datadog via OpenTelemetry. |
| **project vision tools** (planned) | When an active project directory is set, commands that can scan that project’s files, invoke the brainstorming skill at `src/mcp/skills/brainstorming/`, and generate or update a `VISION.md` representation for that project in the central `knowledge/` layer, which is then used as `VisionContext.PROJECT` for that repo. |

### Integrations (current / desired)

- **Input:** CLI arguments, self vision content from `internal/SELF_VISION.md` (via `VisionContext.SELF`), project vision content from `knowledge/VISION.md` for the currently active project (via `VisionContext.PROJECT`), project source files from the active project directory, and environment variables (API keys).
- **Output:** Files in scoped `prd_output/` directories (`default/`, `self/`, `targets/<target-slug>/`) for PRDs and plans in **JSON + Markdown**; scoped execution tracking in `exec_output/`; centrally managed `knowledge/VISION.md` files that capture the macro vision of each active project.
- **LLM:** Support for multiple providers (OpenAI, Anthropic, Groq, etc.) configurable in `dialectic/agents.py`.

---

## Tech Stack

- **Runtime:** Python 3.10–3.13
- **Agent Framework:** CrewAI (Flow API, Crew, Tasks, Agents)
- **Validation:** Pydantic (PRDSchema, UserStory, etc.)
- **Config:** pyproject.toml, uv (recommended), .env for API keys

### Planned Additions

- **API:** FastAPI, WebSocket, ARQ/Celery + Redis
- **Database:** PostgreSQL, SQLAlchemy, Alembic
- **Frontend:** Next.js 15, TypeScript, Tailwind CSS, shadcn/ui
- **Observability:** CrewAI Event Listeners, LLM Hooks, OpenTelemetry, Langfuse (or OpenLIT)

### CrewAI-First Implementation Guidance

This project should continue to prefer **CrewAI-native capabilities first** before adding custom orchestration, memory, routing, observability, or review infrastructure. The purpose of this section is to orient humans and LLMs toward the framework's documented capabilities; implementation status and phased adoption still belong only in `internal/ROADMAP.md`.

**Decision rule**
1. **Check CrewAI docs first** — confirm whether the requirement can be solved with documented CrewAI capabilities.
2. **Reuse existing project patterns second** — prefer the repository's current Flow, Crew, Knowledge, Memory, logging, and target-scoping patterns before inventing new abstractions.
3. **Add custom infrastructure only as a last resort** — introduce new code only when CrewAI and the project's established patterns clearly do not satisfy the requirement.

Agents and contributors working on this repository should consult the CrewAI documentation before proposing new infrastructure or abstractions. Start with the documentation index at `https://docs.crewai.com/llms.txt` to discover the latest available pages.

**Core concepts**
- [Agents](https://docs.crewai.com/en/concepts/agents) — Roles, goals, backstories, tools, and model assignment
- [Tasks](https://docs.crewai.com/en/concepts/tasks) — Structured outputs, guardrails, and task contracts
- [Crews](https://docs.crewai.com/en/concepts/crews) — Crew assembly and execution patterns
- [Flows](https://docs.crewai.com/en/concepts/flows) — `@start`, `@listen`, `@router`, persistence, and orchestration
- [Processes](https://docs.crewai.com/en/concepts/processes) — Sequential vs. hierarchical execution
- [LLMs](https://docs.crewai.com/en/concepts/llms) — Provider/model configuration and tiering
- [Tools](https://docs.crewai.com/en/concepts/tools) — Built-in and custom tools
- [Files](https://docs.crewai.com/en/concepts/files) — File and multimodal document handling

**Framework capabilities to prefer before custom code**
- [Memory](https://docs.crewai.com/en/concepts/memory) — Cross-session learning and recall
- [Knowledge](https://docs.crewai.com/en/concepts/knowledge) — Semantic document access and RAG workflows
- [Reasoning](https://docs.crewai.com/en/concepts/reasoning) — Pre-task reflection and planning
- [Planning](https://docs.crewai.com/en/concepts/planning) — Built-in macro planning support
- [Training](https://docs.crewai.com/en/concepts/training) — Human-feedback-driven improvement
- [Testing](https://docs.crewai.com/en/concepts/testing) — Framework-native quality benchmarking
- [Event Listeners](https://docs.crewai.com/en/concepts/event-listener) — Runtime events and integrations
- [Collaboration](https://docs.crewai.com/en/concepts/collaboration) — Agent delegation and teamwork patterns

**Advanced patterns**
- [Human Feedback in Flows](https://docs.crewai.com/en/learn/human-feedback-in-flows) — Native review/approval routing
- [Human-in-the-Loop](https://docs.crewai.com/en/learn/human-in-the-loop) — Async review workflows
- [LLM Hooks](https://docs.crewai.com/en/learn/llm-hooks) — Cost tracking, approval gates, and guardrails
- [Execution Hooks](https://docs.crewai.com/en/learn/execution-hooks) — Tool-call monitoring and safety hooks
- [Conditional Tasks](https://docs.crewai.com/en/learn/conditional-tasks) — Skip unnecessary work dynamically
- [Kickoff For Each](https://docs.crewai.com/en/learn/kickoff-for-each) — Parallel per-item execution
- [Kickoff Async](https://docs.crewai.com/en/learn/kickoff-async) — Non-blocking execution
- [Custom Tools](https://docs.crewai.com/en/learn/create-custom-tools) — Project-specific tool creation
- [Customizing Prompts](https://docs.crewai.com/en/guides/advanced/customizing-prompts) — Model-specific prompt tuning

**Production and observability**
- [Production Architecture](https://docs.crewai.com/en/concepts/production-architecture) — Deployment and persistence patterns
- [Observability Overview](https://docs.crewai.com/en/observability/overview) — Monitoring and evaluation
- [Langfuse Integration](https://docs.crewai.com/en/observability/langfuse) — Trace integration via OpenTelemetry
- [OpenLIT Integration](https://docs.crewai.com/en/observability/openlit) — Lightweight runtime monitoring
- [CrewAI Tracing](https://docs.crewai.com/en/observability/tracing) — Built-in tracing for crews and flows
- [Hallucination Guardrail](https://docs.crewai.com/en/enterprise/features/hallucination-guardrail) — Context-faithfulness safeguards
- [Webhook Streaming](https://docs.crewai.com/en/enterprise/features/webhook-streaming) — Real-time event delivery

**MCP and integrations**
- [MCP Overview](https://docs.crewai.com/en/mcp/overview) — MCP servers as agent tools
- [MCP DSL Integration](https://docs.crewai.com/en/mcp/dsl-integration) — Simpler MCP configuration patterns
- [Multiple MCP Servers](https://docs.crewai.com/en/mcp/multiple-servers) — Multi-server adapter composition
- [GitHub Integration](https://docs.crewai.com/en/enterprise/integrations/github) — Repository workflows
- [Jira Integration](https://docs.crewai.com/en/enterprise/integrations/jira) — Project tracking
- [Linear Integration](https://docs.crewai.com/en/enterprise/integrations/linear) — Issue and planning workflows
- [Slack Integration](https://docs.crewai.com/en/enterprise/integrations/slack) — Notifications and collaboration
- [Notion Integration](https://docs.crewai.com/en/enterprise/integrations/notion) — Knowledge and documentation workflows

---

## Non-Functional Requirements

- **Reproducibility:** Dependency lock (uv.lock) and stable PRD schema.
- **Clarity:** PRD in Markdown for human reading; JSON for pipelines and automation.
- **Quality:** No PRD approved with score < 9.0 unless the flow has retried up to the configured limit.
- **Maintainability:** Readable code, well-separated responsibilities (flow, agents, schemas).
- **Structured logging:** All core flows (PRD, planning, execution, self-improve, project analysis) emit JSON-structured logs to rotating log files with at least: timestamp, log level, correlation IDs (flow, agent, tool), component name, and message. Human-readable console logs remain concise and are always derivable from the structured logs.
- **Traceable executions:** Given a correlation ID, both humans and LLM agents must be able to reconstruct a full “stacktrace” of what occurred (flows, agents, tools, and key decisions) using structured logs, metrics, and CrewAI Event Listener events.

---

## Design Principles

1. **Dialectics as the core** — Thesis, antithesis, and synthesis are not optional; the Validator is the sole approval gate.
2. **VISION contexts as anchors** — Every proposal is confronted with the correct macro vision: `internal/SELF_VISION.md` via `VisionContext.SELF` for self-evolution flows, and `knowledge/VISION.md` via `VisionContext.PROJECT` for the currently active external project. Anti-drift is mandatory for both.
3. **Dual output (MD + JSON)** — Serve both human readers and tools/integrations.
4. **Extensible** — Architecture must allow new flows (e.g., dialectics for user story execution) without breaking the core.
5. **Framework-first** — Leverage CrewAI's native features (Memory, Knowledge, Event Listeners, Human Feedback, Training, Reasoning, Hooks) before building custom infrastructure. Custom code should only fill gaps the framework doesn't cover.
6. **Single write target per run** — Self-evolution flows are restricted to this repository (plus metrics and logs) and MUST NOT modify external project trees. When an active project directory is set, project-focused commands (PRD, plan, execute, project vision generation) write only to that project tree, scoped shared PRD/exec output folders, and central knowledge locations designated for project VISION files.

## Long-Term Extension Directions

- Extend the dialectic method to adjacent artifacts such as ADR generation, PRD review, and backlog refinement.
- Expand execution outputs beyond Markdown specs into richer automation and external integrations without weakening verification safeguards.
- Deepen framework-native adoption where it improves the product's long-term quality, learning, observability, and human-in-the-loop workflows.

---

*This document must be read by ALL agents before proposing any solution. It defines the product's vocation and the direction of evolution.*
