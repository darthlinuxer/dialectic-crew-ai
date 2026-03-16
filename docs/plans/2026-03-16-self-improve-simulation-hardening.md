## Plan: Self-improve simulation hardening

Tighten `self-improve --simulate` so it behaves like a durable dry run: remove the unnecessary resume assert by using explicit control-flow narrowing, persist simulation artifacts/logs under `.dialectic/self_improve/` instead of a disposable temp root, restore CrewAI logfile visibility after PRD generation by rehoming/reconfiguring logging inside the simulation environment, and add limited automatic execution-stage retries for logical story failures during simulation only. Keep branch isolation and non-destructive simulation guarantees intact, and avoid leaking simulation logging configuration back into the parent runtime.

Recommended repo plan path: `docs/plans/2026-03-16-self-improve-simulation-hardening.md`.

**Steps**
1. Confirm the public/runtime contract before changing behavior by tracing `run_self_improve()` through `src/main/self_improve/internal/orchestrator.py`, `src/main/self_improve/persistence.py`, `src/main/self_improve/paths.py`, `src/dialectic/output_paths.py`, and `src/dialectic/crew_verbose_config.py`; note which simulation expectations in `tests/test_self_improve.py` currently assume temp-runtime artifact paths and which logging paths depend on `DIALECTIC_LOG_DIR` versus explicit `CREWAI_OUTPUT_LOG_FILE`. This step blocks all others.
2. Refactor resume handling in `run_self_improve()` to remove `assert resume_cycle_id is not None` and rely on explicit branching or a small typed helper so runtime behavior is unchanged while type narrowing remains clear. At the same time, add a short code comment or docstring note explaining why `simulate` and `resume` remain mutually exclusive. Add/adjust focused tests around resume semantics rather than keeping an assertion as the contract. *Depends on 1.*
3. Redesign simulation artifact storage so simulated PRD/plan/execution outputs land under `.dialectic/self_improve/` while simulation remains non-destructive. Recommended layout: keep cycle snapshots at `.dialectic/self_improve/<cycle_id>.json`, add a simulation runtime root such as `.dialectic/self_improve/simulations/<cycle_id>/`, and let `prd_output/` / `exec_output/` resolve beneath that root via `DIALECTIC_RUNTIME_ROOT`. Update the simulation context manager in `src/main/self_improve/internal/orchestrator.py` to create a persistent per-cycle directory instead of `TemporaryDirectory`, while preserving isolated flow DB, metrics DB, and pycache state there. Decide whether a lightweight manifest/retention marker should also live there so follow-up cleanup tooling has something stable to inspect. *Depends on 1; parallel with 2 after discovery is complete.*
4. Update artifact/state helpers and printed simulation reporting to surface the new persistent paths consistently. Ensure `record_prd_artifacts()`, `record_plan_artifacts()`, `record_execution_artifacts()`, resume summaries, and the simulation report all reflect the `.dialectic/self_improve/`-scoped locations, and verify that printed artifact paths remain valid after the simulation context exits. Adjust tests that currently hard-code temp runtime paths. *Depends on 3.*
5. Fix CrewAI/logfile visibility during simulation by aligning simulation logging with the persistent runtime root: set `DIALECTIC_LOG_DIR` inside the simulation environment to the per-cycle simulation directory, decide how to handle user-supplied `CREWAI_OUTPUT_LOG_FILE` (recommended: preserve explicit user paths, only rehome the default path), and force logging reconfiguration after entering that environment so default log paths move with the new root. Add a matching restoration step after the simulation context exits so later logs in the same Python process do not keep writing into the simulation directory. Review `src/dialectic/crewai_runtime.py` and `src/dialectic/app_logging.py` so verbose crew output continues to flow into the expected logfile after PRD generation and summarization remains resilient when the file is missing or rotated. *Depends on 3; can be implemented in parallel with 4 if path decisions are already coded.*
6. Add limited automatic execution-stage retries for simulation-only logical failures. Introduce an explicit retry helper and a dedicated config constant in `src/main/self_improve/paths.py` (for example `DEFAULT_SELF_IMPROVE_EXECUTION_RETRIES`) so the retry count is named, testable, and easy to expose later. The helper should retry the full execution stage a small number of times when `exec_result["overall_success"]` is false, not just when exceptions look transient; it should persist attempt metadata and print clear retry/abort messages so users can see each retry and the final failure reason. Keep non-simulated cycles on the current fail-fast behavior unless there is an explicit repo decision to broaden the scope later. *Depends on 1; can begin after 2, but final wiring depends on 4 so persisted state stays coherent.*
7. Extend regression coverage for the new contract in `tests/test_self_improve.py` and related tests: remove the temporary-path assumptions, verify simulation artifacts/logs persist under `.dialectic/self_improve/` after the context exits, verify logging is reconfigured to the simulation log dir and then restored afterward, verify explicit `CREWAI_OUTPUT_LOG_FILE` behavior stays intentional, verify resume behavior still works after removing the assert, and verify simulation execution retries stop after the configured limit and preserve failure details when all attempts fail. *Depends on 2, 4, 5, and 6.*
8. Run focused verification on the touched surfaces first, then the relevant static analysis for touched files. At minimum: self-improve tests, crew verbose/logging tests, and targeted lint/type checks on the changed modules/tests. If package/import boundaries move, include Pyright and pylint on those files as well. *Depends on 7.*

**Relevant files**
- `/home/darthlinuxer/dialectic-crew-ai/src/main/self_improve/internal/orchestrator.py` — main simulation flow, resume branch, runtime environment, execution-stage failure handling, simulation report, and logging reconfiguration/restore points.
- `/home/darthlinuxer/dialectic-crew-ai/src/main/self_improve/persistence.py` — snapshot path resolution and artifact metadata persistence used by resume/reporting.
- `/home/darthlinuxer/dialectic-crew-ai/src/main/self_improve/paths.py` — simulation/runtime env constants and the new named default for logical execution retries.
- `/home/darthlinuxer/dialectic-crew-ai/src/main/self_improve/llm_retries.py` — existing transient-only retry pattern to mirror or keep separate from logical execution retries.
- `/home/darthlinuxer/dialectic-crew-ai/src/dialectic/output_paths.py` — centralized PRD/execution artifact root resolution via `DIALECTIC_RUNTIME_ROOT`.
- `/home/darthlinuxer/dialectic-crew-ai/src/dialectic/crew_verbose_config.py` — decides whether CrewAI uses `DIALECTIC_LOG_DIR` or an explicit `CREWAI_OUTPUT_LOG_FILE` path.
- `/home/darthlinuxer/dialectic-crew-ai/src/dialectic/app_logging.py` — logging config, forced reconfiguration behavior, and post-simulation restoration.
- `/home/darthlinuxer/dialectic-crew-ai/src/dialectic/crewai_runtime.py` — verbose log capture/summarization path that can go silent if logging/file paths drift.
- `/home/darthlinuxer/dialectic-crew-ai/tests/test_self_improve.py` — existing simulation, resume, and transient retry coverage; primary regression file to update.
- `/home/darthlinuxer/dialectic-crew-ai/tests/test_self_improve_lineage.py` — resume/reuse expectations after failed execution.
- `/home/darthlinuxer/dialectic-crew-ai/tests/test_crew_verbose_config.py` — expected logfile path behavior when verbose mode is enabled.
- `/home/darthlinuxer/dialectic-crew-ai/tests/test_app_logging.py` — forced reconfiguration, default-vs-explicit log path behavior, and log-dir path assertions.

**Verification**
1. Update/add focused tests for simulation artifact persistence, valid printed artifact paths after context exit, logging reconfiguration and restoration, explicit-logfile behavior, resume-without-assert behavior, and simulation execution retries.
2. Run `pytest` on the touched suites: `tests/test_self_improve.py`, `tests/test_self_improve_lineage.py`, `tests/test_crew_verbose_config.py`, and `tests/test_app_logging.py`.
3. Run `ruff check` on the touched source and test files.
4. Run focused `mypy` with `MYPYPATH=src` and `--explicit-package-bases` for the modified source files; run the test-package mypy command if test typing changes warrant it.
5. If logging/import surfaces are adjusted materially, run focused `pyright --project pyrightconfig.json` and `pylint` on the touched Python files.
6. Manually exercise `self-improve --simulate` once in a clean worktree and confirm: artifacts remain under `.dialectic/self_improve/`, CrewAI verbose output continues into the expected logfile after PRD generation, a failed execution shows bounded retry attempts before the final abort, and subsequent non-simulation logging in the same process writes back to the normal log destination.

**Decisions**
- Remove the `assert resume_cycle_id is not None` from production control flow; preserve the safety/typing guarantee with explicit code structure, not a runtime assert.
- For simulation, persist artifacts under `.dialectic/self_improve/` rather than `src/main/self_improve/`; this keeps runtime outputs out of the source tree while matching your persistence goal.
- Restrict the new automatic logical-execution retry behavior to `--simulate` for now so dry runs become more resilient without changing the behavior of real self-improve cycles.
- Preserve current non-destructive guarantees for simulation: no commit, no PR creation, no roadmap mutation, and disposable branch cleanup.
- Preserve explicit user logfile overrides unless there is a deliberate product decision that simulation must always override them.

**Further Considerations**
1. If you later want the same logical execution retries for real self-improve cycles, promote the retry count to a documented CLI/env option instead of keeping it simulation-only.
2. Consider exposing the simulation artifact directory in the CLI summary so users can immediately inspect PRD/plan/execution outputs and logs without hunting through `.dialectic/`.
3. If persistent simulation runs accumulate quickly, add a follow-up cleanup/list command for `.dialectic/self_improve/simulations/` rather than reverting to temp directories.

**Execution checklist**
- [ ] Phase 1 — Control flow and config seams
  - Remove the resume `assert` via explicit branching or a typed helper.
  - Add a named default/config seam for simulation execution retries in `src/main/self_improve/paths.py`.
  - Add a short explanatory note for why `--simulate` cannot be combined with `--resume`.
- [ ] Phase 2 — Durable simulation runtime
  - Replace the temporary simulation runtime root with a persistent per-cycle directory under `.dialectic/self_improve/simulations/<cycle_id>/`.
  - Keep flow DB, metrics DB, state, and pycache isolated inside that runtime.
  - Ensure the printed simulation artifact paths remain valid after the command exits.
- [ ] Phase 3 — Logging continuity
  - Rehome default simulation logs via `DIALECTIC_LOG_DIR`.
  - Preserve explicit `CREWAI_OUTPUT_LOG_FILE` unless intentionally overriding it.
  - Force logging reconfiguration on entry and restore normal logging on exit.
  - Confirm CrewAI verbose summaries still work after PRD generation.
- [ ] Phase 4 — Simulation execution resilience
  - Add bounded retries for logical execution failures in simulation only.
  - Persist retry attempt metadata and print each retry reason clearly.
  - Keep real non-simulated self-improve cycles fail-fast.
- [ ] Phase 5 — Regression coverage
  - Update simulation-path tests to assert `.dialectic/self_improve/` persistence.
  - Add tests for logging reconfigure/restore behavior.
  - Add tests for explicit logfile override behavior.
  - Add tests for retry limit success/failure behavior.
- [ ] Phase 6 — Verification
  - Run focused `pytest` for self-improve and logging suites.
  - Run focused `ruff`, `mypy`, and, if needed, `pyright`/`pylint` on touched files.
  - Manually run `self-improve --simulate` once in a clean worktree to confirm artifact persistence, logging continuity, and bounded retry behavior.
