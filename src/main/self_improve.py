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
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from dialectic.hooks import HookScope
from dialectic.introspect import run_introspection
from dialectic.metrics import MetricRecord, MetricsStore, emit, get_metrics_store
from dialectic.prioritize import dialectic_prioritize
from dialectic.vision import VisionContext, resolve_project_root
from schemas import IntrospectionReport, SelfImprovementRecord

logger = logging.getLogger(__name__)

PROTECTED_PATHS = frozenset({
    "internal/SELF_VISION.md",
    "src/main/self_improve.py",
    "src/dialectic/metrics.py",
    "src/dialectic/introspect.py",
})

MIN_METRIC_RETENTION = float(os.getenv("MIN_METRIC_RETENTION", "0.95"))


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


def _snapshot_tests(project_root: Path) -> dict:
    """Run pytest and return pass/fail summary."""
    try:
        r = _run_cmd(["uv", "run", "pytest", "--tb=short", "-q"], cwd=project_root, timeout=300)
        return {
            "returncode": r.returncode,
            "passed": r.returncode == 0,
            "stdout_tail": r.stdout[-500:] if r.stdout else "",
            "stderr_tail": r.stderr[-500:] if r.stderr else "",
        }
    except subprocess.TimeoutExpired:
        return {"returncode": -1, "passed": False, "stdout_tail": "timeout", "stderr_tail": ""}


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


def _create_pr(branch: str, title: str, body: str, cwd: Path) -> str | None:
    r = _run_cmd(
        ["gh", "pr", "create", "--title", title, "--body", body, "--head", branch],
        cwd=cwd,
        timeout=60,
    )
    if r.returncode == 0:
        return r.stdout.strip()
    logger.warning("PR creation failed: %s", r.stderr)
    return None


def run_self_improve(
    max_improvements: int = 1,
    dry_run: bool = False,
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
    project_root = resolve_project_root()
    store = get_metrics_store()
    cycle_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    record = SelfImprovementRecord(
        cycle_id=cycle_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    print(f"\n{'='*60}")
    print(f"Self-Improvement Cycle {cycle_id}")
    print(f"{'='*60}")

    print("\n[1/6] Running baseline tests...")
    baseline_tests = _snapshot_tests(project_root)
    if not baseline_tests["passed"]:
        record.failure_reason = "Baseline tests already failing -- aborting"
        print(f"  ABORT: {record.failure_reason}")
        _persist_record(store, record)
        return record

    print("[2/6] Running introspection against SELF_VISION.md...")
    report = run_introspection(store=store, vision_context=VisionContext.SELF)
    record.opportunities_found = len(report.opportunities)

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
    record.opportunities_attempted = len(selected)
    branch_name = f"self-improve/{cycle_id}"
    record.branch_name = branch_name

    print("  Prioritized order:")
    for i, opp in enumerate(selected, 1):
        print(f"    {i}. [{opp.estimated_impact.upper()}] {opp.title}")

    token_budget = int(os.getenv("SELF_IMPROVE_TOKEN_BUDGET", "500000"))
    max_iterations = int(os.getenv("SELF_IMPROVE_MAX_ITERATIONS", "25"))

    print(f"\n[3/7] Creating branch: {branch_name}")
    if not _git_branch_create(branch_name, project_root):
        record.failure_reason = "Failed to create git branch"
        print(f"  ABORT: {record.failure_reason}")
        _persist_record(store, record)
        return record

    with HookScope(
        token_budget=token_budget,
        max_iterations=max_iterations,
        protected_paths=PROTECTED_PATHS,
        label=f"self-improve/{cycle_id}",
    ) as tracker:
        try:
            for opp in selected:
                feature_request = (
                    f"[Self-Improvement] {opp.title}\n\n"
                    f"Category: {opp.category}\n"
                    f"Description: {opp.description}\n"
                    f"Evidence: {', '.join(opp.evidence)}"
                )

                print(f"\n[4/7] Generating PRD for: {opp.title[:60]}...")
                if tracker.budget_exceeded:
                    record.failure_reason = (
                        f"Token budget exceeded before PRD generation "
                        f"({tracker.total_tokens}/{tracker.budget})"
                    )
                    raise _CycleAbort(record.failure_reason)

                from dialectic.prd_flow import DialecticFlow, _get_persistence

                flow = DialecticFlow(persistence=_get_persistence())
                flow.state.feature_objective = feature_request
                flow.state.vision_context = VisionContext.SELF.value
                flow.kickoff()

                if flow.state.quality_score < 9.0 and not flow.state.consensus_reached:
                    record.failure_reason = f"PRD quality too low: {flow.state.quality_score}"
                    print(f"  PRD did not reach threshold: {flow.state.quality_score}/10")
                    raise _CycleAbort(record.failure_reason)
                record.prd_generated = True

                if tracker.budget_exceeded:
                    record.failure_reason = (
                        f"Token budget exceeded after PRD generation "
                        f"({tracker.total_tokens}/{tracker.budget})"
                    )
                    raise _CycleAbort(record.failure_reason)

                print("[5/7] Planning user story execution...")
                from planning.flow import run_user_story_planning

                plan_result = run_user_story_planning(
                    prd_path=None,
                    us_ref=None,
                    vision_context=VisionContext.SELF,
                )
                if plan_result["quality_score"] < 7.5:
                    record.failure_reason = f"Plan quality too low: {plan_result['quality_score']}"
                    raise _CycleAbort(record.failure_reason)
                record.plan_generated = True

                if tracker.budget_exceeded:
                    record.failure_reason = (
                        f"Token budget exceeded after planning "
                        f"({tracker.total_tokens}/{tracker.budget})"
                    )
                    raise _CycleAbort(record.failure_reason)

                print("[6/7] Executing plan...")
                from execution.dialectic_execution import run_dialectic_execution

                exec_result = run_dialectic_execution(
                    plan_path=plan_result.get("plan_path_json"),
                    vision_context=VisionContext.SELF,
                )
                record.execution_attempted = True

                if not exec_result.get("overall_success"):
                    record.failure_reason = (
                        f"Execution failed: {exec_result.get('story_status', 'unknown')}"
                    )
                    raise _CycleAbort(record.failure_reason)

        except _CycleAbort as e:
            print(f"\n  Cycle aborted: {e}")
            record.total_tokens = tracker.total_tokens
            record.estimated_cost = tracker.estimated_cost
            _git_discard_branch(branch_name, project_root)
            _persist_record(store, record)
            return record
        except Exception as e:
            record.failure_reason = f"Unexpected error: {e}"
            print(f"\n  Unexpected error: {e}")
            record.total_tokens = tracker.total_tokens
            record.estimated_cost = tracker.estimated_cost
            _git_discard_branch(branch_name, project_root)
            _persist_record(store, record)
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
        print(f"  {post_tests['stdout_tail'][-200:]}")
        _git_discard_branch(branch_name, project_root)
        _persist_record(store, record)
        return record

    print("Validating: checking metrics stability...")
    stable, reason = _metrics_stable(store, report.baseline_metrics)
    record.metrics_stable = stable
    if not stable:
        record.failure_reason = f"Metrics regressed: {reason}"
        print(f"  FAIL: {record.failure_reason}")
        _git_discard_branch(branch_name, project_root)
        _persist_record(store, record)
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
