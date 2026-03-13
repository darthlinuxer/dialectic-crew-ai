"""Pytest snapshot helpers for the self-improve orchestrator."""

from __future__ import annotations

import subprocess
import textwrap
from pathlib import Path
from typing import Callable, Protocol


class _LoggerLike(Protocol):
    def warning(self, msg: str, *args) -> None: ...


def self_improve_test_timeout(
    raw_value: str | None,
    *,
    default_timeout: int,
    logger: _LoggerLike,
) -> int:
    """Resolve the pytest timeout used by self-improvement validation."""
    raw = raw_value or str(default_timeout)
    try:
        timeout = int(raw)
    except ValueError:
        logger.warning(
            "Invalid SELF_IMPROVE_TEST_TIMEOUT=%r; using default %s",
            raw,
            default_timeout,
        )
        return default_timeout
    if timeout <= 0:
        logger.warning(
            "Non-positive SELF_IMPROVE_TEST_TIMEOUT=%r; using default %s",
            raw,
            default_timeout,
        )
        return default_timeout
    return timeout


def pytest_command(
    *,
    command_available_fn: Callable[[str], bool],
    python_executable: str,
) -> list[str]:
    """Prefer uv-managed pytest, then fall back to the active Python environment."""
    if command_available_fn("uv"):
        return ["uv", "run", "pytest", "--tb=short", "-q", "--reruns", "1"]
    return [python_executable, "-m", "pytest", "--tb=short", "-q", "--reruns", "1"]


def snapshot_tests(
    project_root: Path,
    *,
    timeout: int | None,
    timeout_resolver: Callable[[], int],
    pytest_command_fn: Callable[[], list[str]],
    run_cmd_fn: Callable[..., subprocess.CompletedProcess[str]],
) -> dict:
    """Run pytest and return pass/fail summary."""
    resolved_timeout = timeout or timeout_resolver()
    cmd = pytest_command_fn()
    try:
        result = run_cmd_fn(cmd, cwd=project_root, timeout=resolved_timeout)
        return {
            "returncode": result.returncode,
            "passed": result.returncode == 0,
            "timed_out": False,
            "timeout_seconds": resolved_timeout,
            "command": cmd,
            "stdout_tail": result.stdout[-500:] if result.stdout else "",
            "stderr_tail": result.stderr[-500:] if result.stderr else "",
        }
    except subprocess.TimeoutExpired as exc:
        stdout_tail = exc.output[-500:] if isinstance(exc.output, str) and exc.output else ""
        stderr_tail = exc.stderr[-500:] if isinstance(exc.stderr, str) and exc.stderr else ""
        return {
            "returncode": -1,
            "passed": False,
            "timed_out": True,
            "timeout_seconds": resolved_timeout,
            "command": cmd,
            "stdout_tail": stdout_tail,
            "stderr_tail": stderr_tail,
        }


def emit_test_failure_details(
    snapshot: dict,
    prefix: str = "  ",
    *,
    print_fn: Callable[[str], None] = print,
) -> None:
    """Print concise diagnostics for a failing pytest snapshot."""
    cmd = snapshot.get("command") or []
    command_str = " ".join(cmd) if cmd else "pytest"
    timeout_seconds = snapshot.get("timeout_seconds")
    if snapshot.get("timed_out"):
        print_fn(f"{prefix}Pytest timed out after {timeout_seconds}s: {command_str}")
    else:
        print_fn(f"{prefix}Pytest exited with code {snapshot.get('returncode')}: {command_str}")

    stdout_tail = (snapshot.get("stdout_tail") or "").strip()
    stderr_tail = (snapshot.get("stderr_tail") or "").strip()

    if stdout_tail:
        print_fn(f"{prefix}stdout tail:")
        print_fn(textwrap.indent(stdout_tail[-500:], prefix + "  "))
    if stderr_tail:
        print_fn(f"{prefix}stderr tail:")
        print_fn(textwrap.indent(stderr_tail[-500:], prefix + "  "))