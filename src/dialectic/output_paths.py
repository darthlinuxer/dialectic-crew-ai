"""Helpers for scoped centralized artifact directories."""

from __future__ import annotations

from pathlib import Path

from dialectic.target import get_active_target
from dialectic.vision import VisionContext, normalize_vision_context, resolve_app_root


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
    return resolve_app_root() / "prd_output" / Path(*_scope_parts(context))


def resolve_exec_output_dir(
    context: VisionContext = VisionContext.PROJECT,
) -> Path:
    """Resolve the centralized execution-tracking directory for the active scope."""
    return resolve_app_root() / "exec_output" / Path(*_scope_parts(context))
