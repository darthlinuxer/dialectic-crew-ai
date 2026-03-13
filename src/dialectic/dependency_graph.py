"""Shared validation helpers for dependency graphs in PRDs and execution plans."""

from __future__ import annotations

from collections.abc import Sequence

from schemas import ImplementationTask, UserStory


def _cycle_to_message(cycle: Sequence[str], item_label: str) -> str:
    return f"{item_label.title()} circular dependencies detected: {' -> '.join(cycle)}"


def _validate_dependency_pairs(
    pairs: Sequence[tuple[str, Sequence[str]]],
    *,
    item_label: str,
) -> list[str]:
    errors: list[str] = []
    dependency_map: dict[str, list[str]] = {}
    duplicate_ids: set[str] = set()

    for item_id, dependencies in pairs:
        if item_id in dependency_map:
            duplicate_ids.add(item_id)
        dependency_map[item_id] = list(dependencies)

    if duplicate_ids:
        duplicates = ", ".join(sorted(duplicate_ids))
        errors.append(f"Duplicate {item_label} ids found: {duplicates}")

    known_ids = set(dependency_map)
    for item_id, dependencies in dependency_map.items():
        unknown = sorted(
            {
                dependency
                for dependency in dependencies
                if dependency not in known_ids
            }
        )
        if unknown:
            errors.append(
                f"{item_label.title()} {item_id} has unknown dependencies: {', '.join(unknown)}"
            )
        if item_id in dependencies:
            errors.append(f"{item_label.title()} {item_id} has a self-dependency")

    cycles = _find_cycles(dependency_map)
    errors.extend(_cycle_to_message(cycle, item_label) for cycle in cycles)
    return errors


def _find_cycles(dependency_map: dict[str, list[str]]) -> list[list[str]]:
    visited: set[str] = set()
    visiting: set[str] = set()
    stack: list[str] = []
    recorded_cycles: set[tuple[str, ...]] = set()
    cycles: list[list[str]] = []

    def visit(node: str) -> None:
        if node in visited:
            return
        visiting.add(node)
        stack.append(node)
        for dependency in dependency_map.get(node, []):
            if dependency not in dependency_map:
                continue
            if dependency in visiting:
                cycle_start = stack.index(dependency)
                cycle = stack[cycle_start:] + [dependency]
                signature = tuple(cycle)
                if signature not in recorded_cycles:
                    recorded_cycles.add(signature)
                    cycles.append(cycle)
                continue
            visit(dependency)
        stack.pop()
        visiting.remove(node)
        visited.add(node)

    for node in dependency_map:
        if node not in visited:
            visit(node)
    return cycles


def validate_user_story_dependencies(user_stories: Sequence[UserStory]) -> list[str]:
    """Return validation errors for user story dependencies."""
    return _validate_dependency_pairs(
        [(story.id, story.dependencies) for story in user_stories],
        item_label="user story",
    )


def validate_task_dependencies(tasks: Sequence[ImplementationTask]) -> list[str]:
    """Return validation errors for implementation task dependencies."""
    return _validate_dependency_pairs(
        [(task.id, task.dependencies) for task in tasks],
        item_label="task",
    )


def format_dependency_errors(errors: Sequence[str], *, subject: str) -> str:
    """Format dependency validation errors for guardrails and runtime failures."""
    joined = "; ".join(errors)
    return (
        f"{subject} has invalid dependencies: {joined}. "
        "Dependencies must reference only known IDs, "
        "must not be self-referential, and must not form circular dependencies."
    )
