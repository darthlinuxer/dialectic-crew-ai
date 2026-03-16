"""Transient LLM failure handling for self-improve stages."""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable
from typing import TypeVar

from .paths import (
    DEFAULT_SELF_IMPROVE_LLM_RETRY_BACKOFF_SECONDS,
    DEFAULT_SELF_IMPROVE_LLM_STAGE_RETRIES,
)

logger = logging.getLogger(__name__)
_StageResultT = TypeVar("_StageResultT")


def _self_improve_llm_stage_retries() -> int:
    """Return how many extra attempts self-improve should make on transient LLM failures."""
    raw_value = os.getenv("SELF_IMPROVE_LLM_STAGE_RETRIES")
    if raw_value in {None, ""}:
        return DEFAULT_SELF_IMPROVE_LLM_STAGE_RETRIES
    assert raw_value is not None
    try:
        retries = int(raw_value)
    except ValueError:
        logger.warning(
            "Invalid SELF_IMPROVE_LLM_STAGE_RETRIES=%r; using default %s",
            raw_value,
            DEFAULT_SELF_IMPROVE_LLM_STAGE_RETRIES,
        )
        return DEFAULT_SELF_IMPROVE_LLM_STAGE_RETRIES
    if retries < 0:
        logger.warning(
            "Negative SELF_IMPROVE_LLM_STAGE_RETRIES=%r; using default %s",
            raw_value,
            DEFAULT_SELF_IMPROVE_LLM_STAGE_RETRIES,
        )
        return DEFAULT_SELF_IMPROVE_LLM_STAGE_RETRIES
    return retries


def _self_improve_llm_retry_backoff_seconds() -> float:
    """Return the base backoff between transient LLM retry attempts."""
    raw_value = os.getenv("SELF_IMPROVE_LLM_RETRY_BACKOFF_SECONDS")
    if raw_value in {None, ""}:
        return DEFAULT_SELF_IMPROVE_LLM_RETRY_BACKOFF_SECONDS
    assert raw_value is not None
    try:
        seconds = float(raw_value)
    except ValueError:
        logger.warning(
            "Invalid SELF_IMPROVE_LLM_RETRY_BACKOFF_SECONDS=%r; using default %s",
            raw_value,
            DEFAULT_SELF_IMPROVE_LLM_RETRY_BACKOFF_SECONDS,
        )
        return DEFAULT_SELF_IMPROVE_LLM_RETRY_BACKOFF_SECONDS
    if seconds < 0:
        logger.warning(
            "Negative SELF_IMPROVE_LLM_RETRY_BACKOFF_SECONDS=%r; using default %s",
            raw_value,
            DEFAULT_SELF_IMPROVE_LLM_RETRY_BACKOFF_SECONDS,
        )
        return DEFAULT_SELF_IMPROVE_LLM_RETRY_BACKOFF_SECONDS
    return seconds


def _is_transient_llm_error(exc: Exception) -> bool:
    """Return True when the exception looks like a transient provider/network failure."""
    message = str(exc).lower()
    transient_markers = (
        "request timed out",
        "timed out",
        "timeout",
        "failed to connect to openai api",
        "connection error",
        "api connection error",
        "temporarily unavailable",
        "service unavailable",
        "rate limit",
        "too many requests",
        "server disconnected",
    )
    return any(marker in message for marker in transient_markers)


def _run_with_transient_llm_retries(
    stage_name: str,
    operation: Callable[[], _StageResultT],
) -> _StageResultT:
    """Retry a self-improve stage when transient LLM/provider failures occur."""
    max_attempts = _self_improve_llm_stage_retries() + 1
    backoff_seconds = _self_improve_llm_retry_backoff_seconds()

    for attempt in range(1, max_attempts + 1):
        try:
            return operation()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            if not _is_transient_llm_error(exc) or attempt >= max_attempts:
                raise

            wait_seconds = backoff_seconds * attempt
            logger.warning(
                "Transient LLM failure during %s (attempt %s/%s): %s",
                stage_name,
                attempt,
                max_attempts,
                exc,
            )
            print(
                f"  Transient LLM failure during {stage_name} "
                f"(attempt {attempt}/{max_attempts}): {exc}"
            )
            print(f"  Retrying {stage_name} in {wait_seconds:.1f}s...")
            if wait_seconds > 0:
                time.sleep(wait_seconds)

    raise RuntimeError(f"Retry loop exited unexpectedly for {stage_name}")


__all__ = [
    "_self_improve_llm_stage_retries",
    "_self_improve_llm_retry_backoff_seconds",
    "_is_transient_llm_error",
    "_run_with_transient_llm_retries",
]

