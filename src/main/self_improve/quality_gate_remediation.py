"""Deterministic remediation helpers for self-improve quality-gate failures."""

from __future__ import annotations

from importlib import import_module
import logging
from pathlib import Path

from .quality_gate_helpers import DEFAULT_QUALITY_GATE_TIMEOUT
from .quality_gate_models import QualityCheckResult, RemediationAction


logger = logging.getLogger(__name__)


def _quality_gate_module():
    return import_module("src.main.self_improve.quality_gate")


def python_remediation_actions(
    project_root: Path,
    touched_files: list[str],
) -> list[RemediationAction]:
    """Return bounded Python remediation actions for touched files."""
    quality_gate = _quality_gate_module()
    if not touched_files or not quality_gate.command_available("ruff"):
        return []

    targets = quality_gate.resolve_python_targets(
        project_root,
        "src/",
        touched_files=touched_files,
    )
    if not targets:
        return []

    return [
        RemediationAction(
            label="ruff-format-fix",
            command=["ruff", "format", *targets],
            reason="Apply deterministic Ruff formatting to touched Python files.",
        ),
        RemediationAction(
            label="ruff-lint-fix",
            command=["ruff", "check", "--fix", *targets],
            reason="Apply deterministic Ruff lint fixes to touched Python files.",
        ),
    ]


def run_python_remediation(
    project_root: Path,
    touched_files: list[str],
) -> tuple[bool, list[str]]:
    """Run bounded Python remediation and report whether any change was attempted."""
    quality_gate = _quality_gate_module()
    executed_steps: list[str] = []
    for action in python_remediation_actions(project_root, touched_files):
        logger.info("Running remediation step %s: %s", action.label, action.reason)
        quality_gate.run_cmd(
            action.command,
            project_root,
            timeout=DEFAULT_QUALITY_GATE_TIMEOUT,
        )
        executed_steps.append(action.label)
    return bool(executed_steps), executed_steps


def should_attempt_python_remediation(
    checks: list[QualityCheckResult],
    touched_files: list[str],
) -> bool:
    """Return whether failed checks warrant deterministic Python remediation."""
    if not touched_files:
        return False
    failing_tools = {check.tool for check in checks if not check.passed}
    return bool(failing_tools & {"ruff", "ruff-format", "mypy"})
