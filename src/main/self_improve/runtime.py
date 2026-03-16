"""Runtime/config helpers for the self-improve orchestrator."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path

from dialectic.crewai_runtime import configure_crewai_runtime

from .git_helpers import run_cmd
from .test_runner import self_improve_test_timeout

from .paths import DEFAULT_SELF_IMPROVE_PRD_MIN_SCORE, DEFAULT_SELF_IMPROVE_TEST_TIMEOUT

logger = logging.getLogger(__name__)


def _configure_crewai_runtime() -> None:
    """Apply runtime defaults that keep self-improve runs deterministic."""
    configure_crewai_runtime()


def _command_available(command: str) -> bool:
    return shutil.which(command) is not None


def _run_cmd(
    cmd: list[str],
    cwd: str | Path | None = None,
    timeout: int = 120,
) -> subprocess.CompletedProcess[str]:
    return run_cmd(cmd, cwd=cwd, timeout=timeout)


def _self_improve_test_timeout() -> int:
    """Return the pytest timeout used by self-improvement validation."""
    return self_improve_test_timeout(
        os.getenv("SELF_IMPROVE_TEST_TIMEOUT"),
        default_timeout=DEFAULT_SELF_IMPROVE_TEST_TIMEOUT,
        logger=logger,
    )


def _self_improve_prd_min_score() -> float:
    """Return the minimum PRD score that allows self-improve to continue."""
    raw_value = os.getenv("SELF_IMPROVE_MIN_PRD_SCORE")
    if raw_value in {None, ""}:
        return DEFAULT_SELF_IMPROVE_PRD_MIN_SCORE
    assert raw_value is not None
    try:
        score = float(raw_value)
    except ValueError:
        logger.warning(
            "Invalid SELF_IMPROVE_MIN_PRD_SCORE=%r; using default %s",
            raw_value,
            DEFAULT_SELF_IMPROVE_PRD_MIN_SCORE,
        )
        return DEFAULT_SELF_IMPROVE_PRD_MIN_SCORE
    if not 0.0 <= score <= 10.0:
        logger.warning(
            "Out-of-range SELF_IMPROVE_MIN_PRD_SCORE=%r; using default %s",
            raw_value,
            DEFAULT_SELF_IMPROVE_PRD_MIN_SCORE,
        )
        return DEFAULT_SELF_IMPROVE_PRD_MIN_SCORE
    return score


__all__ = [
    "_configure_crewai_runtime",
    "_command_available",
    "_run_cmd",
    "_self_improve_test_timeout",
    "_self_improve_prd_min_score",
]

