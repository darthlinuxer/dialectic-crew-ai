# VISION.md — System Macro Vision

## About the Project

**Dialectic Crew AI** is itself the product: an application that uses the **dialectic method** (thesis → antithesis → synthesis → validation) to generate high-quality PRDs (Product Requirement Documents). The system self-orients by this vision to prevent drift and to evolve toward its vocation.

**Intent:** Be the best dialectic-method **platform** capable of generating PRDs in **Markdown** and **JSON**, with validated quality (score >= 9.0), explicit alignment to a macro vision (VISION.md), and the ability to **use its own dialectic process to evolve itself**. The platform leverages CrewAI's native capabilities (Memory, Knowledge, Event Listeners, Human Feedback, Training, Reasoning) to maximize quality while minimizing custom infrastructure.

**Vocation:**
- **Core:** Generate structured PRDs (objective, macro_impact, user_stories, anti_drift_questions) in **two formats** — `.md` (readable, versionable, collaborative) and `.json` (machine-friendly, integrations, APIs).
- **Method:** Ensure every proposal goes through contradiction (antithesis) and synthesis before approval, reducing bias and overscope.
- **Evolution:** Extend the same dialectic method to other artifacts and lifecycle phases (see "Possible Uses" below).

---

## Business Objectives

1. **PRDs in Markdown and JSON** — Every approved PRD must be persisted in `prd_output/` as both `.md` (narrative document, human-ready) and `.json` (validated schema, tool-ready).
2. **Quality through dialectics** — Maintain the Thesis → Antithesis → Synthesis → Validation loop with retry until score >= 9.0 and zero contradictions with VISION.md.
3. **Anti-drift** — All agents read VISION.md; anti-drift questions and validation ensure continuous alignment with the macro vision.
4. **Self-improvement** — The project uses this VISION to guide itself; behavior or scope changes must be consistent with this document.
5. **API-first architecture** — Expose all capabilities (PRD creation, planning, execution, verification) through a REST API backed by CrewAI Event Listeners for real-time progress streaming, enabling programmatic integration and a web frontend.
6. **Web experience** — Provide a web UI for PRD creation, browsing, review workflows (powered by CrewAI's `@human_feedback` decorator), user story boards, and live dialectic visualization — making the tool accessible to non-technical stakeholders.
7. **Self-evolution** — The system uses its own dialectic pipeline to generate PRDs for its own features. VISION.md defines the target; the app generates the PRDs to get there, plans the user stories, and produces execution artifacts. CrewAI Training (`crew.train()`) captures human feedback to permanently improve agent behavior. Human review remains the final gate.
8. **Framework-first** — Before building custom solutions, leverage CrewAI's native features: Memory for cross-session learning, Knowledge for semantic document access, Event Listeners for observability, Human Feedback for review workflows, Training for self-improvement, Reasoning for deeper agent thinking, and Conditional Tasks for efficient flow control.

---

## System Scope

### Main Modules / Components

| Component       | Description |
|-----------------|-------------|
| **dialectic**   | Dialectic core: agents (Visionary, Socratic Critic, Synthesizer, Validator), tools, state, DialecticFlow (PRD with retry), export (PRD and plan to Markdown). |
| **planning**    | Execution planning: per user story, produces UserStoryExecutionPlan (thesis → antithesis → synthesis → validation). |
| **execution**   | Approved plan execution: consumes UserStoryExecutionPlan and generates artifacts (spec/draft in Markdown; extensible to code or integrations). Three-phase pipeline: Dialectic → Verify (A+B) → Reimplement (C) via @router. |
| **schemas**     | Source of truth for PRDs and plans: PRDSchema, UserStory, MacroImpact, AntiDriftQuestion; UserStoryExecutionPlan, ImplementationTask, VerificationResult. |
| **main / CLI**  | Commands: `prd "feature"` (PRD with dialectics), `plan [prd] [US]` (plan per user story), `execute [plan]` (execution artifact), `status`, `mark`, `verify`. |
| **api** (planned) | FastAPI REST + WebSocket layer. CrewAI Event Listeners feed real-time progress to connected clients. Background workers for long-running LLM flows. JWT/OAuth2 auth with multi-tenant isolation. |
| **db** (planned) | PostgreSQL persistence for PRDs, plans, executions, reviews, and LLM usage. Version history with diffs. Replaces flat-file storage as the primary store. |
| **frontend** (planned) | Next.js web application: PRD creator with live dialectic visualization, `@human_feedback`-powered review workflow, story board, analytics dashboard. |
| **observability** (planned) | CrewAI Event Listeners + LLM Hooks for cost tracking, token usage, latency metrics. Pluggable into Langfuse, OpenLIT, or Datadog via OpenTelemetry. |

### Integrations (current / desired)

- **Input:** CLI arguments, VISION.md content, environment variables (API keys).
- **Output:** Files in `prd_output/` (PRDs and plans in **JSON + Markdown**); execution artifacts in `exec_output/`.
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

### CrewAI Features to Adopt

- **Memory** (`memory=True`) — Cross-session agent learning with hierarchical scopes
- **Knowledge** (`TextFileKnowledgeSource`) — Semantic VISION.md access and past-PRD retrieval
- **Event Listeners** (`BaseEventListener`) — Real-time progress, cost tracking, audit trail
- **Human Feedback** (`@human_feedback`) — Native review/approval workflow with routing
- **Training** (`crew.train()`) — Self-improvement via human feedback distillation
- **Testing** (`crewai test`) — Framework-level quality benchmarking (CI-ready)
- **Reasoning** (`reasoning=True`) — Pre-task reflection for deeper agent thinking
- **Planning** (`planning=True`) — AgentPlanner for macro step-by-step planning
- **LLM Hooks** (`@before_llm_call`) — Cost tracking, iteration limiting, guardrails
- **Conditional Tasks** (`ConditionalTask`) — Skip unnecessary dialectic steps
- **`kickoff_for_each`** — Parallel user story planning and execution

---

## Non-Functional Requirements

- **Reproducibility:** Dependency lock (uv.lock) and stable PRD schema.
- **Clarity:** PRD in Markdown for human reading; JSON for pipelines and automation.
- **Quality:** No PRD approved with score < 9.0 unless the flow has retried up to the configured limit.
- **Maintainability:** Readable code, well-separated responsibilities (flow, agents, schemas).

---

## Design Principles

1. **Dialectics as the core** — Thesis, antithesis, and synthesis are not optional; the Validator is the sole approval gate.
2. **VISION.md as anchor** — Every proposal is confronted with the macro vision; anti-drift is mandatory.
3. **Dual output (MD + JSON)** — Serve both human readers and tools/integrations.
4. **Extensible** — Architecture must allow new flows (e.g., dialectics for user story execution) without breaking the core.
5. **Framework-first** — Leverage CrewAI's native features (Memory, Knowledge, Event Listeners, Human Feedback, Training, Reasoning, Hooks) before building custom infrastructure. Custom code should only fill gaps the framework doesn't cover.

---

## CrewAI Features to Adopt

The following CrewAI capabilities are available but not yet leveraged. Each should be adopted in the phase indicated.

| Feature | Use Case | Phase |
|---------|----------|-------|
| **Memory** (`memory=True`) | Agents remember past decisions, past PRDs, and past critiques across sessions. Visionary remembers architectural decisions; Critic remembers past objections. | Phase 2 |
| **Knowledge** (`TextFileKnowledgeSource`) | VISION.md and past PRDs as semantic knowledge sources instead of raw text injection. Agents query rather than read. | Phase 2 |
| **Reasoning** (`reasoning=True`) | Visionary, Synthesizer, and Critic agents reflect and plan before producing output. Reduces retries. | Phase 2 |
| **Planning** (`planning=True`) | AgentPlanner creates a macro plan for the dialectic crew before thesis generation. | Phase 2 |
| **Conditional Tasks** (`ConditionalTask`) | Skip antithesis if thesis scores >= 9.5. Skip reimplementation if verification passes. | Phase 2 |
| **LLM Hooks** (`@before_llm_call`) | Token counting, cost-per-PRD tracking, iteration limiting, debug logging. | Phase 2 |
| **Training** (`crew.train()`) | Human feedback on dialectic output improves agents permanently. Self-evolution mechanism. | Phase 3 |
| **Testing** (`crewai test`) | CI-ready quality benchmarking: run N iterations, score agents, track regressions. | Phase 3 |
| **Event Listeners** (`BaseEventListener`) | Stream progress events (agent started, task completed, LLM call) to API/WebSocket layer. | Phase 4 |
| **Human Feedback** (`@human_feedback`) | Stakeholder review workflow: approved/rejected/needs_revision routing within the flow. | Phase 5 |
| **`kickoff_for_each`** | Plan and execute all user stories in a PRD simultaneously. | Phase 4 |
| **Observability** (Langfuse/OpenLIT) | Production monitoring dashboards: cost, latency, quality score trends. | Phase 4 |

### CrewAI Reference Documentation

Agents working on self-evolution PRDs MUST consult these sources before proposing solutions. The documentation index at `https://docs.crewai.com/llms.txt` lists every available page and should be fetched first to discover new or updated content.

**Core Concepts**
- [Agents](https://docs.crewai.com/en/concepts/agents) — Creating and managing agents, roles, goals, backstory, tools, LLM assignment
- [Tasks](https://docs.crewai.com/en/concepts/tasks) — Task definition, expected output, guardrails, structured output (`output_pydantic`)
- [Crews](https://docs.crewai.com/en/concepts/crews) — Crew assembly, process types (sequential, hierarchical), configuration
- [Flows](https://docs.crewai.com/en/concepts/flows) — Flow API (`@start`, `@listen`, `@router`), state management, persistence, `or_()` combinator
- [Processes](https://docs.crewai.com/en/concepts/processes) — Sequential vs. hierarchical workflow management
- [LLMs](https://docs.crewai.com/en/concepts/llms) — Model configuration, provider support, tiered model strategy
- [Tools](https://docs.crewai.com/en/concepts/tools) — Built-in and custom tool creation, 40+ available tools
- [Files](https://docs.crewai.com/en/concepts/files) — Multimodal file processing (images, PDFs, audio, video, text)

**Features to Adopt (Phase 2-6)**
- [Memory](https://docs.crewai.com/en/concepts/memory) — Unified memory with hierarchical scopes, semantic recall, composite scoring
- [Knowledge](https://docs.crewai.com/en/concepts/knowledge) — RAG-based knowledge sources (text, PDF, JSON, CSV, web), vector store configuration
- [Reasoning](https://docs.crewai.com/en/concepts/reasoning) — Agent pre-task reflection and structured planning (`reasoning=True`)
- [Planning](https://docs.crewai.com/en/concepts/planning) — Built-in AgentPlanner for macro step-by-step planning (`planning=True`)
- [Training](https://docs.crewai.com/en/concepts/training) — Human feedback distillation into permanent agent improvement (`crew.train()`)
- [Testing](https://docs.crewai.com/en/concepts/testing) — Built-in crew benchmarking with scored iterations (`crewai test`)
- [Event Listeners](https://docs.crewai.com/en/concepts/event-listener) — Event bus with 40+ event types for custom integrations and monitoring
- [Collaboration](https://docs.crewai.com/en/concepts/collaboration) — Agent delegation, communication, and teamwork patterns

**Advanced Patterns**
- [Human Feedback in Flows](https://docs.crewai.com/en/learn/human-feedback-in-flows) — `@human_feedback` decorator with emit routing and learning
- [Human-in-the-Loop](https://docs.crewai.com/en/learn/human-in-the-loop) — Webhook-based HITL for production async workflows
- [LLM Hooks](https://docs.crewai.com/en/learn/llm-hooks) — `@before_llm_call`, `@after_llm_call` for cost tracking, guardrails, approval gates
- [Execution Hooks](https://docs.crewai.com/en/learn/execution-hooks) — Tool call hooks for monitoring, safety, caching
- [Conditional Tasks](https://docs.crewai.com/en/learn/conditional-tasks) — `ConditionalTask` for dynamic workflow adaptation
- [Kickoff For Each](https://docs.crewai.com/en/learn/kickoff-for-each) — Parallel crew execution per list item
- [Kickoff Async](https://docs.crewai.com/en/learn/kickoff-async) — Non-blocking crew execution
- [Custom Tools](https://docs.crewai.com/en/learn/create-custom-tools) — Creating project-specific tools for agents
- [Customizing Prompts](https://docs.crewai.com/en/guides/advanced/customizing-prompts) — Low-level prompt customization for different models

**Production & Deployment**
- [Production Architecture](https://docs.crewai.com/en/concepts/production-architecture) — Flow-first mindset, deployment patterns, persistence, async execution
- [Observability Overview](https://docs.crewai.com/en/observability/overview) — Monitoring, evaluation, and optimization tools
- [Langfuse Integration](https://docs.crewai.com/en/observability/langfuse) — OpenTelemetry-based tracing via OpenLit
- [OpenLIT Integration](https://docs.crewai.com/en/observability/openlit) — One-line monitoring with OpenTelemetry
- [CrewAI Tracing](https://docs.crewai.com/en/observability/tracing) — Built-in tracing for Crews and Flows
- [Hallucination Guardrail](https://docs.crewai.com/en/enterprise/features/hallucination-guardrail) — Faithfulness scoring against reference context
- [Webhook Streaming](https://docs.crewai.com/en/enterprise/features/webhook-streaming) — Real-time event delivery to external endpoints

**MCP (Model Context Protocol)**
- [MCP Overview](https://docs.crewai.com/en/mcp/overview) — MCP servers as agent tools
- [MCP DSL Integration](https://docs.crewai.com/en/mcp/dsl-integration) — Simplified `mcps` field syntax for agents
- [Multiple MCP Servers](https://docs.crewai.com/en/mcp/multiple-servers) — `MCPServerAdapter` for aggregating multiple servers

**Integrations (Phase 6)**
- [GitHub Integration](https://docs.crewai.com/en/enterprise/integrations/github) — Repository and issue management
- [Jira Integration](https://docs.crewai.com/en/enterprise/integrations/jira) — Issue tracking and project management
- [Linear Integration](https://docs.crewai.com/en/enterprise/integrations/linear) — Software project and bug tracking
- [Slack Integration](https://docs.crewai.com/en/enterprise/integrations/slack) — Team communication and notifications
- [Notion Integration](https://docs.crewai.com/en/enterprise/integrations/notion) — Documentation and knowledge management

---

## Possible Uses (Conceptual Roadmap)

### Already in scope

- Generate a PRD from a feature request, with output in **JSON** and **Markdown** in `prd_output/`.
- **Plan** user story execution in the format defined in `schemas.py`: each user story follows the **UserStory** model (id, title, description, acceptance_criteria, effort, dependencies). Planning produces **UserStoryExecutionPlan** (user_story_id, approach_summary, tasks as **ImplementationTask** — id, title, description, order, dependencies, acceptance_checks —, risks_mitigated, tech_notes, quality_score, consensus_reached).
- **Execute** the approved plan: the execution module consumes the UserStoryExecutionPlan and generates artifacts (Markdown spec with ordered tasks and acceptance criteria; extensible to code drafts, specs, or issue integration).

### Evolving

- **Dialectic cycle per user story (planning)** — Already implemented: thesis (initial plan) → antithesis (critiques) → synthesis (refined plan) → validation (approved UserStoryExecutionPlan). Format aligned with `schemas.py`.
- **Advanced execution** — From the approved plan: code draft generation, optional integration with GitHub Issues/Jira, or backlog updates (keeping the dialectic method as a gate). Three-phase pipeline (Dialectic → Verify → Reimplement) via native CrewAI Flow `@router`.

- **Other possibilities**
  - Generate ADRs (Architecture Decision Records) via the same dialectic flow.
  - Refine backlog (prioritization and slicing) with thesis/antithesis/synthesis.
  - Review existing PRDs (re-thesis, re-antithesis, re-synthesis from an old PRD or from feedback).

---

## Suggested Roadmap

### Phase 1 (completed)

- [x] Dialectic flow with 4 agents and retry until 9.0
- [x] PRD output in JSON and Markdown in `prd_output/`
- [x] Modules **dialectic**, **planning**, **execution** and CLI (`prd` | `plan` | `execute` | `status` | `mark` | `verify`)
- [x] Planning in UserStoryExecutionPlan format with dialectic cycle
- [x] Three-phase execution pipeline: Dialectic → Verify → Reimplement via `@router`

### Phase 2: CrewAI Feature Adoption (engine enhancement)

- [ ] Harden **Memory** (`memory=True`) for cross-session learning beyond a single crew run
- [x] Convert VISION.md to a **Knowledge** source (`TextFileKnowledgeSource`) for semantic access
- [x] Enable **Reasoning** (`reasoning=True`) on Visionary, Critic, and Synthesizer agents
- [x] Enable **Planning** (`planning=True`) for macro step-by-step planning before dialectic
- [ ] Add **Conditional Tasks** to skip unnecessary dialectic steps (e.g., skip antithesis if score >= 9.5)
- [x] Register **LLM Hooks** for cost tracking (token counting per PRD) and iteration limiting
- [ ] Option to choose only MD, only JSON, or both; configurable Markdown templates

> Note: Memory, Knowledge, Reasoning, and Planning are already partially adopted in the current engine. Remaining work is focused on hardening, cross-session behavior, and removing documentation/introspection drift.

### Phase 3: Self-Improvement (training and testing)

- [ ] Implement **Training** workflow: `crewai train` with human feedback to improve agents over time
- [ ] Integrate **Testing** (`crewai test`) into CI pipeline for quality regression detection
- [ ] **Self-evolution loop**: the system generates PRDs for its own roadmap items by running `prd` against VISION.md; human review is the final gate

### Phase 4: API Foundation

- [ ] FastAPI app wrapping the existing engine with REST endpoints
- [ ] **Event Listeners** (`BaseEventListener`) streaming progress to WebSocket hub
- [ ] PostgreSQL + SQLAlchemy models with Alembic migrations
- [ ] Background workers (ARQ/Celery + Redis) for async LLM flows
- [ ] JWT auth and multi-tenant data isolation
- [ ] **`kickoff_for_each`** for parallel user story processing
- [ ] **Observability** integration (Langfuse or OpenLIT) for production monitoring

### Phase 5: Web UI

- [ ] Next.js frontend with PRD creator and live dialectic visualization
- [ ] **`@human_feedback`**-powered review workflow (approve/reject/revise routing)
- [ ] PRD list/detail with version history and diffs
- [ ] Story board (Kanban) and execution live view
- [ ] Analytics dashboard (cost, quality trends, agent performance)

### Phase 6: Integrations and Scale

- [ ] GitHub Issues / Jira / Linear sync for user stories
- [ ] Slack / webhook notifications via CrewAI Webhook Streaming
- [ ] LLM cost tracking with per-organization budgets
- [ ] Collaborative real-time PRD editing
- [ ] **Hallucination Guardrail** on thesis output (validate against VISION.md context)

---

*This document must be read by ALL agents before proposing any solution. It defines the product's vocation and the direction of evolution.*
