"""
CrewAI execution hooks for cost tracking, token budgeting, iteration
limiting, debug logging, and tool safety guardrails.

Uses CrewAI's hook system:
- @before_llm_call / @after_llm_call for LLM monitoring
- @before_tool_call / @after_tool_call for tool safety

All hooks emit metrics to the MetricsStore for persistent telemetry.

Usage::

    from dialectic.hooks import HookScope

    with HookScope(
        token_budget=500_000,
        max_iterations=25,
        protected_paths=frozenset({"internal/SELF_VISION.md"}),
        label="self-improve/20260309",
    ) as tracker:
        crew.kickoff()
        print(tracker.total_tokens, tracker.estimated_cost)
"""

from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path
from typing import Any

from crewai.hooks import (
    LLMCallHookContext,
    ToolCallHookContext,
    register_after_llm_call_hook,
    register_after_tool_call_hook,
    register_before_llm_call_hook,
    register_before_tool_call_hook,
    unregister_after_llm_call_hook,
    unregister_after_tool_call_hook,
    unregister_before_llm_call_hook,
    unregister_before_tool_call_hook,
)

from dialectic.metrics import emit as emit_metric
from dialectic.token_tracker import TokenBudgetTracker, count_messages_tokens, count_tokens

logger = logging.getLogger(__name__)

_DEFAULT_TOKEN_BUDGET = int(os.getenv("TOKEN_BUDGET", "0"))
_DEFAULT_MAX_ITERATIONS = int(os.getenv("MAX_LLM_ITERATIONS", "25"))
_DEFAULT_COST_PER_INPUT = float(os.getenv("COST_PER_INPUT_TOKEN", "0.0000025"))
_DEFAULT_COST_PER_OUTPUT = float(os.getenv("COST_PER_OUTPUT_TOKEN", "0.00001"))


# ---------------------------------------------------------------------------
# Active scope -- thread-local so nested scopes work correctly
# ---------------------------------------------------------------------------

_active_scope: threading.local = threading.local()


def _get_active_scope() -> HookScope | None:
    return getattr(_active_scope, "current", None)


# ---------------------------------------------------------------------------
# LLM hooks
# ---------------------------------------------------------------------------


def _before_llm_call_hook(context: LLMCallHookContext) -> bool | None:
    """Pre-LLM hook: count input tokens, enforce budget, limit iterations."""
    scope = _get_active_scope()
    if scope is None:
        return None

    tracker = scope.tracker
    messages = getattr(context, "messages", []) or []
    input_count = count_messages_tokens(messages)
    tracker.add_input_tokens(input_count)

    agent_role = ""
    agent_obj = getattr(context, "agent", None)
    if agent_obj is not None:
        agent_role = getattr(agent_obj, "role", str(agent_obj))

    task_obj = getattr(context, "task", None)
    del task_obj

    iterations = getattr(context, "iterations", 0)

    logger.debug(
        "LLM call: agent=%s, iteration=%d, input_tokens=%d, total=%d, budget=%d",
        agent_role[:40],
        iterations,
        input_count,
        tracker.total_tokens,
        tracker.budget,
    )

    if tracker.budget_exceeded:
        logger.warning(
            "Token budget exceeded (%d/%d). Blocking LLM call for agent=%s.",
            tracker.total_tokens,
            tracker.budget,
            agent_role[:40],
        )
        emit_metric(
            "llm_budget_abort",
            1.0,
            agent=agent_role[:60],
            total_tokens=tracker.total_tokens,
            budget=tracker.budget,
            label=scope.label,
        )
        return False

    max_iters = scope.max_iterations
    if max_iters > 0 and iterations > max_iters:
        logger.warning(
            "Iteration limit exceeded (%d/%d). Blocking LLM call for agent=%s.",
            iterations,
            max_iters,
            agent_role[:40],
        )
        emit_metric(
            "llm_iteration_abort",
            1.0,
            agent=agent_role[:60],
            iterations=iterations,
            limit=max_iters,
            label=scope.label,
        )
        return False

    return None


def _after_llm_call_hook(context: LLMCallHookContext) -> str | None:
    """Post-LLM hook: count output tokens, emit metrics."""
    scope = _get_active_scope()
    if scope is None:
        return None

    tracker = scope.tracker
    tracker.increment_llm_calls()

    response = getattr(context, "response", None) or ""
    output_count = count_tokens(str(response))
    tracker.add_output_tokens(output_count)

    agent_role = ""
    agent_obj = getattr(context, "agent", None)
    if agent_obj is not None:
        agent_role = getattr(agent_obj, "role", str(agent_obj))

    llm_model = ""
    llm_obj = getattr(context, "llm", None)
    if llm_obj is not None:
        llm_model = getattr(llm_obj, "model", str(llm_obj))

    emit_metric(
        "llm_tokens",
        float(output_count),
        input_tokens=tracker.input_tokens,
        output_tokens=output_count,
        agent=agent_role[:60],
        model=str(llm_model)[:60],
        label=scope.label,
    )

    return None  # never modify the response


# ---------------------------------------------------------------------------
# Tool hooks
# ---------------------------------------------------------------------------


def _before_tool_call_hook(context: ToolCallHookContext) -> bool | None:
    """Pre-tool hook: block writes to protected paths, log invocations."""
    scope = _get_active_scope()
    if scope is None:
        return None

    tool_name = getattr(context, "tool_name", "") or ""
    tool_input = getattr(context, "tool_input", {}) or {}

    agent_role = ""
    agent_obj = getattr(context, "agent", None)
    if agent_obj is not None:
        agent_role = getattr(agent_obj, "role", str(agent_obj))

    logger.debug("Tool call: tool=%s, agent=%s", tool_name, agent_role[:40])

    write_tools = {"write_to_file", "file_writer", "FileWriterTool"}
    is_write_tool = tool_name in write_tools or "write" in tool_name.lower()
    if is_write_tool:
        target_path = (
            tool_input.get("file_path", "")
            or tool_input.get("path", "")
            or tool_input.get("filename", "")
        )
        if scope.allowed_write_roots:
            if not target_path:
                logger.warning(
                    "Blocked write without target path metadata (tool=%s, agent=%s)",
                    tool_name,
                    agent_role[:40],
                )
                emit_metric(
                    "tool_blocked",
                    1.0,
                    tool=tool_name,
                    path="<missing>",
                    agent=agent_role[:60],
                    label=scope.label,
                )
                return False

            resolved_target = Path(str(target_path)).expanduser()
            if not resolved_target.is_absolute():
                resolved_target = (Path.cwd() / resolved_target).resolve()
            else:
                resolved_target = resolved_target.resolve()

            if not any(
                resolved_target == allowed_root or allowed_root in resolved_target.parents
                for allowed_root in scope.allowed_write_roots
            ):
                logger.warning(
                    "Blocked write outside allowed roots: %s (tool=%s, agent=%s)",
                    resolved_target,
                    tool_name,
                    agent_role[:40],
                )
                emit_metric(
                    "tool_blocked",
                    1.0,
                    tool=tool_name,
                    path=str(resolved_target)[:120],
                    agent=agent_role[:60],
                    label=scope.label,
                )
                return False

        for protected in scope.protected_paths:
            if protected in str(target_path):
                logger.warning(
                    "Blocked write to protected path: %s (tool=%s, agent=%s)",
                    target_path,
                    tool_name,
                    agent_role[:40],
                )
                emit_metric(
                    "tool_blocked",
                    1.0,
                    tool=tool_name,
                    path=str(target_path)[:120],
                    agent=agent_role[:60],
                    label=scope.label,
                )
                return False

    context.tool_input["_hook_start_time"] = time.time()
    return None


def _after_tool_call_hook(context: ToolCallHookContext) -> str | None:
    """Post-tool hook: emit usage metrics, log results."""
    scope = _get_active_scope()
    if scope is None:
        return None

    scope.tracker.increment_tool_calls()

    tool_name = getattr(context, "tool_name", "") or ""
    tool_input = getattr(context, "tool_input", {}) or {}
    tool_result = getattr(context, "tool_result", None)

    start_time = tool_input.pop("_hook_start_time", None)
    duration = (time.time() - start_time) if start_time else 0.0

    has_result = tool_result is not None and str(tool_result).strip() != ""
    errored = (
        tool_result is not None
        and isinstance(tool_result, str)
        and "error" in tool_result.lower()
    )

    emit_metric(
        "tool_call",
        duration,
        tool=tool_name,
        success=has_result and not errored,
        label=scope.label,
    )

    return None  # never modify the result


# ---------------------------------------------------------------------------
# HookScope context manager
# ---------------------------------------------------------------------------


class HookScope:
    """Context manager that registers/unregisters CrewAI hooks for a scope.

    On enter: creates a TokenBudgetTracker, registers all 4 hooks, sets this
    scope as active.
    On exit: unregisters hooks, emits a summary metric, logs final stats.
    """

    def __init__(
        self,
        token_budget: int | None = None,
        max_iterations: int | None = None,
        protected_paths: frozenset[str] | None = None,
        allowed_write_roots: frozenset[str | Path] | None = None,
        label: str = "",
        cost_per_input_token: float | None = None,
        cost_per_output_token: float | None = None,
    ) -> None:
        budget = token_budget if token_budget is not None else _DEFAULT_TOKEN_BUDGET
        self.tracker = TokenBudgetTracker(
            budget=budget,
            cost_per_input_token=(
                cost_per_input_token
                if cost_per_input_token is not None
                else _DEFAULT_COST_PER_INPUT
            ),
            cost_per_output_token=(
                cost_per_output_token
                if cost_per_output_token is not None
                else _DEFAULT_COST_PER_OUTPUT
            ),
        )
        self.max_iterations = (
            max_iterations if max_iterations is not None else _DEFAULT_MAX_ITERATIONS
        )
        self.protected_paths = protected_paths or frozenset()
        self.allowed_write_roots = frozenset(
            Path(root).expanduser().resolve() for root in (allowed_write_roots or frozenset())
        )
        self.label = label
        self._previous_scope: HookScope | None = None
        self._entered = False

    def __enter__(self) -> TokenBudgetTracker:
        self._previous_scope = _get_active_scope()
        _active_scope.current = self
        register_before_llm_call_hook(_before_llm_call_hook)
        register_after_llm_call_hook(_after_llm_call_hook)
        register_before_tool_call_hook(_before_tool_call_hook)
        register_after_tool_call_hook(_after_tool_call_hook)
        self._entered = True
        logger.info(
            "HookScope entered: label=%s, budget=%d, max_iter=%d, protected=%d paths",
            self.label,
            self.tracker.budget,
            self.max_iterations,
            len(self.protected_paths),
        )
        return self.tracker

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        unregister_before_llm_call_hook(_before_llm_call_hook)
        unregister_after_llm_call_hook(_after_llm_call_hook)
        unregister_before_tool_call_hook(_before_tool_call_hook)
        unregister_after_tool_call_hook(_after_tool_call_hook)

        _active_scope.current = self._previous_scope
        self._entered = False

        snap = self.tracker.snapshot()
        logger.info(
            "HookScope exited: label=%s, tokens=%d (in=%d, out=%d), "
            "llm_calls=%d, tool_calls=%d, cost=$%.4f",
            self.label,
            snap["total_tokens"],
            snap["input_tokens"],
            snap["output_tokens"],
            snap["llm_calls"],
            snap["tool_calls"],
            snap["estimated_cost"],
        )

        emit_metric(
            "hook_scope_summary",
            float(snap["total_tokens"]),
            label=self.label,
            input_tokens=snap["input_tokens"],
            output_tokens=snap["output_tokens"],
            llm_calls=snap["llm_calls"],
            tool_calls=snap["tool_calls"],
            estimated_cost=snap["estimated_cost"],
            budget=snap["budget"],
            budget_exceeded=snap["budget_exceeded"],
        )
