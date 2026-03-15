"""Quality gate module for self-improve validation.

Runs comprehensive code quality checks: ruff, mypy, pyright (optional).
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_QUALITY_GATE_TIMEOUT = 120


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
        self.checks.append(check)
        if not check.passed:
            self.passed = False

    def build_summary(self) -> str:
        lines = []
        for check in self.checks:
            status = "PASS" if check.passed else "FAIL"
            lines.append(f"{check.tool}: {status} ({check.error_count} errors)")
        self.summary = "; ".join(lines)
        return self.summary


def _command_available(command: str) -> bool:
    return shutil.which(command) is not None


def _run_cmd(
    cmd: list[str],
    cwd: Path,
    timeout: int = DEFAULT_QUALITY_GATE_TIMEOUT,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _run_ruff_check(
    project_root: Path,
    target_path: str = "src/",
) -> QualityCheckResult:
    """Run ruff linting check."""
    if not _command_available("ruff"):
        return QualityCheckResult(
            tool="ruff-lint",
            passed=True,
            output="ruff not available, skipping",
        )

    target = project_root / target_path
    if not target.exists():
        return QualityCheckResult(
            tool="ruff-lint",
            passed=True,
            output=f"Target path {target_path} does not exist, skipping",
        )

    cmd = ["ruff", "check", str(target), "--output-format=json"]
    try:
        result = _run_cmd(cmd, project_root)
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
) -> QualityCheckResult:
    """Run ruff format check (dry-run)."""
    if not _command_available("ruff"):
        return QualityCheckResult(
            tool="ruff-format",
            passed=True,
            output="ruff not available, skipping",
        )

    target = project_root / target_path
    if not target.exists():
        return QualityCheckResult(
            tool="ruff-format",
            passed=True,
            output=f"Target path {target_path} does not exist, skipping",
        )

    cmd = ["ruff", "format", "--check", "--diff", str(target)]
    try:
        result = _run_cmd(cmd, project_root)
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
) -> QualityCheckResult:
    """Run mypy type checking."""
    if not _command_available("mypy"):
        return QualityCheckResult(
            tool="mypy",
            passed=True,
            output="mypy not available, skipping",
        )

    target = project_root / target_path
    if not target.exists():
        return QualityCheckResult(
            tool="mypy",
            passed=True,
            output=f"Target path {target_path} does not exist, skipping",
        )

    cmd = ["mypy", str(target), "--no-error-summary"]
    try:
        result = _run_cmd(cmd, project_root)
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
) -> QualityCheckResult:
    """Run pyright type checking (optional, warn-only)."""
    if not _command_available("pyright"):
        return QualityCheckResult(
            tool="pyright",
            passed=True,
            output="pyright not available, skipping",
        )

    target = project_root / target_path
    if not target.exists():
        return QualityCheckResult(
            tool="pyright",
            passed=True,
            output=f"Target path {target_path} does not exist, skipping",
        )

    cmd = ["pyright", str(target), "--outputjson"]
    try:
        result = _run_cmd(cmd, project_root)
        errors: list[str] = []
        error_count = 0
        warning_count = 0

        if result.stdout.strip():
            try:
                data = json.loads(result.stdout)
                diagnostics = data.get("generalDiagnostics", [])
                for diag in diagnostics:
                    if diag.get("severity") == 1:
                        error_count += 1
                    else:
                        warning_count += 1
                for diag in diagnostics[:10]:
                    file_path = diag.get("file", "?")
                    rng = diag.get("range", {}).get("start", {})
                    msg = (
                        f"{file_path}:{rng.get('line', '?')}: "
                        f"{diag.get('message', '')}"
                    )
                    errors.append(msg)
                if len(diagnostics) > 10:
                    errors.append(f"... and {len(diagnostics) - 10} more")
            except json.JSONDecodeError:
                if result.returncode != 0:
                    errors.append(result.stdout[:500])
                    error_count = 1

        return QualityCheckResult(
            tool="pyright",
            passed=True,  # pyright is warn-only
            error_count=error_count,
            warning_count=warning_count,
            output=result.stdout[:1000],
            errors=errors,
        )
    except subprocess.TimeoutExpired:
        return QualityCheckResult(
            tool="pyright",
            passed=True,  # warn-only
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
    """Run all quality checks and return aggregated result.

    Args:
        project_root: Root directory of the project.
        target_path: Relative path to check (default: src/).
        include_pyright: Whether to run pyright (warn-only).

    Returns:
        QualityGateResult with all check results.
    """
    result = QualityGateResult(passed=True)

    logger.info("Running ruff lint check...")
    result.add_check(_run_ruff_check(project_root, target_path))

    logger.info("Running ruff format check...")
    result.add_check(_run_ruff_format_check(project_root, target_path))

    logger.info("Running mypy type check...")
    result.add_check(_run_mypy(project_root, target_path))

    if include_pyright:
        logger.info("Running pyright type check (warn-only)...")
        result.add_check(_run_pyright(project_root, target_path))

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
