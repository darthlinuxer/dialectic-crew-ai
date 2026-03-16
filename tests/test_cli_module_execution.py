"""Regression tests for runnable CLI module surfaces."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _module_env() -> dict[str, str]:
    env = os.environ.copy()
    python_path_entries = [str(REPO_ROOT), str(REPO_ROOT / "src")]
    existing_pythonpath = env.get("PYTHONPATH")
    if existing_pythonpath:
        python_path_entries.append(existing_pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(python_path_entries)
    return env


@pytest.mark.parametrize("module_name", ["src.main.cli", "main.cli"])
def test_cli_module_supports_self_improve_help(module_name: str) -> None:
    """Each supported CLI module surface should render self-improve help."""
    result = subprocess.run(
        [sys.executable, "-m", module_name, "self-improve", "--help"],
        capture_output=True,
        cwd=REPO_ROOT,
        env=_module_env(),
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "self-improve" in result.stdout
    assert "skip-baseline-tests" in result.stdout
