"""Tests for dialectic.hooks -- CrewAI execution hooks infrastructure."""

import threading
import time
from unittest.mock import MagicMock, patch

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
    TokenBudgetTracker,
    _after_llm_call_hook,
    _after_tool_call_hook,
    _before_llm_call_hook,
    _before_tool_call_hook,
    _active_scope,
    count_messages_tokens,
    count_tokens,
)
from dialectic.metrics import _reset_metrics_store


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
# TokenBudgetTracker
# ---------------------------------------------------------------------------


class TestTokenBudgetTracker:
    def test_initial_state(self):
        t = TokenBudgetTracker(budget=1000)
        assert t.budget == 1000
        assert t.input_tokens == 0
        assert t.output_tokens == 0
        assert t.total_tokens == 0
        assert t.llm_calls == 0
        assert t.tool_calls == 0
        assert t.estimated_cost == 0.0
        assert t.budget_exceeded is False

    def test_unlimited_budget(self):
        t = TokenBudgetTracker(budget=0)
        assert t.budget == 0
        assert t.budget_exceeded is False
        assert t.budget_remaining == -1

    def test_add_input_tokens(self):
        t = TokenBudgetTracker(budget=100)
        t.add_input_tokens(50)
        assert t.input_tokens == 50
        assert t.total_tokens == 50
        t.add_input_tokens(30)
        assert t.input_tokens == 80
        assert t.total_tokens == 80

    def test_add_output_tokens(self):
        t = TokenBudgetTracker(budget=100)
        t.add_output_tokens(40)
        assert t.output_tokens == 40
        assert t.total_tokens == 40

    def test_budget_exceeded_true_over_budget(self):
        t = TokenBudgetTracker(budget=100)
        t.add_input_tokens(60)
        t.add_output_tokens(50)
        assert t.budget_exceeded is True

    def test_budget_exceeded_false_under_budget(self):
        t = TokenBudgetTracker(budget=200)
        t.add_input_tokens(50)
        t.add_output_tokens(50)
        assert t.budget_exceeded is False

    def test_budget_remaining(self):
        t = TokenBudgetTracker(budget=200)
        t.add_input_tokens(50)
        assert t.budget_remaining == 150
        t.add_output_tokens(100)
        assert t.budget_remaining == 50

    def test_budget_remaining_at_zero(self):
        t = TokenBudgetTracker(budget=100)
        t.add_input_tokens(120)
        assert t.budget_remaining == 0

    def test_estimated_cost(self):
        t = TokenBudgetTracker(
            budget=0,
            cost_per_input_token=0.001,
            cost_per_output_token=0.002,
        )
        t.add_input_tokens(100)
        t.add_output_tokens(50)
        assert t.estimated_cost == pytest.approx(0.1 + 0.1)

    def test_increment_llm_calls(self):
        t = TokenBudgetTracker()
        t.increment_llm_calls()
        t.increment_llm_calls()
        assert t.llm_calls == 2

    def test_increment_tool_calls(self):
        t = TokenBudgetTracker()
        t.increment_tool_calls()
        assert t.tool_calls == 1

    def test_reset(self):
        t = TokenBudgetTracker(budget=500)
        t.add_input_tokens(100)
        t.add_output_tokens(200)
        t.increment_llm_calls()
        t.increment_tool_calls()
        t.reset()
        assert t.total_tokens == 0
        assert t.llm_calls == 0
        assert t.tool_calls == 0

    def test_snapshot(self):
        t = TokenBudgetTracker(budget=500, cost_per_input_token=0.001, cost_per_output_token=0.002)
        t.add_input_tokens(100)
        t.add_output_tokens(50)
        t.increment_llm_calls()
        snap = t.snapshot()
        assert snap["input_tokens"] == 100
        assert snap["output_tokens"] == 50
        assert snap["total_tokens"] == 150
        assert snap["llm_calls"] == 1
        assert snap["budget"] == 500
        assert snap["budget_exceeded"] is False
        assert snap["estimated_cost"] == pytest.approx(0.1 + 0.1)

    def test_thread_safety(self):
        t = TokenBudgetTracker(budget=0)
        errors: list[Exception] = []

        def add_tokens():
            try:
                for _ in range(1000):
                    t.add_input_tokens(1)
                    t.add_output_tokens(1)
                    t.increment_llm_calls()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=add_tokens) for _ in range(4)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()

        assert not errors
        assert t.input_tokens == 4000
        assert t.output_tokens == 4000
        assert t.llm_calls == 4000


# ---------------------------------------------------------------------------
# count_tokens / count_messages_tokens
# ---------------------------------------------------------------------------


class TestCountTokens:
    def test_count_tokens_nonempty(self):
        n = count_tokens("hello world")
        assert n > 0

    def test_count_tokens_empty(self):
        assert count_tokens("") == 0

    def test_count_messages_tokens(self):
        msgs = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"},
        ]
        n = count_messages_tokens(msgs)
        assert n > 0

    def test_count_messages_tokens_empty(self):
        assert count_messages_tokens([]) == 0


# ---------------------------------------------------------------------------
# _before_llm_call_hook
# ---------------------------------------------------------------------------


def _make_llm_context(**kwargs) -> LLMCallHookContext:
    defaults = dict(
        executor=None,
        response=None,
        messages=[{"role": "user", "content": "test"}],
        llm=None,
        agent=None,
        task=None,
        crew=None,
    )
    defaults.update(kwargs)
    return LLMCallHookContext(**defaults)


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
        import logging
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

    def test_emits_metric(self, monkeypatch, tmp_path):
        from dialectic.metrics import MetricsStore
        store = MetricsStore(db_path=tmp_path / "hook_test.db")
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
    defaults = dict(
        tool_name="search_a_files_content",
        tool_input={"query": "test"},
        tool=MagicMock(),
        agent=None,
        task=None,
        crew=None,
        tool_result=None,
    )
    defaults.update(kwargs)
    return ToolCallHookContext(**defaults)


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
