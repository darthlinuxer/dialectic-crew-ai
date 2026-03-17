> Roadmap scope: `internal/SELF_VISION.md` defines the app's long-term product vision. `internal/ROADMAP.md` is the only file that should track phased implementation status. When the vision changes, update this file to reflect what is shipped, partially implemented, and still planned.

### Phase 1 (completed)

- [x] Dialectic flow with 4 agents and retry until 9.0
- [x] PRD output in JSON and Markdown in `prd_output/`
- [x] Modules **dialectic**, **planning**, **execution** and CLI (`prd` | `plan` | `execute` | `status` | `mark` | `verify`)
- [x] Planning in UserStoryExecutionPlan format with dialectic cycle
- [x] Three-phase execution pipeline: Dialectic → Verify → Reimplement via `@router`

### Phase 2: CrewAI Feature Adoption (engine enhancement)

- [x] Establish vision-scoped **Memory** (`memory=True`) foundations for crews
- [ ] Harden **Memory** for cross-session learning beyond a single crew run
- [x] Convert VISION.md to a **Knowledge** source (`TextFileKnowledgeSource`) for semantic access
- [x] Enable **Reasoning** (`reasoning=True`) on Visionary, Critic, and Synthesizer agents
- [x] Enable **Planning** (`planning=True`) for macro step-by-step planning before dialectic
- [ ] Add **Conditional Tasks** to skip unnecessary dialectic steps (e.g., skip antithesis if score >= 9.5)
- [x] Register **LLM Hooks** for cost tracking (token counting per PRD) and iteration limiting
- [x] Implement target-aware **anti-drift** vision resolution for `VisionContext.SELF` vs `VisionContext.PROJECT`
- [ ] Harden **anti-drift enforcement** with stronger validation, routing safeguards, and coverage
- [x] Support PRD exporter output modes for JSON, Markdown, or both
- [ ] Expose output-format selection and configurable Markdown templates through the CLI/runtime UX
- [x] Introduce a **structured logging foundation** with centralized config, rotating log files, JSON output, and correlation-aware runtime context
- [ ] Extend structured logging coverage through all tool calls and richer end-to-end stacktrace reconstruction

> Note: Phase 2 foundations are mostly in place. Remaining work is focused on hardening cross-session behavior, adopting native `ConditionalTask`, extending output/template UX, and deepening structured logging/tool trace coverage without weakening the shipped PRD → plan → execute workflow.

### Phase 3: Self-Improvement (training and testing)

- [ ] Implement **Training** workflow: `crewai train` with human feedback to improve agents over time, while keeping human review as the final gate for self-evolution changes
- [ ] Integrate **Testing** (`crewai test`) into CI pipeline for quality regression detection
- [x] Implement a resumable **self-evolution loop** that runs against `internal/SELF_VISION.md` via `VisionContext.SELF` and stays scoped to this repository
- [x] Leverage **structured logging** in self-improve cycles with correlation-aware runtime context and persisted run artifacts
- [ ] Expand self-improve reporting into richer machine- and human-readable stacktrace summaries for failed cycles

### Phase 3b: Active Project & External Repo Support

- [x] Implement CLI commands to set, inspect, clear, and list the active target project directory
- [x] Ensure `VisionContext.PROJECT` resolves from the active target and central knowledge file, using `knowledge/target/<target-slug>/VISION.md` with `knowledge/VISION.md` as fallback
- [x] Scope `prd`, `plan`, `execute`, and shared outputs to the active target while keeping `self-improve` strictly scoped to this repository and `internal/SELF_VISION.md`
- [x] Add a `make-vision` command to analyze the active target or this repository and write a generated vision document
- [ ] Add a richer project-scanning workflow that explicitly invokes the brainstorming skill and improves per-project `VISION.md` generation fidelity

### Phase 4: API Foundation

- [ ] FastAPI app wrapping the existing engine with REST endpoints for PRD creation, planning, execution, verification, active-project management, and trace inspection
- [ ] **Event Listeners** (`BaseEventListener`) streaming real-time progress to a WebSocket hub for connected clients
- [ ] PostgreSQL + SQLAlchemy models with Alembic migrations
- [ ] Background workers (ARQ/Celery + Redis) for async LLM flows
- [ ] JWT auth and multi-tenant data isolation
- [ ] **`kickoff_for_each`** for parallel user story processing
- [ ] **Observability** integration (Langfuse or OpenLIT) for production monitoring
- [ ] API endpoints for retrieving **structured logging traces**, inspecting per-run correlation IDs, and reconstructing per-run execution stacktraces from logs, metrics, and CrewAI events

### Phase 5: Web UI

- [ ] Next.js frontend with PRD creator, browsing flows, and live dialectic visualization for non-technical stakeholders
- [ ] **`@human_feedback`**-powered review workflow (approve/reject/revise routing)
- [ ] PRD list/detail with version history and diffs
- [ ] Story board (Kanban) and execution live view
- [ ] Analytics dashboard (cost, quality trends, agent performance)
- [ ] UI for viewing **structured logs** and run stacktraces, selecting/managing the **active project directory**, and browsing/editing per-project `VISION.md` documents derived from the central `knowledge/` layer

### Phase 6: Integrations and Scale

- [ ] GitHub Issues / Jira / Linear sync for user stories
- [ ] Slack / webhook notifications via CrewAI Webhook Streaming
- [ ] LLM cost tracking with per-organization budgets
- [ ] Collaborative real-time PRD editing
- [ ] **Hallucination Guardrail** on thesis output (validate against VISION.md context)
- [ ] Integrations aware of both `internal/SELF_VISION.md` and project-scoped `knowledge/target/<target-slug>/VISION.md` / `knowledge/VISION.md`, ensuring external systems can reference the correct vision context for self-evolution vs active project work

### Long-horizon Capability Backlog

These items remain aligned to `internal/SELF_VISION.md` but are intentionally tracked only here, not in the vision file itself.

- [ ] Generate ADRs (Architecture Decision Records) through the same dialectic workflow
- [ ] Refine backlog prioritization and slicing through thesis → antithesis → synthesis workflows
- [ ] Re-review existing PRDs through re-thesis / re-antithesis / re-synthesis flows
