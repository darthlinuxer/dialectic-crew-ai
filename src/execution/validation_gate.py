"""Execution-time hard gate for stack-aware validation."""

from __future__ import annotations

from typing import Literal

from dialectic.stack_validation import (
    ValidationPlan,
    ValidationStepResult,
    build_validation_plan,
    run_validation_plan,
    step_labels_for_profile,
)
from dialectic.vision import resolve_project_root
from schemas import VerificationResult


ValidationProfile = Literal["task", "story"]


def run_stack_validation_gate(profile: ValidationProfile = "task") -> VerificationResult:
    """Run the allowlisted stack validation plan as an execution hard gate."""
    project_root = resolve_project_root()
    plan = build_validation_plan(project_root)
    selected_labels = step_labels_for_profile(plan, profile)

    if not plan.steps or not selected_labels:
        return VerificationResult(
            verified=True,
            notes=f"No stack validation steps detected for {profile} profile.",
        )

    report = run_validation_plan(plan.project_root, include_steps=selected_labels)
    passed = [f"stack validation: {result.label}" for result in report.results if result.passed]
    failed = [f"stack validation: {result.label}" for result in report.results if not result.passed]

    return VerificationResult(
        verified=report.passed,
        checks_passed=passed,
        checks_failed=failed,
        notes=_render_validation_notes(plan, report.passed, selected_labels, report.results),
    )


def _render_validation_notes(
    plan: ValidationPlan,
    passed: bool,
    selected_labels: list[str],
    results: list[ValidationStepResult],
) -> str:
    stack_summary = ", ".join(plan.detected_stacks) if plan.detected_stacks else "none"
    selected_summary = ", ".join(selected_labels)
    if passed:
        return (
            "Stack validation passed for "
            f"[{stack_summary}] using steps: {selected_summary}."
        )

    failed_details = []
    for result in results:
        if result.passed:
            continue
        detail = (
            result.reason
            or result.stderr_tail
            or result.stdout_tail
            or "unknown failure"
        )
        failed_details.append(f"{result.label}: {detail[:160]}")

    detail_summary = "; ".join(failed_details) if failed_details else "unknown failure"
    return (
        "Stack validation failed for "
        f"[{stack_summary}] using steps: {selected_summary}. {detail_summary}"
    )
