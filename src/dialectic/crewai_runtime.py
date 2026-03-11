"""CrewAI runtime defaults for this project.

The app disables external telemetry by default and runs primarily in
non-interactive CLI contexts. CrewAI's first-run tracing prompt can spawn an
input thread after successful executions, which is undesirable in automated or
captured runs. This helper applies safe defaults while preserving explicit user
opt-in to tracing via environment variables.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from typing import Any

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

    suppress_messages, mark_first_execution_done, first_time_trace_hook, first_time_trace_handler = _load_tracing_utils()
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