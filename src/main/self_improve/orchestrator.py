"""Public orchestrator facade for the self-improve package."""

from __future__ import annotations

import inspect
import os
import shutil
import sys
import time
from functools import wraps
from typing import Any, Callable, TypeVar, cast

from .internal import orchestrator as _impl
from .llm_retries import _is_transient_llm_error, _self_improve_llm_stage_retries
from .paths import PROTECTED_PATHS, SIMULATION_BRANCH_NAME
from .runtime import _self_improve_test_timeout

_F = TypeVar("_F", bound=Callable[..., Any])
_SYNC_EXCLUDED = {
    "Any",
    "Callable",
    "PROTECTED_PATHS",
    "SIMULATION_BRANCH_NAME",
    "TypeVar",
    "_F",
    "_SYNC_EXCLUDED",
    "_impl",
    "_is_transient_llm_error",
    "_make_wrapper",
    "_self_improve_llm_stage_retries",
    "_self_improve_test_timeout",
    "annotations",
    "cast",
    "inspect",
    "wraps",
}


def _sync_impl_globals() -> None:
    for name, value in globals().items():
        if name.startswith("__") or name in _SYNC_EXCLUDED:
            continue
        setattr(_impl, name, value)
    _impl.os = os
    setattr(_impl, "shutil", shutil)
    setattr(_impl, "time", time)


def _make_wrapper(func: _F) -> _F:
    @wraps(func)
    def _wrapped(*args: Any, **kwargs: Any) -> Any:
        _sync_impl_globals()
        return func(*args, **kwargs)

    return cast(_F, _wrapped)


for _name in dir(_impl):
    if _name.startswith("__"):
        continue
    _value = getattr(_impl, _name)
    if inspect.isfunction(_value):
        globals()[_name] = _make_wrapper(_value)
    else:
        globals()[_name] = _value

sys.modules.setdefault("main.self_improve.orchestrator", sys.modules[__name__])

run_self_improve = cast(Callable[..., Any], globals()["run_self_improve"])
_build_pr_body = cast(Callable[..., Any], globals()["_build_pr_body"])
_create_pr = cast(Callable[..., Any], globals()["_create_pr"])
_git_worktree_clean = cast(Callable[..., Any], globals()["_git_worktree_clean"])
_list_resumable_cycles = cast(Callable[..., Any], globals()["_list_resumable_cycles"])
_metrics_stable = cast(Callable[..., Any], globals()["_metrics_stable"])
_prepare_simulation_branch = cast(
    Callable[..., Any], globals()["_prepare_simulation_branch"]
)
_pytest_command = cast(Callable[..., Any], globals()["_pytest_command"])
_recover_stale_self_improve_worktree = cast(
    Callable[..., Any], globals()["_recover_stale_self_improve_worktree"]
)
_run_with_transient_llm_retries = cast(
    Callable[..., Any], globals()["_run_with_transient_llm_retries"]
)
_save_self_improve_record = cast(
    Callable[..., Any], globals()["_save_self_improve_record"]
)
_snapshot_tests = cast(Callable[..., Any], globals()["_snapshot_tests"])
_summarize_resume_state = cast(Callable[..., Any], globals()["_summarize_resume_state"])

__all__ = [
    "PROTECTED_PATHS",
    "SIMULATION_BRANCH_NAME",
    "_build_pr_body",
    "_create_pr",
    "_git_worktree_clean",
    "_is_transient_llm_error",
    "_list_resumable_cycles",
    "_metrics_stable",
    "_prepare_simulation_branch",
    "_pytest_command",
    "_recover_stale_self_improve_worktree",
    "_run_with_transient_llm_retries",
    "_save_self_improve_record",
    "_self_improve_llm_stage_retries",
    "_self_improve_test_timeout",
    "_snapshot_tests",
    "_summarize_resume_state",
    "os",
    "run_self_improve",
    "shutil",
    "time",
]
