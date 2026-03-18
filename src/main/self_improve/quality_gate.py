"""Quality gate module for self-improve validation.

Runs comprehensive code quality checks: ruff, mypy, pyright (optional).
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .quality_gate_helpers import (
    DEFAULT_QUALITY_GATE_TIMEOUT,
    build_mypy_command,
    collect_touched_python_files,
    command_available,
    parse_pyright_output,
    resolve_python_targets,
    run_cmd,
)

logger = logging.getLogger(__name__)


@dataclass
class QualityCheckResult:
    """Result of a single quality check."""

    tool: str
    passed: bool
    error_count: int = 0
    warning_count: int = 0
    output: str = ""
    errors: list[str] = field(default_factory=list)


@dataclass
class QualityGateResult:
    """Aggregated result of all quality checks."""

    passed: bool
    checks: list[QualityCheckResult] = field(default_factory=list)
    summary: str = ""

    def add_check(self, check: QualityCheckResult) -> None:
        """Record a check result and update aggregate pass/fail state."""
        self.checks.append(check)
        if not check.passed:
            self.passed = False

    def build_summary(self) -> str:
        """Build and cache a single-line human-readable summary."""
        lines = []
        for check in self.checks:
            status = "PASS" if check.passed else "FAIL"
            lines.append(f"{check.tool}: {status} ({check.error_count} errors)")
        self.summary = "; ".join(lines)
        return self.summary


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


def _run_mypy(
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

    cmd, env = mypy_command
    cmd.append("--no-error-summary")
    try:
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
) -> QualityGateResult:
    """Run all quality checks and return aggregated result."""
    result = QualityGateResult(passed=True)
    touched_files = collect_touched_python_files(project_root)

    logger.info("Running ruff lint check...")
    result.add_check(
        _run_ruff_check(project_root, target_path, touched_files=touched_files)
    )

    logger.info("Running ruff format check...")
    result.add_check(
        _run_ruff_format_check(project_root, target_path, touched_files=touched_files)
    )

    logger.info("Running mypy type check...")
    result.add_check(_run_mypy(project_root, target_path, touched_files=touched_files))

    if include_pyright:
        logger.info("Running pyright type check (warn-only)...")
        result.add_check(
            _run_pyright(project_root, target_path, touched_files=touched_files)
        )

    result.build_summary()
    return result


def print_quality_gate_result(
    result: QualityGateResult,
    prefix: str = "  ",
) -> None:
    """Print quality gate results to console."""
    for check in result.checks:
        status = "PASS" if check.passed else "FAIL"
        print(f"{prefix}{check.tool}: {status}")
        if check.errors:
            for error in check.errors[:5]:
                print(f"{prefix}  {error}")
            if len(check.errors) > 5:
                print(f"{prefix}  ... and {len(check.errors) - 5} more")


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
