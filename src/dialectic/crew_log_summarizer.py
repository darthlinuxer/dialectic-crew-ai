"""Summarize CrewAI verbose log files for concise console output."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any, Callable

from dialectic.crewai_event_logger import is_crewai_event_logger_registered
from dialectic.crew_verbose_config import get_output_log_file
from dialectic.llm import llm_simple

logger = logging.getLogger(__name__)

_MAX_EXCERPT_CHARS = 12_000
_SHUTDOWN_NOISE_MARKERS = (
    "cannot schedule new futures after shutdown",
    "event loop is closed",
)
_SUMMARY_PROMPT = """
Summarize this CrewAI execution log in exactly 4 to 5 short lines for the console.
Include: (1) current stage of the flow, (2) brief summary of what the agent(s)
did so far, (3) task or step name if visible, (4) any pass/fail or retry
indication. Be concise; no preamble.
Log excerpt:
---
{excerpt}
---
Reply with only the 4-5 line summary, nothing else.
""".strip()


def get_step_summarizer_callback() -> Callable[[Any], None] | None:
    """
    Return a callback for CrewAI step_callback that prints a log summary after each step.

    When CREWAI_VERBOSE is true and CREWAI_OUTPUT_LOG_FILE is set, returns a callable
    that CrewAI invokes after each agent step; it reads the current log file and prints
    a 4-5 line LLM summary to stderr. Returns None when no log file is configured.
    """
    if is_crewai_event_logger_registered():
        return None

    log_path = get_output_log_file()
    if not log_path:
        return None

    def _on_step(_step_output: Any) -> None:
        summary = summarize_crew_log(log_path)
        print(summary, file=sys.stderr, flush=True)

    return _on_step


def summarize_crew_log(log_path: str | Path) -> str:  # pylint: disable=too-many-return-statements
    """
    Read the log file and return an LLM-generated 4-5 line summary.

    Supports .txt and .json log formats. On any error returns a fallback message.
    """
    path = Path(log_path)
    if not path.exists():
        logger.debug("Crew log file missing: %s", path)
        return "Crew log summary unavailable (file not found)."

    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        logger.warning("Failed to read crew log %s: %s", path, exc)
        return "Crew log summary unavailable (read error)."

    if not raw.strip():
        return "Crew run completed (log empty)."

    excerpt = _to_excerpt(raw, path)
    if not excerpt.strip():
        return "Crew run completed (no summarizable content)."

    try:
        prompt = _SUMMARY_PROMPT.format(excerpt=excerpt)
        summary = llm_simple.call(prompt)
        if summary and isinstance(summary, str):
            summary = summary.strip()
        if not summary:
            return "Crew log summary unavailable (empty response)."
        return summary
    except Exception as exc:  # pylint: disable=broad-exception-caught
        if _looks_like_shutdown_noise(exc):
            logger.debug(
                "Crew log summarization skipped because the runtime is shutting down: %s",
                exc,
            )
            return "Crew log summary unavailable (runtime shutting down)."
        logger.warning("Crew log summarization failed: %s", exc)
        return "Crew log summary unavailable (LLM error)."


def _looks_like_shutdown_noise(exc: Exception) -> bool:
    """Return whether a summarizer exception matches known shutdown noise."""
    message = str(exc).lower()
    return any(marker in message for marker in _SHUTDOWN_NOISE_MARKERS)


def _to_excerpt(raw: str, path: Path) -> str:
    """Produce a bounded text excerpt for the LLM (last N chars or structured for JSON)."""
    if path.suffix.lower() == ".json":
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                # Keep last entries to stay under limit
                text_parts = []
                for entry in data[-50:]:
                    text_parts.append(json.dumps(entry, ensure_ascii=False))
                excerpt = "\n".join(text_parts)
            elif isinstance(data, dict):
                excerpt = json.dumps(data, ensure_ascii=False, indent=0)
            else:
                excerpt = raw
        except json.JSONDecodeError:
            excerpt = raw
    else:
        excerpt = raw

    if len(excerpt) > _MAX_EXCERPT_CHARS:
        excerpt = excerpt[-_MAX_EXCERPT_CHARS:]
    return excerpt
