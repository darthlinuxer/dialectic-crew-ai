"""
Self-improvement orchestrator.

Wires introspection + existing PRD/plan/execute commands + safety gates
into a semi-autonomous improvement cycle with a human PR gate.

Usage:
    dialectic-crew self-improve [--dry-run] [--max N]
"""

# pylint: disable=too-many-locals,too-many-return-statements,too-many-branches
# pylint: disable=too-many-statements,too-many-nested-blocks

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
from typing import Callable, TypeVar

from dialectic.hooks import HookScope
from dialectic.introspect import run_introspection
from dialectic.crewai_runtime import configure_crewai_runtime
from dialectic.metrics import MetricsStore, emit, get_metrics_store
from dialectic.prioritize import dialectic_prioritize
from dialectic.vision import VisionContext, resolve_project_root
from .git_helpers import (
    dirty_worktree_guidance,
    git_branch_create,
    git_branch_create_from_head,
    git_checkout_branch,
    git_commit_all,
    git_current_branch,
    git_discard_branch,
    git_has_commits_ahead,
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
from schemas import ImprovementOpportunity, IntrospectionReport, SelfImprovementRecord

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


def _git_branch_create_from_head(branch: str, cwd: Path) -> tuple[bool, str]:
    return git_branch_create_from_head(branch, cwd, run_cmd_fn=_run_cmd)


def _git_discard_branch(branch: str, cwd: Path) -> None:
    git_discard_branch(branch, cwd, run_cmd_fn=_run_cmd)


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


def run_self_improve(
    max_improvements: int = 1,
    dry_run: bool = False,
    stash_dirty: bool = False,
    resume_cycle_id: str | None = None,
) -> SelfImprovementRecord:
    """
    Run one self-improvement cycle.

    1. Snapshot baseline
    2. Introspect against SELF_VISION.md
    3. If dry_run: print report and return
    4. Create branch, generate PRD → plan → execute (VisionContext.SELF)
    5. Validate (tests + metrics)
    6. Pass → PR, Fail → discard branch
    """
    _configure_crewai_runtime()
    project_root = resolve_project_root()
    store = get_metrics_store()
    is_resume = resume_cycle_id is not None
    resume_summary: dict[str, str | list[str]] = {}
    if is_resume:
        assert resume_cycle_id is not None
        record = _load_self_improve_record(project_root, resume_cycle_id)
        cycle_id = record.cycle_id
        resume_summary = _summarize_resume_state(record, record.failure_reason)
        record.failure_reason = ""
        record.tests_passed = False
        record.metrics_stable = False
        record.pr_created = False
        _save_self_improve_record(project_root, record)
    else:
        cycle_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        record = SelfImprovementRecord(
            cycle_id=cycle_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
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

    if not dry_run and not is_resume:
        print("[1b/6] Checking git preflight...")
        if not _command_available("git"):
            record.failure_reason = (
                "Git is required for self-improve branch isolation "
                "but was not found on PATH"
            )
            print(f"  ABORT: {record.failure_reason}")
            _persist_record(store, record)
            return record

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
                    record.failure_reason = _dirty_worktree_guidance(project_root, worktree_reason)
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
        branch_name = record.branch_name or f"self-improve/{cycle_id}"
        print(f"[resume] Loaded {len(selected)} saved opportunities.")
    else:
        print("[2/6] Running introspection against SELF_VISION.md...")
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

        if dry_run:
            print("\n[DRY RUN] Printing full introspection report and stopping.")
            _print_report(report, max_improvements)
            record.failure_reason = "dry_run"
            _persist_record(store, record)
            return record

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
        branch_name = f"self-improve/{cycle_id}"
        record.branch_name = branch_name
        _save_self_improve_record(project_root, record)

    print("  Prioritized order:")
    for i, opp in enumerate(selected, 1):
        print(f"    {i}. [{opp.estimated_impact.upper()}] {opp.title}")

    token_budget = int(os.getenv("SELF_IMPROVE_TOKEN_BUDGET", "500000"))
    max_iterations = int(os.getenv("SELF_IMPROVE_MAX_ITERATIONS", "25"))

    if not is_resume:
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
                                f"Failed to resume on branch '{branch_name}': {switch_reason}; "
                                "also failed to recreate it from "
                                f"{current_branch}: {recreate_reason}"
                            )
                            print(f"  ABORT: {record.failure_reason}")
                            _persist_record(store, record)
                            _save_self_improve_record(project_root, record)
                            return record
                        print(f"  Recreated recorded branch from {current_branch}: {branch_name}")
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
                        partial(_run_planning_stage, run_user_story_planning, prd_path=prd_path),
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
                            f"Execution failed: {exec_result.get('story_status', 'unknown')}"
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
            _git_discard_branch(branch_name, project_root)
            _persist_record(store, record)
            _save_self_improve_record(project_root, record)
            return record
        except Exception as e:  # pylint: disable=broad-exception-caught
            record.failure_reason = f"Unexpected error: {e}"
            print(f"\n  Unexpected error: {e}")
            record.total_tokens = tracker.total_tokens
            record.estimated_cost = tracker.estimated_cost
            _git_discard_branch(branch_name, project_root)
            _persist_record(store, record)
            _save_self_improve_record(project_root, record)
            return record

        record.total_tokens = tracker.total_tokens
        record.estimated_cost = tracker.estimated_cost

    print(f"\n  Token usage: {record.total_tokens} tokens, ${record.estimated_cost:.4f}")

    print("\n[7/7] Validating: running tests...")
    post_tests = _snapshot_tests(project_root)
    record.tests_passed = post_tests["passed"]
    if not record.tests_passed:
        record.failure_reason = "Tests failed after execution"
        print(f"  FAIL: {record.failure_reason}")
        _emit_test_failure_details(post_tests)
        _git_discard_branch(branch_name, project_root)
        _persist_record(store, record)
        _save_self_improve_record(project_root, record)
        return record

    print("Validating: checking metrics stability...")
    stable, reason = _metrics_stable(store, record.baseline_metrics or report.baseline_metrics)
    record.metrics_stable = stable
    if not stable:
        record.failure_reason = f"Metrics regressed: {reason}"
        print(f"  FAIL: {record.failure_reason}")
        _git_discard_branch(branch_name, project_root)
        _persist_record(store, record)
        _save_self_improve_record(project_root, record)
        return record

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
        record.failure_reason = "No committable source changes were produced after validation"
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
