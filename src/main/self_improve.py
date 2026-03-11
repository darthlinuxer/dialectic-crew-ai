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
import textwrap
from datetime import datetime, timezone
from pathlib import Path

from dialectic.hooks import HookScope
from dialectic.introspect import run_introspection
from dialectic.crewai_runtime import configure_crewai_runtime
from dialectic.metrics import MetricRecord, MetricsStore, emit, get_metrics_store
from dialectic.prioritize import dialectic_prioritize
from dialectic.vision import VisionContext, resolve_project_root
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
    return shutil.which(command) is not None


def _run_cmd(
    cmd: list[str],
    cwd: str | Path | None = None,
    timeout: int = 120,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(cwd) if cwd else None,
    )


def _self_improve_test_timeout() -> int:
    """Return the pytest timeout used by self-improvement validation."""
    raw = os.getenv("SELF_IMPROVE_TEST_TIMEOUT", str(DEFAULT_SELF_IMPROVE_TEST_TIMEOUT))
    try:
        timeout = int(raw)
    except ValueError:
        logger.warning(
            "Invalid SELF_IMPROVE_TEST_TIMEOUT=%r; using default %s",
            raw,
            DEFAULT_SELF_IMPROVE_TEST_TIMEOUT,
        )
        return DEFAULT_SELF_IMPROVE_TEST_TIMEOUT
    if timeout <= 0:
        logger.warning(
            "Non-positive SELF_IMPROVE_TEST_TIMEOUT=%r; using default %s",
            raw,
            DEFAULT_SELF_IMPROVE_TEST_TIMEOUT,
        )
        return DEFAULT_SELF_IMPROVE_TEST_TIMEOUT
    return timeout


def _snapshot_tests(project_root: Path, timeout: int | None = None) -> dict:
    """Run pytest and return pass/fail summary."""
    timeout = timeout or _self_improve_test_timeout()
    cmd = _pytest_command()
    try:
        r = _run_cmd(cmd, cwd=project_root, timeout=timeout)
        return {
            "returncode": r.returncode,
            "passed": r.returncode == 0,
            "timed_out": False,
            "timeout_seconds": timeout,
            "command": cmd,
            "stdout_tail": r.stdout[-500:] if r.stdout else "",
            "stderr_tail": r.stderr[-500:] if r.stderr else "",
        }
    except subprocess.TimeoutExpired as exc:
        stdout_tail = exc.output[-500:] if isinstance(exc.output, str) and exc.output else ""
        stderr_tail = exc.stderr[-500:] if isinstance(exc.stderr, str) and exc.stderr else ""
        return {
            "returncode": -1,
            "passed": False,
            "timed_out": True,
            "timeout_seconds": timeout,
            "command": cmd,
            "stdout_tail": stdout_tail,
            "stderr_tail": stderr_tail,
        }


def _pytest_command() -> list[str]:
    """Prefer uv-managed pytest, then fall back to the active Python environment."""
    if _command_available("uv"):
        return ["uv", "run", "pytest", "--tb=short", "-q", "--reruns", "1"]
    return [sys.executable, "-m", "pytest", "--tb=short", "-q", "--reruns", "1"]


def _emit_test_failure_details(snapshot: dict, prefix: str = "  ") -> None:
    """Print concise diagnostics for a failing pytest snapshot."""
    cmd = snapshot.get("command") or []
    command_str = " ".join(cmd) if cmd else "pytest"
    timeout_seconds = snapshot.get("timeout_seconds")
    if snapshot.get("timed_out"):
        print(f"{prefix}Pytest timed out after {timeout_seconds}s: {command_str}")
    else:
        print(f"{prefix}Pytest exited with code {snapshot.get('returncode')}: {command_str}")

    stdout_tail = (snapshot.get("stdout_tail") or "").strip()
    stderr_tail = (snapshot.get("stderr_tail") or "").strip()

    if stdout_tail:
        print(f"{prefix}stdout tail:")
        print(textwrap.indent(stdout_tail[-500:], prefix + "  "))
    if stderr_tail:
        print(f"{prefix}stderr tail:")
        print(textwrap.indent(stderr_tail[-500:], prefix + "  "))


def _metrics_stable(
    store: MetricsStore,
    baseline: dict,
    retention: float = MIN_METRIC_RETENTION,
) -> tuple[bool, str]:
    """Compare current metrics against baseline; no metric may drop by more than (1 - retention)."""
    for metric_type in ("prd_score", "task_score"):
        old = baseline.get(metric_type, {})
        if old.get("count", 0) < 3:
            continue
        new = store.trend(metric_type, window=10)
        if new["count"] < 3:
            continue
        if new["mean"] < old["mean"] * retention:
            return False, (
                f"{metric_type} regressed: {old['mean']:.1f} → {new['mean']:.1f} "
                f"(retention threshold: {retention:.0%})"
            )
    return True, "metrics stable"


def _git_branch_create(branch: str, cwd: Path) -> bool:
    r = _run_cmd(["git", "checkout", "-b", branch], cwd=cwd)
    return r.returncode == 0


def _git_discard_branch(branch: str, cwd: Path) -> None:
    _run_cmd(["git", "checkout", "-"], cwd=cwd)
    _run_cmd(["git", "branch", "-D", branch], cwd=cwd)


def _git_current_branch(cwd: Path) -> str:
    r = _run_cmd(["git", "branch", "--show-current"], cwd=cwd)
    if r.returncode != 0:
        return ""
    return r.stdout.strip()


def _recover_stale_self_improve_worktree(cwd: Path) -> tuple[bool, str]:
    """Recover from an interrupted run only when already on a self-improve branch."""
    branch = _git_current_branch(cwd)
    if not branch.startswith("self-improve/"):
        return False, "not on a self-improve branch"

    reset_result = _run_cmd(["git", "reset", "--hard", "HEAD"], cwd=cwd)
    if reset_result.returncode != 0:
        return False, f"failed to reset stale self-improve branch {branch}"

    clean_result = _run_cmd(["git", "clean", "-fd"], cwd=cwd)
    if clean_result.returncode != 0:
        return False, f"failed to clean stale self-improve branch {branch}"

    return True, f"discarded stale self-improve worktree on {branch}"


def _git_stash_worktree(cwd: Path, message: str) -> tuple[bool, str]:
    r = _run_cmd(["git", "stash", "push", "--include-untracked", "-m", message], cwd=cwd)
    if r.returncode != 0:
        return False, "failed to stash current branch changes"
    return True, (r.stdout or r.stderr or "stashed current branch changes").strip()


def _dirty_worktree_guidance(cwd: Path, worktree_reason: str) -> str:
    branch = _git_current_branch(cwd) or "<detached HEAD>"
    return (
        f"{worktree_reason} on branch '{branch}'. "
        "Commit the changes, discard them manually, or rerun with --stash-dirty "
        "to stash current branch changes before self-improve continues."
    )


def _git_worktree_clean(cwd: Path) -> tuple[bool, str]:
    r = _run_cmd(["git", "status", "--porcelain"], cwd=cwd)
    if r.returncode != 0:
        return False, "Unable to determine git worktree status"

    dirty_entries = [line.strip() for line in r.stdout.splitlines() if line.strip()]
    if not dirty_entries:
        return True, "clean"

    preview = ", ".join(dirty_entries[:5])
    suffix = "" if len(dirty_entries) <= 5 else f", +{len(dirty_entries) - 5} more"
    return False, f"Worktree has uncommitted changes: {preview}{suffix}"


def _create_pr(branch: str, title: str, body: str, cwd: Path) -> str | None:
    if not _command_available("gh"):
        logger.warning("PR creation skipped: GitHub CLI (gh) not found")
        return None
    r = _run_cmd(
        ["gh", "pr", "create", "--title", title, "--body", body, "--head", branch],
        cwd=cwd,
        timeout=60,
    )
    if r.returncode == 0:
        return r.stdout.strip()
    logger.warning("PR creation failed: %s", r.stderr)
    return None


def _record_prd_artifacts(record: SelfImprovementRecord, flow) -> str:
    record.prd_flow_id = getattr(flow, "flow_id", "") or getattr(flow.state, "id", "") or ""
    record.prd_path_json = flow.state.prd_path_json or ""
    record.prd_path_md = flow.state.prd_path_md or ""
    return record.prd_path_json


def _record_plan_artifacts(record: SelfImprovementRecord, plan_result: dict) -> str:
    record.plan_path_json = plan_result.get("plan_path_json", "") or ""
    record.plan_path_md = plan_result.get("plan_path_md", "") or ""
    return record.plan_path_json


def _record_execution_artifacts(record: SelfImprovementRecord, exec_result: dict) -> None:
    record.execution_run_id = exec_result.get("run_id", "") or ""
    record.execution_task_flow_ids = exec_result.get("task_flow_ids", {}) or {}
    record.execution_output_path = exec_result.get("output_path", "") or ""
    record.execution_report_path = exec_result.get("report_path", "") or ""


def _self_improve_record_path(project_root: Path, cycle_id: str) -> Path:
    path = project_root / SELF_IMPROVE_STATE_DIR / f"{cycle_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _save_self_improve_record(project_root: Path, record: SelfImprovementRecord) -> None:
    path = _self_improve_record_path(project_root, record.cycle_id)
    path.write_text(record.model_dump_json(indent=2), encoding="utf-8")


def _load_self_improve_record(project_root: Path, cycle_id: str) -> SelfImprovementRecord:
    path = _self_improve_record_path(project_root, cycle_id)
    if not path.exists():
        raise FileNotFoundError(f"Self-improve snapshot not found: {path}")
    return SelfImprovementRecord.model_validate_json(path.read_text(encoding="utf-8"))


def _resolve_resume_context(record: SelfImprovementRecord) -> tuple[list[ImprovementOpportunity], dict]:
    return list(record.selected_opportunities), dict(record.baseline_metrics)


def _summarize_resume_state(
    record: SelfImprovementRecord,
    last_failure_reason: str = "",
) -> dict[str, str | list[str]]:
    reused: list[str] = []
    if record.prd_generated and record.prd_path_json:
        reused.append(f"PRD: {record.prd_path_json}")
    if record.plan_generated and record.plan_path_json:
        reused.append(f"Plan: {record.plan_path_json}")
    if record.execution_run_id:
        reused.append(f"Execution run: {record.execution_run_id}")

    if not record.prd_generated:
        next_stage = "PRD generation"
    elif not record.plan_generated:
        next_stage = "planning"
    elif (
        not record.execution_attempted
        or not record.execution_output_path
        or not record.execution_report_path
        or last_failure_reason.startswith("Execution failed:")
    ):
        next_stage = "execution"
    elif not record.tests_passed:
        next_stage = "test validation"
    elif not record.metrics_stable:
        next_stage = "metrics validation"
    elif not record.pr_created:
        next_stage = "PR creation"
    else:
        next_stage = "completed"

    return {
        "last_failure": last_failure_reason or "unknown",
        "next_stage": next_stage,
        "reused": reused,
    }


def _list_resumable_cycles(project_root: Path) -> list[dict[str, str]]:
    state_dir = project_root / SELF_IMPROVE_STATE_DIR
    if not state_dir.exists():
        return []

    rows: list[dict[str, str]] = []
    for path in state_dir.glob("*.json"):
        try:
            record = SelfImprovementRecord.model_validate_json(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        summary = _summarize_resume_state(record, record.failure_reason)
        rows.append(
            {
                "cycle_id": record.cycle_id,
                "timestamp": record.timestamp,
                "next_stage": str(summary["next_stage"]),
                "last_failure": str(summary["last_failure"]),
            }
        )

    rows.sort(key=lambda row: (row["timestamp"], row["cycle_id"]), reverse=True)
    return rows


def _require_artifact(path: str, failure_reason: str) -> str:
    if not path:
        raise _CycleAbort(failure_reason)
    return path


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
    print(f"\nIntrospection Report ({report.timestamp})")
    print(f"{'='*60}")
    for i, opp in enumerate(report.opportunities):
        marker = ">>>" if i < max_items else "   "
        print(f"  {marker} [{opp.estimated_impact.upper():>6}] {opp.id}: {opp.title}")
        if opp.evidence:
            print(f"         Evidence: {', '.join(opp.evidence[:3])}")
    print(f"\nBaseline metrics:")
    for key, val in report.baseline_metrics.items():
        if val.get("count", 0) > 0:
            print(f"  {key}: mean={val['mean']:.1f}, count={val['count']}")


def _build_pr_body(
    report: IntrospectionReport,
    selected: list,
    record: SelfImprovementRecord,
) -> str:
    lines = [
        "## Self-Improvement Cycle",
        "",
        f"**Cycle ID:** {record.cycle_id}",
        f"**Opportunities found:** {record.opportunities_found}",
        f"**Attempted:** {record.opportunities_attempted}",
        "",
        "### Improvements",
        "",
    ]
    for opp in selected:
        lines.append(f"- **{opp.title}** ({opp.category}, {opp.estimated_impact})")
        lines.append(f"  {opp.description}")
    lines.extend([
        "",
        "### Artifacts",
        "",
        f"- PRD JSON: {record.prd_path_json or 'n/a'}",
        f"- PRD Markdown: {record.prd_path_md or 'n/a'}",
        f"- PRD flow ID: {record.prd_flow_id or 'n/a'}",
        f"- Plan JSON: {record.plan_path_json or 'n/a'}",
        f"- Plan Markdown: {record.plan_path_md or 'n/a'}",
        f"- Execution run: {record.execution_run_id or 'n/a'}",
        f"- Execution task flows: {record.execution_task_flow_ids or 'n/a'}",
        f"- Execution output dir: {record.execution_output_path or 'n/a'}",
        f"- Execution report: {record.execution_report_path or 'n/a'}",
        "",
        "### Validation",
        "",
        f"- Tests: {'PASSED' if record.tests_passed else 'FAILED'}",
        f"- Metrics stable: {'YES' if record.metrics_stable else 'NO'}",
        "",
        "### Token Usage",
        "",
        f"- Total tokens: {record.total_tokens:,}",
        f"- Estimated cost: ${record.estimated_cost:.4f}",
        "",
        "### Baseline Metrics",
        "",
    ])
    for key, val in report.baseline_metrics.items():
        if val.get("count", 0) > 0:
            lines.append(f"- {key}: mean={val['mean']:.1f}")
    return "\n".join(lines)
