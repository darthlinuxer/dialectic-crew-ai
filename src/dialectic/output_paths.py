# pylint: disable=duplicate-code
"""Helpers for scoped centralized artifact directories."""

from __future__ import annotations

import os
from pathlib import Path

from dialectic.target import get_active_target
from dialectic.vision import VisionContext, normalize_vision_context, resolve_app_root


RUNTIME_ROOT_ENV_VAR = "DIALECTIC_RUNTIME_ROOT"


def _resolve_runtime_root() -> Path:
    raw_root = os.getenv(RUNTIME_ROOT_ENV_VAR, "").strip()
    if not raw_root:
        return resolve_app_root()

    runtime_root = Path(raw_root).expanduser()
    if not runtime_root.is_absolute():
        runtime_root = resolve_app_root() / runtime_root
    return runtime_root


def _scope_parts(context: VisionContext) -> tuple[str, ...]:
    if normalize_vision_context(context) is VisionContext.SELF:
        return ("self",)
    active_target = get_active_target()
    if active_target is not None:
        return ("targets", active_target.target_slug)
    return ("default",)


def resolve_prd_output_dir(
    context: VisionContext = VisionContext.PROJECT,
) -> Path:
    """Resolve the centralized PRD/plan artifact directory for the active scope."""
    return _resolve_runtime_root() / "prd_output" / Path(*_scope_parts(context))


def resolve_exec_output_dir(
    context: VisionContext = VisionContext.PROJECT,
) -> Path:
    """Resolve the centralized execution-tracking directory for the active scope."""
    return _resolve_runtime_root() / "exec_output" / Path(*_scope_parts(context))
