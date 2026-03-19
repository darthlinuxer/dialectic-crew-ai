# Continue-PRD Self-Improve Implementation Plan

> **Note:** This plan should be executed task-by-task with verification at each step.

**Goal:** Add an explicit self-improve mode that continues a roadmap-backed or SELF PRD through all unfinished user stories with safe resume semantics and accurate final roadmap completion.

**Architecture:** Keep `--next-available-story` as a single-story command and introduce a new explicit `--continue-prd` mode. Implement the loop in `run_self_improve()` while extending `SelfImprovementRecord` with per-story progress/history so resume, debugging, and artifact lineage remain correct across multiple story iterations.

**Tech Stack:** Python 3.12, Typer CLI, Pydantic schemas, pytest, Ruff, mypy.

**Prerequisites:** Existing next-story continuation logic must remain green; use the current self-improve focused regression suite as the safety net before widening behavior.

---

## Current status update

Already implemented and verified before this plan starts:

- `--next-available-story` exists as a single-story self-improve mode.
- Pathless next-story discovery prefers the newest unfinished SELF PRD instead of the newest PRD blindly.
- Roadmap completion is deferred until the source roadmap-backed PRD has no unfinished stories remaining.
- Supplied plan artifacts preserve `source_prd_path`, so roadmap gating still evaluates the full PRD and avoids premature completion.

Not implemented yet:

- No critical gaps remain for the initial `--continue-prd` implementation slice.
- The last audit gaps were closed: the CLI/runtime now reject `--continue-prd` together with `--next-available-story`, resume can advance after a completed story when the next one had not started yet, and the loop has explicit regression coverage proving it stops after an intermediate failure without starting later stories.
- Optional future hardening could still promote story history to a dedicated typed model or add bounded loop controls such as `--max-stories`.

## Recommended repo plan path

`docs/plans/2026-03-18-continue-prd-self-improve.md`

## Steps

1. Confirm the public contract before changing behavior by tracing `cmd_self_improve()` and `self_improve_command()` in `src/main/cli/commands.py` and `src/main/cli/entrypoint.py`, plus `run_self_improve()` and the persistence helpers in `src/main/self_improve/internal/orchestrator.py` and `src/main/self_improve/persistence.py`. Record the current invariants: `--next-available-story` is one-story-per-run, `--resume` is mutually exclusive with artifact-start modes, and roadmap updates are deferred until the source PRD has no unfinished stories. This step blocks the rest.
2. Add RED CLI tests for the new mode in `tests/test_cli_runtime.py` (and command-layer tests if needed): allow `--continue-prd` with a PRD artifact or no artifact, reject it with `--resume`, reject it with a supplied plan artifact, and ensure the flag is passed through from the entrypoint to `cmd_self_improve()` and then to `run_self_improve()`. Keep `--next-available-story` semantics unchanged. *Depends on 1.*
3. Extend `SelfImprovementRecord` in `src/schemas.py` with explicit multi-story loop state. Recommended fields: `continue_prd: bool`, `continue_prd_source_prd_path: str`, `continue_prd_current_story_ref: str`, `continue_prd_completed_story_refs: List[str]`, and `continue_prd_story_history: List[dict]` (or a small typed Pydantic model if you prefer stronger structure). Do not overload the existing single-story fields alone, because they are currently reused by resume logic and would otherwise overwrite earlier iterations. Add focused schema tests if any serialization or defaults change. *Depends on 1; can begin in parallel with 2 after contract discovery is done.*
4. Add RED orchestrator tests in `tests/test_self_improve.py` for the loop behavior before implementing it. Cover at minimum: (a) continue through multiple unfinished stories in PRD order, (b) auto-discover the newest unfinished SELF PRD when no artifact is supplied, (c) stop on an intermediate failure without starting later stories, (d) preserve per-story history and completed-story refs, and (e) mark the roadmap item only after the final story completes. Reuse colocated `exec_*.json` artifacts and `source_prd_path` as the source of truth so the new tests match the existing continuation contract. *Depends on 1 and 3.*
5. Implement the new CLI and runtime contract. Add `continue_prd: bool = False` to `self_improve_command()`, `cmd_self_improve()`, and `run_self_improve()`. Update validation helpers so `--continue-prd` can start from a PRD artifact or from auto-discovery, but not from a plan artifact and not in combination with `--resume` or `--next-available-story` unless there is a deliberate documented reason. Update CLI help/examples to explain that `--continue-prd` loops until the PRD is complete, while `--next-available-story` remains single-step. *Depends on 2.*
6. Implement the orchestrator loop in `run_self_improve()` using a small explicit helper rather than burying the logic inside the main function body. Recommended flow: resolve the source PRD path, choose the next unfinished story via `next_available_story_for_prd()`, set current-story state on the record, clear per-story active fields (`plan_generated`, `execution_attempted`, `quality_gate_passed`, `tests_passed`, `metrics_stable`, etc.), run planning/execution/validation for that story, append a history entry, mark the story completed in the record, then continue until `next_available_story_for_prd()` returns `None`. Preserve the existing single-story path for all other modes. *Depends on 3, 4, and 5.*
7. Tighten resume semantics for the loop mode. On resume, use the persisted `continue_prd_*` fields to decide whether to re-enter planning or execution for the current story, or to advance to the next unfinished story if the previous story is already complete. Ensure a resumed loop does not accidentally reuse the previous story’s plan/execution artifacts for the next story. Add RED/green tests covering interruption during second-story planning, interruption during second-story execution, and resume after one story completed but before the next began. *Depends on 6.*
8. Finalize roadmap and PR behavior for the loop mode. Ensure roadmap completion still happens exactly once, only after the full source PRD has no unfinished stories left. Create at most one final commit/PR for the whole cycle, not one per story. Confirm the no-change/no-commit path still behaves sensibly when all stories are already complete or when the loop fails before producing committable changes. *Depends on 6 and 7.*
9. Run focused verification first, then broaden only if needed. At minimum, run the focused self-improve next-story/roadmap tests, the new continue-PRD regressions, CLI runtime tests for the new flag, targeted `ruff`, targeted `mypy`, and any additional `pyright`/`pylint` checks if public interfaces or package surfaces change. *Depends on 8.*

## Relevant files

- `/home/darthlinuxer/dialectic-crew-ai/src/main/cli/entrypoint.py` — Typer flag surface and CLI examples.
- `/home/darthlinuxer/dialectic-crew-ai/src/main/cli/commands.py` — command validation and `run_self_improve()` argument wiring.
- `/home/darthlinuxer/dialectic-crew-ai/src/main/self_improve/internal/orchestrator.py` — primary loop implementation, artifact handling, roadmap gating, and resume behavior.
- `/home/darthlinuxer/dialectic-crew-ai/src/main/self_improve/persistence.py` — PRD/story completion discovery helpers already used by next-story selection.
- `/home/darthlinuxer/dialectic-crew-ai/src/schemas.py` — `SelfImprovementRecord` state extensions for per-story progress/history.
- `/home/darthlinuxer/dialectic-crew-ai/tests/test_self_improve.py` — orchestration regressions, loop behavior, resume scenarios, and roadmap finalization tests.
- `/home/darthlinuxer/dialectic-crew-ai/tests/test_cli_runtime.py` — CLI flag pass-through and rejection/allowance coverage.

## Verification

1. Add/adjust focused regression tests for `--continue-prd` CLI validation and pass-through.
2. Add/adjust focused orchestration tests for multi-story completion, auto-discovery, interruption/resume, and final roadmap marking.
3. Run `pytest tests/test_self_improve.py -q -k "continue_prd or next_available_story or roadmap"` (passed: `19 passed, 72 deselected`).
4. Run `pytest tests/test_cli_runtime.py -q -k "continue_prd or next_available_story"` (passed: `7 passed, 49 deselected`).
5. Run focused gap-closing regressions:
	- `pytest tests/test_cli_runtime.py -q -k "continue_prd and next_available_story"` (passed: `1 passed, 55 deselected`)
	- `pytest tests/test_self_improve.py -q -k "continue_prd and (next_available_story or intermediate_execution_failure or completed_story_advances)"` (passed: `3 passed, 88 deselected`)
6. Run `ruff check` on touched source/test files (passed).
7. Run focused `mypy` with `MYPYPATH=src` and `--explicit-package-bases` on touched source files, plus touched tests in the test-package mypy command (passed).
8. Run focused `pyright --project pyrightconfig.json` and `pylint` on the touched files (passed).

## Decisions

- Keep `--next-available-story` single-step; do not silently change its behavior into a loop.
- Add a new explicit loop mode (`--continue-prd`) so runtime cost and duration are opt-in and predictable.
- Preserve roadmap gating at the PRD level; roadmap completion remains a full-PRD event, not a per-story event.
- Extend the cycle record with explicit per-story loop state/history instead of relying only on the existing single-story fields.
- Reject starting loop mode from a plan artifact; the loop contract should be PRD-centric.

## Further considerations

1. If per-story history starts getting bulky, promote it from `List[dict]` to a dedicated typed Pydantic model for better editor/type support.
2. Live per-story progress summary output is now implemented for loop mode; keep it concise if more detail is added later.
3. If users later want partial loop scopes, add a bounded option like `--max-stories N` rather than overloading the base loop semantics.

## Execution checklist

- [x] Phase 1a — Contract discovery
	- Confirm the current single-story contract, auto-discovery rules, and roadmap gating behavior.
	- Capture the already-implemented foundations listed in the status update above.
- [x] Phase 1b — Contract and tests
	- Add CLI RED tests for `--continue-prd` allowance/rejection rules.
	- Add orchestration RED tests for multi-story continuation and roadmap finalization.
- [x] Phase 2 — State model
	- Extend `SelfImprovementRecord` with explicit continue-PRD state/history fields.
	- Keep existing single-story fields for backward compatibility and current flows.
- [x] Phase 3 — CLI wiring
	- Add the new Typer flag and command-layer validation.
	- Keep `--next-available-story` behavior unchanged.
- [x] Phase 4 — Orchestrator loop
	- Implement the story loop and per-story record resets/history append.
	- Preserve artifact-based completion and final roadmap gating.
- [x] Phase 5 — Resume semantics
	- Resume planning/execution for the current story correctly.
	- Advance to the next unfinished story only when the prior one is truly complete.
- [x] Phase 6 — Verification
	- Run focused pytest suites for self-improve and CLI runtime.
	- Run focused Ruff and mypy, plus Pyright/pylint if interfaces shift.
	- Close the remaining audit gaps with explicit regressions for mode conflict, post-story resume advancement, and stop-on-intermediate-failure behavior.
