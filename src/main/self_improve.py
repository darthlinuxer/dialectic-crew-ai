"""
Self-improvement orchestrator.

Wires introspection + existing PRD/plan/execute commands + safety gates
into a semi-autonomous improvement cycle with a human PR gate.

Usage:
    dialectic-crew self-improve [--dry-run] [--max N]
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from dialectic.hooks import HookScope
from dialectic.introspect import run_introspection
from dialectic.crewai_runtime import configure_crewai_runtime
from dialectic.metrics import MetricRecord, MetricsStore, emit, get_metrics_store
from dialectic.prioritize import dialectic_prioritize
from dialectic.vision import VisionContext, resolve_project_root
from main.git_helpers import (
    command_available,
    dirty_worktree_guidance,
    git_branch_create,
    git_commit_all,
    git_current_branch,
    git_discard_branch,
    git_has_commits_ahead,
    git_stash_worktree,
    git_worktree_clean,
    recover_stale_self_improve_worktree,
    run_cmd,
)
from main.test_runner import (
    emit_test_failure_details,
    pytest_command,
    self_improve_test_timeout,
    snapshot_tests,
)
from main.self_improve_persistence import (
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
from main.pr_builder import build_pr_body, create_pr, print_report
from main.metrics_comparison import metrics_stable
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
SELF_IMPROVE_STATE_DIR = Path(".dialectic") / "self_improve"


def _configure_crewai_runtime() -> None:
    """Apply runtime defaults that keep self-improve runs deterministic."""
    configure_crewai_runtime()


def _command_available(command: str) -> bool:
    return command_available(command)


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


def _git_discard_branch(branch: str, cwd: Path) -> None:
    git_discard_branch(branch, cwd, run_cmd_fn=_run_cmd)


def _git_current_branch(cwd: Path) -> str:
    return git_current_branch(cwd, run_cmd_fn=_run_cmd)


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


def _resolve_resume_context(record: SelfImprovementRecord) -> tuple[list[ImprovementOpportunity], dict]:
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
    if is_resume:
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
            record.failure_reason = "Git is required for self-improve branch isolation but was not found on PATH"
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
        except Exception as e:
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

                    from dialectic.prd_flow import DialecticFlow, _get_persistence

                    flow = DialecticFlow(persistence=_get_persistence())
                    record.prd_flow_id = record.prd_flow_id or flow.flow_id
                    _save_self_improve_record(project_root, record)
                    flow.kickoff(
                        inputs={
                            "id": record.prd_flow_id,
                            "feature_objective": feature_request,
                            "vision_context": VisionContext.SELF.value,
                        }
                    )
                    prd_path = _record_prd_artifacts(record, flow)
                    _save_self_improve_record(project_root, record)

                    if flow.state.quality_score < 9.0 and not flow.state.consensus_reached:
                        record.failure_reason = f"PRD quality too low: {flow.state.quality_score}"
                        print(f"  PRD did not reach threshold: {flow.state.quality_score}/10")
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
                    from planning.flow import run_user_story_planning

                    plan_result = run_user_story_planning(
                        prd_path=prd_path,
                        user_story_ref=None,
                        vision_context=VisionContext.SELF,
                    )
                    plan_path = _record_plan_artifacts(record, plan_result)
                    _save_self_improve_record(project_root, record)
                    if plan_result["quality_score"] < 7.5:
                        record.failure_reason = f"Plan quality too low: {plan_result['quality_score']}"
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
                    from execution.dialectic_execution import run_dialectic_execution

                    exec_result = run_dialectic_execution(
                        plan_path=plan_path,
                        vision_context=VisionContext.SELF,
                        resume_run_id=record.execution_run_id or None,
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
                    print(f"[resume] Reusing execution artifacts from run: {record.execution_run_id}")

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
        except Exception as e:
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


def _persist_record(store: MetricsStore, record: SelfImprovementRecord) -> None:
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
