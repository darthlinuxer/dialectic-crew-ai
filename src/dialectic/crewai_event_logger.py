"""Bridge CrewAI runtime events into the centralized application logger."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Sequence

from dialectic.app_logging import log_context

logger = logging.getLogger(__name__)

_CrewAIBaseEventListener: type[Any] = object
_CREWAI_EVENT_BUS: Any = None
AgentExecutionCompletedEvent: type[Any] | None = None
AgentExecutionErrorEvent: type[Any] | None = None
AgentExecutionStartedEvent: type[Any] | None = None
CrewKickoffCompletedEvent: type[Any] | None = None
CrewKickoffFailedEvent: type[Any] | None = None
CrewKickoffStartedEvent: type[Any] | None = None
FlowFinishedEvent: type[Any] | None = None
FlowStartedEvent: type[Any] | None = None
LLMCallCompletedEvent: type[Any] | None = None
LLMCallFailedEvent: type[Any] | None = None
LLMCallStartedEvent: type[Any] | None = None
MethodExecutionFailedEvent: type[Any] | None = None
MethodExecutionFinishedEvent: type[Any] | None = None
MethodExecutionStartedEvent: type[Any] | None = None
TaskCompletedEvent: type[Any] | None = None
TaskFailedEvent: type[Any] | None = None
TaskStartedEvent: type[Any] | None = None
ToolUsageErrorEvent: type[Any] | None = None
ToolUsageFinishedEvent: type[Any] | None = None
ToolUsageStartedEvent: type[Any] | None = None

try:
    from crewai.events import (
        AgentExecutionCompletedEvent,
        AgentExecutionErrorEvent,
        AgentExecutionStartedEvent,
        BaseEventListener as _ImportedCrewAIBaseEventListener,
        CrewKickoffCompletedEvent,
        CrewKickoffFailedEvent,
        CrewKickoffStartedEvent,
        FlowFinishedEvent,
        FlowStartedEvent,
        LLMCallCompletedEvent,
        LLMCallFailedEvent,
        LLMCallStartedEvent,
        MethodExecutionFailedEvent,
        MethodExecutionFinishedEvent,
        MethodExecutionStartedEvent,
        TaskCompletedEvent,
        TaskFailedEvent,
        TaskStartedEvent,
        ToolUsageErrorEvent,
        ToolUsageFinishedEvent,
        ToolUsageStartedEvent,
        crewai_event_bus as _IMPORTED_CREWAI_EVENT_BUS,
    )
    _CrewAIBaseEventListener = _ImportedCrewAIBaseEventListener
    _CREWAI_EVENT_BUS = _IMPORTED_CREWAI_EVENT_BUS
    _HAS_CREWAI_EVENTS = True
except (ImportError, AttributeError):  # pragma: no cover - defensive import fallback
    _HAS_CREWAI_EVENTS = False


def _safe_get_attr(obj: Any, *names: str, default: str = "-") -> str:
    for name in names:
        value = getattr(obj, name, None)
        if value not in {None, ""}:
            return str(value)
    return default


def _event_level(event: Any) -> int:
    name = event.__class__.__name__.lower()
    if "failed" in name or "error" in name:
        return logging.ERROR
    if "started" in name:
        return logging.DEBUG
    return logging.INFO


def _event_context(source: Any, event: Any) -> dict[str, str]:
    source_state = getattr(source, "state", None)
    return {
        "flow_id": _safe_get_attr(event, "flow_id", "id", default=_safe_get_attr(source, "flow_id", default=_safe_get_attr(source_state, "id"))),
        "run_id": _safe_get_attr(event, "run_id", default=_safe_get_attr(source, "run_id")),
        "task_id": _safe_get_attr(event, "task_id", default=_safe_get_attr(source_state, "task_id")),
        "story_id": _safe_get_attr(event, "user_story_id", "plan_id", default="-"),
        "vision_context": _safe_get_attr(event, "vision_context", default=_safe_get_attr(source_state, "vision_context")),
        "phase": _safe_get_attr(event, "phase", default=event.__class__.__name__),
    }


def _event_extra(source: Any, event: Any) -> dict[str, str]:
    agent = getattr(event, "agent", None)
    return {
        "event_type": _safe_get_attr(event, "type", default=event.__class__.__name__),
        "event_name": event.__class__.__name__,
        "source_name": source.__class__.__name__ if source is not None else "-",
        "agent_role": _safe_get_attr(agent, "role"),
        "tool_name": _safe_get_attr(event, "tool_name"),
    }


def _default_event_types() -> tuple[type[Any], ...]:
    if not _HAS_CREWAI_EVENTS:
        return ()
    return tuple(
        event_type
        for event_type in (
            CrewKickoffStartedEvent,
            CrewKickoffCompletedEvent,
            CrewKickoffFailedEvent,
            AgentExecutionStartedEvent,
            AgentExecutionCompletedEvent,
            AgentExecutionErrorEvent,
            TaskStartedEvent,
            TaskCompletedEvent,
            TaskFailedEvent,
            FlowStartedEvent,
            FlowFinishedEvent,
            MethodExecutionStartedEvent,
            MethodExecutionFinishedEvent,
            MethodExecutionFailedEvent,
            LLMCallStartedEvent,
            LLMCallCompletedEvent,
            LLMCallFailedEvent,
            ToolUsageStartedEvent,
            ToolUsageFinishedEvent,
            ToolUsageErrorEvent,
        )
        if event_type is not None
    )


class CrewAIRuntimeEventLogger(_CrewAIBaseEventListener):
    """Best-effort CrewAI event listener that forwards events into app logs."""

    def __init__(self, event_types: Sequence[type[Any]] | None = None) -> None:
        self._event_types = tuple(event_types) if event_types is not None else _default_event_types()
        super().__init__()

    def setup_listeners(self, crewai_event_bus: Any) -> None:
        for event_type in self._event_types:
            self._register_handler(crewai_event_bus, event_type)

    def _register_handler(self, event_bus: Any, event_type: type[Any]) -> None:
        @event_bus.on(event_type)
        def _handler(source: Any, event: Any) -> None:
            self._emit_runtime_log(source, event)

    def _emit_runtime_log(self, source: Any, event: Any) -> None:
        context = _event_context(source, event)
        with log_context(**context):
            logger.log(
                _event_level(event),
                "CrewAI runtime event",
                extra=_event_extra(source, event),
            )



@dataclass
class _EventLoggerState:
    listener: CrewAIRuntimeEventLogger | None = None


_EVENT_LOGGER_STATE = _EventLoggerState()


def register_crewai_event_logger() -> bool:
    if not _HAS_CREWAI_EVENTS or _CREWAI_EVENT_BUS is None:
        return False
    if _EVENT_LOGGER_STATE.listener is not None:
        return True

    listener = CrewAIRuntimeEventLogger()
    _EVENT_LOGGER_STATE.listener = listener
    listener.setup_listeners(_CREWAI_EVENT_BUS)
    logger.debug("CrewAI event listener bridge registered")
    return True


__all__ = ["CrewAIRuntimeEventLogger", "register_crewai_event_logger"]