"""Quality gate module for self-improve validation.

Runs comprehensive code quality checks: ruff, mypy, pyright (optional).
"""

from __future__ import annotations

import json
import logging
import subprocess
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
from .quality_gate_models import QualityCheckResult, QualityGateResult
from .quality_gate_output import print_quality_gate_result
from .quality_gate_remediation import (
    run_python_remediation as _run_python_remediation,
    should_attempt_python_remediation as _should_attempt_python_remediation,
)

logger = logging.getLogger(__name__)


def _run_ruff_check(
    project_root: Path,
    target_path: str = "src/",
    touched_files: list[str] | None = None,
) -> QualityCheckResult:
    """Run ruff linting check."""
    if not command_available("ruff"):
        return QualityCheckResult(
            tool="ruff-lint",
            passed=True,
            output="ruff not available, skipping",
        )

    if touched_files is None:
        target = project_root / target_path
        if not target.exists():
            return QualityCheckResult(
                tool="ruff-lint",
                passed=True,
                output=f"Target path {target_path} does not exist, skipping",
            )

    targets = resolve_python_targets(project_root, target_path, touched_files)
    if not targets:
        return QualityCheckResult(
            tool="ruff-lint",
            passed=True,
            output="No touched Python source files to lint, skipping",
        )

    cmd = ["ruff", "check", *targets, "--output-format=json"]
    try:
        result = run_cmd(cmd, project_root)
        errors: list[str] = []
        error_count = 0

        if result.stdout.strip():
            try:
                issues = json.loads(result.stdout)
                error_count = len(issues)
                for issue in issues[:10]:
                    loc = issue.get("location", {})
                    msg = (
                        f"{issue.get('filename', '?')}:{loc.get('row', '?')}: "
                        f"{issue.get('code', '?')} {issue.get('message', '')}"
                    )
                    errors.append(msg)
                if error_count > 10:
                    errors.append(f"... and {error_count - 10} more")
            except json.JSONDecodeError:
                errors.append(result.stdout[:500])
                error_count = 1 if result.returncode != 0 else 0

        return QualityCheckResult(
            tool="ruff-lint",
            passed=result.returncode == 0,
            error_count=error_count,
            output=result.stdout[:1000],
            errors=errors,
        )
    except subprocess.TimeoutExpired:
        return QualityCheckResult(
            tool="ruff-lint",
            passed=False,
            error_count=1,
            output="Timeout expired",
            errors=["ruff check timed out"],
        )


def _run_ruff_format_check(
    project_root: Path,
    target_path: str = "src/",
    touched_files: list[str] | None = None,
) -> QualityCheckResult:
    """Run ruff format check (dry-run)."""
    if not command_available("ruff"):
        return QualityCheckResult(
            tool="ruff-format",
            passed=True,
            output="ruff not available, skipping",
        )

    if touched_files is None:
        target = project_root / target_path
        if not target.exists():
            return QualityCheckResult(
                tool="ruff-format",
                passed=True,
                output=f"Target path {target_path} does not exist, skipping",
            )

    targets = resolve_python_targets(project_root, target_path, touched_files)
    if not targets:
        return QualityCheckResult(
            tool="ruff-format",
            passed=True,
            output="No touched Python source files to format-check, skipping",
        )

    cmd = ["ruff", "format", "--check", "--diff", *targets]
    try:
        result = run_cmd(cmd, project_root)
        errors: list[str] = []
        if result.returncode != 0 and result.stdout.strip():
            diff_lines = result.stdout.strip().split("\n")
            errors = diff_lines[:20]
            if len(diff_lines) > 20:
                errors.append(f"... and {len(diff_lines) - 20} more lines")

        return QualityCheckResult(
            tool="ruff-format",
            passed=result.returncode == 0,
            error_count=1 if result.returncode != 0 else 0,
            output=result.stdout[:1000],
            errors=errors,
        )
    except subprocess.TimeoutExpired:
        return QualityCheckResult(
            tool="ruff-format",
            passed=False,
            error_count=1,
            output="Timeout expired",
            errors=["ruff format check timed out"],
        )


def _run_mypy(  # pylint: disable=too-many-return-statements
    project_root: Path,
    target_path: str = "src/",
    touched_files: list[str] | None = None,
) -> QualityCheckResult:
    """Run mypy type checking."""
    if not command_available("mypy"):
        return QualityCheckResult(
            tool="mypy",
            passed=True,
            output="mypy not available, skipping",
        )

    if touched_files is None:
        target = project_root / target_path
        if not target.exists():
            return QualityCheckResult(
                tool="mypy",
                passed=True,
                output=f"Target path {target_path} does not exist, skipping",
            )

    python_targets = resolve_python_targets(project_root, target_path, touched_files)
    mypy_command = build_mypy_command(
        python_targets,
        prefer_precise_paths=touched_files is not None,
    )
    if mypy_command is None:
        return QualityCheckResult(
            tool="mypy",
            passed=True,
            output="No touched typed source modules to type-check, skipping",
        )

    def _execute_mypy(
        command_and_env: tuple[list[str], dict[str, str]],
    ) -> QualityCheckResult:
        cmd, env = command_and_env
        cmd = [*cmd, "--no-error-summary"]
        result = run_cmd(cmd, project_root, env=env)
        errors: list[str] = []
        error_count = 0

        if result.stdout.strip():
            lines = result.stdout.strip().split("\n")
            error_lines = [ln for ln in lines if ": error:" in ln]
            error_count = len(error_lines)
            errors = error_lines[:10]
            if error_count > 10:
                errors.append(f"... and {error_count - 10} more errors")

        return QualityCheckResult(
            tool="mypy",
            passed=result.returncode == 0,
            error_count=error_count,
            output=result.stdout[:1000],
            errors=errors,
        )

    try:
        precise_result = _execute_mypy(mypy_command)
        if precise_result.passed or touched_files is None:
            return precise_result

        fallback_command = build_mypy_command(
            python_targets,
            prefer_precise_paths=False,
        )
        if fallback_command is None:
            return precise_result

        fallback_result = _execute_mypy(fallback_command)
        if fallback_result.passed:
            fallback_result.output = (
                "Precise-path mypy failed; package-level fallback passed.\n"
                f"Precise summary: {precise_result.output[:400]}"
            )
            return fallback_result

        canonical_result = _execute_mypy(build_repo_mypy_command())
        if canonical_result.passed:
            canonical_result.output = (
                "Precise-path and derived package-level mypy failed; "
                "canonical repo-wide fallback passed.\n"
                f"Precise summary: {precise_result.output[:400]}"
            )
            return canonical_result

        return precise_result
    except subprocess.TimeoutExpired:
        return QualityCheckResult(
            tool="mypy",
            passed=False,
            error_count=1,
            output="Timeout expired",
            errors=["mypy timed out"],
        )


def _run_pyright(
    project_root: Path,
    target_path: str = "src/",
    touched_files: list[str] | None = None,
) -> QualityCheckResult:
    """Run pyright type checking (optional, warn-only)."""
    if not command_available("pyright"):
        return QualityCheckResult(
            tool="pyright",
            passed=True,
            output="pyright not available, skipping",
        )

    if touched_files is None:
        target = project_root / target_path
        if not target.exists():
            return QualityCheckResult(
                tool="pyright",
                passed=True,
                output=f"Target path {target_path} does not exist, skipping",
            )

    targets = resolve_python_targets(project_root, target_path, touched_files)
    if not targets:
        return QualityCheckResult(
            tool="pyright",
            passed=True,
            output="No touched Python source files to type-check with pyright, skipping",
        )

    cmd = ["pyright", "--project", "pyrightconfig.json", *targets, "--outputjson"]
    try:
        result = run_cmd(cmd, project_root)
        errors, error_count, warning_count = parse_pyright_output(
            result.stdout,
            result.returncode,
        )

        return QualityCheckResult(
            tool="pyright",
            passed=True,
            error_count=error_count,
            warning_count=warning_count,
            output=result.stdout[:1000],
            errors=errors,
        )
    except subprocess.TimeoutExpired:
        return QualityCheckResult(
            tool="pyright",
            passed=True,
            error_count=0,
            warning_count=1,
            output="Timeout expired",
            errors=["pyright timed out"],
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

    initial_result = _run_quality_gate_validation(project_root, selected_labels)
    initial_result.remediation_attempt_count = previous_remediation_attempt_count
    if (
        initial_result.passed
        or not allow_python_remediation
        or not _should_attempt_python_remediation(initial_result.checks, touched_files)
    ):
        if (
            not initial_result.passed
            and previous_remediation_attempt_count >= max_python_remediation_attempts
        ):
            initial_result.remediation_exhausted = True
            initial_result.remediation_failure_reason = initial_result.build_summary()
        else:
            initial_result.build_summary()
        return initial_result

    if previous_remediation_attempt_count >= max_python_remediation_attempts:
        initial_result.remediation_exhausted = True
        initial_result.remediation_failure_reason = initial_result.build_summary()
        return initial_result

    remediation_attempted, remediation_steps = _run_python_remediation(
        project_root,
        touched_files,
    )
    if not remediation_attempted:
        initial_result.build_summary()
        return initial_result

    remediated_result = _run_quality_gate_validation(project_root, selected_labels)
    remediated_result.remediation_attempted = True
    remediated_result.remediation_attempt_count = previous_remediation_attempt_count + 1
    remediated_result.remediation_succeeded = remediated_result.passed
    remediated_result.remediation_steps = remediation_steps
    remediated_result.remediation_exhausted = (
        not remediated_result.passed
        and remediated_result.remediation_attempt_count
        >= max_python_remediation_attempts
    )
    if not remediated_result.passed:
        remediated_result.remediation_failure_reason = remediated_result.build_summary()
        return remediated_result

    remediated_result.build_summary()
    return remediated_result


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
