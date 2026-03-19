"""Reusable quality-check runners for self-improve validation."""

# pylint: disable=duplicate-code,too-many-arguments
# pylint: disable=too-many-locals,too-many-return-statements

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Callable

from .quality_gate_models import QualityCheckResult


CommandAvailable = Callable[[str], bool]
ResolveTargets = Callable[[Path, str, list[str] | None], list[str]]
RunCommand = Callable[..., subprocess.CompletedProcess[str]]
ParsePyright = Callable[[str, int], tuple[list[str], int, int]]
BuildMypyCommand = Callable[..., tuple[list[str], dict[str, str]] | None]
BuildRepoMypyCommand = Callable[[], tuple[list[str], dict[str, str]]]


def run_ruff_check(
    project_root: Path,
    *,
    target_path: str,
    touched_files: list[str] | None,
    command_available: CommandAvailable,
    resolve_python_targets: ResolveTargets,
    run_cmd: RunCommand,
) -> QualityCheckResult:
    """Run Ruff linting for the selected Python targets."""
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
                    errors.append(
                        f"{issue.get('filename', '?')}:{loc.get('row', '?')}: "
                        f"{issue.get('code', '?')} {issue.get('message', '')}"
                    )
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


def run_ruff_format_check(
    project_root: Path,
    *,
    target_path: str,
    touched_files: list[str] | None,
    command_available: CommandAvailable,
    resolve_python_targets: ResolveTargets,
    run_cmd: RunCommand,
) -> QualityCheckResult:
    """Run Ruff format dry-run for the selected Python targets."""
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


def run_mypy(
    project_root: Path,
    *,
    target_path: str,
    touched_files: list[str] | None,
    command_available: CommandAvailable,
    resolve_python_targets: ResolveTargets,
    run_cmd: RunCommand,
    build_mypy_command: BuildMypyCommand,
    build_repo_mypy_command: BuildRepoMypyCommand,
) -> QualityCheckResult:
    """Run mypy with precise-path and fallback package-level strategies."""
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

    def _execute(
        command_and_env: tuple[list[str], dict[str, str]],
    ) -> QualityCheckResult:
        cmd, env = command_and_env
        result = run_cmd([*cmd, "--no-error-summary"], project_root, env=env)
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
        precise_result = _execute(mypy_command)
        if precise_result.passed or touched_files is None:
            return precise_result

        fallback_command = build_mypy_command(
            python_targets,
            prefer_precise_paths=False,
        )
        if fallback_command is None:
            return precise_result

        fallback_result = _execute(fallback_command)
        if fallback_result.passed:
            fallback_result.output = (
                "Precise-path mypy failed; package-level fallback passed.\n"
                f"Precise summary: {precise_result.output[:400]}"
            )
            return fallback_result

        canonical_result = _execute(build_repo_mypy_command())
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


def run_pyright(
    project_root: Path,
    *,
    target_path: str,
    touched_files: list[str] | None,
    command_available: CommandAvailable,
    resolve_python_targets: ResolveTargets,
    run_cmd: RunCommand,
    parse_pyright_output: ParsePyright,
) -> QualityCheckResult:
    """Run warn-only pyright validation for the selected Python targets."""
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
