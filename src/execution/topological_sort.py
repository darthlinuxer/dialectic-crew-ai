"""Task dependency ordering helpers for execution plans."""

from __future__ import annotations

from collections import deque
import logging

from schemas import ImplementationTask

logger = logging.getLogger(__name__)


def topological_sort(tasks: list[ImplementationTask]) -> list[ImplementationTask]:
    """Return tasks ordered by dependency, with stable fallback for cycles."""
    by_id = {task.id: task for task in tasks}
    in_degree = {task.id: 0 for task in tasks}
    unknown_dependencies: dict[str, list[str]] = {}
    for task in tasks:
        for dependency in task.dependencies:
            if dependency in by_id:
                in_degree[task.id] += 1
            else:
                unknown_dependencies.setdefault(task.id, []).append(dependency)

    for task_id, dependencies in unknown_dependencies.items():
        logger.warning(
            "Task %s references unknown dependencies: %s",
            task_id,
            ", ".join(dependencies),
        )

    queue = deque(task_id for task_id, degree in in_degree.items() if degree == 0)
    result: list[ImplementationTask] = []
    while queue:
        task_id = queue.popleft()
        result.append(by_id[task_id])
        for task in tasks:
            if task_id in task.dependencies:
                in_degree[task.id] -= 1
                if in_degree[task.id] == 0:
                    queue.append(task.id)
    if len(result) != len(tasks):
        return sorted(tasks, key=lambda item: (item.order, item.id))
    return result
