"""CrewAI runtime defaults for this project.

The app disables external telemetry by default and runs primarily in
non-interactive CLI contexts. CrewAI's first-run tracing prompt can spawn an
input thread after successful executions, which is undesirable in automated or
captured runs. This helper applies safe defaults while preserving explicit user
opt-in to tracing via environment variables.

When verbose logs are routed to a file (CREWAI_OUTPUT_LOG_FILE), run_crew_kickoff
runs the crew without flooding the console. In contexts without the native
CrewAI event bridge, it then prints an LLM-generated 4-5 line summary instead
of the full verbose stream.
"""

# pylint: disable=import-outside-toplevel,broad-exception-caught

from __future__ import annotations

import logging
import os
import sys
from collections.abc import Callable
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from typing import Any

from dialectic.crewai_event_logger import is_crewai_event_logger_registered
from dialectic.crew_log_summarizer import summarize_crew_log
from dialectic.crew_verbose_config import get_output_log_file

logger = logging.getLogger(__name__)


def _load_tracing_utils() -> tuple[
    Callable[[bool], object] | None,
    Callable[..., Any] | None,
    Any | None,
    type[Any] | None,
]:
    try:
        from crewai.events.listeners.tracing.first_time_trace_handler import (
            FirstTimeTraceHandler,
        )
        from crewai.events.listeners.tracing.utils import (
            _first_time_trace_hook,
            mark_first_execution_done,
            set_suppress_tracing_messages,
        )
    except Exception:  # pragma: no cover - defensive import fallback
        return None, None, None, None
    return (
        set_suppress_tracing_messages,
        mark_first_execution_done,
        _first_time_trace_hook,
        FirstTimeTraceHandler,
    )


def _is_tracing_explicitly_enabled() -> bool:
    return os.getenv("CREWAI_TRACING_ENABLED", "").lower() in {"true", "1"}


def configure_crewai_runtime() -> None:
    """Apply deterministic CrewAI defaults for this application.

    Behavior:
    - Disable CrewAI telemetry by default.
    - Default tracing to disabled unless the user explicitly enabled it.
    - Suppress the first-run trace prompt in non-interactive CLI usage.

    If the user explicitly opted into tracing with ``CREWAI_TRACING_ENABLED``,
    this helper preserves that choice and skips suppression.
    """

    os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")

    tracing_enabled = _is_tracing_explicitly_enabled()
    if not tracing_enabled:
        os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")

    (
        suppress_messages,
        mark_first_execution_done,
        first_time_trace_hook,
        first_time_trace_handler,
    ) = _load_tracing_utils()
    if suppress_messages is None or mark_first_execution_done is None:
        return

    try:
        suppress_messages(True)
        if first_time_trace_hook is not None:
            first_time_trace_hook.set(lambda: False)
        if first_time_trace_handler is not None:
            first_time_trace_handler.initialize_for_first_time_user = lambda self: False
            first_time_trace_handler.handle_execution_completion = lambda self: None
        mark_first_execution_done(user_consented=tracing_enabled)
    except Exception as exc:  # pragma: no cover - defensive runtime fallback
        logger.debug("Failed to suppress CrewAI tracing prompt: %s", exc)


def run_crew_kickoff(crew: Any, **kickoff_kwargs: Any) -> Any:
    """
    Run crew.kickoff() and optionally print an LLM summary of verbose logs.

    When CREWAI_VERBOSE is true and CREWAI_OUTPUT_LOG_FILE is set, verbose
    output is written to that file. During kickoff we redirect stdout/stderr
    so the console is not flooded. After kickoff we print a 4-5 line LLM
    summary of the log only when the native CrewAI event logger is not active.
    When no log file is configured, kickoff runs normally (verbose output goes
    to console if CREWAI_VERBOSE is true).
    """
    log_path = get_output_log_file()
    if log_path:
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            result = crew.kickoff(**kickoff_kwargs)
        if is_crewai_event_logger_registered():
            logger.debug(
                "Skipping post-kickoff CrewAI log summarization because the "
                "native event logger is active"
            )
            return result
        summary = summarize_crew_log(log_path)
        print(summary, file=sys.stderr, flush=True)
        return result
    return crew.kickoff(**kickoff_kwargs)
