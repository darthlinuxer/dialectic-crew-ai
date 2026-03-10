## Plan: CrewAI-Native Persistence Resume

## Audit status

- Implemented on 2026-03-10.
- PRD and task execution now use CrewAI-native persisted flow state with explicit phase-based resume.
- Planning remains artifact-based by design for this phase.
- CLI resume entry points exist for `prd`, `execute`, and `self-improve`.
- Self-improve resumes from saved cycle snapshots and reuses persisted PRD/execution handles.
- Focused regression coverage exists for PRD/task-flow persistence, execution checkpoint resume, self-improve resume, and CLI forwarding.

This draft plan shifts the next phase away from more ad hoc runtime patching and toward CrewAI-native persistence and resume semantics. The core idea is to formalize crash recovery and continuation around the existing flow architecture by using documented persistence patterns in `src/dialectic/prd_flow.py` and `src/execution/task_flow.py`, then threading stable flow identity and resume behavior through `src/main/self_improve.py` and `src/main/cli.py`. The plan deliberately treats `src/planning/flow.py` as a staged decision point rather than forcing it into a Flow rewrite immediately, because planning is currently artifact-driven rather than Flow-based.

**Steps**
1. Audit the current persistence boundary in [`src/dialectic/prd_flow.py`](../src/dialectic/prd_flow.py) `DialecticFlow`, `_get_persistence`, and `run_dialectic_flow`, plus [`src/execution/task_flow.py`](../src/execution/task_flow.py) `TaskExecutionFlow`, `TaskFlowState`, and `_get_task_persistence`, and document exactly where CrewAI persistence is already in use versus where recovery still depends on custom orchestration.
2. Design the target persistence model for PRD and task execution flows using CrewAI-native persisted flow state, including when class-level or method-level `@persist` should apply, what state fields must remain durable, and how `self.state.id` should be surfaced without breaking existing behavior.
3. Define explicit resume semantics in [`src/main/cli.py`](../src/main/cli.py) `cmd_prd`, `cmd_plan`, and `cmd_execute`, including how users start fresh runs versus resume interrupted ones, what gets printed to the terminal, and how flow identifiers or recovery handles are exposed.
4. Thread the same resume model through [`src/main/self_improve.py`](../src/main/self_improve.py) `run_self_improve`, `_record_prd_artifacts`, `_record_plan_artifacts`, `_record_execution_artifacts`, and `_require_artifact` so self-improve can recover from mid-cycle interruptions while preserving current git-safety and lineage guarantees.
5. Decide whether [`src/planning/flow.py`](../src/planning/flow.py) should remain artifact-based in this phase or be migrated into a Flow-backed state machine, using `run_user_story_planning`, `_extract_plan`, and `_ensure_acceptance_checks` as the main decision surface; document the tradeoff explicitly so execution does not drift mid-implementation.
6. Extend schema and lineage design only where necessary by reviewing [`src/dialectic/state.py`](../src/dialectic/state.py) `DialecticState` and the relevant models in [`src/schemas.py`](../src/schemas.py), especially `UserStoryExecutionPlan`, `ExecutionReport`, and `SelfImprovementRecord`, to determine whether persisted flow IDs or resume metadata should become first-class tracked fields.
7. Preserve and reuse the existing hook and safety model by aligning persistence work with [`src/dialectic/hooks.py`](../src/dialectic/hooks.py) rather than bypassing it, so token/cost tracking, protected-path enforcement, and tool/LLM observability still apply cleanly after resume.
8. Add focused regression coverage around persisted state restoration, resumed self-improve orchestration, and CLI behavior in [`tests/test_prd_flow.py`](../tests/test_prd_flow.py), [`tests/test_task_flow_state.py`](../tests/test_task_flow_state.py), [`tests/test_self_improve.py`](../tests/test_self_improve.py), [`tests/test_self_improve_lineage.py`](../tests/test_self_improve_lineage.py), [`tests/test_self_improve_git_safety.py`](../tests/test_self_improve_git_safety.py), and [`tests/test_cli_runtime.py`](../tests/test_cli_runtime.py).
9. Update the corresponding docs in [`docs/flows.md`](../flows.md), [`docs/architecture.md`](../architecture.md), [`docs/cli.md`](../cli.md), and [`docs/schemas.md`](../schemas.md) so the new persistence model, resume entry points, and limitations are documented where contributors will actually look.

**Verification**
Review the implementation against three layers: flow-level persistence behavior, self-improve recovery behavior, and user-facing CLI semantics. At minimum, run the focused PRD/task flow regression files, then the self-improve lineage and git-safety regressions, and finally the CLI runtime checks using the project venv. Add one crash-and-resume style test path that proves persisted state can be resumed without corrupting artifacts or bypassing protected-path rules.

**Decisions**
- Choose CrewAI-native persisted flow state over more local retry/export patching because the current failure pattern is architectural, not just prompt-level.
- Treat replay as a debugging aid rather than the primary recovery mechanism because this repository constructs work dynamically and already has artifact lineage that is better served by persisted flow state.
- Keep `allow_code_execution` disabled for this phase; recovery and persistence are the primary concern, and expanding execution capability would broaden risk without addressing the root cause.
- Do not force annotation-based crews in this phase because the repository convention is still explicit factory/orchestrator code, and persistence can be improved without a large stylistic migration.
- Use `docs/plan/` for this document because the user explicitly requested that location, even though other planning guidance in the repository references slightly different naming conventions.

**Open questions to settle before implementation**
- Should planning stay artifact-based in this phase, or is converting it into a real Flow worth the scope increase?
	- Settled for this phase: planning stays artifact-based.
- Where should persisted flow identifiers live long-term: runtime logs only, CLI output, lineage artifacts, or schema models?
	- Settled for this phase: expose them in CLI output and persist them in schema-backed lineage artifacts.
- Should persistence backend configuration remain implicit, or should the database location become an explicit configurable runtime setting?
	- Settled for this phase: default to `.dialectic/flows.db` with `DIALECTIC_FLOW_DB` override.
