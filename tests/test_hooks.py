"""Tests for dialectic.hooks -- CrewAI execution hooks infrastructure."""

# pylint: disable=missing-class-docstring,missing-function-docstring
# pylint: disable=import-outside-toplevel,assignment-from-none,use-dict-literal
# pylint: disable=too-few-public-methods

import logging
import time
from typing import Any, cast
from unittest.mock import MagicMock

import pytest

from crewai.hooks import (
    LLMCallHookContext,
    ToolCallHookContext,
    clear_all_global_hooks,
    get_before_llm_call_hooks,
    get_after_llm_call_hooks,
    get_before_tool_call_hooks,
    get_after_tool_call_hooks,
)
from dialectic.hooks import (
    HookScope,
    _after_llm_call_hook,
    _after_tool_call_hook,
    _before_llm_call_hook,
    _before_tool_call_hook,
    _active_scope,
)
from dialectic.metrics import _reset_metrics_store
from dialectic.token_tracker import TokenBudgetTracker


@pytest.fixture(autouse=True)
def _clean_hooks():
    """Ensure no hooks leak between tests."""
    clear_all_global_hooks()
    _active_scope.current = None
    _reset_metrics_store()
    yield
    clear_all_global_hooks()
    _active_scope.current = None
    _reset_metrics_store()


# ---------------------------------------------------------------------------
# _before_llm_call_hook
# ---------------------------------------------------------------------------


def _make_llm_context(**kwargs) -> LLMCallHookContext:
    defaults: dict[str, Any] = {
        "executor": None,
        "response": None,
        "messages": [{"role": "user", "content": "test"}],
        "llm": None,
        "agent": None,
        "task": None,
        "crew": None,
    }
    defaults.update(kwargs)
    return LLMCallHookContext(
        executor=cast(Any, defaults["executor"]),
        response=cast(str | None, defaults["response"]),
        messages=cast(Any, defaults["messages"]),
        llm=cast(Any, defaults["llm"]),
        agent=cast(Any, defaults["agent"]),
        task=cast(Any, defaults["task"]),
        crew=cast(Any, defaults["crew"]),
    )


class TestBeforeLLMCallHook:
    def test_returns_none_when_no_scope(self):
        ctx = _make_llm_context()
        assert _before_llm_call_hook(ctx) is None

    def test_allows_under_budget(self):
        scope = HookScope(token_budget=100_000, label="test")
        _active_scope.current = scope
        ctx = _make_llm_context()
        result = _before_llm_call_hook(ctx)
        assert result is None

    def test_blocks_over_budget(self):
        scope = HookScope(token_budget=10, label="test")
        _active_scope.current = scope
        scope.tracker.add_input_tokens(20)
        ctx = _make_llm_context()
        result = _before_llm_call_hook(ctx)
        assert result is False

    def test_blocks_over_iteration_limit(self):
        scope = HookScope(max_iterations=5, label="test")
        _active_scope.current = scope
        ctx = _make_llm_context()
        ctx.iterations = 10
        result = _before_llm_call_hook(ctx)
        assert result is False

    def test_allows_under_iteration_limit(self):
        scope = HookScope(max_iterations=20, label="test")
        _active_scope.current = scope
        ctx = _make_llm_context()
        ctx.iterations = 5
        result = _before_llm_call_hook(ctx)
        assert result is None

    def test_counts_input_tokens(self):
        scope = HookScope(token_budget=100_000, label="test")
        _active_scope.current = scope
        ctx = _make_llm_context(
            messages=[
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "What is Python?"},
            ]
        )
        _before_llm_call_hook(ctx)
        assert scope.tracker.input_tokens > 0

    def test_emits_debug_log(self, caplog):
        scope = HookScope(token_budget=100_000, label="test")
        _active_scope.current = scope
        agent_mock = MagicMock()
        agent_mock.role = "Visionary"
        ctx = _make_llm_context(agent=agent_mock)
        with caplog.at_level(logging.DEBUG, logger="dialectic.hooks"):
            _before_llm_call_hook(ctx)
        assert any("LLM call" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# _after_llm_call_hook
# ---------------------------------------------------------------------------


class TestAfterLLMCallHook:
    def test_returns_none_when_no_scope(self):
        ctx = _make_llm_context(response="Hello!")
        assert _after_llm_call_hook(ctx) is None

    def test_counts_output_tokens(self):
        scope = HookScope(label="test")
        _active_scope.current = scope
        ctx = _make_llm_context(response="This is a response with several words.")
        _after_llm_call_hook(ctx)
        assert scope.tracker.output_tokens > 0

    def test_increments_llm_calls(self):
        scope = HookScope(label="test")
        _active_scope.current = scope
        ctx = _make_llm_context(response="ok")
        _after_llm_call_hook(ctx)
        assert scope.tracker.llm_calls == 1

    def test_handles_none_response(self):
        scope = HookScope(label="test")
        _active_scope.current = scope
        ctx = _make_llm_context(response=None)
        result = _after_llm_call_hook(ctx)
        assert result is None
        assert scope.tracker.output_tokens == 0

    def test_returns_none_never_modifies(self):
        scope = HookScope(label="test")
        _active_scope.current = scope
        ctx = _make_llm_context(response="original response")
        result = _after_llm_call_hook(ctx)
        assert result is None

    def test_emits_metric(self, monkeypatch):
        monkeypatch.setattr("dialectic.hooks.emit_metric", lambda *a, **kw: None)
        scope = HookScope(label="test")
        _active_scope.current = scope
        agent_mock = MagicMock()
        agent_mock.role = "Critic"
        llm_mock = MagicMock()
        llm_mock.model = "gpt-4o"
        ctx = _make_llm_context(response="output", agent=agent_mock, llm=llm_mock)
        _after_llm_call_hook(ctx)
        assert scope.tracker.llm_calls == 1


# ---------------------------------------------------------------------------
# _before_tool_call_hook
# ---------------------------------------------------------------------------


def _make_tool_context(**kwargs) -> ToolCallHookContext:
    defaults: dict[str, Any] = {
        "tool_name": "search_a_files_content",
        "tool_input": {"query": "test"},
        "tool": MagicMock(),
        "agent": None,
        "task": None,
        "crew": None,
        "tool_result": None,
    }
    defaults.update(kwargs)
    return ToolCallHookContext(
        tool_name=cast(str, defaults["tool_name"]),
        tool_input=cast(dict[str, Any], defaults["tool_input"]),
        tool=cast(Any, defaults["tool"]),
        agent=cast(Any, defaults["agent"]),
        task=cast(Any, defaults["task"]),
        crew=cast(Any, defaults["crew"]),
        tool_result=cast(str | None, defaults["tool_result"]),
    )


class TestBeforeToolCallHook:
    def test_returns_none_when_no_scope(self):
        ctx = _make_tool_context()
        assert _before_tool_call_hook(ctx) is None

    def test_allows_non_protected_path(self):
        scope = HookScope(
            protected_paths=frozenset({"internal/SELF_VISION.md"}),
            label="test",
        )
        _active_scope.current = scope
        ctx = _make_tool_context(
            tool_name="write_to_file",
            tool_input={"file_path": "src/new_feature.py"},
        )
        result = _before_tool_call_hook(ctx)
        assert result is None

    def test_blocks_protected_path(self):
        scope = HookScope(
            protected_paths=frozenset({"internal/SELF_VISION.md"}),
            label="test",
        )
        _active_scope.current = scope
        ctx = _make_tool_context(
            tool_name="write_to_file",
            tool_input={"file_path": "internal/SELF_VISION.md"},
        )
        result = _before_tool_call_hook(ctx)
        assert result is False

    def test_blocks_write_to_file_tool(self):
        scope = HookScope(
            protected_paths=frozenset({"src/dialectic/metrics.py"}),
            label="test",
        )
        _active_scope.current = scope
        ctx = _make_tool_context(
            tool_name="write_to_file",
            tool_input={"path": "src/dialectic/metrics.py"},
        )
        result = _before_tool_call_hook(ctx)
        assert result is False

    def test_blocks_write_outside_allowed_root(self, tmp_path, monkeypatch):
        allowed_root = tmp_path / "target"
        allowed_root.mkdir()
        monkeypatch.chdir(allowed_root)
        scope = HookScope(
            allowed_write_roots=frozenset({allowed_root}),
            label="test",
        )
        _active_scope.current = scope
        ctx = _make_tool_context(
            tool_name="write_to_file",
            tool_input={"file_path": "../outside.py"},
        )

        result = _before_tool_call_hook(ctx)

        assert result is False

    def test_allows_write_inside_allowed_root(self, tmp_path, monkeypatch):
        allowed_root = tmp_path / "target"
        allowed_root.mkdir()
        monkeypatch.chdir(allowed_root)
        scope = HookScope(
            allowed_write_roots=frozenset({allowed_root}),
            label="test",
        )
        _active_scope.current = scope
        ctx = _make_tool_context(
            tool_name="write_to_file",
            tool_input={"file_path": "src/new_feature.py"},
        )

        result = _before_tool_call_hook(ctx)

        assert result is None

    def test_allows_when_no_protection_active(self):
        scope = HookScope(label="test")
        _active_scope.current = scope
        ctx = _make_tool_context(
            tool_name="write_to_file",
            tool_input={"file_path": "internal/SELF_VISION.md"},
        )
        result = _before_tool_call_hook(ctx)
        assert result is None

    def test_allows_read_tools_on_protected(self):
        scope = HookScope(
            protected_paths=frozenset({"internal/SELF_VISION.md"}),
            label="test",
        )
        _active_scope.current = scope
        ctx = _make_tool_context(
            tool_name="search_a_files_content",
            tool_input={"path": "internal/SELF_VISION.md"},
        )
        result = _before_tool_call_hook(ctx)
        assert result is None

    def test_sets_start_time(self):
        scope = HookScope(label="test")
        _active_scope.current = scope
        ctx = _make_tool_context()
        _before_tool_call_hook(ctx)
        assert "_hook_start_time" in ctx.tool_input


# ---------------------------------------------------------------------------
# _after_tool_call_hook
# ---------------------------------------------------------------------------


class TestAfterToolCallHook:
    def test_returns_none_when_no_scope(self):
        ctx = _make_tool_context(tool_result="some result")
        assert _after_tool_call_hook(ctx) is None

    def test_increments_tool_calls(self):
        scope = HookScope(label="test")
        _active_scope.current = scope
        ctx = _make_tool_context(tool_result="result text")
        ctx.tool_input["_hook_start_time"] = time.time() - 0.1
        _after_tool_call_hook(ctx)
        assert scope.tracker.tool_calls == 1

    def test_handles_none_result(self):
        scope = HookScope(label="test")
        _active_scope.current = scope
        ctx = _make_tool_context(tool_result=None)
        result = _after_tool_call_hook(ctx)
        assert result is None
        assert scope.tracker.tool_calls == 1

    def test_returns_none_never_modifies(self):
        scope = HookScope(label="test")
        _active_scope.current = scope
        ctx = _make_tool_context(tool_result="original tool output")
        ctx.tool_input["_hook_start_time"] = time.time()
        result = _after_tool_call_hook(ctx)
        assert result is None

    def test_cleans_up_start_time(self):
        scope = HookScope(label="test")
        _active_scope.current = scope
        ctx = _make_tool_context(tool_result="done")
        ctx.tool_input["_hook_start_time"] = time.time()
        _after_tool_call_hook(ctx)
        assert "_hook_start_time" not in ctx.tool_input


# ---------------------------------------------------------------------------
# HookScope
# ---------------------------------------------------------------------------


class TestHookScope:
    def test_enters_and_exits_cleanly(self):
        with HookScope(label="test") as tracker:
            assert tracker is not None
            assert isinstance(tracker, TokenBudgetTracker)

    def test_returns_tracker(self):
        scope = HookScope(token_budget=1000, label="test")
        with scope as tracker:
            assert tracker is scope.tracker
            assert tracker.budget == 1000

    def test_registers_hooks(self):
        before_count = len(get_before_llm_call_hooks())
        with HookScope(label="test"):
            assert len(get_before_llm_call_hooks()) == before_count + 1
            assert len(get_after_llm_call_hooks()) >= 1
            assert len(get_before_tool_call_hooks()) >= 1
            assert len(get_after_tool_call_hooks()) >= 1

    def test_unregisters_hooks_on_exit(self):
        before_llm = len(get_before_llm_call_hooks())
        before_tool = len(get_before_tool_call_hooks())
        with HookScope(label="test"):
            pass
        assert len(get_before_llm_call_hooks()) == before_llm
        assert len(get_before_tool_call_hooks()) == before_tool

    def test_hooks_not_registered_after_exit(self):
        with HookScope(label="test"):
            pass
        ctx = _make_llm_context()
        result = _before_llm_call_hook(ctx)
        assert result is None  # no active scope

    def test_emits_summary_metric_on_exit(self, monkeypatch, tmp_path):
        from dialectic.metrics import MetricsStore

        store = MetricsStore(db_path=tmp_path / "scope_test.db")
        monkeypatch.setattr("dialectic.metrics._store", store)

        with HookScope(label="scope-test"):
            pass

        results = store.query("hook_scope_summary")
        assert len(results) == 1
        assert results[0].context["label"] == "scope-test"

    def test_nested_scopes(self):
        with HookScope(token_budget=1000, label="outer") as outer:
            outer.add_input_tokens(50)
            with HookScope(token_budget=500, label="inner") as inner:
                inner.add_input_tokens(30)
                assert inner.total_tokens == 30
            assert outer.input_tokens == 50

    def test_nested_scope_restores_previous(self):
        outer_scope = HookScope(label="outer")
        inner_scope = HookScope(label="inner")
        with outer_scope:
            assert _active_scope.current is outer_scope
            with inner_scope:
                assert _active_scope.current is inner_scope
            assert _active_scope.current is outer_scope
        assert _active_scope.current is None

    def test_scope_with_protected_paths(self):
        paths = frozenset({"a.py", "b.py"})
        scope = HookScope(protected_paths=paths, label="test")
        assert scope.protected_paths == paths

    def test_scope_with_allowed_write_roots(self, tmp_path):
        root = tmp_path / "target"
        root.mkdir()
        scope = HookScope(allowed_write_roots=frozenset({root}), label="test")
        assert root.resolve() in scope.allowed_write_roots

    def test_scope_default_budget_unlimited(self):
        scope = HookScope(label="test")
        assert scope.tracker.budget == 0
        assert scope.tracker.budget_exceeded is False

    def test_unregisters_on_exception(self):
        before_count = len(get_before_llm_call_hooks())
        try:
            with HookScope(label="test"):
                raise ValueError("boom")
        except ValueError:
            pass
        assert len(get_before_llm_call_hooks()) == before_count
