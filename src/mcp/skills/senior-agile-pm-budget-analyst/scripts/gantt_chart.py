#!/usr/bin/env python3
"""
Gantt Chart Generator

Creates Gantt chart data structures for Agile/Scrum project scheduling:
- Generates timeline representations from epics/sprints
- Calculates dependencies and parallel tracks
- Produces ASCII and structured data outputs
- Integrates with Critical Path Analysis

Author: Senior Agile PM Budget Analyst Skill
License: MIT
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when validation fails"""
    pass


class TaskStatus(Enum):
    """Task status enumeration"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class TaskType(Enum):
    """Task type enumeration"""
    EPIC = "epic"
    SPRINT = "sprint"
    STORY = "story"
    MILESTONE = "milestone"


@dataclass
class Task:
    """Represents a task in the Gantt chart"""
    id: str
    name: str
    task_type: TaskType
    start_date: datetime
    duration_days: int
    dependencies: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.NOT_STARTED
    assigned_to: Optional[str] = None
    progress_percent: float = 0.0
    sprint_number: Optional[int] = None
    story_points: Optional[int] = None

    @property
    def end_date(self) -> datetime:
        """Calculate end date based on start and duration"""
        return self.start_date + timedelta(days=self.duration_days)

    @property
    def is_critical(self) -> bool:
        """Check if task is on critical path (set by external analysis)"""
        return getattr(self, '_is_critical', False)

    @is_critical.setter
    def is_critical(self, value: bool):
        self._is_critical = value

    def validate(self) -> None:
        """Validate task data"""
        if self.duration_days <= 0:
            raise ValidationError(f"Task {self.id}: duration must be positive")

        if not (0 <= self.progress_percent <= 100):
            raise ValidationError(f"Task {self.id}: progress must be between 0 and 100")


@dataclass
class GanttConfig:
    """Configuration for Gantt chart generation"""
    project_start_date: datetime
    sprint_duration_days: int = 14  # 2 weeks
    work_days_per_week: int = 5
    show_weekends: bool = False
    milestone_markers: bool = True
    show_progress: bool = True
    ascii_chart_width: int = 80

    def validate(self) -> None:
        """Validate configuration"""
        if self.sprint_duration_days <= 0:
            raise ValidationError("sprint_duration_days must be positive")

        if not (1 <= self.work_days_per_week <= 7):
            raise ValidationError("work_days_per_week must be between 1 and 7")

        if self.ascii_chart_width < 40:
            raise ValidationError("ascii_chart_width must be at least 40")


class GanttChartGenerator:
    """
    Gantt Chart Generator

    Creates Gantt chart representations for project scheduling:
    - Supports epics, sprints, stories, milestones
    - Handles dependencies and parallel execution
    - Generates ASCII visualization and structured data
    - Calculates timeline metrics

    Example:
        config = GanttConfig(
            project_start_date=datetime(2024, 1, 1),
            sprint_duration_days=14
        )

        generator = GanttChartGenerator(config)

        # Add tasks
        generator.add_task(Task(
            id="EPIC-001",
            name="Authentication System",
            task_type=TaskType.EPIC,
            start_date=config.project_start_date,
            duration_days=28
        ))

        # Generate chart
        chart_data = generator.generate()
    """

    def __init__(self, config: GanttConfig):
        """
        Initialize generator with configuration

        Args:
            config: GanttConfig instance

        Raises:
            ValidationError: If configuration is invalid
        """
        config.validate()
        self.config = config
        self.tasks: Dict[str, Task] = {}
        self.milestones: List[Task] = []

        logger.info("GanttChartGenerator initialized")

    def add_task(self, task: Task) -> None:
        """
        Add a task to the Gantt chart

        Args:
            task: Task instance

        Raises:
            ValidationError: If task is invalid or duplicate ID
        """
        task.validate()

        if task.id in self.tasks:
            raise ValidationError(f"Task with ID {task.id} already exists")

        self.tasks[task.id] = task

        if task.task_type == TaskType.MILESTONE:
            self.milestones.append(task)

        logger.info(f"Added task: {task.id} - {task.name}")

    def add_tasks_batch(self, tasks: List[Task]) -> None:
        """Add multiple tasks at once"""
        for task in tasks:
            self.add_task(task)

    def validate_dependencies(self) -> List[str]:
        """
        Validate all task dependencies

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        for task_id, task in self.tasks.items():
            for dep_id in task.dependencies:
                if dep_id not in self.tasks:
                    errors.append(f"Task {task_id} depends on non-existent task {dep_id}")

        # Check for circular dependencies
        def has_cycle(task_id: str, visited: set, rec_stack: set) -> bool:
            visited.add(task_id)
            rec_stack.add(task_id)

            if task_id in self.tasks:
                for dep in self.tasks[task_id].dependencies:
                    if dep not in visited:
                        if has_cycle(dep, visited, rec_stack):
                            return True
                    elif dep in rec_stack:
                        return True

            rec_stack.remove(task_id)
            return False

        visited = set()
        for task_id in self.tasks.keys():
            if task_id not in visited:
                if has_cycle(task_id, visited, set()):
                    errors.append(f"Circular dependency detected involving task {task_id}")

        return errors

    def calculate_timeline(self) -> Dict:
        """
        Calculate overall project timeline

        Returns:
            Dictionary with timeline metrics
        """
        if not self.tasks:
            return {"error": "No tasks added to chart"}

        all_start_dates = [task.start_date for task in self.tasks.values()]
        all_end_dates = [task.end_date for task in self.tasks.values()]

        project_start = min(all_start_dates)
        project_end = max(all_end_dates)
        project_duration = (project_end - project_start).days

        # Calculate working days (excluding weekends if configured)
        working_days = 0
        current = project_start
        while current <= project_end:
            if self.config.show_weekends or current.weekday() < 5:  # 0-4 is Mon-Fri
                working_days += 1
            current += timedelta(days=1)

        timeline = {
            "project_start": project_start.strftime("%Y-%m-%d"),
            "project_end": project_end.strftime("%Y-%m-%d"),
            "total_duration_days": project_duration,
            "working_days": working_days,
            "calendar_weeks": project_duration // 7,
            "total_tasks": len(self.tasks),
            "milestones": len(self.milestones)
        }

        return timeline

    def get_task_timeline(self, task_id: str) -> Dict:
        """
        Get detailed timeline for a specific task

        Args:
            task_id: Task identifier

        Returns:
            Dictionary with task timeline details
        """
        if task_id not in self.tasks:
            return {"error": f"Task {task_id} not found"}

        task = self.tasks[task_id]

        # Calculate earliest start based on dependencies
        earliest_start = task.start_date
        if task.dependencies:
            dep_end_dates = [
                self.tasks[dep_id].end_date
                for dep_id in task.dependencies
                if dep_id in self.tasks
            ]
            if dep_end_dates:
                earliest_start = max(dep_end_dates)

        # Calculate slack (difference between earliest and actual start)
        slack_days = (task.start_date - earliest_start).days

        timeline = {
            "task_id": task.id,
            "name": task.name,
            "type": task.task_type.value,
            "start_date": task.start_date.strftime("%Y-%m-%d"),
            "end_date": task.end_date.strftime("%Y-%m-%d"),
            "duration_days": task.duration_days,
            "status": task.status.value,
            "progress": task.progress_percent,
            "dependencies": task.dependencies,
            "earliest_possible_start": earliest_start.strftime("%Y-%m-%d"),
            "slack_days": slack_days,
            "is_critical": task.is_critical,
            "assigned_to": task.assigned_to
        }

        return timeline

    def get_parallel_tasks(self, date: datetime) -> List[str]:
        """
        Get all tasks running in parallel on a given date

        Args:
            date: Date to check

        Returns:
            List of task IDs active on that date
        """
        parallel = []
        for task_id, task in self.tasks.items():
            if task.start_date <= date <= task.end_date:
                parallel.append(task_id)
        return parallel

    def get_resource_allocation(self) -> Dict:
        """
        Analyze resource allocation across timeline

        Returns:
            Dictionary with resource allocation details
        """
        if not self.tasks:
            return {"error": "No tasks added"}

        # Group by assignee
        by_assignee: Dict[str, List[Task]] = {}
        for task in self.tasks.values():
            assignee = task.assigned_to or "Unassigned"
            if assignee not in by_assignee:
                by_assignee[assignee] = []
            by_assignee[assignee].append(task)

        allocation = {
            "total_resources": len(by_assignee),
            "by_resource": {}
        }

        for assignee, tasks in by_assignee.items():
            total_days = sum(t.duration_days for t in tasks)
            completed_tasks = [t for t in tasks if t.status == TaskStatus.COMPLETED]
            in_progress_tasks = [t for t in tasks if t.status == TaskStatus.IN_PROGRESS]

            allocation["by_resource"][assignee] = {
                "total_tasks": len(tasks),
                "total_duration_days": total_days,
                "completed": len(completed_tasks),
                "in_progress": len(in_progress_tasks),
                "not_started": len(tasks) - len(completed_tasks) - len(in_progress_tasks),
                "task_ids": [t.id for t in tasks]
            }

        return allocation

    def generate_ascii_chart(self, max_tasks: int = 20) -> str:
        """
        Generate ASCII Gantt chart

        Args:
            max_tasks: Maximum number of tasks to display

        Returns:
            ASCII string representation of Gantt chart
        """
        if not self.tasks:
            return "No tasks to display"

        # Sort tasks by start date
        sorted_tasks = sorted(self.tasks.values(), key=lambda t: t.start_date)
        display_tasks = sorted_tasks[:max_tasks]

        # Calculate timeline range
        min_date = min(t.start_date for t in display_tasks)
        max_date = max(t.end_date for t in display_tasks)
        total_days = (max_date - min_date).days + 1

        # Chart dimensions
        name_width = 30
        chart_width = self.config.ascii_chart_width - name_width - 10

        # Build chart
        lines = []
        lines.append("=" * self.config.ascii_chart_width)
        lines.append(f"{'TASK':<{name_width}} | TIMELINE")
        lines.append("-" * self.config.ascii_chart_width)

        # Timeline header (weeks)
        header = " " * name_width + " | "
        for i in range(0, total_days, 7):
            week_num = i // 7 + 1
            header += f"W{week_num:<2} "
        lines.append(header)
        lines.append("-" * self.config.ascii_chart_width)

        # Tasks
        for task in display_tasks:
            # Task name (truncate if too long)
            name_display = task.name[:name_width-2]
            name_display = f"{name_display:<{name_width}}"

            # Calculate bar position and length
            days_from_start = (task.start_date - min_date).days
            bar_start = int((days_from_start / total_days) * chart_width)
            bar_length = max(1, int((task.duration_days / total_days) * chart_width))

            # Build task bar
            bar = " " * bar_start

            # Choose bar character based on status
            if task.status == TaskStatus.COMPLETED:
                char = "█"
            elif task.status == TaskStatus.IN_PROGRESS:
                completed_length = int(bar_length * (task.progress_percent / 100))
                bar += "█" * completed_length
                bar += "░" * (bar_length - completed_length)
                char = None
            elif task.status == TaskStatus.BLOCKED:
                char = "▓"
            else:
                char = "░"

            if char:
                bar += char * bar_length

            # Mark critical path
            if task.is_critical:
                name_display = "🔴 " + name_display[3:]

            # Add milestone marker
            if task.task_type == TaskType.MILESTONE:
                bar += " ◆"

            line = f"{name_display} | {bar}"
            lines.append(line)

        lines.append("=" * self.config.ascii_chart_width)

        # Legend
        lines.append("\nLEGEND:")
        lines.append("  █ = Completed    ░ = Not Started    ▓ = Blocked")
        lines.append("  🔴 = Critical Path    ◆ = Milestone")

        if max_tasks < len(self.tasks):
            lines.append(f"\n(Showing {max_tasks} of {len(self.tasks)} tasks)")

        return "\n".join(lines)

    def generate(self) -> Dict:
        """
        Generate complete Gantt chart data

        Returns:
            Dictionary with all chart data and analysis
        """
        # Validate dependencies
        dep_errors = self.validate_dependencies()
        if dep_errors:
            return {
                "error": "Dependency validation failed",
                "details": dep_errors
            }

        # Calculate timeline
        timeline = self.calculate_timeline()

        # Get task details
        tasks_data = {}
        for task_id in self.tasks:
            tasks_data[task_id] = self.get_task_timeline(task_id)

        # Resource allocation
        resource_allocation = self.get_resource_allocation()

        # Critical path tasks
        critical_tasks = [
            {"id": t.id, "name": t.name}
            for t in self.tasks.values()
            if t.is_critical
        ]

        # Generate ASCII chart
        ascii_chart = self.generate_ascii_chart()

        chart_data = {
            "timeline": timeline,
            "tasks": tasks_data,
            "critical_path": {
                "total_critical_tasks": len(critical_tasks),
                "tasks": critical_tasks
            },
            "resource_allocation": resource_allocation,
            "milestones": [
                {
                    "id": m.id,
                    "name": m.name,
                    "date": m.start_date.strftime("%Y-%m-%d")
                }
                for m in self.milestones
            ],
            "ascii_chart": ascii_chart
        }

        return chart_data

    def export_json(self) -> Dict:
        """
        Export chart data in structured JSON format

        Returns:
            Dictionary ready for JSON serialization
        """
        return self.generate()

    def get_sprint_view(self) -> Dict:
        """
        Generate sprint-specific view of the Gantt chart

        Returns:
            Dictionary with sprint-organized data
        """
        sprints: Dict[int, List[Task]] = {}

        for task in self.tasks.values():
            if task.sprint_number is not None:
                if task.sprint_number not in sprints:
                    sprints[task.sprint_number] = []
                sprints[task.sprint_number].append(task)

        sprint_data = {}
        for sprint_num, sprint_tasks in sorted(sprints.items()):
            total_points = sum(t.story_points or 0 for t in sprint_tasks)
            completed_points = sum(
                t.story_points or 0
                for t in sprint_tasks
                if t.status == TaskStatus.COMPLETED
            )

            sprint_data[f"Sprint {sprint_num}"] = {
                "sprint_number": sprint_num,
                "total_tasks": len(sprint_tasks),
                "story_points": total_points,
                "completed_points": completed_points,
                "completion_rate": (completed_points / total_points * 100) if total_points > 0 else 0,
                "tasks": [
                    {
                        "id": t.id,
                        "name": t.name,
                        "points": t.story_points,
                        "status": t.status.value,
                        "progress": t.progress_percent
                    }
                    for t in sprint_tasks
                ]
            }

        return {
            "total_sprints": len(sprints),
            "sprints": sprint_data
        }


def main():
    """Example usage of GanttChartGenerator"""

    print("=" * 80)
    print("GANTT CHART GENERATOR - Example Usage")
    print("=" * 80)

    # Example: E-commerce Platform Project
    print("\n" + "=" * 80)
    print("EXAMPLE: E-commerce Platform Project")
    print("=" * 80)

    # Configuration
    project_start = datetime(2024, 3, 1)
    config = GanttConfig(
        project_start_date=project_start,
        sprint_duration_days=14,
        ascii_chart_width=100
    )

    generator = GanttChartGenerator(config)

    # Define project tasks
    tasks = [
        # Sprint 1
        Task(
            id="EPIC-001",
            name="User Authentication",
            task_type=TaskType.EPIC,
            start_date=project_start,
            duration_days=14,
            status=TaskStatus.COMPLETED,
            progress_percent=100,
            assigned_to="Team A",
            sprint_number=1,
            story_points=21
        ),

        # Sprint 2
        Task(
            id="EPIC-002",
            name="Product Catalog",
            task_type=TaskType.EPIC,
            start_date=project_start + timedelta(days=14),
            duration_days=14,
            dependencies=["EPIC-001"],
            status=TaskStatus.IN_PROGRESS,
            progress_percent=60,
            assigned_to="Team A",
            sprint_number=2,
            story_points=18
        ),

        Task(
            id="EPIC-003",
            name="Shopping Cart",
            task_type=TaskType.EPIC,
            start_date=project_start + timedelta(days=14),
            duration_days=14,
            dependencies=["EPIC-001"],
            status=TaskStatus.IN_PROGRESS,
            progress_percent=40,
            assigned_to="Team B",
            sprint_number=2,
            story_points=15
        ),

        # Sprint 3
        Task(
            id="EPIC-004",
            name="Checkout Process",
            task_type=TaskType.EPIC,
            start_date=project_start + timedelta(days=28),
            duration_days=14,
            dependencies=["EPIC-002", "EPIC-003"],
            status=TaskStatus.NOT_STARTED,
            assigned_to="Team A",
            sprint_number=3,
            story_points=20
        ),

        Task(
            id="EPIC-005",
            name="Payment Integration",
            task_type=TaskType.EPIC,
            start_date=project_start + timedelta(days=28),
            duration_days=14,
            dependencies=["EPIC-003"],
            status=TaskStatus.NOT_STARTED,
            assigned_to="Team B",
            sprint_number=3,
            story_points=13
        ),

        # Sprint 4
        Task(
            id="EPIC-006",
            name="Order Management",
            task_type=TaskType.EPIC,
            start_date=project_start + timedelta(days=42),
            duration_days=14,
            dependencies=["EPIC-004", "EPIC-005"],
            status=TaskStatus.NOT_STARTED,
            assigned_to="Team A",
            sprint_number=4,
            story_points=18
        ),

        # Milestones
        Task(
            id="MILE-001",
            name="MVP Release",
            task_type=TaskType.MILESTONE,
            start_date=project_start + timedelta(days=28),
            duration_days=1,
            dependencies=["EPIC-002", "EPIC-003"]
        ),

        Task(
            id="MILE-002",
            name="Beta Launch",
            task_type=TaskType.MILESTONE,
            start_date=project_start + timedelta(days=56),
            duration_days=1,
            dependencies=["EPIC-006"]
        ),
    ]

    # Add tasks to generator
    generator.add_tasks_batch(tasks)

    # Mark critical path (would normally come from CPM analysis)
    generator.tasks["EPIC-001"].is_critical = True
    generator.tasks["EPIC-002"].is_critical = True
    generator.tasks["EPIC-004"].is_critical = True
    generator.tasks["EPIC-006"].is_critical = True

    # Generate chart
    print("\n" + "=" * 80)
    print("TIMELINE ANALYSIS")
    print("=" * 80)

    chart_data = generator.generate()

    timeline = chart_data["timeline"]
    print(f"\nProject Timeline:")
    print(f"  Start Date: {timeline['project_start']}")
    print(f"  End Date: {timeline['project_end']}")
    print(f"  Total Duration: {timeline['total_duration_days']} days "
          f"({timeline['calendar_weeks']} weeks)")
    print(f"  Working Days: {timeline['working_days']}")
    print(f"  Total Tasks: {timeline['total_tasks']}")
    print(f"  Milestones: {timeline['milestones']}")

    # Critical Path
    print("\n" + "=" * 80)
    print("CRITICAL PATH")
    print("=" * 80)

    critical = chart_data["critical_path"]
    print(f"\nCritical Tasks: {critical['total_critical_tasks']}")
    for task in critical["tasks"]:
        print(f"  - {task['id']}: {task['name']}")

    # Resource Allocation
    print("\n" + "=" * 80)
    print("RESOURCE ALLOCATION")
    print("=" * 80)

    resources = chart_data["resource_allocation"]
    print(f"\nTotal Resources: {resources['total_resources']}")
    for resource, data in resources["by_resource"].items():
        print(f"\n{resource}:")
        print(f"  Total Tasks: {data['total_tasks']}")
        print(f"  Total Duration: {data['total_duration_days']} days")
        print(f"  Completed: {data['completed']}")
        print(f"  In Progress: {data['in_progress']}")
        print(f"  Not Started: {data['not_started']}")

    # Milestones
    print("\n" + "=" * 80)
    print("MILESTONES")
    print("=" * 80)

    for milestone in chart_data["milestones"]:
        print(f"\n{milestone['name']}:")
        print(f"  ID: {milestone['id']}")
        print(f"  Date: {milestone['date']}")

    # ASCII Chart
    print("\n" + "=" * 80)
    print("GANTT CHART")
    print("=" * 80)
    print("\n" + chart_data["ascii_chart"])

    # Sprint View
    print("\n" + "=" * 80)
    print("SPRINT VIEW")
    print("=" * 80)

    sprint_view = generator.get_sprint_view()
    print(f"\nTotal Sprints: {sprint_view['total_sprints']}")

    for sprint_name, sprint_data in sprint_view["sprints"].items():
        print(f"\n{sprint_name}:")
        print(f"  Total Tasks: {sprint_data['total_tasks']}")
        print(f"  Story Points: {sprint_data['story_points']}")
        print(f"  Completed Points: {sprint_data['completed_points']}")
        print(f"  Completion Rate: {sprint_data['completion_rate']:.1f}%")
        print(f"\n  Tasks:")
        for task in sprint_data['tasks']:
            status_icon = "✓" if task['status'] == 'completed' else "•"
            print(f"    {status_icon} {task['id']}: {task['name']} "
                  f"({task['points']} pts, {task['progress']:.0f}%)")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
