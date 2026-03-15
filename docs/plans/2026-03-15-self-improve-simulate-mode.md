# Self-Improve Simulate Mode Implementation Plan

> **Note:** This plan should be executed task-by-task with verification at each step.

**Goal:** Replace the current introspection-only `self-improve --dry-run` behavior with a full-pipeline `--simulate` mode that exercises self-improve safely without leaving changes in the caller's active branch.

**Architecture:** Add a dedicated simulation path to the self-improve orchestrator that runs on a disposable `self-improve/simulate` branch while routing runtime artifacts and persistence into a temporary directory outside the repository. Keep real-run semantics unchanged, skip irreversible side effects during simulation, and clean up the branch/worktree on both success and failure.

**Tech Stack:** Python, Typer CLI, CrewAI flows, pytest, existing git helper abstractions.

**Prerequisites:** Local git checkout, project virtualenv, ability to run focused pytest selections.

---

### Task 1: Replace the CLI flag surface

**Files:**
- Modify: `src/main/cli.py`
- Modify: `src/main/cli_commands.py`
- Test: `tests/test_cli_runtime.py`

**Step 1:** Replace `--dry-run` with `--simulate` in the Typer command, help text, and CLI passthrough.

**Step 2:** Update the command wrapper to call `run_self_improve(simulate=True)` and print a simulation-specific completion message.

**Step 3:** Adjust CLI runtime tests to assert the new flag name and argument passthrough.

**Step 4:** Run focused CLI tests.

### Task 2: Add temp-rooted simulation runtime plumbing

**Files:**
- Modify: `src/dialectic/output_paths.py`
- Modify: `src/main/self_improve_persistence.py`
- Modify: `src/main/self_improve.py`
- Test: `tests/test_self_improve.py`

**Step 1:** Introduce a runtime-root override for centralized PRD/exec artifact paths.

**Step 2:** Introduce a self-improve snapshot path override so simulation snapshots live outside the repo.

**Step 3:** Add a temporary simulation-runtime context in `self_improve.py` that redirects artifact and persistence paths to a temp directory.

**Step 4:** Run focused tests covering path redirection and simulation completion messaging.

### Task 3: Add disposable simulate-branch orchestration

**Files:**
- Modify: `src/main/git_helpers.py`
- Modify: `src/main/self_improve.py`
- Test: `tests/test_self_improve.py`
- Test: `tests/test_self_improve_git_safety.py`

**Step 1:** Add explicit helpers for checking, deleting, resetting, and cleaning a specific branch/worktree.

**Step 2:** Teach `run_self_improve` to reject `--resume` with simulation, recreate `self-improve/simulate` fresh, and run the full pipeline on that branch.

**Step 3:** Skip roadmap mutation, commit creation, PR creation, and resume-state semantics during simulation.

**Step 4:** Ensure the simulate branch is reset/cleaned/discarded on both success and failure.

**Step 5:** Run focused simulation safety tests.

### Task 4: Update documentation and verify

**Files:**
- Modify: `README.md`
- Modify: `docs/cli.md`
- Modify: `docs/getting-started.md`

**Step 1:** Replace `--dry-run` examples with `--simulate` and explain the new full-pipeline semantics.

**Step 2:** Document that simulation uses a disposable branch plus temporary runtime artifacts.

**Step 3:** Run focused pytest, then relevant lint/type checks on touched files.

