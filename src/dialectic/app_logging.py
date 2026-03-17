"""Centralized application logging with structured runtime context."""

# pylint: disable=missing-function-docstring,missing-class-docstring
# pylint: disable=too-many-instance-attributes,too-few-public-methods
# pylint: disable=too-many-arguments

from __future__ import annotations

import json
import logging
import os
import re
import threading
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4


_SECRET_PATTERNS = (
    re.compile(r"(sk-[A-Za-z0-9_-]{10,})"),
    re.compile(r"(ctx7sk-[A-Za-z0-9_-]{10,})"),
    re.compile(r"(Bearer\s+)[A-Za-z0-9._-]+", re.IGNORECASE),
)
_LOG_CONTEXT_KEYS = (
    "command",
    "phase",
    "flow_id",
    "run_id",
    "task_id",
    "story_id",
    "correlation_id",
    "vision_context",
)
_OPTIONAL_RECORD_KEYS = (
    "agent_role",
    "tool_name",
    "event_type",
    "event_name",
    "source_name",
    "guardrail",
    "reason",
    "preview",
    "iteration",
    "retry",
)
_SHUTDOWN_NOISE_PATTERNS = (
    re.compile(r"cannot schedule new futures after shutdown", re.IGNORECASE),
    re.compile(r"Error emitting reasoning failed event", re.IGNORECASE),
)
_DEFAULT_CONTEXT = {key: "-" for key in _LOG_CONTEXT_KEYS}
_runtime_log_context: ContextVar[dict[str, str]] = ContextVar(
    "dialectic_runtime_log_context",
    default=_DEFAULT_CONTEXT,
)
_installed_handlers: list[logging.Handler] = []


@dataclass
class _LoggingRuntimeState:
    installed_filter: logging.Filter | None = None
    configured_signature: tuple[Any, ...] | None = None
    suppress_shutdown_noise: bool = False
    suppression_lock: threading.Lock | None = None


_LOGGING_RUNTIME_STATE = _LoggingRuntimeState()
_LOGGING_RUNTIME_STATE.suppression_lock = threading.Lock()


@dataclass(frozen=True)
class LoggingConfig:
    enabled: bool
    level_name: str
    log_dir: Path
    text_log_path: Path
    json_log_path: Path
    error_log_path: Path
    log_to_stderr: bool
    max_bytes: int
    backup_count: int

    def signature(self) -> tuple[Any, ...]:
        return (
            self.enabled,
            self.level_name,
            self.log_dir,
            self.text_log_path,
            self.json_log_path,
            self.error_log_path,
            self.log_to_stderr,
            self.max_bytes,
            self.backup_count,
        )


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _resolve_path(raw_value: str | None, fallback: Path) -> Path:
    if not raw_value:
        return fallback
    return Path(raw_value).expanduser()


def _uses_default_log_path(raw_value: str | None, default_path: Path) -> bool:
    if raw_value is None:
        return True
    return Path(raw_value).expanduser() == default_path


def get_logging_config() -> LoggingConfig:
    default_log_dir = Path(".dialectic").expanduser()
    log_dir = Path(os.getenv("DIALECTIC_LOG_DIR", ".dialectic")).expanduser()
    text_default = default_log_dir / "app.log"
    json_default = default_log_dir / "app.jsonl"
    error_default = default_log_dir / "error.log"
    text_raw = os.getenv("DIALECTIC_TEXT_LOG")
    json_raw = os.getenv("DIALECTIC_JSON_LOG")
    error_raw = os.getenv("DIALECTIC_ERROR_LOG")

    text_log_path = (
        log_dir / "app.log"
        if log_dir != default_log_dir and _uses_default_log_path(text_raw, text_default)
        else _resolve_path(text_raw, log_dir / "app.log")
    )
    json_log_path = (
        log_dir / "app.jsonl"
        if log_dir != default_log_dir and _uses_default_log_path(json_raw, json_default)
        else _resolve_path(json_raw, log_dir / "app.jsonl")
    )
    error_log_path = (
        log_dir / "error.log"
        if log_dir != default_log_dir and _uses_default_log_path(error_raw, error_default)
        else _resolve_path(error_raw, log_dir / "error.log")
    )

    return LoggingConfig(
        enabled=_parse_bool(os.getenv("DIALECTIC_LOG_ENABLED"), True),
        level_name=os.getenv("DIALECTIC_LOG_LEVEL", "INFO").strip().upper(),
        log_dir=log_dir,
        text_log_path=text_log_path,
        json_log_path=json_log_path,
        error_log_path=error_log_path,
        log_to_stderr=_parse_bool(os.getenv("DIALECTIC_LOG_TO_STDERR"), True),
        max_bytes=_parse_int(os.getenv("DIALECTIC_LOG_MAX_BYTES"), 5_000_000),
        backup_count=_parse_int(os.getenv("DIALECTIC_LOG_BACKUP_COUNT"), 5),
    )


def new_correlation_id() -> str:
    return uuid4().hex


def get_log_context() -> dict[str, str]:
    current = _runtime_log_context.get()
    merged = dict(_DEFAULT_CONTEXT)
    merged.update(current)
    return merged


def bind_log_context(**context: Any) -> Token[dict[str, str]]:
    merged = get_log_context()
    for key, value in context.items():
        if key in _LOG_CONTEXT_KEYS and value is not None:
            merged[key] = str(value)
    return _runtime_log_context.set(merged)


def reset_log_context(token: Token[dict[str, str]]) -> None:
    _runtime_log_context.reset(token)


@contextmanager
def log_context(**context: Any) -> Iterator[dict[str, str]]:
    token = bind_log_context(**context)
    try:
        yield get_log_context()
    finally:
        reset_log_context(token)


def _redact_secrets(value: str) -> str:
    redacted = value
    for pattern in _SECRET_PATTERNS:
        if pattern.pattern.lower().startswith("(bearer"):
            redacted = pattern.sub(r"\1[REDACTED]", redacted)
        else:
            redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


class RuntimeContextFilter(logging.Filter):
    """Inject stable runtime context fields into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        if _should_suppress_shutdown_noise(record):
            return False
        context = get_log_context()
        for key in _LOG_CONTEXT_KEYS:
            setattr(record, key, context.get(key, "-"))
        for key in _OPTIONAL_RECORD_KEYS:
            if not hasattr(record, key):
                setattr(record, key, "-")
        return True


class TextLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        return _redact_secrets(message)


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": _redact_secrets(record.getMessage()),
        }
        for key in _LOG_CONTEXT_KEYS + _OPTIONAL_RECORD_KEYS:
            payload[key] = getattr(record, key, "-")
        if record.exc_info:
            payload["exception"] = _redact_secrets(self.formatException(record.exc_info))
        return json.dumps(payload, ensure_ascii=False)


def _build_rotating_handler(
    *,
    path: Path,
    level: int,
    formatter: logging.Formatter,
    context_filter: logging.Filter,
    max_bytes: int,
    backup_count: int,
) -> RotatingFileHandler:
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setLevel(level)
    handler.setFormatter(formatter)
    handler.addFilter(context_filter)
    return handler


def _should_suppress_shutdown_noise(record: logging.LogRecord) -> bool:
    if not _LOGGING_RUNTIME_STATE.suppress_shutdown_noise:
        return False
    message = record.getMessage()
    return any(pattern.search(message) for pattern in _SHUTDOWN_NOISE_PATTERNS)


def enable_shutdown_noise_suppression() -> None:
    lock = _LOGGING_RUNTIME_STATE.suppression_lock
    if lock is None:
        _LOGGING_RUNTIME_STATE.suppress_shutdown_noise = True
        return
    with lock:
        _LOGGING_RUNTIME_STATE.suppress_shutdown_noise = True


def disable_shutdown_noise_suppression() -> None:
    lock = _LOGGING_RUNTIME_STATE.suppression_lock
    if lock is None:
        _LOGGING_RUNTIME_STATE.suppress_shutdown_noise = False
        return
    with lock:
        _LOGGING_RUNTIME_STATE.suppress_shutdown_noise = False


def shutdown_application_logging() -> None:
    root_logger = logging.getLogger()
    for handler in list(_installed_handlers):
        try:
            handler.flush()
        except (OSError, ValueError):  # pragma: no cover - defensive logging cleanup
            pass
        root_logger.removeHandler(handler)
        handler.close()
    _installed_handlers.clear()
    if _LOGGING_RUNTIME_STATE.installed_filter is not None:
        root_logger.removeFilter(_LOGGING_RUNTIME_STATE.installed_filter)
        _LOGGING_RUNTIME_STATE.installed_filter = None
    _LOGGING_RUNTIME_STATE.configured_signature = None
    disable_shutdown_noise_suppression()


def configure_application_logging(*, force: bool = False) -> LoggingConfig:
    config = get_logging_config()
    signature = config.signature()
    if not force and _LOGGING_RUNTIME_STATE.configured_signature == signature:
        return config

    shutdown_application_logging()
    if not config.enabled:
        _LOGGING_RUNTIME_STATE.configured_signature = signature
        return config

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.level_name, logging.INFO))

    context_filter = RuntimeContextFilter()
    _LOGGING_RUNTIME_STATE.installed_filter = context_filter
    root_logger.addFilter(context_filter)

    text_formatter = TextLogFormatter(
        fmt=(
            "%(asctime)s %(levelname)s %(name)s %(message)s "
            "[command=%(command)s phase=%(phase)s flow_id=%(flow_id)s "
            "run_id=%(run_id)s task_id=%(task_id)s story_id=%(story_id)s "
            "correlation_id=%(correlation_id)s vision_context=%(vision_context)s]"
        ),
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    json_formatter = JsonLogFormatter(datefmt="%Y-%m-%dT%H:%M:%S%z")

    handlers: list[logging.Handler] = [
        _build_rotating_handler(
            path=config.text_log_path,
            level=getattr(logging, config.level_name, logging.INFO),
            formatter=text_formatter,
            context_filter=context_filter,
            max_bytes=config.max_bytes,
            backup_count=config.backup_count,
        ),
        _build_rotating_handler(
            path=config.json_log_path,
            level=getattr(logging, config.level_name, logging.INFO),
            formatter=json_formatter,
            context_filter=context_filter,
            max_bytes=config.max_bytes,
            backup_count=config.backup_count,
        ),
        _build_rotating_handler(
            path=config.error_log_path,
            level=logging.ERROR,
            formatter=text_formatter,
            context_filter=context_filter,
            max_bytes=config.max_bytes,
            backup_count=config.backup_count,
        ),
    ]
    if config.log_to_stderr:
        stderr_handler = logging.StreamHandler()
        stderr_handler.setLevel(getattr(logging, config.level_name, logging.INFO))
        stderr_handler.setFormatter(text_formatter)
        stderr_handler.addFilter(context_filter)
        handlers.append(stderr_handler)

    for handler in handlers:
        root_logger.addHandler(handler)
    _installed_handlers.extend(handlers)
    _LOGGING_RUNTIME_STATE.configured_signature = signature

    logging.getLogger(__name__).debug("Application logging configured")
    return config


__all__ = [
    "LoggingConfig",
    "bind_log_context",
    "configure_application_logging",
    "disable_shutdown_noise_suppression",
    "enable_shutdown_noise_suppression",
    "get_log_context",
    "get_logging_config",
    "log_context",
    "new_correlation_id",
    "reset_log_context",
    "shutdown_application_logging",
]
