"""Tests for the centralized application logging subsystem."""

# pylint: disable=missing-function-docstring,missing-class-docstring
# pylint: disable=too-few-public-methods,duplicate-code

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import cast

from dialectic.app_logging import (
    bind_log_context,
    configure_application_logging,
    get_log_context,
    get_logging_config,
    reset_log_context,
    shutdown_application_logging,
)
from execution.task_guardrails import _text_result_guardrail


def _read_json_lines(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_get_logging_config_defaults(tmp_path, monkeypatch):
    monkeypatch.delenv("DIALECTIC_LOG_ENABLED", raising=False)
    monkeypatch.delenv("DIALECTIC_LOG_LEVEL", raising=False)
    monkeypatch.delenv("DIALECTIC_TEXT_LOG", raising=False)
    monkeypatch.delenv("DIALECTIC_JSON_LOG", raising=False)
    monkeypatch.delenv("DIALECTIC_ERROR_LOG", raising=False)
    monkeypatch.setenv("DIALECTIC_LOG_DIR", str(tmp_path / "logs"))

    config = get_logging_config()

    assert config.enabled is True
    assert config.level_name == "INFO"
    assert config.log_dir == tmp_path / "logs"
    assert config.text_log_path == tmp_path / "logs" / "app.log"
    assert config.json_log_path == tmp_path / "logs" / "app.jsonl"
    assert config.error_log_path == tmp_path / "logs" / "error.log"


def test_get_logging_config_honors_explicit_paths(tmp_path, monkeypatch):
    monkeypatch.setenv("DIALECTIC_LOG_DIR", str(tmp_path / "custom-dir"))
    monkeypatch.setenv("DIALECTIC_TEXT_LOG", str(tmp_path / "text.log"))
    monkeypatch.setenv("DIALECTIC_JSON_LOG", str(tmp_path / "json.log"))
    monkeypatch.setenv("DIALECTIC_ERROR_LOG", str(tmp_path / "errors.log"))
    monkeypatch.setenv("DIALECTIC_LOG_LEVEL", "debug")

    config = get_logging_config()

    assert config.level_name == "DEBUG"
    assert config.text_log_path == tmp_path / "text.log"
    assert config.json_log_path == tmp_path / "json.log"
    assert config.error_log_path == tmp_path / "errors.log"


def test_runtime_log_dir_override_rehomes_default_file_paths(tmp_path, monkeypatch):
    monkeypatch.setenv("DIALECTIC_LOG_DIR", str(tmp_path / "override-logs"))
    monkeypatch.setenv("DIALECTIC_TEXT_LOG", ".dialectic/app.log")
    monkeypatch.setenv("DIALECTIC_JSON_LOG", ".dialectic/app.jsonl")
    monkeypatch.setenv("DIALECTIC_ERROR_LOG", ".dialectic/error.log")

    config = get_logging_config()

    assert config.log_dir == tmp_path / "override-logs"
    assert config.text_log_path == tmp_path / "override-logs" / "app.log"
    assert config.json_log_path == tmp_path / "override-logs" / "app.jsonl"
    assert config.error_log_path == tmp_path / "override-logs" / "error.log"


def test_bind_log_context_populates_missing_fields():
    token = bind_log_context(run_id="run-123")
    try:
        context = get_log_context()
    finally:
        reset_log_context(token)

    assert context["run_id"] == "run-123"
    assert context["flow_id"] == "-"
    assert context["task_id"] == "-"
    assert context["correlation_id"] == "-"


def test_configure_application_logging_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("DIALECTIC_LOG_DIR", str(tmp_path))
    shutdown_application_logging()

    configure_application_logging(force=True)
    root_logger = logging.getLogger()
    first_handlers = tuple(id(handler) for handler in root_logger.handlers)

    configure_application_logging()
    second_handlers = tuple(id(handler) for handler in root_logger.handlers)

    assert second_handlers == first_handlers


def test_configure_application_logging_writes_text_json_and_error_logs(tmp_path, monkeypatch):
    monkeypatch.setenv("DIALECTIC_LOG_DIR", str(tmp_path))
    monkeypatch.setenv("DIALECTIC_LOG_TO_STDERR", "false")
    monkeypatch.setenv("DIALECTIC_LOG_LEVEL", "DEBUG")
    shutdown_application_logging()

    config = configure_application_logging(force=True)
    token = bind_log_context(
        command="test",
        phase="unit",
        correlation_id="corr-123",
        flow_id="flow-456",
    )
    try:
        logger = logging.getLogger("tests.logging")
        logger.info("Hello structured world")
        logger.error("Boom goes the logger")
    finally:
        reset_log_context(token)
        logging.shutdown()
        shutdown_application_logging()

    text_log = config.text_log_path.read_text(encoding="utf-8")
    assert "Hello structured world" in text_log
    assert "command=test" in text_log
    assert "correlation_id=corr-123" in text_log

    json_lines = _read_json_lines(config.json_log_path)
    assert any(line["message"] == "Hello structured world" for line in json_lines)
    info_line = next(line for line in json_lines if line["message"] == "Hello structured world")
    assert info_line["command"] == "test"
    assert info_line["phase"] == "unit"
    assert info_line["correlation_id"] == "corr-123"
    assert info_line["flow_id"] == "flow-456"

    error_log = config.error_log_path.read_text(encoding="utf-8")
    assert "Boom goes the logger" in error_log
    assert "Hello structured world" not in error_log


def test_json_logging_preserves_optional_event_metadata(tmp_path, monkeypatch):
    monkeypatch.setenv("DIALECTIC_LOG_DIR", str(tmp_path))
    monkeypatch.setenv("DIALECTIC_LOG_TO_STDERR", "false")
    shutdown_application_logging()

    config = configure_application_logging(force=True)
    token = bind_log_context(command="execute", phase="tool")
    try:
        logger = logging.getLogger("tests.events")
        logger.info(
            "CrewAI event observed",
            extra={
                "event_type": "ToolUsageFinishedEvent",
                "agent_role": "Implementer",
                "tool_name": "read_file",
            },
        )
    finally:
        reset_log_context(token)
        logging.shutdown()
        shutdown_application_logging()

    json_line = next(
        line
        for line in _read_json_lines(config.json_log_path)
        if line["message"] == "CrewAI event observed"
    )
    assert json_line["event_type"] == "ToolUsageFinishedEvent"
    assert json_line["agent_role"] == "Implementer"
    assert json_line["tool_name"] == "read_file"


def test_text_result_guardrail_json_log_includes_guardrail_reason(tmp_path, monkeypatch):
    monkeypatch.setenv("DIALECTIC_LOG_DIR", str(tmp_path))
    monkeypatch.setenv("DIALECTIC_LOG_TO_STDERR", "false")
    shutdown_application_logging()

    config = configure_application_logging(force=True)

    class Result:  # pylint: disable=too-few-public-methods
        raw = (
            "[ChatCompletionMessageFunctionToolCall(id='call_123', "
            'function=Function(arguments=\'{"file_path":"internal/SELF_VISION.md"}\', '
            "name='search_a_files_content'), type='function')]"
        )

    try:
        _text_result_guardrail(Result())
    finally:
        logging.shutdown()
        shutdown_application_logging()

    json_line = next(
        line
        for line in _read_json_lines(config.json_log_path)
        if cast(str, line["message"]).startswith(
            "tool-call-output-rejected by text_result guardrail"
        )
    )
    assert json_line["guardrail"] == "text_result"
    assert json_line["reason"] == "tool_call_output"
    assert "ChatCompletionMessageFunctionToolCall" in cast(str, json_line["preview"])
