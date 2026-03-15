"""CrewAI verbose and log file configuration from environment."""

from __future__ import annotations

import os
from pathlib import Path

_CREWAI_VERBOSE_ENV = "CREWAI_VERBOSE"
_CREWAI_OUTPUT_LOG_FILE_ENV = "CREWAI_OUTPUT_LOG_FILE"
_DEFAULT_LOG_DIR = ".dialectic"
_DEFAULT_CREWAI_LOG_NAME = "crewai_verbose.log"


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def is_verbose() -> bool:
    """Return True if CrewAI verbose logging is enabled (CREWAI_VERBOSE). Default False."""
    return _parse_bool(os.getenv(_CREWAI_VERBOSE_ENV), False)


def get_output_log_file() -> str | None:
    """
    Return the path to which CrewAI should write verbose logs, or None.

    When CREWAI_VERBOSE is true and CREWAI_OUTPUT_LOG_FILE is set, returns that path.
    When CREWAI_VERBOSE is true and CREWAI_OUTPUT_LOG_FILE is unset, returns a path
    under DIALECTIC_LOG_DIR (or .dialectic): crewai_verbose.log.
    When CREWAI_VERBOSE is false, returns None.
    """
    if not is_verbose():
        return None
    raw = os.getenv(_CREWAI_OUTPUT_LOG_FILE_ENV)
    if raw is not None and raw.strip():
        return Path(raw.strip()).expanduser().as_posix()
    log_dir = Path(os.getenv("DIALECTIC_LOG_DIR", _DEFAULT_LOG_DIR)).expanduser()
    return (log_dir / _DEFAULT_CREWAI_LOG_NAME).as_posix()
