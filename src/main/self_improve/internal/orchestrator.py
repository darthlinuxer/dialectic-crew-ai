"""
Internal self-improvement orchestrator implementation.

The public package surface lives at `src/main/self_improve/` and forwards into
this module so callers keep a small, stable import surface while the internals
remain decomposable.
"""

# pylint: disable=too-many-locals,too-many-return-statements,too-many-branches
# pylint: disable=too-many-statements,too-many-nested-blocks,too-many-lines

from __future__ import annotations

import json
import logging
import os
import re
import sys
from contextlib import contextmanager, nullcontext
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
from typing import Literal

from dialectic.app_logging import configure_application_logging
from dialectic.hooks import HookScope
from dialectic.introspect import run_introspection
from dialectic.metrics import MetricsStore, emit, get_metrics_store
from dialectic.prioritize import dialectic_prioritize
from dialectic.vision import VisionContext, resolve_project_root
from schemas import ImprovementOpportunity, IntrospectionReport, SelfImprovementRecord

from ..code_structure import print_structure_validation_result, validate_code_structure
from ..git_helpers import (
    dirty_worktree_guidance,
    git_branch_create,
    git_branch_create_from_head,
    git_branch_exists,
    git_checkout_branch,
    git_clean_untracked,
    git_commit_all,
    git_current_branch,
    git_delete_branch,
    git_discard_branch,
    git_has_commits_ahead,
    git_reset_hard_head,
    git_stash_worktree,
    git_worktree_clean,
    recover_stale_self_improve_worktree,
)
from ..llm_retries import _run_with_transient_llm_retries
from ..metrics import metrics_stable
from ..paths import (
    FLOW_DB_ENV_VAR,
    METRICS_DB_ENV_VAR,
    MIN_METRIC_RETENTION,
    PROTECTED_PATHS,
    RUNTIME_ROOT_ENV_VAR,
    DEFAULT_SELF_IMPROVE_EXECUTION_RETRIES,
    SELF_IMPROVE_ROADMAP_PATH,
    SELF_IMPROVE_SIMULATIONS_DIR,
    SELF_IMPROVE_STATE_DIR,
    SELF_IMPROVE_STATE_DIR_ENV_VAR,
    SIMULATED_CYCLE_RESULT,
    SIMULATION_BRANCH_NAME,
)
from ..persistence import (
    list_resumable_cycles,
    load_self_improve_record,
    record_execution_artifacts,
    record_plan_artifacts,
    record_prd_artifacts,
    require_artifact,
    resolve_resume_context,
    save_self_improve_record,
    self_improve_record_path,
    summarize_resume_state,
)
from ..pr_builder import build_pr_body, create_pr, print_report
from ..quality_gate import print_quality_gate_result, run_quality_gate
from ..runtime import (
    _command_available,
    _configure_crewai_runtime,
    _run_cmd,
    _self_improve_prd_min_score,
    _self_improve_test_timeout,
)
from ..test_runner import emit_test_failure_details, pytest_command, snapshot_tests

logger = logging.getLogger(__name__)

_ArtifactKind = Literal["prd", "plan"]


def _kickoff_prd_flow(
    flow,
    *,
    flow_id: str,
    feature_request: str,
) -> None:
    flow.kickoff(
        inputs={
            "id": flow_id,
            "feature_objective": feature_request,
            "vision_context": VisionContext.SELF.value,
        }
    )


def _run_planning_stage(run_user_story_planning_fn, *, prd_path: str) -> dict:
    return run_user_story_planning_fn(
        prd_path=prd_path,
        user_story_ref=None,
        vision_context=VisionContext.SELF,
    )


def _run_execution_stage(
    run_dialectic_execution_fn,
    *,
    plan_path: str,
    resume_run_id: str | None,
) -> dict:
    return run_dialectic_execution_fn(
        plan_path=plan_path,
        vision_context=VisionContext.SELF,
        resume_run_id=resume_run_id,
    )


def _load_starting_artifact(artifact_path: str) -> tuple[_ArtifactKind, str]:
    path = Path(artifact_path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"Self-improve artifact not found: {path}")

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Self-improve artifact is not valid JSON: {path}") from exc

    if not isinstance(payload, dict):
        raise ValueError(f"Self-improve artifact must contain a JSON object: {path}")

    if isinstance(payload.get("user_stories"), list):
        return "prd", str(path)
    if isinstance(payload.get("tasks"), list) or isinstance(
        payload.get("implementation_tasks"),
        list,
    ):
        return "plan", str(path)

    raise ValueError(
        "Self-improve artifact must look like an exported PRD (user_stories) "
        f"or execution plan (tasks): {path}"
    )


def _make_artifact_opportunity(
    kind: _ArtifactKind,
    artifact_path: str,
) -> ImprovementOpportunity:
    label = "PRD" if kind == "prd" else "plan"
    return ImprovementOpportunity(
        id=f"artifact:{kind}",
        category="code_health",
        title=f"Continue self-improve from supplied {label}",
        description=(
            "Resume self-improve from the supplied "
            f"{label.lower()} artifact: {artifact_path}"
        ),
        evidence=[artifact_path],
        estimated_impact="medium",
    )


def _collect_touched_files(project_root: Path) -> list[str]:
    if not _command_available("git") or not (project_root / ".git").exists():
        return []

    result = _run_cmd(["git", "status", "--short"], cwd=project_root, timeout=30)
    if result.returncode != 0:
        return []

    touched: list[str] = []
    for line in result.stdout.splitlines():
        entry = line[3:].strip() if len(line) > 3 else line.strip()
        if entry:
            touched.append(entry)
    return touched


def _print_simulation_report(
    record: SelfImprovementRecord,
    selected: list[ImprovementOpportunity],
    project_root: Path,
    *,
    artifact_path: str | None = None,
) -> None:
    print("\nSimulation report")
    print(f"{'=' * 60}")
    if selected:
        print(f"Selected objective: {selected[0].title}")
    if artifact_path:
        print(f"Starting artifact: {artifact_path}")

    print("\nArtifacts created or reused:")
    artifacts = [
        ("PRD JSON", record.prd_path_json),
        ("PRD Markdown", record.prd_path_md),
        ("Plan JSON", record.plan_path_json),
        ("Plan Markdown", record.plan_path_md),
        ("Execution output", record.execution_output_path),
        ("Execution report", record.execution_report_path),
    ]
    for label, value in artifacts:
        print(f"  - {label}: {value or 'n/a'}")

    touched_files = _collect_touched_files(project_root)
    print("\nFiles touched:")
    if touched_files:
        for file_path in touched_files[:20]:
            print(f"  - {file_path}")
        if len(touched_files) > 20:
            print(f"  - ... and {len(touched_files) - 20} more")
    else:
        print("  - unavailable (git status not accessible in this runtime)")

    story_status = record.execution_story_status or "unknown"
    objective_achieved = story_status == "completed" and record.tests_passed
    print("\nOutcome:")
    print(f"  - Execution story status: {story_status}")
    print(f"  - Tests passed: {'yes' if record.tests_passed else 'no'}")
    print(f"  - Metrics stable: {'yes' if record.metrics_stable else 'no'}")
    print(
        "  - Objective achieved: "
        f"{'yes' if objective_achieved else 'no'}"
    )
    print(f"{'=' * 60}")


def _snapshot_tests(project_root: Path, timeout: int | None = None) -> dict:
    return snapshot_tests(
        project_root,
        timeout=timeout,
        timeout_resolver=_self_improve_test_timeout,
        pytest_command_fn=_pytest_command,
        run_cmd_fn=_run_cmd,
    )


def _pytest_command() -> list[str]:
    return pytest_command(
        command_available_fn=_command_available,
        python_executable=sys.executable,
    )


def _emit_test_failure_details(snapshot: dict, prefix: str = "  ") -> None:
    emit_test_failure_details(snapshot, prefix=prefix)


def _metrics_stable(
    store: MetricsStore,
    baseline: dict,
    retention: float = MIN_METRIC_RETENTION,
) -> tuple[bool, str]:
    return metrics_stable(store, baseline, retention)


def _git_branch_create(branch: str, cwd: Path) -> bool:
    return git_branch_create(branch, cwd, run_cmd_fn=_run_cmd)


def _git_branch_exists(branch: str, cwd: Path) -> bool:
    return git_branch_exists(branch, cwd, run_cmd_fn=_run_cmd)


def _git_delete_branch(branch: str, cwd: Path) -> tuple[bool, str]:
    return git_delete_branch(branch, cwd, run_cmd_fn=_run_cmd)


def _git_branch_create_from_head(branch: str, cwd: Path) -> tuple[bool, str]:
    return git_branch_create_from_head(branch, cwd, run_cmd_fn=_run_cmd)


def _git_discard_branch(branch: str, cwd: Path) -> None:
    git_discard_branch(branch, cwd, run_cmd_fn=_run_cmd)


def _git_reset_hard_head(cwd: Path) -> tuple[bool, str]:
    return git_reset_hard_head(cwd, run_cmd_fn=_run_cmd)


def _git_clean_untracked(cwd: Path) -> tuple[bool, str]:
    return git_clean_untracked(cwd, run_cmd_fn=_run_cmd)


def _git_current_branch(cwd: Path) -> str:
    return git_current_branch(cwd, run_cmd_fn=_run_cmd)


def _git_checkout_branch(branch: str, cwd: Path) -> tuple[bool, str]:
    return git_checkout_branch(branch, cwd, run_cmd_fn=_run_cmd)


def _recover_stale_self_improve_worktree(cwd: Path) -> tuple[bool, str]:
    return recover_stale_self_improve_worktree(
        cwd,
        git_current_branch_fn=_git_current_branch,
        run_cmd_fn=_run_cmd,
    )


def _git_stash_worktree(cwd: Path, message: str) -> tuple[bool, str]:
    return git_stash_worktree(cwd, message, run_cmd_fn=_run_cmd)


def _dirty_worktree_guidance(cwd: Path, worktree_reason: str) -> str:
    return dirty_worktree_guidance(
        cwd,
        worktree_reason,
        git_current_branch_fn=_git_current_branch,
    )


def _git_worktree_clean(cwd: Path) -> tuple[bool, str]:
    return git_worktree_clean(cwd, run_cmd_fn=_run_cmd)


def _git_commit_all(cwd: Path, message: str) -> tuple[bool, str]:
    return git_commit_all(cwd, message, run_cmd_fn=_run_cmd)


def _git_has_commits_ahead(cwd: Path, base_branch: str = "main") -> tuple[bool, str]:
    return git_has_commits_ahead(cwd, base_branch=base_branch, run_cmd_fn=_run_cmd)


def _create_pr(branch: str, title: str, body: str, cwd: Path) -> str | None:
    return create_pr(
        branch,
        title,
        body,
        cwd,
        command_available_fn=_command_available,
        run_cmd_fn=_run_cmd,
        logger=logger,
    )


def _record_prd_artifacts(record: SelfImprovementRecord, flow) -> str:
    return record_prd_artifacts(record, flow)


def _record_plan_artifacts(record: SelfImprovementRecord, plan_result: dict) -> str:
    return record_plan_artifacts(record, plan_result)


def _record_execution_artifacts(record: SelfImprovementRecord, exec_result: dict) -> None:
    record_execution_artifacts(record, exec_result)


def _self_improve_record_path(project_root: Path, cycle_id: str) -> Path:
    return self_improve_record_path(
        project_root,
        cycle_id,
        state_dir=SELF_IMPROVE_STATE_DIR,
    )


def _save_self_improve_record(project_root: Path, record: SelfImprovementRecord) -> None:
    save_self_improve_record(
        project_root,
        record,
        state_dir=SELF_IMPROVE_STATE_DIR,
    )


def _load_self_improve_record(project_root: Path, cycle_id: str) -> SelfImprovementRecord:
    return load_self_improve_record(
        project_root,
        cycle_id,
        state_dir=SELF_IMPROVE_STATE_DIR,
    )


def _resolve_resume_context(
    record: SelfImprovementRecord,
) -> tuple[list[ImprovementOpportunity], dict]:
    return resolve_resume_context(record)


def _summarize_resume_state(
    record: SelfImprovementRecord,
    last_failure_reason: str = "",
) -> dict[str, str | list[str]]:
    return summarize_resume_state(record, last_failure_reason)


def _list_resumable_cycles(project_root: Path) -> list[dict[str, str]]:
    return list_resumable_cycles(project_root, state_dir=SELF_IMPROVE_STATE_DIR)


def _require_artifact(path: str, failure_reason: str) -> str:
    return require_artifact(path, failure_reason, error_cls=_CycleAbort)


def _mark_roadmap_items_completed(
    project_root: Path,
    opportunities: list[ImprovementOpportunity],
) -> list[str]:
    roadmap_path = project_root / SELF_IMPROVE_ROADMAP_PATH
    if not roadmap_path.exists():
        return []

    targets = {
        (opportunity.description or opportunity.title).strip()
        for opportunity in opportunities
        if (opportunity.description or opportunity.title).strip()
    }
    if not targets:
        return []

    updated_labels: list[str] = []
    lines = roadmap_path.read_text(encoding="utf-8").splitlines()
    updated_lines: list[str] = []
    pattern = re.compile(r"^(?P<prefix>\s*-\s*)\[ \](?P<suffix>\s+)(?P<label>.+?)\s*$")

    for line in lines:
        match = pattern.match(line)
        if match is None:
            updated_lines.append(line)
            continue

        label = match.group("label").strip()
        if label in targets:
            updated_lines.append(
                f"{match.group('prefix')}[x]{match.group('suffix')}{label}"
            )
            updated_labels.append(label)
            continue

        updated_lines.append(line)

    if updated_labels:
        roadmap_path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")
    return updated_labels


@contextmanager
def _temporary_environment(overrides: dict[str, str]):
    previous_values = {key: os.environ.get(key) for key in overrides}
    try:
        for key, value in overrides.items():
            os.environ[key] = value
        yield
    finally:
        for key, previous in previous_values.items():
            if previous is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = previous


def _simulation_runtime_root(project_root: Path, cycle_id: str) -> Path:
    return project_root / SELF_IMPROVE_SIMULATIONS_DIR / cycle_id


def _self_improve_execution_retries() -> int:
    raw_value = os.getenv("SELF_IMPROVE_EXECUTION_RETRIES")
    if raw_value is None or raw_value == "":
        return DEFAULT_SELF_IMPROVE_EXECUTION_RETRIES
    try:
        retries = int(raw_value)
    except ValueError:
        logger.warning(
            "Invalid SELF_IMPROVE_EXECUTION_RETRIES=%r; using default %s",
            raw_value,
            DEFAULT_SELF_IMPROVE_EXECUTION_RETRIES,
        )
        return DEFAULT_SELF_IMPROVE_EXECUTION_RETRIES
    if retries < 0:
        logger.warning(
            "Negative SELF_IMPROVE_EXECUTION_RETRIES=%r; using default %s",
            raw_value,
            DEFAULT_SELF_IMPROVE_EXECUTION_RETRIES,
        )
        return DEFAULT_SELF_IMPROVE_EXECUTION_RETRIES
    return retries


@contextmanager
def _simulation_runtime_environment(project_root: Path, cycle_id: str):
    runtime_root = _simulation_runtime_root(project_root, cycle_id)
    runtime_root.mkdir(parents=True, exist_ok=True)
    pytest_addopts_parts = [os.getenv("PYTEST_ADDOPTS", "").strip(), "-p no:cacheprovider"]
    pytest_addopts = " ".join(part for part in pytest_addopts_parts if part).strip()
    overrides = {
        RUNTIME_ROOT_ENV_VAR: str(runtime_root),
        FLOW_DB_ENV_VAR: str(runtime_root / "flows.db"),
        METRICS_DB_ENV_VAR: str(runtime_root / "metrics.db"),
        SELF_IMPROVE_STATE_DIR_ENV_VAR: str(project_root / SELF_IMPROVE_STATE_DIR),
        "DIALECTIC_LOG_DIR": str(runtime_root / "logs"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPYCACHEPREFIX": str(runtime_root / ".pycache"),
        "PYTEST_ADDOPTS": pytest_addopts,
    }
    try:
        with _temporary_environment(overrides):
            configure_application_logging(force=True)
            yield runtime_root
    finally:
        configure_application_logging(force=True)


def _record_execution_attempt(
    record: SelfImprovementRecord,
    exec_result: dict,
    *,
    attempt: int,
    failure_reason: str | None = None,
) -> None:
    _record_execution_artifacts(record, exec_result)
    record.execution_attempted = True
    record.execution_attempt_count = max(record.execution_attempt_count, attempt)
    if failure_reason:
        record.execution_failure_reasons.append(failure_reason)


def _execute_plan_with_retries(  # pylint: disable=too-many-arguments
    run_dialectic_execution_fn,
    *,
    plan_path: str,
    resume_run_id: str | None,
    simulate: bool,
    record: SelfImprovementRecord,
    project_root: Path,
) -> dict:
    """Run execution with bounded logical retries for simulation-only dry runs."""
    max_attempts = (_self_improve_execution_retries() + 1) if simulate else 1

    for attempt in range(1, max_attempts + 1):
        exec_result = _run_with_transient_llm_retries(
            "execution",
            partial(
                _run_execution_stage,
                run_dialectic_execution_fn,
                plan_path=plan_path,
                resume_run_id=resume_run_id,
            ),
        )
        failure_reason: str | None = None
        if not exec_result.get("overall_success"):
            failure_reason = (
                "Execution failed: "
                f"{exec_result.get('story_status', 'unknown')}"
            )
        _record_execution_attempt(
            record,
            exec_result,
            attempt=attempt,
            failure_reason=failure_reason,
        )
        _save_self_improve_record(project_root, record)
        if failure_reason is None:
            return exec_result
        if attempt >= max_attempts:
            record.failure_reason = failure_reason
            return exec_result

        print(
            "  Execution attempt "
            f"{attempt}/{max_attempts} failed: {exec_result.get('story_status', 'unknown')}"
        )
        print("  Retrying execution from the approved plan...")
        resume_run_id = None

    raise RuntimeError("Execution retry loop exited unexpectedly")


def _run_git_preflight(
    project_root: Path,
    *,
    cycle_id: str,
    stash_dirty: bool,
    step_label: str,
) -> str | None:
    print(step_label)
    if not _command_available("git"):
        return (
            "Git is required for self-improve branch isolation "
            "but was not found on PATH"
        )

    clean_worktree, worktree_reason = _git_worktree_clean(project_root)
    if not clean_worktree:
        recovered, recovery_reason = _recover_stale_self_improve_worktree(project_root)
        if recovered:
            print(f"  Recovered stale run: {recovery_reason}")
            clean_worktree, worktree_reason = _git_worktree_clean(project_root)
        if not clean_worktree:
            if stash_dirty:
                stashed, stash_reason = _git_stash_worktree(
                    project_root,
                    f"self-improve-preflight/{cycle_id}",
                )
                if stashed:
                    print(f"  Stashed current branch changes: {stash_reason}")
                    clean_worktree, worktree_reason = _git_worktree_clean(project_root)
                else:
                    worktree_reason = f"{worktree_reason}; {stash_reason}"
            if not clean_worktree:
                return _dirty_worktree_guidance(project_root, worktree_reason)

    return None


def _prepare_simulation_branch(project_root: Path) -> tuple[bool, str]:
    current_branch = _git_current_branch(project_root)
    if current_branch == SIMULATION_BRANCH_NAME:
        reset_ok, reset_reason = _git_reset_hard_head(project_root)
        if not reset_ok:
            return False, reset_reason
        clean_ok, clean_reason = _git_clean_untracked(project_root)
        if not clean_ok:
            return False, clean_reason
        _git_discard_branch(SIMULATION_BRANCH_NAME, project_root)
        print("  Discarded currently checked-out simulate branch before recreating it.")
    elif _git_branch_exists(SIMULATION_BRANCH_NAME, project_root):
        deleted, delete_reason = _git_delete_branch(SIMULATION_BRANCH_NAME, project_root)
        if not deleted:
            return False, delete_reason
        print(f"  Deleted previous simulate branch: {delete_reason}")

    if not _git_branch_create(SIMULATION_BRANCH_NAME, project_root):
        return False, f"Failed to create simulate branch {SIMULATION_BRANCH_NAME}"
    return True, SIMULATION_BRANCH_NAME


def _cleanup_simulation_branch(project_root: Path) -> None:
    current_branch = _git_current_branch(project_root)
    if current_branch == SIMULATION_BRANCH_NAME:
        reset_ok, reset_reason = _git_reset_hard_head(project_root)
        if not reset_ok:
            print(f"  WARN: failed to reset simulate branch before cleanup: {reset_reason}")
        clean_ok, clean_reason = _git_clean_untracked(project_root)
        if not clean_ok:
            print(f"  WARN: failed to clean simulate branch before cleanup: {clean_reason}")
        _git_discard_branch(SIMULATION_BRANCH_NAME, project_root)
        return

    if _git_branch_exists(SIMULATION_BRANCH_NAME, project_root):
        deleted, delete_reason = _git_delete_branch(SIMULATION_BRANCH_NAME, project_root)
        if not deleted:
            print(f"  WARN: failed to delete simulate branch: {delete_reason}")


def run_self_improve(  # pylint: disable=too-many-arguments
    max_improvements: int = 1,
    simulate: bool = False,
    stash_dirty: bool = False,
    resume_cycle_id: str | None = None,
    skip_baseline_tests: bool = False,
    *,
    artifact_path: str | None = None,
    next_roadmap_item: bool = False,
) -> SelfImprovementRecord:
    """Run a self-improve cycle, optionally as a non-destructive simulation."""
    if max_improvements != 1:
        raise ValueError(
            "self-improve currently supports exactly one opportunity per cycle"
        )
    # Simulation uses an isolated throwaway branch plus a separate runtime root,
    # so resuming a previous cycle inside that sandbox would be misleading.
    if simulate and resume_cycle_id is not None:
        raise ValueError("self-improve simulation does not support --resume")
    if artifact_path is not None and resume_cycle_id is not None:
        raise ValueError("self-improve does not support using an artifact path with --resume")

    _configure_crewai_runtime()
    project_root = resolve_project_root()
    is_resume = resume_cycle_id is not None
    supplied_artifact = _load_starting_artifact(artifact_path) if artifact_path else None
    cycle_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    branch_name = SIMULATION_BRANCH_NAME if simulate else ""
    resume_summary: dict[str, str | list[str]] = {}
    simulation_context = (
        _simulation_runtime_environment(project_root, cycle_id)
        if simulate
        else nullcontext()
    )
    simulation_branch_active = False

    with simulation_context:
        store = get_metrics_store()
        if resume_cycle_id is not None:
            record = _load_self_improve_record(project_root, resume_cycle_id)
            cycle_id = record.cycle_id
            branch_name = record.branch_name or f"self-improve/{cycle_id}"
            resume_summary = _summarize_resume_state(record, record.failure_reason)
            record.failure_reason = ""
            record.tests_passed = False
            record.metrics_stable = False
            record.pr_created = False
            record.execution_failure_reasons = list(record.execution_failure_reasons)
            _save_self_improve_record(project_root, record)
        else:
            record = SelfImprovementRecord(
                cycle_id=cycle_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            _save_self_improve_record(project_root, record)

        try:
            if simulate and not is_resume:
                preflight_failure = _run_git_preflight(
                    project_root,
                    cycle_id=cycle_id,
                    stash_dirty=stash_dirty,
                    step_label=(
                        "[simulate preflight] Checking git availability "
                        "and worktree cleanliness..."
                    ),
                )
                if preflight_failure:
                    record.failure_reason = preflight_failure
                    print(f"  ABORT: {record.failure_reason}")
                    _persist_record(store, record)
                    _save_self_improve_record(project_root, record)
                    return record

                print("[simulate preflight] Preparing disposable simulation branch...")
                prepared, prepare_reason = _prepare_simulation_branch(project_root)
                if not prepared:
                    record.failure_reason = prepare_reason
                    print(f"  ABORT: {record.failure_reason}")
                    _persist_record(store, record)
                    _save_self_improve_record(project_root, record)
                    return record
                branch_name = prepare_reason
                record.branch_name = branch_name
                simulation_branch_active = True
                _save_self_improve_record(project_root, record)

            print(f"\n{'='*60}")
            print(f"Self-Improvement Cycle {cycle_id}{' (resume)' if is_resume else ''}")
            print(f"{'='*60}")
            if is_resume:
                print(f"[resume] Last failure: {resume_summary['last_failure']}")
                print(f"[resume] Next stage: {resume_summary['next_stage']}")
                reused_items = resume_summary["reused"]
                if reused_items:
                    print("[resume] Reusing:")
                    for item in reused_items:
                        print(f"  - {item}")

            if not is_resume:
                if skip_baseline_tests:
                    print(
                        "\n[preflight] Skipping baseline tests because "
                        "--skip-baseline-tests was requested."
                    )
                else:
                    print("\n[1/6] Running baseline tests...")
                    baseline_tests = _snapshot_tests(project_root)
                    if not baseline_tests["passed"]:
                        record.failure_reason = "Baseline tests already failing -- aborting"
                        print(f"  ABORT: {record.failure_reason}")
                        _emit_test_failure_details(baseline_tests)
                        _persist_record(store, record)
                        return record

            if not simulate and not is_resume:
                preflight_failure = _run_git_preflight(
                    project_root,
                    cycle_id=cycle_id,
                    stash_dirty=stash_dirty,
                    step_label="[1b/6] Checking git preflight...",
                )
                if preflight_failure:
                    record.failure_reason = preflight_failure
                    print(f"  ABORT: {record.failure_reason}")
                    _persist_record(store, record)
                    return record

            if is_resume:
                selected, baseline_metrics = _resolve_resume_context(record)
                report = IntrospectionReport(
                    timestamp=record.timestamp,
                    opportunities=selected,
                    baseline_metrics=baseline_metrics,
                )
                print(f"[resume] Loaded {len(selected)} saved opportunities.")
            elif supplied_artifact is not None:
                artifact_kind, supplied_artifact_path = supplied_artifact
                selected = [_make_artifact_opportunity(artifact_kind, supplied_artifact_path)]
                report = IntrospectionReport(
                    timestamp=record.timestamp,
                    opportunities=selected,
                    baseline_metrics={},
                )
                record.opportunities_found = len(selected)
                record.selected_opportunities = selected
                record.opportunities_attempted = len(selected)
                branch_name = SIMULATION_BRANCH_NAME if simulate else f"self-improve/{cycle_id}"
                record.branch_name = branch_name
                if artifact_kind == "prd":
                    record.prd_generated = True
                    record.prd_path_json = supplied_artifact_path
                else:
                    record.prd_generated = True
                    record.plan_generated = True
                    record.plan_path_json = supplied_artifact_path
                _save_self_improve_record(project_root, record)
                print(
                    f"[2/6] Using supplied {artifact_kind.upper()} artifact: "
                    f"{supplied_artifact_path}"
                )
            else:
                print("[2/6] Running introspection against SELF_VISION.md + ROADMAP.md...")
                report = run_introspection(store=store, vision_context=VisionContext.SELF)
                record.opportunities_found = len(report.opportunities)
                record.baseline_metrics = dict(report.baseline_metrics)

                if not report.opportunities:
                    record.failure_reason = "No improvement opportunities found"
                    print(f"  {record.failure_reason}")
                    _persist_record(store, record)
                    return record

                print(f"  Found {len(report.opportunities)} opportunities:")
                for opp in report.opportunities[:max_improvements]:
                    print(f"    [{opp.estimated_impact.upper()}] {opp.title}")

                if next_roadmap_item:
                    print(
                        "\n[2b/7] Selecting the next roadmap item without "
                        "dialectic prioritization..."
                    )
                    prioritized = list(report.opportunities)
                else:
                    print("\n[2b/7] Running dialectic prioritization...")
                    try:
                        prioritized = dialectic_prioritize(
                            report.opportunities,
                            vision_context=VisionContext.SELF,
                            max_to_debate=min(len(report.opportunities), 5),
                        )
                    except Exception as e:  # pylint: disable=broad-exception-caught
                        logger.warning(
                            "Dialectic prioritization failed: %s; using impact sort",
                            e,
                        )
                        print(f"  Prioritization failed ({e}); falling back to impact sort.")
                        prioritized = sorted(
                            report.opportunities,
                            key=lambda o: {
                                "high": 0,
                                "medium": 1,
                                "low": 2,
                            }.get(o.estimated_impact, 1),
                        )
                selected = prioritized[:max_improvements]
                record.selected_opportunities = selected
                record.opportunities_attempted = len(selected)
                branch_name = SIMULATION_BRANCH_NAME if simulate else f"self-improve/{cycle_id}"
                record.branch_name = branch_name
                _save_self_improve_record(project_root, record)
            print("  Prioritized order:")
            for i, opp in enumerate(selected, 1):
                print(f"    {i}. [{opp.estimated_impact.upper()}] {opp.title}")

            token_budget = int(os.getenv("SELF_IMPROVE_TOKEN_BUDGET", "500000"))
            max_iterations = int(os.getenv("SELF_IMPROVE_MAX_ITERATIONS", "25"))

            if not is_resume:
                if simulate:
                    print(
                        "\n[3/7] Using previously prepared disposable "
                        f"simulation branch: {branch_name}"
                    )
                else:
                    print(f"\n[3/7] Creating branch: {branch_name}")
                    if not _git_branch_create(branch_name, project_root):
                        record.failure_reason = "Failed to create git branch"
                        print(f"  ABORT: {record.failure_reason}")
                        _persist_record(store, record)
                        return record
            else:
                print(f"\n[resume] Continuing on branch: {branch_name}")
                git_metadata_exists = (project_root / ".git").exists()
                if git_metadata_exists and _command_available("git"):
                    current_branch = _git_current_branch(project_root)
                    if current_branch != branch_name:
                        switched, switch_reason = _git_checkout_branch(branch_name, project_root)
                        if not switched:
                            if current_branch.startswith("self-improve/"):
                                recreated, recreate_reason = _git_branch_create_from_head(
                                    branch_name,
                                    project_root,
                                )
                                if not recreated:
                                    record.failure_reason = (
                                        f"Failed to resume on branch '{branch_name}': "
                                        f"{switch_reason}; "
                                        "also failed to recreate it from "
                                        f"{current_branch}: {recreate_reason}"
                                    )
                                    print(f"  ABORT: {record.failure_reason}")
                                    _persist_record(store, record)
                                    _save_self_improve_record(project_root, record)
                                    return record
                                print(
                                    "  Recreated recorded branch from "
                                    f"{current_branch}: {branch_name}"
                                )
                            else:
                                record.failure_reason = (
                                    f"Failed to resume on branch '{branch_name}': {switch_reason}"
                                )
                                print(f"  ABORT: {record.failure_reason}")
                                _persist_record(store, record)
                                _save_self_improve_record(project_root, record)
                                return record
                        else:
                            print(f"  Resumed on recorded branch: {branch_name}")

            with HookScope(
                token_budget=token_budget,
                max_iterations=max_iterations,
                protected_paths=PROTECTED_PATHS,
                label=f"self-improve/{cycle_id}",
            ) as tracker:
                try:
                    for opp in selected:
                        feature_request = record.feature_request or (
                            f"[Self-Improvement] {opp.title}\n\n"
                            f"Category: {opp.category}\n"
                            f"Description: {opp.description}\n"
                            f"Evidence: {', '.join(opp.evidence)}"
                        )
                        record.feature_request = feature_request
                        _save_self_improve_record(project_root, record)

                        if not record.prd_generated:
                            print(f"\n[4/7] Generating PRD for: {opp.title[:60]}...")
                            if tracker.budget_exceeded:
                                record.failure_reason = (
                                    f"Token budget exceeded before PRD generation "
                                    f"({tracker.total_tokens}/{tracker.budget})"
                                )
                                raise _CycleAbort(record.failure_reason)

                            from dialectic.prd_flow import (  # pylint: disable=import-outside-toplevel
                                DialecticFlow,
                                _get_persistence,
                            )

                            flow = DialecticFlow(persistence=_get_persistence())
                            record.prd_flow_id = record.prd_flow_id or flow.flow_id
                            _save_self_improve_record(project_root, record)

                            _run_with_transient_llm_retries(
                                "PRD generation",
                                partial(
                                    _kickoff_prd_flow,
                                    flow,
                                    flow_id=record.prd_flow_id,
                                    feature_request=feature_request,
                                ),
                            )
                            prd_path = _record_prd_artifacts(record, flow)
                            _save_self_improve_record(project_root, record)

                            prd_min_score = _self_improve_prd_min_score()
                            if (
                                flow.state.quality_score < prd_min_score
                                and not flow.state.consensus_reached
                            ):
                                record.failure_reason = (
                                    f"PRD quality too low: {flow.state.quality_score}"
                                )
                                print(
                                    "  PRD did not reach threshold: "
                                    f"{flow.state.quality_score}/10 "
                                    f"(required {prd_min_score}/10)"
                                )
                                raise _CycleAbort(record.failure_reason)
                            prd_path = _require_artifact(
                                prd_path,
                                "PRD generation did not produce an exported JSON artifact",
                            )
                            record.prd_generated = True
                        else:
                            if record.prd_path_json:
                                prd_path = _require_artifact(
                                    record.prd_path_json,
                                    "PRD generation did not produce an exported JSON artifact",
                                )
                                print(f"\n[resume] Reusing PRD artifact: {prd_path}")
                            else:
                                prd_path = record.plan_path_json
                                print(
                                    "\n[resume] Skipping PRD artifact reuse because "
                                    "execution is starting from a supplied plan."
                                )

                        if tracker.budget_exceeded:
                            record.failure_reason = (
                                f"Token budget exceeded after PRD generation "
                                f"({tracker.total_tokens}/{tracker.budget})"
                            )
                            raise _CycleAbort(record.failure_reason)

                        if not record.plan_generated:
                            print("[5/7] Planning user story execution...")
                            from planning.flow import (  # pylint: disable=import-outside-toplevel
                                run_user_story_planning,
                            )

                            plan_result = _run_with_transient_llm_retries(
                                "planning",
                                partial(
                                    _run_planning_stage,
                                    run_user_story_planning,
                                    prd_path=prd_path,
                                ),
                            )
                            plan_path = _record_plan_artifacts(record, plan_result)
                            _save_self_improve_record(project_root, record)
                            if plan_result["quality_score"] < 7.5:
                                record.failure_reason = (
                                    f"Plan quality too low: {plan_result['quality_score']}"
                                )
                                raise _CycleAbort(record.failure_reason)
                            plan_path = _require_artifact(
                                plan_path,
                                "Planning did not produce an exported artifact",
                            )
                            record.plan_generated = True
                        else:
                            plan_path = _require_artifact(
                                record.plan_path_json,
                                "Planning did not produce an exported artifact",
                            )
                            print(f"[resume] Reusing plan artifact: {plan_path}")

                        if tracker.budget_exceeded:
                            record.failure_reason = (
                                f"Token budget exceeded after planning "
                                f"({tracker.total_tokens}/{tracker.budget})"
                            )
                            raise _CycleAbort(record.failure_reason)

                        needs_execution = (
                            not record.execution_attempted
                            or not record.execution_output_path
                            or not record.execution_report_path
                        )
                        if needs_execution:
                            print("[6/7] Executing plan...")
                            from execution.dialectic_execution import (  # pylint: disable=import-outside-toplevel
                                run_dialectic_execution,
                            )

                            exec_result = _execute_plan_with_retries(
                                run_dialectic_execution,
                                plan_path=plan_path,
                                resume_run_id=record.execution_run_id or None,
                                simulate=simulate,
                                record=record,
                                project_root=project_root,
                            )

                            if not exec_result.get("overall_success"):
                                raise _CycleAbort(record.failure_reason)
                            _require_artifact(
                                record.execution_output_path,
                                "Execution did not produce an exported artifact",
                            )
                            _require_artifact(
                                record.execution_report_path,
                                "Execution report did not produce an exported artifact",
                            )
                        else:
                            print(
                                "[resume] Reusing execution artifacts from run: "
                                f"{record.execution_run_id}"
                            )

                except _CycleAbort as e:
                    print(f"\n  Cycle aborted: {e}")
                    if not record.failure_reason:
                        record.failure_reason = str(e)
                    record.total_tokens = tracker.total_tokens
                    record.estimated_cost = tracker.estimated_cost
                    if not simulate:
                        _git_discard_branch(branch_name, project_root)
                    _persist_record(store, record)
                    _save_self_improve_record(project_root, record)
                    return record
                except Exception as e:  # pylint: disable=broad-exception-caught
                    record.failure_reason = f"Unexpected error: {e}"
                    print(f"\n  Unexpected error: {e}")
                    record.total_tokens = tracker.total_tokens
                    record.estimated_cost = tracker.estimated_cost
                    if not simulate:
                        _git_discard_branch(branch_name, project_root)
                    _persist_record(store, record)
                    _save_self_improve_record(project_root, record)
                    return record

                record.total_tokens = tracker.total_tokens
                record.estimated_cost = tracker.estimated_cost

            print(f"\n  Token usage: {record.total_tokens} tokens, ${record.estimated_cost:.4f}")

            print("\n[7a/9] Validating: running code quality checks...")
            quality_result = run_quality_gate(project_root)
            if not quality_result.passed:
                record.failure_reason = f"Quality gate failed: {quality_result.summary}"
                print(f"  FAIL: {record.failure_reason}")
                print_quality_gate_result(quality_result)
                if not simulate:
                    _git_discard_branch(branch_name, project_root)
                _persist_record(store, record)
                _save_self_improve_record(project_root, record)
                return record
            print(f"  Quality gate passed: {quality_result.summary}")

            print("\n[7b/9] Validating: code structure (SOLID, deep modules)...")
            structure_result = validate_code_structure(project_root, check_all_src=True)
            if not structure_result.passed:
                record.failure_reason = f"Structure validation failed: {structure_result.summary}"
                print(f"  FAIL: {record.failure_reason}")
                print_structure_validation_result(structure_result)
                if not simulate:
                    _git_discard_branch(branch_name, project_root)
                _persist_record(store, record)
                _save_self_improve_record(project_root, record)
                return record
            if structure_result.violations:
                print(f"  Structure validation: {structure_result.summary}")
                print_structure_validation_result(structure_result)
            else:
                print("  Structure validation passed.")

            print("\n[8/9] Validating: running tests...")
            post_tests = _snapshot_tests(project_root)
            record.tests_passed = post_tests["passed"]
            if not record.tests_passed:
                record.failure_reason = "Tests failed after execution"
                print(f"  FAIL: {record.failure_reason}")
                _emit_test_failure_details(post_tests)
                if not simulate:
                    _git_discard_branch(branch_name, project_root)
                _persist_record(store, record)
                _save_self_improve_record(project_root, record)
                return record

            if skip_baseline_tests:
                print(
                    "[9/9] Skipping metrics stability check because "
                    "baseline tests were skipped."
                )
                record.metrics_stable = True
            else:
                print("[9/9] Validating: checking metrics stability...")
                stable, reason = _metrics_stable(
                    store,
                    record.baseline_metrics or report.baseline_metrics,
                )
                record.metrics_stable = stable
                if not stable:
                    record.failure_reason = f"Metrics regressed: {reason}"
                    print(f"  FAIL: {record.failure_reason}")
                    if not simulate:
                        _git_discard_branch(branch_name, project_root)
                    _persist_record(store, record)
                    _save_self_improve_record(project_root, record)
                    return record

            if simulate:
                record.failure_reason = SIMULATED_CYCLE_RESULT
                print("\nSimulation completed successfully. Cleaning up disposable branch...")
                _print_simulation_report(
                    record,
                    selected,
                    project_root,
                    artifact_path=artifact_path,
                )
                _persist_record(store, record)
                _save_self_improve_record(project_root, record)
                return record

            completed_roadmap_items = _mark_roadmap_items_completed(project_root, selected)
            if completed_roadmap_items:
                print("  Updated roadmap items:")
                for item in completed_roadmap_items:
                    print(f"    - {item}")

            commit_message = f"chore(self-improve): apply cycle {cycle_id}"
            committed, commit_reason = _git_commit_all(project_root, commit_message)
            if committed:
                print(f"  Created commit for PR: {commit_reason}")
            elif commit_reason != "nothing to commit":
                record.failure_reason = f"Failed to create PR commit: {commit_reason}"
                print(f"  FAIL: {record.failure_reason}")
                _persist_record(store, record)
                _save_self_improve_record(project_root, record)
                return record

            ahead, ahead_reason = _git_has_commits_ahead(project_root)
            if not ahead:
                record.failure_reason = (
                    "No committable source changes were produced "
                    "after validation"
                )
                print(f"  PR skipped: {record.failure_reason}")
                print(f"  Details: {ahead_reason}")
                _persist_record(store, record)
                _save_self_improve_record(project_root, record)
                return record

            print("\nAll gates passed. Creating PR...")
            pr_body = _build_pr_body(report, selected, record)
            pr_url = _create_pr(
                branch_name,
                f"[self-improve] {selected[0].title[:60]}",
                pr_body,
                project_root,
            )
            if pr_url:
                record.pr_created = True
                print(f"  PR created: {pr_url}")
            else:
                print("  PR creation failed (gh CLI not available?). Branch preserved.")

            _persist_record(store, record)
            _save_self_improve_record(project_root, record)
            return record
        finally:
            if simulation_branch_active:
                _cleanup_simulation_branch(project_root)


class _CycleAbort(Exception):
    pass


def _persist_record(_store: MetricsStore, record: SelfImprovementRecord) -> None:
    emit(
        "self_improve_cycle",
        1.0 if record.pr_created else 0.0,
        cycle_id=record.cycle_id,
        opportunities_found=record.opportunities_found,
        tests_passed=record.tests_passed,
        pr_created=record.pr_created,
        failure_reason=record.failure_reason,
        total_tokens=record.total_tokens,
        estimated_cost=record.estimated_cost,
    )


def _print_report(report: IntrospectionReport, max_items: int) -> None:
    print_report(report, max_items)


def _build_pr_body(
    report: IntrospectionReport,
    selected: list,
    record: SelfImprovementRecord,
) -> str:
    return build_pr_body(report, selected, record)
