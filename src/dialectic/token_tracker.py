"""Token counting and budget tracking helpers for CrewAI hook scopes."""

from __future__ import annotations

import os
import threading
from typing import Any

import tiktoken

_DEFAULT_COST_PER_INPUT = float(os.getenv("COST_PER_INPUT_TOKEN", "0.0000025"))
_DEFAULT_COST_PER_OUTPUT = float(os.getenv("COST_PER_OUTPUT_TOKEN", "0.00001"))

_ENCODING: tiktoken.Encoding | None = None
_ENCODING_LOCK = threading.Lock()


def _get_encoding() -> tiktoken.Encoding:
    """Lazy-init the tiktoken cl100k_base encoding (thread-safe)."""
    global _ENCODING
    if _ENCODING is None:
        with _ENCODING_LOCK:
            if _ENCODING is None:
                _ENCODING = tiktoken.get_encoding("cl100k_base")
    return _ENCODING


def count_tokens(text: str) -> int:
    """Count tokens in *text* using cl100k_base encoding."""
    if not text:
        return 0
    return len(_get_encoding().encode(text))


def count_messages_tokens(messages: list[dict[str, Any]]) -> int:
    """Estimate token count for a list of LLM chat messages."""
    total = 0
    for msg in messages:
        content = msg.get("content", "") if isinstance(msg, dict) else str(msg)
        total += count_tokens(str(content))
        total += 4
    return total


class TokenBudgetTracker:
    """Thread-safe tracker for token usage and cost across a hook scope."""

    def __init__(
        self,
        budget: int = 0,
        cost_per_input_token: float = _DEFAULT_COST_PER_INPUT,
        cost_per_output_token: float = _DEFAULT_COST_PER_OUTPUT,
    ) -> None:
        self._budget = budget
        self._cost_per_input = cost_per_input_token
        self._cost_per_output = cost_per_output_token
        self._input_tokens = 0
        self._output_tokens = 0
        self._llm_calls = 0
        self._tool_calls = 0
        self._lock = threading.Lock()

    @property
    def budget(self) -> int:
        return self._budget

    @property
    def input_tokens(self) -> int:
        with self._lock:
            return self._input_tokens

    @property
    def output_tokens(self) -> int:
        with self._lock:
            return self._output_tokens

    @property
    def total_tokens(self) -> int:
        with self._lock:
            return self._input_tokens + self._output_tokens

    @property
    def llm_calls(self) -> int:
        with self._lock:
            return self._llm_calls

    @property
    def tool_calls(self) -> int:
        with self._lock:
            return self._tool_calls

    @property
    def estimated_cost(self) -> float:
        with self._lock:
            return (
                self._input_tokens * self._cost_per_input
                + self._output_tokens * self._cost_per_output
            )

    @property
    def budget_remaining(self) -> int:
        if self._budget <= 0:
            return -1
        with self._lock:
            return max(0, self._budget - self._input_tokens - self._output_tokens)

    @property
    def budget_exceeded(self) -> bool:
        if self._budget <= 0:
            return False
        with self._lock:
            return (self._input_tokens + self._output_tokens) > self._budget

    def add_input_tokens(self, n: int) -> None:
        with self._lock:
            self._input_tokens += n

    def add_output_tokens(self, n: int) -> None:
        with self._lock:
            self._output_tokens += n

    def increment_llm_calls(self) -> None:
        with self._lock:
            self._llm_calls += 1

    def increment_tool_calls(self) -> None:
        with self._lock:
            self._tool_calls += 1

    def reset(self) -> None:
        with self._lock:
            self._input_tokens = 0
            self._output_tokens = 0
            self._llm_calls = 0
            self._tool_calls = 0

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "input_tokens": self._input_tokens,
                "output_tokens": self._output_tokens,
                "total_tokens": self._input_tokens + self._output_tokens,
                "llm_calls": self._llm_calls,
                "tool_calls": self._tool_calls,
                "estimated_cost": (
                    self._input_tokens * self._cost_per_input
                    + self._output_tokens * self._cost_per_output
                ),
                "budget": self._budget,
                "budget_exceeded": (
                    (self._input_tokens + self._output_tokens) > self._budget
                    if self._budget > 0
                    else False
                ),
            }
