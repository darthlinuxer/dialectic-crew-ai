"""Task dependency ordering helpers for execution plans."""

from __future__ import annotations

from collections import deque

from schemas import ImplementationTask


def topological_sort(tasks: list[ImplementationTask]) -> list[ImplementationTask]:
    """Return tasks ordered by dependency, with stable fallback for cycles."""
    by_id = {task.id: task for task in tasks}
    in_degree = {task.id: 0 for task in tasks}
    for task in tasks:
        for dependency in task.dependencies:
            if dependency in by_id:
                in_degree[task.id] += 1
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
