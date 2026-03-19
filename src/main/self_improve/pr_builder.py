"""PR creation and reporting helpers for self-improve cycles."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Protocol

from schemas import IntrospectionReport, SelfImprovementRecord


class _LoggerLike(Protocol):
    def warning(self, msg: str, *args) -> None: ...


def create_pr(
    branch: str,
    title: str,
    body: str,
    cwd: Path,
    *,
    command_available_fn: Callable[[str], bool],
    run_cmd_fn,
    logger: _LoggerLike,
) -> str | None:
    if not command_available_fn("gh"):
        logger.warning("PR creation skipped: GitHub CLI (gh) not found")
        return None

    push_result = run_cmd_fn(
        ["git", "push", "-u", "origin", branch],
        cwd=cwd,
        timeout=60,
    )
    if push_result.returncode != 0:
        logger.warning("PR branch push failed: %s", push_result.stderr)
        return None

    result = run_cmd_fn(
        ["gh", "pr", "create", "--title", title, "--body", body, "--head", branch],
        cwd=cwd,
        timeout=60,
    )
    if result.returncode == 0:
        return result.stdout.strip()

    logger.warning("PR creation failed: %s", result.stderr)
    return None


def print_report(report: IntrospectionReport, max_items: int) -> None:
    print(f"\nIntrospection Report ({report.timestamp})")
    print(f"{'=' * 60}")
    for index, opportunity in enumerate(report.opportunities):
        marker = ">>>" if index < max_items else "   "
        print(
            f"  {marker} [{opportunity.estimated_impact.upper():>6}] {opportunity.id}: {opportunity.title}"
        )
        if opportunity.evidence:
            print(f"         Evidence: {', '.join(opportunity.evidence[:3])}")
    print("\nBaseline metrics:")
    for key, value in report.baseline_metrics.items():
        if value.get("count", 0) > 0:
            print(f"  {key}: mean={value['mean']:.1f}, count={value['count']}")


def build_pr_body(
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
    for opportunity in selected:
        lines.append(
            f"- **{opportunity.title}** ({opportunity.category}, {opportunity.estimated_impact})"
        )
        lines.append(f"  {opportunity.description}")
    lines.extend(
        [
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
        ]
    )
    for key, value in report.baseline_metrics.items():
        if value.get("count", 0) > 0:
            lines.append(f"- {key}: mean={value['mean']:.1f}")
    return "\n".join(lines)


__all__ = ["build_pr_body", "create_pr", "print_report"]
