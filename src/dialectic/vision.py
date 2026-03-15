"""Vision path resolution for project and self contexts."""

from __future__ import annotations

import hashlib
import os
from enum import Enum
from pathlib import Path


_ENV_PROJECT_ROOT = "DIALECTIC_PROJECT_ROOT"


class VisionContext(str, Enum):
    """Determines which vision document to load.

    PROJECT: the user's project vision (knowledge/VISION.md)
    SELF: the app's own evolution vision (internal/SELF_VISION.md)
    """

    PROJECT = "project"
    SELF = "self"


def normalize_vision_context(
    context: VisionContext | str | Enum = VisionContext.PROJECT,
) -> VisionContext:
    """Coerce compatible enum/string values into the canonical VisionContext."""
    if isinstance(context, VisionContext):
        return context

    raw_value = getattr(context, "value", context)
    try:
        return VisionContext(str(raw_value))
    except ValueError as exc:
        raise ValueError(f"Unsupported vision context: {context!r}") from exc


_VISION_PATHS: dict[VisionContext, Path] = {
    VisionContext.PROJECT: Path("knowledge") / "VISION.md",
    VisionContext.SELF: Path("internal") / "SELF_VISION.md",
}

_PROJECT_VISION_PATH = _VISION_PATHS[VisionContext.PROJECT]


def _search_lineage(start: Path) -> list[Path]:
    return [start, *start.parents]


def _find_first_matching(candidates: list[Path], predicate) -> Path | None:
    for candidate in candidates:
        if predicate(candidate):
            return candidate
    return None


def resolve_app_root() -> Path:
    """Resolve the dialectic-crew-ai application root."""
    env_root = os.getenv(_ENV_PROJECT_ROOT)
    if env_root:
        env_path = Path(env_root).expanduser().resolve()
        if env_path.exists():
            return env_path

    cwd_candidates = _search_lineage(Path.cwd().resolve())
    module_candidates = _search_lineage(Path(__file__).resolve().parent)

    for candidates in (cwd_candidates, module_candidates):
        exact = _find_first_matching(
            candidates,
            lambda candidate: (candidate / "pyproject.toml").exists()
            and (candidate / _PROJECT_VISION_PATH).exists(),
        )
        if exact is not None:
            return exact

        project_root = _find_first_matching(
            candidates,
            lambda candidate: (candidate / "pyproject.toml").exists(),
        )
        if project_root is not None:
            return project_root

        vision_root = _find_first_matching(
            candidates,
            lambda candidate: (candidate / _PROJECT_VISION_PATH).exists(),
        )
        if vision_root is not None:
            return vision_root

    return Path.cwd().resolve()


def resolve_project_root() -> Path:
    """Backward-compatible alias for the application root resolver."""
    return resolve_app_root()


def get_vision_path(
    context: VisionContext = VisionContext.PROJECT,
) -> Path:
    """Return the absolute vision path for the requested context."""
    normalized_context = normalize_vision_context(context)
    if normalized_context is VisionContext.PROJECT:
        from dialectic.target import (  # pylint: disable=import-outside-toplevel
            resolve_project_vision_path,
        )

        return resolve_project_vision_path()
    return resolve_app_root() / _VISION_PATHS[normalized_context]


def ensure_vision_path(
    context: VisionContext = VisionContext.PROJECT,
) -> Path:
    """Ensure the requested vision path exists and return it."""
    normalized_context = normalize_vision_context(context)
    vision_path = get_vision_path(normalized_context)
    if not vision_path.exists():
        if normalized_context is VisionContext.PROJECT:
            from dialectic.target import (  # pylint: disable=import-outside-toplevel
                get_active_target,
            )

            active_target = get_active_target()
            if active_target is not None:
                raise FileNotFoundError(
                    "Active target vision not found. Expected at: "
                    f"{vision_path}. Run `dialectic-crew make-vision` for the active target "
                    "or `dialectic-crew clear-target` to return to the default project vision."
                )
        label = _VISION_PATHS[normalized_context]
        raise FileNotFoundError(
            f"{label} not found. Expected at: {vision_path}"
        )
    return vision_path


def prepare_vision_runtime(
    context: VisionContext = VisionContext.PROJECT,
) -> Path:
    """Prepare the active vision path without mutating the process working directory."""
    return ensure_vision_path(normalize_vision_context(context))


def get_vision_hash(
    context: VisionContext = VisionContext.PROJECT,
) -> str | None:
    """Return a stable content hash for the requested vision document."""
    try:
        content = ensure_vision_path(normalize_vision_context(context)).read_text(
            encoding="utf-8"
        )
    except OSError:
        return None
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
