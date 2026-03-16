"""CLI command handlers for target project management."""

from __future__ import annotations

import sys
from pathlib import Path

from dialectic.target import (
    clear_target,
    get_active_target,
    list_known_targets,
    set_target,
)


def _format_set_at(value) -> str:
    """Render a human-friendly timestamp for CLI output."""
    return value.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


def _print_target(prefix: str, target_config) -> None:
    """Print a consistent multi-line target summary."""
    print(f"{prefix}: {target_config.target_path}")
    print(f"  Repo:   {target_config.repo_name}")
    print(f"  Remote: {target_config.repo_remote or 'none'}")
    print(f"  Set at: {_format_set_at(target_config.set_at)}")


def cmd_set_target(path: str) -> None:
    """Set and print the active target repository."""
    try:
        target_config = set_target(Path(path))
    except ValueError as exc:
        print(f"{exc}")
        sys.exit(1)
    _print_target("Active target", target_config)


def cmd_get_target() -> None:
    """Print the active target repository or a helpful empty-state message."""
    target_config = get_active_target()
    if target_config is None:
        print("No target project set.")
        print("Use: dialectic-crew set-target <path>")
        return
    _print_target("Active target", target_config)


def cmd_clear_target() -> None:
    """Clear the active target repository selection."""
    clear_target()
    print("Target project cleared.")


def cmd_list_targets() -> None:
    """Print all known targets and indicate which one is currently active."""
    targets = list_known_targets()
    active = get_active_target()
    if not targets:
        print("No known targets yet.")
        print("Use: dialectic-crew set-target <path>")
        return

    active_slug = active.target_slug if active is not None else None
    print("Known targets:")
    for target_config in targets:
        is_active = target_config.target_slug == active_slug
        marker = "*" if is_active else " "
        status = "ACTIVE" if is_active else "inactive"
        has_vision = (
            "yes"
            if target_config.vision_path and target_config.vision_path.exists()
            else "no"
        )
        print(
            f"  {marker} {target_config.repo_name:<12} [{status}] "
            f"{target_config.target_path}  VISION: {has_vision}"
        )

