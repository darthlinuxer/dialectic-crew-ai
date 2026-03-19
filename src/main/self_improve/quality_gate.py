"""Quality gate module for self-improve validation."""

# pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
# pylint: disable=too-many-return-statements,too-many-statements

from __future__ import annotations

import logging
import os
from pathlib import Path

from dialectic.stack_validation import (
    ValidationStepResult,
    build_validation_plan,
    run_validation_plan,
    step_labels_for_profile,
)

from .quality_gate_helpers import (
    DEFAULT_QUALITY_GATE_TIMEOUT,
    build_mypy_command,
    build_repo_mypy_command,
    collect_touched_python_files,
    command_available,
    parse_pyright_output,
    resolve_python_targets,
    run_cmd,
)
from .quality_gate_checks import (
    run_mypy as _run_mypy_impl,
    run_pyright as _run_pyright_impl,
    run_ruff_check as _run_ruff_check_impl,
    run_ruff_format_check as _run_ruff_format_check_impl,
)
from .quality_gate_models import QualityCheckResult, QualityGateResult
from .quality_gate_output import print_quality_gate_result
from .quality_gate_remediation import (
    run_crew_remediation as _run_crew_remediation,
    run_python_remediation as _run_python_remediation,
    should_attempt_crew_remediation as _should_attempt_crew_remediation,
    should_attempt_python_remediation as _should_attempt_python_remediation,
)

logger = logging.getLogger(__name__)


def _run_ruff_check(
    project_root: Path,
    target_path: str = "src/",
    touched_files: list[str] | None = None,
) -> QualityCheckResult:
    """Run ruff linting check."""
    return _run_ruff_check_impl(
        project_root,
        target_path=target_path,
        touched_files=touched_files,
        command_available=command_available,
        resolve_python_targets=resolve_python_targets,
        run_cmd=run_cmd,
    )


def _run_ruff_format_check(
    project_root: Path,
    target_path: str = "src/",
    touched_files: list[str] | None = None,
) -> QualityCheckResult:
    """Run ruff format check (dry-run)."""
    return _run_ruff_format_check_impl(
        project_root,
        target_path=target_path,
        touched_files=touched_files,
        command_available=command_available,
        resolve_python_targets=resolve_python_targets,
        run_cmd=run_cmd,
    )


def _run_mypy(  # pylint: disable=too-many-return-statements
    project_root: Path,
    target_path: str = "src/",
    touched_files: list[str] | None = None,
) -> QualityCheckResult:
    """Run mypy type checking."""
    return _run_mypy_impl(
        project_root,
        target_path=target_path,
        touched_files=touched_files,
        command_available=command_available,
        resolve_python_targets=resolve_python_targets,
        run_cmd=run_cmd,
        build_mypy_command=build_mypy_command,
        build_repo_mypy_command=build_repo_mypy_command,
    )


def _run_pyright(
    project_root: Path,
    target_path: str = "src/",
    touched_files: list[str] | None = None,
) -> QualityCheckResult:
    """Run pyright type checking (optional, warn-only)."""
    return _run_pyright_impl(
        project_root,
        target_path=target_path,
        touched_files=touched_files,
        command_available=command_available,
        resolve_python_targets=resolve_python_targets,
        run_cmd=run_cmd,
        parse_pyright_output=parse_pyright_output,
    )


def run_quality_gate(
    project_root: Path,
    target_path: str = "src/",
    include_pyright: bool = True,
    allow_python_remediation: bool = True,
    previous_remediation_attempt_count: int = 0,
    max_python_remediation_attempts: int = 1,
) -> QualityGateResult:
    """Run all quality checks and return aggregated result."""

    def _crew_remediation_enabled() -> bool:
        raw_value = os.getenv(
            "DIALECTIC_SELF_IMPROVE_ENABLE_QUALITY_REPAIR_CREW",
            "",
        )
        return raw_value.strip().lower() in {"1", "true", "yes", "on"}

    def _copy_remediation_metadata(
        target: QualityGateResult,
        source: QualityGateResult,
    ) -> QualityGateResult:
        target.remediation_attempted = source.remediation_attempted
        target.remediation_attempt_count = source.remediation_attempt_count
        target.remediation_succeeded = source.remediation_succeeded
        target.remediation_steps = list(source.remediation_steps)
        target.remediation_failure_reason = source.remediation_failure_reason
        target.remediation_exhausted = source.remediation_exhausted
        return target

    del target_path
    touched_files = collect_touched_python_files(project_root)
    logger.info(
        "Running shared release validation plan for %s touched Python files...",
        len(touched_files),
    )
    plan = build_validation_plan(project_root)
    selected_labels = step_labels_for_profile(plan, "release")
    if not include_pyright:
        selected_labels = [label for label in selected_labels if label != "pyright"]

    current_result = _run_quality_gate_validation(project_root, selected_labels)
    current_result.remediation_attempt_count = previous_remediation_attempt_count
    if current_result.passed:
        current_result.build_summary()
        return current_result

    deterministic_attempted = False
    if allow_python_remediation and _should_attempt_python_remediation(
        current_result.checks,
        touched_files,
    ):
        if previous_remediation_attempt_count >= max_python_remediation_attempts:
            current_result.remediation_exhausted = True
            current_result.remediation_failure_reason = current_result.build_summary()
            return current_result

        remediation_attempted, remediation_steps = _run_python_remediation(
            project_root,
            touched_files,
        )
        if remediation_attempted:
            deterministic_attempted = True
            remediated_result = _run_quality_gate_validation(
                project_root, selected_labels
            )
            remediated_result.remediation_attempted = True
            remediated_result.remediation_attempt_count = (
                previous_remediation_attempt_count + 1
            )
            remediated_result.remediation_succeeded = remediated_result.passed
            remediated_result.remediation_steps = remediation_steps
            current_result = remediated_result
            if current_result.passed:
                current_result.build_summary()
                return current_result
            current_result.remediation_failure_reason = current_result.build_summary()

    crew_enabled = _crew_remediation_enabled()
    if (
        crew_enabled
        and previous_remediation_attempt_count < max_python_remediation_attempts
        and _should_attempt_crew_remediation(current_result.checks, touched_files)
    ):
        crew_attempted, crew_steps, _crew_summary = _run_crew_remediation(
            project_root,
            touched_files,
            current_result.checks,
        )
        if crew_attempted:
            crew_result = _run_quality_gate_validation(project_root, selected_labels)
            crew_result = _copy_remediation_metadata(crew_result, current_result)
            crew_result.remediation_attempted = True
            crew_result.remediation_attempt_count = (
                previous_remediation_attempt_count + 1
            )
            crew_result.remediation_succeeded = crew_result.passed
            crew_result.remediation_steps = list(
                dict.fromkeys([*current_result.remediation_steps, *crew_steps])
            )
            crew_result.remediation_exhausted = not crew_result.passed
            if not crew_result.passed:
                crew_result.remediation_failure_reason = crew_result.build_summary()
                return crew_result
            crew_result.build_summary()
            return crew_result

    current_result.remediation_exhausted = not current_result.passed and (
        current_result.remediation_attempt_count >= max_python_remediation_attempts
        or deterministic_attempted
    )
    if not current_result.passed:
        current_result.remediation_failure_reason = current_result.build_summary()
        return current_result

    current_result.build_summary()
    return current_result


def _run_quality_gate_validation(
    project_root: Path,
    selected_labels: list[str],
) -> QualityGateResult:
    """Run the shared validation plan and translate results to quality checks."""
    result = QualityGateResult(passed=True)
    report = run_validation_plan(project_root, include_steps=selected_labels)
    for step_result in report.results:
        result.add_check(_quality_check_from_validation_result(step_result))
    return result


def _quality_check_from_validation_result(
    step_result: ValidationStepResult,
) -> QualityCheckResult:
    """Translate a shared validation step result into quality-gate output."""
    output = step_result.stdout_tail or step_result.stderr_tail

    if step_result.label == "pyright":
        errors, error_count, warning_count = parse_pyright_output(
            output,
            step_result.returncode,
        )
        return QualityCheckResult(
            tool="pyright",
            passed=True,
            error_count=error_count,
            warning_count=warning_count,
            output=output,
            errors=errors,
        )

    errors = [output[:500]] if output and not step_result.passed else []
    return QualityCheckResult(
        tool=step_result.label,
        passed=step_result.passed,
        error_count=0 if step_result.passed else 1,
        output=output,
        errors=errors,
    )


__all__ = [
    "DEFAULT_QUALITY_GATE_TIMEOUT",
    "QualityCheckResult",
    "QualityGateResult",
    "build_mypy_command",
    "collect_touched_python_files",
    "command_available",
    "parse_pyright_output",
    "print_quality_gate_result",
    "resolve_python_targets",
    "run_cmd",
    "run_quality_gate",
]
