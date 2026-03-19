"""Compatibility package for the self-improve orchestrator.

This package is the public surface for `main.self_improve`. It wraps the package
module implementation in `src/main/self_improve/orchestrator.py` so tests and
callers can monkeypatch package globals while the orchestrator continues to
route all staged work through `VisionContext.SELF`.
Compatibility contract: `vision_context=VisionContext.SELF`.
"""

# pylint: disable=trailing-newlines

from __future__ import annotations

import inspect
import os
import shutil
import sys
import time
from functools import wraps
from typing import Any, Callable, TypeVar, cast

from . import (
    code_structure,
    git_helpers,
    llm_retries,
    metrics,
    orchestrator,
    paths,
    persistence,
    pr_builder,
    quality_gate,
    runtime,
    test_runner,
)

_llm_retries = llm_retries
_runtime = runtime

_F = TypeVar("_F", bound=Callable[..., Any])
_PACKAGE_INTERNALS = {
    "Any",
    "Callable",
    "TypeVar",
    "_F",
    "_PACKAGE_INTERNALS",
    "_SYNC_EXCLUDED",
    "_llm_retries",
    "_legacy",
    "_make_wrapper",
    "_runtime",
    "_sync_legacy_globals",
    "_impl",
    "_sync_impl_globals",
    "annotations",
    "cast",
    "inspect",
    "orchestrator",
    "wraps",
}
_SYNC_EXCLUDED = _PACKAGE_INTERNALS | {"__all__"}


def _sync_legacy_globals() -> None:
    for name, value in globals().items():
        if name.startswith("__") or name in _SYNC_EXCLUDED:
            continue
        setattr(_legacy, name, value)
    _runtime.os = os
    _runtime.shutil = shutil
    _llm_retries.os = os
    _llm_retries.time = time


def _make_wrapper(func: _F) -> _F:
    @wraps(func)
    def _wrapped(*args: Any, **kwargs: Any) -> Any:
        _sync_legacy_globals()
        return func(*args, **kwargs)

    return cast(_F, _wrapped)


_legacy = orchestrator
sys.modules.setdefault("main.self_improve", sys.modules[__name__])

for _name in dir(_legacy):
    if _name.startswith("__") or _name in _PACKAGE_INTERNALS:
        continue
    _value = getattr(_legacy, _name)
    if inspect.isfunction(_value):
        globals()[_name] = _make_wrapper(_value)
    else:
        globals()[_name] = _value

PROTECTED_PATHS = paths.PROTECTED_PATHS
SIMULATION_BRANCH_NAME = paths.SIMULATION_BRANCH_NAME
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
_self_improve_execution_retries = cast(
    Callable[..., Any], globals()["_self_improve_execution_retries"]
)
_run_with_transient_llm_retries = cast(
    Callable[..., Any], globals()["_run_with_transient_llm_retries"]
)
_save_self_improve_record = cast(
    Callable[..., Any], globals()["_save_self_improve_record"]
)
_simulation_runtime_environment = cast(
    Callable[..., Any], globals()["_simulation_runtime_environment"]
)
_simulation_runtime_root = cast(
    Callable[..., Any], globals()["_simulation_runtime_root"]
)
_self_improve_llm_stage_retries = getattr(
    llm_retries,
    "_self_improve_llm_stage_retries",
)
_self_improve_test_timeout = getattr(runtime, "_self_improve_test_timeout")
_snapshot_tests = cast(Callable[..., Any], globals()["_snapshot_tests"])
_summarize_resume_state = cast(Callable[..., Any], globals()["_summarize_resume_state"])
_is_transient_llm_error = getattr(llm_retries, "_is_transient_llm_error")
run_self_improve = cast(Callable[..., Any], globals()["run_self_improve"])

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
    "_self_improve_execution_retries",
    "_run_with_transient_llm_retries",
    "_save_self_improve_record",
    "_simulation_runtime_environment",
    "_simulation_runtime_root",
    "_self_improve_llm_stage_retries",
    "_self_improve_test_timeout",
    "_snapshot_tests",
    "_summarize_resume_state",
    "code_structure",
    "git_helpers",
    "llm_retries",
    "metrics",
    "os",
    "paths",
    "persistence",
    "pr_builder",
    "quality_gate",
    "run_self_improve",
    "runtime",
    "shutil",
    "test_runner",
    "time",
]
# End of public compatibility exports.
