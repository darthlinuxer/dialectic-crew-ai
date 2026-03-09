# VISION.md — System Macro Vision

## About the Project

**Dialectic Crew AI** is itself the product: an application that uses the **dialectic method** (thesis → antithesis → synthesis → validation) to generate high-quality PRDs (Product Requirement Documents). The system self-orients by this vision to prevent drift and to evolve toward its vocation.

**Intent:** Be the best dialectic-method tool capable of generating PRDs in **Markdown** and **JSON**, with validated quality (score >= 9.0) and explicit alignment to a macro vision (VISION.md).

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

### Phase 1 (current)

- [x] Dialectic flow with 4 agents and retry until 9.0
- [x] PRD output in JSON and Markdown in `prd_output/`
- [x] Modules **dialectic**, **planning**, **execution** and CLI (`prd` | `plan` | `execute` | `status` | `mark` | `verify`)

### Phase 2

- [ ] Option to choose only MD, only JSON, or both
- [ ] Configurable Markdown templates for the PRD
- [ ] Documentation on "how to extend" for new formats (e.g., YAML)

### Phase 3 (user story planning and execution)

- [x] **Planning** in UserStoryExecutionPlan format: for each user story, dialectic cycle (thesis → antithesis → synthesis → validation) produces a plan with tasks (ImplementationTask) and score; persisted in `prd_output/exec_*.json` and `.md`.
- [x] **Execution** from the plan: artifact generation (Markdown spec) in `exec_output/`; entry point for future code generation or tool integration.
- [x] **Three-phase pipeline**: Dialectic → Verify (acceptance checks) → Reimplement (if verification fails) via `TaskExecutionFlow` with `@router`.
- [ ] Optional integration with GitHub Issues, Jira, etc. to create tasks from the approved plan
- [ ] Option to generate code drafts per task (keeping the dialectic method as a gate)

---

*This document must be read by ALL agents before proposing any solution. It defines the product's vocation and the direction of evolution.*
