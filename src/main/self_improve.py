"""
Self-improvement orchestrator.

Wires introspection + existing PRD/plan/execute commands + safety gates
into a semi-autonomous improvement cycle with a human PR gate.

Usage:
    dialectic-crew self-improve [--simulate] [--max N]
"""

# pylint: disable=too-many-locals,too-many-return-statements,too-many-branches
# pylint: disable=too-many-statements,too-many-nested-blocks,too-many-lines

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import sys
import time
from contextlib import contextmanager, nullcontext
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable, TypeVar

from dialectic.hooks import HookScope
from dialectic.introspect import run_introspection
from dialectic.crewai_runtime import configure_crewai_runtime
from dialectic.metrics import MetricsStore, emit, get_metrics_store
from dialectic.prioritize import dialectic_prioritize
from dialectic.vision import VisionContext, resolve_project_root
from schemas import ImprovementOpportunity, IntrospectionReport, SelfImprovementRecord
from .git_helpers import (
    git_branch_exists,
    dirty_worktree_guidance,
    git_branch_create,
    git_branch_create_from_head,
    git_checkout_branch,
    git_commit_all,
    git_current_branch,
    git_delete_branch,
    git_discard_branch,
    git_clean_untracked,
    git_has_commits_ahead,
    git_reset_hard_head,
    git_stash_worktree,
    git_worktree_clean,
    recover_stale_self_improve_worktree,
    run_cmd,
)
from .test_runner import (
    emit_test_failure_details,
    pytest_command,
    self_improve_test_timeout,
    snapshot_tests,
)
from .self_improve_persistence import (
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
from .pr_builder import build_pr_body, create_pr, print_report
from .metrics_comparison import metrics_stable
from .quality_gate import run_quality_gate, print_quality_gate_result
from .code_structure_validation import (
    validate_code_structure,
    print_structure_validation_result,
)

logger = logging.getLogger(__name__)

PROTECTED_PATHS = frozenset({
    "internal/SELF_VISION.md",
    "src/main/self_improve.py",
    "src/dialectic/metrics.py",
    "src/dialectic/introspect.py",
})

MIN_METRIC_RETENTION = float(os.getenv("MIN_METRIC_RETENTION", "0.95"))
DEFAULT_SELF_IMPROVE_TEST_TIMEOUT = 1800
DEFAULT_SELF_IMPROVE_PRD_MIN_SCORE = 8.5
DEFAULT_SELF_IMPROVE_LLM_STAGE_RETRIES = 2
DEFAULT_SELF_IMPROVE_LLM_RETRY_BACKOFF_SECONDS = 2.0
SELF_IMPROVE_STATE_DIR = Path(".dialectic") / "self_improve"
SELF_IMPROVE_ROADMAP_PATH = Path("internal") / "ROADMAP.md"
SIMULATION_BRANCH_NAME = "self-improve/simulate"
SIMULATED_CYCLE_RESULT = "simulated"
RUNTIME_ROOT_ENV_VAR = "DIALECTIC_RUNTIME_ROOT"
FLOW_DB_ENV_VAR = "DIALECTIC_FLOW_DB"
METRICS_DB_ENV_VAR = "DIALECTIC_METRICS_DB"
SELF_IMPROVE_STATE_DIR_ENV_VAR = "DIALECTIC_SELF_IMPROVE_STATE_DIR"
_StageResultT = TypeVar("_StageResultT")


def _configure_crewai_runtime() -> None:
    """Apply runtime defaults that keep self-improve runs deterministic."""
    configure_crewai_runtime()


def _command_available(command: str) -> bool:
    return shutil.which(command) is not None


def _run_cmd(
    cmd: list[str],
    cwd: str | Path | None = None,
    timeout: int = 120,
) -> subprocess.CompletedProcess[str]:
    return run_cmd(cmd, cwd=cwd, timeout=timeout)


def _self_improve_test_timeout() -> int:
    """Return the pytest timeout used by self-improvement validation."""
    return self_improve_test_timeout(
        os.getenv("SELF_IMPROVE_TEST_TIMEOUT"),
        default_timeout=DEFAULT_SELF_IMPROVE_TEST_TIMEOUT,
        logger=logger,
    )


def _self_improve_prd_min_score() -> float:
    """Return the minimum PRD score that allows self-improve to continue."""
    raw_value = os.getenv("SELF_IMPROVE_MIN_PRD_SCORE")
    if raw_value in {None, ""}:
        return DEFAULT_SELF_IMPROVE_PRD_MIN_SCORE
    assert raw_value is not None
    try:
        score = float(raw_value)
    except ValueError:
        logger.warning(
            "Invalid SELF_IMPROVE_MIN_PRD_SCORE=%r; using default %s",
            raw_value,
            DEFAULT_SELF_IMPROVE_PRD_MIN_SCORE,
        )
        return DEFAULT_SELF_IMPROVE_PRD_MIN_SCORE
    if not 0.0 <= score <= 10.0:
        logger.warning(
            "Out-of-range SELF_IMPROVE_MIN_PRD_SCORE=%r; using default %s",
            raw_value,
            DEFAULT_SELF_IMPROVE_PRD_MIN_SCORE,
        )
        return DEFAULT_SELF_IMPROVE_PRD_MIN_SCORE
    return score


def _self_improve_llm_stage_retries() -> int:
    """Return how many extra attempts self-improve should make on transient LLM failures."""
    raw_value = os.getenv("SELF_IMPROVE_LLM_STAGE_RETRIES")
    if raw_value in {None, ""}:
        return DEFAULT_SELF_IMPROVE_LLM_STAGE_RETRIES
    assert raw_value is not None
    try:
        retries = int(raw_value)
    except ValueError:
        logger.warning(
            "Invalid SELF_IMPROVE_LLM_STAGE_RETRIES=%r; using default %s",
            raw_value,
            DEFAULT_SELF_IMPROVE_LLM_STAGE_RETRIES,
        )
        return DEFAULT_SELF_IMPROVE_LLM_STAGE_RETRIES
    if retries < 0:
        logger.warning(
            "Negative SELF_IMPROVE_LLM_STAGE_RETRIES=%r; using default %s",
            raw_value,
            DEFAULT_SELF_IMPROVE_LLM_STAGE_RETRIES,
        )
        return DEFAULT_SELF_IMPROVE_LLM_STAGE_RETRIES
    return retries


def _self_improve_llm_retry_backoff_seconds() -> float:
    """Return the base backoff between transient LLM retry attempts."""
    raw_value = os.getenv("SELF_IMPROVE_LLM_RETRY_BACKOFF_SECONDS")
    if raw_value in {None, ""}:
        return DEFAULT_SELF_IMPROVE_LLM_RETRY_BACKOFF_SECONDS
    assert raw_value is not None
    try:
        seconds = float(raw_value)
    except ValueError:
        logger.warning(
            "Invalid SELF_IMPROVE_LLM_RETRY_BACKOFF_SECONDS=%r; using default %s",
            raw_value,
            DEFAULT_SELF_IMPROVE_LLM_RETRY_BACKOFF_SECONDS,
        )
        return DEFAULT_SELF_IMPROVE_LLM_RETRY_BACKOFF_SECONDS
    if seconds < 0:
        logger.warning(
            "Negative SELF_IMPROVE_LLM_RETRY_BACKOFF_SECONDS=%r; using default %s",
            raw_value,
            DEFAULT_SELF_IMPROVE_LLM_RETRY_BACKOFF_SECONDS,
        )
        return DEFAULT_SELF_IMPROVE_LLM_RETRY_BACKOFF_SECONDS
    return seconds


def _is_transient_llm_error(exc: Exception) -> bool:
    """Return True when the exception looks like a transient provider/network failure."""
    message = str(exc).lower()
    transient_markers = (
        "request timed out",
        "timed out",
        "timeout",
        "failed to connect to openai api",
        "connection error",
        "api connection error",
        "temporarily unavailable",
        "service unavailable",
        "rate limit",
        "too many requests",
        "server disconnected",
    )
    return any(marker in message for marker in transient_markers)


def _run_with_transient_llm_retries(
    stage_name: str,
    operation: Callable[[], _StageResultT],
) -> _StageResultT:
    """Retry a self-improve stage when transient LLM/provider failures occur."""
    max_attempts = _self_improve_llm_stage_retries() + 1
    backoff_seconds = _self_improve_llm_retry_backoff_seconds()

    for attempt in range(1, max_attempts + 1):
        try:
            return operation()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            if not _is_transient_llm_error(exc) or attempt >= max_attempts:
                raise

            wait_seconds = backoff_seconds * attempt
            logger.warning(
                "Transient LLM failure during %s (attempt %s/%s): %s",
                stage_name,
                attempt,
                max_attempts,
                exc,
            )
            print(
                f"  Transient LLM failure during {stage_name} "
                f"(attempt {attempt}/{max_attempts}): {exc}"
            )
            print(f"  Retrying {stage_name} in {wait_seconds:.1f}s...")
            if wait_seconds > 0:
                time.sleep(wait_seconds)

    raise RuntimeError(f"Retry loop exited unexpectedly for {stage_name}")


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


def _snapshot_tests(project_root: Path, timeout: int | None = None) -> dict:
    """Run pytest and return pass/fail summary."""
    return snapshot_tests(
        project_root,
        timeout=timeout,
        timeout_resolver=_self_improve_test_timeout,
        pytest_command_fn=_pytest_command,
        run_cmd_fn=_run_cmd,
    )


def _pytest_command() -> list[str]:
    """Prefer uv-managed pytest, then fall back to the active Python environment."""
    return pytest_command(
        command_available_fn=_command_available,
        python_executable=sys.executable,
    )


def _emit_test_failure_details(snapshot: dict, prefix: str = "  ") -> None:
    """Print concise diagnostics for a failing pytest snapshot."""
    emit_test_failure_details(snapshot, prefix=prefix)


def _metrics_stable(
    store: MetricsStore,
    baseline: dict,
    retention: float = MIN_METRIC_RETENTION,
) -> tuple[bool, str]:
    """Compare current metrics against baseline; no metric may drop by more than (1 - retention)."""
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
    """Mark successfully completed self-improve roadmap items as done."""
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
    """Temporarily apply environment variable overrides for a bounded scope."""
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


@contextmanager
def _simulation_runtime_environment():
    """Redirect runtime artifacts and caches to a temporary directory."""
    with TemporaryDirectory(prefix="dialectic-self-improve-sim-") as temp_dir:
        runtime_root = Path(temp_dir)
        pytest_addopts_parts = [os.getenv("PYTEST_ADDOPTS", "").strip(), "-p no:cacheprovider"]
        pytest_addopts = " ".join(part for part in pytest_addopts_parts if part).strip()
        overrides = {
            RUNTIME_ROOT_ENV_VAR: str(runtime_root),
            FLOW_DB_ENV_VAR: str(runtime_root / ".dialectic" / "flows.db"),
            METRICS_DB_ENV_VAR: str(runtime_root / ".dialectic" / "metrics.db"),
            SELF_IMPROVE_STATE_DIR_ENV_VAR: str(runtime_root / ".dialectic" / "self_improve"),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPYCACHEPREFIX": str(runtime_root / ".pycache"),
            "PYTEST_ADDOPTS": pytest_addopts,
        }
        with _temporary_environment(overrides):
            yield runtime_root


def _run_git_preflight(
    project_root: Path,
    *,
    cycle_id: str,
    stash_dirty: bool,
    step_label: str,
) -> str | None:
    """Validate git availability and worktree cleanliness before self-improve starts."""
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
    """Recreate the disposable simulation branch from the current HEAD."""
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
    """Discard the disposable simulation branch and return to the caller's branch."""
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


def run_self_improve(
    max_improvements: int = 1,
    simulate: bool = False,
    stash_dirty: bool = False,
    resume_cycle_id: str | None = None,
) -> SelfImprovementRecord:
    """
    Run one self-improvement cycle.

    1. Snapshot baseline
    2. Introspect against SELF_VISION.md
    3. If simulate: run the full pipeline on a disposable branch with temporary runtime state
    4. Create branch, generate PRD → plan → execute (VisionContext.SELF)
    5. Validate (tests + metrics)
    6. Pass → PR, or clean up and report for simulation
    """
    if max_improvements != 1:
        raise ValueError(
            "self-improve currently supports exactly one opportunity per cycle"
        )
    if simulate and resume_cycle_id is not None:
        raise ValueError("self-improve simulation does not support --resume")

    _configure_crewai_runtime()
    project_root = resolve_project_root()
    is_resume = resume_cycle_id is not None
    cycle_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    branch_name = SIMULATION_BRANCH_NAME if simulate else ""
    resume_summary: dict[str, str | list[str]] = {}
    simulation_context = _simulation_runtime_environment() if simulate else nullcontext()
    simulation_branch_active = False

    with simulation_context:
        store = get_metrics_store()
        if is_resume:
            assert resume_cycle_id is not None
            record = _load_self_improve_record(project_root, resume_cycle_id)
            cycle_id = record.cycle_id
            branch_name = record.branch_name or f"self-improve/{cycle_id}"
            resume_summary = _summarize_resume_state(record, record.failure_reason)
            record.failure_reason = ""
            record.tests_passed = False
            record.metrics_stable = False
            record.pr_created = False
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

                print("\n[2b/7] Running dialectic prioritization...")
                try:
                    prioritized = dialectic_prioritize(
                        report.opportunities,
                        vision_context=VisionContext.SELF,
                        max_to_debate=min(len(report.opportunities), 5),
                    )
                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.warning("Dialectic prioritization failed: %s; using impact sort", e)
                    print(f"  Prioritization failed ({e}); falling back to impact sort.")
                    prioritized = sorted(
                        report.opportunities,
                        key=lambda o: {"high": 0, "medium": 1, "low": 2}.get(o.estimated_impact, 1),
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
                    print(f"\n[3/7] Using disposable simulation branch: {branch_name}")
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
                            prd_path = _require_artifact(
                                record.prd_path_json,
                                "PRD generation did not produce an exported JSON artifact",
                            )
                            print(f"\n[resume] Reusing PRD artifact: {prd_path}")

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

                            exec_result = _run_with_transient_llm_retries(
                                "execution",
                                partial(
                                    _run_execution_stage,
                                    run_dialectic_execution,
                                    plan_path=plan_path,
                                    resume_run_id=record.execution_run_id or None,
                                ),
                            )
                            _record_execution_artifacts(record, exec_result)
                            record.execution_attempted = True
                            _save_self_improve_record(project_root, record)

                            if not exec_result.get("overall_success"):
                                record.failure_reason = (
                                    "Execution failed: "
                                    f"{exec_result.get('story_status', 'unknown')}"
                                )
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
                print(
                    "\nSimulation completed successfully. "
                    "Cleaning up disposable branch..."
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
