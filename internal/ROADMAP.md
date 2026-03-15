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
- [ ] Introduce a **structured logging layer** that centralizes log configuration and emits JSON-structured events for core flows, with correlation IDs plumbed through flows, agents, and tools.

> Note: Memory, Knowledge, Reasoning, and Planning are already partially adopted in the current engine. Remaining work is focused on hardening, cross-session behavior, and removing documentation/introspection drift.

### Phase 3: Self-Improvement (training and testing)

- [ ] Implement **Training** workflow: `crewai train` with human feedback to improve agents over time
- [ ] Integrate **Testing** (`crewai test`) into CI pipeline for quality regression detection
- [ ] **Self-evolution loop**: the system generates PRDs for its own roadmap items by running `prd` against `internal/SELF_VISION.md` (VisionContext.SELF) and applying changes only to this repository; human review is the final gate
- [ ] Leverage **structured logging** in self-improve cycles to produce machine- and human-readable run reports (stacktraces) for debugging failed cycles.

### Phase 3b: Active Project & External Repo Support

- [ ] Implement a CLI command to **set an active project directory** that points to a local checkout of a remote repo and persist that configuration.
- [ ] Ensure `VisionContext.PROJECT` is resolved from the active project and its corresponding `knowledge/VISION.md`.
- [ ] Add a command to **scan the active project**, run the brainstorming skill at `src/mcp/skills/brainstorming/`, and generate or update that project’s `VISION.md` in the central `knowledge/` layer.
- [ ] Update `prd`, `plan`, and `execute` behavior so that, when an active project is set, these commands operate only within that project tree for reads/writes, while `self-improve` remains scoped strictly to this repository and `internal/SELF_VISION.md`.

### Phase 4: API Foundation

- [ ] FastAPI app wrapping the existing engine with REST endpoints
- [ ] **Event Listeners** (`BaseEventListener`) streaming progress to WebSocket hub
- [ ] PostgreSQL + SQLAlchemy models with Alembic migrations
- [ ] Background workers (ARQ/Celery + Redis) for async LLM flows
- [ ] JWT auth and multi-tenant data isolation
- [ ] **`kickoff_for_each`** for parallel user story processing
- [ ] **Observability** integration (Langfuse or OpenLIT) for production monitoring
- [ ] API endpoints for retrieving **structured logging traces** and inspecting per-run correlation IDs, as well as endpoints for managing the **active project directory** and associated project VISION metadata.

### Phase 5: Web UI

- [ ] Next.js frontend with PRD creator and live dialectic visualization
- [ ] **`@human_feedback`**-powered review workflow (approve/reject/revise routing)
- [ ] PRD list/detail with version history and diffs
- [ ] Story board (Kanban) and execution live view
- [ ] Analytics dashboard (cost, quality trends, agent performance)
- [ ] UI for viewing **structured logs** and run stacktraces, selecting/managing the **active project directory**, and browsing/editing per-project `VISION.md` documents derived from the central `knowledge/` layer.

### Phase 6: Integrations and Scale

- [ ] GitHub Issues / Jira / Linear sync for user stories
- [ ] Slack / webhook notifications via CrewAI Webhook Streaming
- [ ] LLM cost tracking with per-organization budgets
- [ ] Collaborative real-time PRD editing
- [ ] **Hallucination Guardrail** on thesis output (validate against VISION.md context)
- [ ] Integrations aware of both `internal/SELF_VISION.md` and per-project `knowledge/VISION.md`, ensuring external systems (GitHub, Jira, etc.) can reference the correct vision context for self-evolution vs active project work.
