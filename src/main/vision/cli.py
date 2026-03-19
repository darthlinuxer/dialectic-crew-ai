"""CLI command handlers for vision generation workflows."""

from __future__ import annotations

import sys
from pathlib import Path

from dialectic.repo_analyzer import analyze_repository
from dialectic.target import get_active_target
from dialectic.vision import resolve_app_root
from dialectic.vision_generator import generate_vision_markdown


def _resolve_output_path(
    output_path: str | None,
    *,
    self_mode: bool,
    active_target,
) -> Path:
    """Resolve the destination for a generated vision document."""
    app_root = resolve_app_root()
    if output_path:
        candidate = Path(output_path).expanduser()
        return candidate if candidate.is_absolute() else (app_root / candidate)
    if self_mode:
        return app_root / "internal" / "SELF_VISION.md"
    if active_target is None or active_target.vision_path is None:
        raise ValueError("Target vision path is unavailable.")
    return active_target.vision_path


def cmd_make_vision(*, output_path: str | None, self_mode: bool = False) -> None:
    """Generate a VISION.md draft for the active target or the app itself."""
    if self_mode:
        active_target = None
        repo_root = resolve_app_root()
    else:
        active_target = get_active_target()
        if active_target is None:
            print("No target project set.")
            print("Use: dialectic-crew set-target <path>")
            sys.exit(1)
        repo_root = active_target.target_path

    analysis = analyze_repository(repo_root)
    rendered = generate_vision_markdown(analysis)
    destination = _resolve_output_path(
        output_path,
        self_mode=self_mode,
        active_target=active_target,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(rendered, encoding="utf-8")
    print(f"Vision saved: {destination}")
    print(f"Analyzed repository: {repo_root}")
