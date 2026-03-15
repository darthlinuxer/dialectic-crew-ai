# Pylint Remediation Plan

> **Note:** This plan should be executed task-by-task with verification at each step.

**Goal:** Make the touched files from the VisionContext/self-improve fix pass `pylint` without weakening the underlying runtime or test guarantees.

**Architecture:** Keep the production fix centered on canonical import surfaces and normalized `VisionContext` values, then reduce or explicitly justify `pylint` violations with the smallest safe refactors. Prefer local code improvements over broad lint suppression, and use narrowly scoped disables only when a stable public API would otherwise be harmed.

**Tech Stack:** Python 3.12, pytest, Ruff, mypy, pylint, CrewAI runtime/task builders.

**Prerequisites:**
- `uv sync` has been run and the virtualenv includes `pylint`
- Work from the repo root: `/home/darthlinuxer/dialectic-crew-ai`
- Start with the currently failing command:
	`./.venv/bin/python -m pylint src/dialectic/vision.py src/dialectic/knowledge.py src/dialectic/output_paths.py src/dialectic/introspect.py src/execution/runtime.py tests/test_self_improve_vision_injection.py --score=n`

## Progress update

- Completed: regression tests were stabilized around canonical imports plus tightly scoped legacy `src.*` probes.
- Completed: runtime/task builder helpers were refactored away from generic `**overrides` patterns to explicit typed parameters.
- Completed: shared CrewAI builder helpers now live in `src/dialectic/crew_builder.py` to remove repeated task/crew construction logic.
- Completed: focused verification is green via `pytest`, `ruff`, `mypy`, and `pylint` on the touched runtime and regression-test files.

---

### Task 1: Lock down current behavior before refactoring

**Files:**
- Verify: `tests/test_self_improve_vision_injection.py`
- Verify: `tests/test_execution_runtime.py`
- Verify: `tests/test_introspect.py`
- Verify: `tests/test_output_paths.py`
- Verify: `tests/test_target_scoped_outputs.py`

**Step 1: Run the focused regression tests before making code changes**

Run:
`./.venv/bin/python -m pytest tests/test_self_improve_vision_injection.py tests/test_execution_runtime.py tests/test_introspect.py tests/test_output_paths.py tests/test_target_scoped_outputs.py -q`

Expected:
- PASS
- Confirms the current enum-normalization behavior is protected before lint-driven refactors start.

**Step 2: Save the current pylint output for comparison**

Run:
`./.venv/bin/python -m pylint src/dialectic/vision.py src/dialectic/knowledge.py src/dialectic/output_paths.py src/dialectic/introspect.py src/execution/runtime.py tests/test_self_improve_vision_injection.py --score=n`

Expected current issues:
- `src/execution/runtime.py`: missing module docstring, missing function docstring, too-many-arguments, too-many-locals, missing final newline
- `tests/test_self_improve_vision_injection.py`: import-outside-toplevel, line-too-long, too-few-public-methods

---

### Task 2: Clean up the regression test file first

**Files:**
- Modify: `tests/test_self_improve_vision_injection.py`

**Step 1: Move safe imports to module scope**

Make these changes:
- Move `import inspect` to module scope.
- Move `from execution import runtime as execution_runtime` to module scope if it does not reintroduce the duplicate-import tooling issue.
- Keep the legacy `src.*` compatibility probe tightly scoped.

**Step 2: Replace method-local imports with module-level references**

Examples of target shape:

```python
import inspect

from execution import runtime as execution_runtime


def test_self_improve_uses_self_vision_context():
		self_improve = __import__("main", fromlist=["self_improve"]).self_improve
		source = inspect.getsource(self_improve)
		...
```

**Step 3: Remove the `too-few-public-methods` warning**

Prefer converting the single-method `TestSelfImproveVisionContext` class into a module-level test function.

**Step 4: Wrap the long assertion line**

Replace the single long assertion with a parenthesized multi-line form.

**Step 5: Re-run the test file and pylint on just that file**

Run:
- `./.venv/bin/python -m pytest tests/test_self_improve_vision_injection.py -q`
- `./.venv/bin/python -m pylint tests/test_self_improve_vision_injection.py --score=n`

Expected:
- Test file stays green
- Test-file pylint issues are gone

---

### Task 3: Fix low-risk formatting/documentation issues in execution runtime

**Files:**
- Modify: `src/execution/runtime.py`

**Step 1: Add the missing module docstring**

Add a short top-level docstring describing the module as the per-task dialectic execution crew builder.

**Step 2: Add/expand docstrings on public helpers**

At minimum:
- `build_task_dialectic_crew`

Keep the docstring concise, describing parameters/behavior rather than implementation trivia.

**Step 3: Ensure file formatting is clean**

Add the missing final newline and keep the file Ruff-clean.

**Step 4: Re-run focused checks**

Run:
- `./.venv/bin/python -m ruff check src/execution/runtime.py`
- `./.venv/bin/python -m pylint src/execution/runtime.py --score=n`

Expected:
- Formatting/docstring complaints removed
- Only complexity/signature warnings may remain

---

### Task 4: Reduce `too-many-locals` in `build_task_dialectic_crew`

**Files:**
- Modify: `src/execution/runtime.py`
- Verify: `tests/test_execution_runtime.py`

**Step 1: Extract helper(s) that shrink local state**

Preferred extractions:
- `_build_runtime_placeholders(...) -> dict[str, Any]`
- `_build_runtime_agents(vision_context: VisionContext) -> tuple[...] | dict[...]`
- `_build_runtime_tasks(task_templates, placeholders, agents) -> list[Task]`
- `_build_runtime_knowledge_sources(vision_context: VisionContext) -> list[Any]`

The goal is to reduce the local variable count in `build_task_dialectic_crew` without changing externally observable behavior.

**Step 2: Keep the public function signature stable unless there is a compelling reason to change it**

This function is part of a runtime surface used by task orchestration. Avoid unnecessary call-site churn.

**Step 3: Re-run focused tests**

Run:
- `./.venv/bin/python -m pytest tests/test_execution_runtime.py tests/test_self_improve_vision_injection.py -q`
- `./.venv/bin/python -m pylint src/execution/runtime.py --score=n`

Expected:
- `too-many-locals` resolved or substantially reduced
- runtime behavior unchanged

---

### Task 5: Decide how to handle `too-many-arguments`

**Files:**
- Modify: `src/execution/runtime.py`

**Decision point:**

There are two acceptable directions; choose the smallest safe one.

**Option A — Preferred if call sites are few and internal:**
- Introduce a small typed value object (for example a frozen dataclass) for the task-build inputs.
- Update callers and tests.

**Option B — Preferred if the function is a stable public integration seam:**
- Keep the current explicit signature.
- Add a narrowly scoped local pylint disable on `build_task_dialectic_crew` with a short justification comment explaining that the explicit keyword-only signature is intentional for readability and orchestration-call clarity.

**Important:**
- Do **not** add broad file-level disables for design warnings.
- Do **not** suppress both `too-many-arguments` and `too-many-locals` if refactoring can remove one of them.

**Step 1: Implement the chosen option**

**Step 2: Re-run runtime verification**

Run:
- `./.venv/bin/python -m pytest tests/test_execution_runtime.py tests/test_self_improve_vision_injection.py -q`
- `./.venv/bin/python -m ruff check src/execution/runtime.py`
- `./.venv/bin/python -m pylint src/execution/runtime.py --score=n`

Expected:
- No remaining pylint findings in `src/execution/runtime.py`
- No regression in task-crew construction tests

---

### Task 6: Final focused verification

**Files:**
- Verify: `src/dialectic/vision.py`
- Verify: `src/dialectic/knowledge.py`
- Verify: `src/dialectic/output_paths.py`
- Verify: `src/dialectic/introspect.py`
- Verify: `src/execution/runtime.py`
- Verify: `tests/test_self_improve_vision_injection.py`

**Step 1: Run the focused test slice**

Run:
`./.venv/bin/python -m pytest tests/test_self_improve_vision_injection.py tests/test_execution_runtime.py tests/test_introspect.py tests/test_output_paths.py tests/test_target_scoped_outputs.py -q`

**Step 2: Run static checks on touched files**

Run:
- `./.venv/bin/python -m ruff check src/dialectic/vision.py src/dialectic/knowledge.py src/dialectic/output_paths.py src/dialectic/introspect.py src/execution/runtime.py tests/test_self_improve_vision_injection.py`
- `MYPYPATH=src ./.venv/bin/python -m mypy --explicit-package-bases src/dialectic/vision.py src/dialectic/knowledge.py src/dialectic/output_paths.py src/dialectic/introspect.py src/execution/runtime.py`
- `PYTHONPATH=tests ./.venv/bin/python -m mypy --disable-error-code import-untyped tests/test_self_improve_vision_injection.py`
- `./.venv/bin/python -m pylint src/dialectic/vision.py src/dialectic/knowledge.py src/dialectic/output_paths.py src/dialectic/introspect.py src/execution/runtime.py tests/test_self_improve_vision_injection.py --score=n`

**Step 3: Commit**

Suggested commit message:

`chore(lint): resolve focused pylint findings`

---

## Notes for the implementer

- The recent bug fix established that `VisionContext` values may arrive from both canonical and legacy import surfaces. Do not regress that behavior while cleaning lint issues.
- Prefer canonical imports in tests unless the test is explicitly verifying legacy import-surface compatibility.
- Avoid using dynamic imports as a blanket lint workaround; they should only remain where they are deliberately guarding compatibility behavior.
