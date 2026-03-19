"""Tests for the CrewAI event-to-logging bridge."""

# pylint: disable=missing-function-docstring,too-few-public-methods

from __future__ import annotations

import logging
from collections.abc import Callable

from dialectic.crewai_event_logger import CrewAIRuntimeEventLogger


class _FakeEventBus:
    """Minimal event bus stub for listener registration tests."""

    def __init__(self):
        self.handlers: dict[type[object], list[Callable[[object, object], None]]] = {}

    def on(self, event_type):
        def decorator(func):
            self.handlers.setdefault(event_type, []).append(func)
            return func

        return decorator


class _FlowStartedEvent:
    """Tiny fake CrewAI event used by bridge tests."""

    type = "flow_started"

    def __init__(self):
        self.flow_id = "flow-123"
        self.timestamp = "2026-03-12T12:00:00Z"


def test_crewai_event_logger_registers_handlers():
    event_bus = _FakeEventBus()
    listener = CrewAIRuntimeEventLogger(event_types=[_FlowStartedEvent])

    listener.setup_listeners(event_bus)

    assert _FlowStartedEvent in event_bus.handlers
    assert len(event_bus.handlers[_FlowStartedEvent]) == 1


def test_crewai_event_logger_emits_structured_log(caplog):
    event_bus = _FakeEventBus()
    listener = CrewAIRuntimeEventLogger(event_types=[_FlowStartedEvent])
    listener.setup_listeners(event_bus)
    handler = event_bus.handlers[_FlowStartedEvent][0]

    source = type("Source", (), {"flow_id": "flow-123"})()
    event = _FlowStartedEvent()

    with caplog.at_level(logging.DEBUG, logger="dialectic.crewai_event_logger"):
        handler(source, event)

    assert any("CrewAI runtime event" in record.message for record in caplog.records)
    assert any(
        getattr(record, "event_type", None) == "flow_started"
        for record in caplog.records
    )


def test_crewai_event_logger_suppresses_immediate_duplicate_events(caplog):
    event_bus = _FakeEventBus()
    listener = CrewAIRuntimeEventLogger(event_types=[_FlowStartedEvent])
    listener.setup_listeners(event_bus)
    handler = event_bus.handlers[_FlowStartedEvent][0]

    source = type("Source", (), {"flow_id": "flow-123"})()
    event = _FlowStartedEvent()

    with caplog.at_level(logging.DEBUG, logger="dialectic.crewai_event_logger"):
        handler(source, event)
        handler(source, event)

    matching = [
        record
        for record in caplog.records
        if record.message == "CrewAI runtime event"
        and getattr(record, "event_type", None) == "flow_started"
    ]
    assert len(matching) == 1
