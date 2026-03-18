"""Regression tests for guardrail registration and free-form text output checks."""

# pylint: disable=missing-function-docstring,missing-class-docstring
# pylint: disable=protected-access

import logging

from crewai import Agent, Task

from execution import task_guardrails
from dialectic.yaml_config import get_guardrail_registry


def test_registered_guardrails_are_accepted_by_crewai_task_validation():
    agent = Agent(
        role="Guardrail Validation Tester",
        goal="Exercise CrewAI task validation without executing LLM work",
        backstory="You exist only so tests can instantiate Task objects safely.",
        verbose=False,
        allow_delegation=False,
    )

    for name, guardrail in get_guardrail_registry().items():
        task = Task(
            description=f"Validate guardrail registration for {name}",
            expected_output="Any structured output",
            agent=agent,
            guardrail=guardrail,
        )

        assert task.guardrail is guardrail


def test_text_result_guardrail_rejects_tool_call_objects():
    class Result:  # pylint: disable=too-few-public-methods
        raw = (
            "[ChatCompletionMessageFunctionToolCall(id='call_123', "
            'function=Function(arguments=\'{"file_path":"internal/SELF_VISION.md"}\', '
            "name='search_a_files_content'), type='function')]"
        )

    ok, message = task_guardrails._text_result_guardrail(Result())

    assert ok is False
    assert "plain-text answer" in message
    assert "tool call" in message.lower()


def test_text_result_guardrail_logs_tool_call_rejection(caplog):
    class Result:  # pylint: disable=too-few-public-methods
        raw = (
            "[ChatCompletionMessageFunctionToolCall(id='call_123', "
            'function=Function(arguments=\'{"file_path":"internal/SELF_VISION.md"}\', '
            "name='search_a_files_content'), type='function')]"
        )

    with caplog.at_level(logging.WARNING, logger="execution.task_guardrails"):
        ok, _message = task_guardrails._text_result_guardrail(Result())

    assert ok is False
    assert any(
        "tool-call-output-rejected" in record.message for record in caplog.records
    )


def test_text_result_guardrail_accepts_normal_text():
    class Result:  # pylint: disable=too-few-public-methods
        raw = "Implemented config loading and updated src/main/cli/entrypoint.py."

    ok, payload = task_guardrails._text_result_guardrail(Result())

    assert ok is True
    assert payload == Result.raw
