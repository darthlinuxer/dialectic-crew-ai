"""Tests for dialectic.token_tracker."""

import threading

import pytest

from dialectic.token_tracker import TokenBudgetTracker, count_messages_tokens, count_tokens


class TestTokenBudgetTracker:
    def test_initial_state(self):
        tracker = TokenBudgetTracker(budget=1000)
        assert tracker.budget == 1000
        assert tracker.input_tokens == 0
        assert tracker.output_tokens == 0
        assert tracker.total_tokens == 0
        assert tracker.llm_calls == 0
        assert tracker.tool_calls == 0
        assert tracker.estimated_cost == 0.0
        assert tracker.budget_exceeded is False

    def test_unlimited_budget(self):
        tracker = TokenBudgetTracker(budget=0)
        assert tracker.budget == 0
        assert tracker.budget_exceeded is False
        assert tracker.budget_remaining == -1

    def test_add_input_tokens(self):
        tracker = TokenBudgetTracker(budget=100)
        tracker.add_input_tokens(50)
        assert tracker.input_tokens == 50
        assert tracker.total_tokens == 50
        tracker.add_input_tokens(30)
        assert tracker.input_tokens == 80
        assert tracker.total_tokens == 80

    def test_add_output_tokens(self):
        tracker = TokenBudgetTracker(budget=100)
        tracker.add_output_tokens(40)
        assert tracker.output_tokens == 40
        assert tracker.total_tokens == 40

    def test_budget_exceeded_true_over_budget(self):
        tracker = TokenBudgetTracker(budget=100)
        tracker.add_input_tokens(60)
        tracker.add_output_tokens(50)
        assert tracker.budget_exceeded is True

    def test_budget_exceeded_false_under_budget(self):
        tracker = TokenBudgetTracker(budget=200)
        tracker.add_input_tokens(50)
        tracker.add_output_tokens(50)
        assert tracker.budget_exceeded is False

    def test_budget_remaining(self):
        tracker = TokenBudgetTracker(budget=200)
        tracker.add_input_tokens(50)
        assert tracker.budget_remaining == 150
        tracker.add_output_tokens(100)
        assert tracker.budget_remaining == 50

    def test_budget_remaining_at_zero(self):
        tracker = TokenBudgetTracker(budget=100)
        tracker.add_input_tokens(120)
        assert tracker.budget_remaining == 0

    def test_estimated_cost(self):
        tracker = TokenBudgetTracker(
            budget=0,
            cost_per_input_token=0.001,
            cost_per_output_token=0.002,
        )
        tracker.add_input_tokens(100)
        tracker.add_output_tokens(50)
        assert tracker.estimated_cost == pytest.approx(0.1 + 0.1)

    def test_increment_llm_calls(self):
        tracker = TokenBudgetTracker()
        tracker.increment_llm_calls()
        tracker.increment_llm_calls()
        assert tracker.llm_calls == 2

    def test_increment_tool_calls(self):
        tracker = TokenBudgetTracker()
        tracker.increment_tool_calls()
        assert tracker.tool_calls == 1

    def test_reset(self):
        tracker = TokenBudgetTracker(budget=500)
        tracker.add_input_tokens(100)
        tracker.add_output_tokens(200)
        tracker.increment_llm_calls()
        tracker.increment_tool_calls()
        tracker.reset()
        assert tracker.total_tokens == 0
        assert tracker.llm_calls == 0
        assert tracker.tool_calls == 0

    def test_snapshot(self):
        tracker = TokenBudgetTracker(
            budget=500,
            cost_per_input_token=0.001,
            cost_per_output_token=0.002,
        )
        tracker.add_input_tokens(100)
        tracker.add_output_tokens(50)
        tracker.increment_llm_calls()
        snapshot = tracker.snapshot()
        assert snapshot["input_tokens"] == 100
        assert snapshot["output_tokens"] == 50
        assert snapshot["total_tokens"] == 150
        assert snapshot["llm_calls"] == 1
        assert snapshot["budget"] == 500
        assert snapshot["budget_exceeded"] is False
        assert snapshot["estimated_cost"] == pytest.approx(0.1 + 0.1)

    def test_thread_safety(self):
        tracker = TokenBudgetTracker(budget=0)
        errors: list[Exception] = []

        def add_tokens():
            try:
                for _ in range(1000):
                    tracker.add_input_tokens(1)
                    tracker.add_output_tokens(1)
                    tracker.increment_llm_calls()
            except Exception as exc:  # pragma: no cover - defensive
                errors.append(exc)

        threads = [threading.Thread(target=add_tokens) for _ in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert not errors
        assert tracker.input_tokens == 4000
        assert tracker.output_tokens == 4000
        assert tracker.llm_calls == 4000


class TestCountTokens:
    def test_count_tokens_nonempty(self):
        assert count_tokens("hello world") > 0

    def test_count_tokens_empty(self):
        assert count_tokens("") == 0

    def test_count_messages_tokens(self):
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"},
        ]
        assert count_messages_tokens(messages) > 0

    def test_count_messages_tokens_empty(self):
        assert count_messages_tokens([]) == 0
