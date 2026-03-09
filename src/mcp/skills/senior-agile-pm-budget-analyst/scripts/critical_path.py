"""
Module: critical_path.py
Purpose: Critical Path Method (CPM) analysis for project scheduling
Author: AI PM Assistant - senior-agile-pm-budget-analyst
Date: 2026-02-05

Implements the Critical Path Method algorithm to identify the longest sequence
of dependent activities, calculate slack times, and optimize project schedules.
"""

from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
import json
import logging
from collections import defaultdict, deque

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when input validation fails."""
    pass


class CalculationError(Exception):
    """Raised when calculations produce invalid results."""
    pass


@dataclass
class Activity:
    """Represents a project activity/task."""
    id: str
    name: str
    duration: float
    predecessors: List[str] = field(default_factory=list)

    # Calculated fields
    ES: float = 0.0  # Earliest Start
    EF: float = 0.0  # Earliest Finish
    LS: float = 0.0  # Latest Start
    LF: float = 0.0  # Latest Finish
    slack: float = 0.0  # Total Float
    critical: bool = False

    def __post_init__(self):
        """Validate activity data."""
        if not self.id:
            raise ValidationError("Activity ID cannot be empty")
        if self.duration < 0:
            raise ValidationError(f"Activity {self.id} has negative duration")


class CriticalPathAnalyzer:
    """
    Performs Critical Path Method (CPM) analysis on project activities.

    The CPM algorithm identifies the longest path through a project network,
    which determines the minimum project duration. Activities on this path
    have zero slack and are critical to project completion.

    Example:
        >>> activities = [
        ...     {"id": "A", "name": "Design", "duration": 3, "predecessors": []},
        ...     {"id": "B", "name": "Dev", "duration": 5, "predecessors": ["A"]},
        ...     {"id": "C", "name": "Test", "duration": 2, "predecessors": ["B"]}
        ... ]
        >>> analyzer = CriticalPathAnalyzer(activities, unit="days")
        >>> result = analyzer.analyze()
        >>> print(result['critical_path'])
        ['A', 'B', 'C']
    """

    def __init__(self, activities_data: List[Dict], unit: str = "days"):
        """
        Initialize the CPM analyzer.

        Args:
            activities_data: List of activity dictionaries
            unit: Time unit (days, weeks, sprints)

        Raises:
            ValidationError: If activities data is invalid
        """
        self.unit = unit
        self.activities: Dict[str, Activity] = {}
        self.graph: Dict[str, List[str]] = defaultdict(list)  # Adjacency list
        self.reverse_graph: Dict[str, List[str]] = defaultdict(list)

        # Parse and validate activities
        for act_data in activities_data:
            try:
                activity = Activity(
                    id=act_data['id'],
                    name=act_data['name'],
                    duration=float(act_data['duration']),
                    predecessors=act_data.get('predecessors', [])
                )
                self.activities[activity.id] = activity
            except KeyError as e:
                raise ValidationError(f"Missing required field {e} in activity {act_data.get('id', '<unknown>')}")

        # Build graph
        for act_id, activity in self.activities.items():
            for pred_id in activity.predecessors:
                if pred_id not in self.activities:
                    raise ValidationError(f"Unknown predecessor '{pred_id}' for activity '{act_id}'")
                self.graph[pred_id].append(act_id)
                self.reverse_graph[act_id].append(pred_id)

        # Validate no cycles
        if self._has_cycle():
            raise ValidationError("Project network contains circular dependencies")

    def _has_cycle(self) -> bool:
        """
        Detect cycles in the activity network using DFS.

        Returns:
            True if cycle exists, False otherwise
        """
        visited = set()
        rec_stack = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in self.graph[node]:
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        return any(dfs(node) for node in self.activities if node not in visited)

    def _topological_sort(self) -> List[str]:
        """
        Perform topological sort using Kahn's algorithm.

        Returns:
            List of activity IDs in topological order

        Raises:
            CalculationError: If cycle detected (shouldn't happen after validation)
        """
        in_degree = {act_id: 0 for act_id in self.activities}

        for act_id in self.activities:
            for successor in self.graph[act_id]:
                in_degree[successor] += 1

        queue = deque([act_id for act_id, degree in in_degree.items() if degree == 0])
        result = []

        while queue:
            node = queue.popleft()
            result.append(node)

            for successor in self.graph[node]:
                in_degree[successor] -= 1
                if in_degree[successor] == 0:
                    queue.append(successor)

        if len(result) != len(self.activities):
            raise CalculationError("Topological sort failed - cycle detected")

        return result

    def _forward_pass(self) -> float:
        """
        Calculate Earliest Start (ES) and Earliest Finish (EF) times.

        Forward pass algorithm:
        - For activities with no predecessors: ES = 0
        - For other activities: ES = max(EF of all predecessors)
        - EF = ES + Duration

        Returns:
            Project duration (max EF of all activities)
        """
        topo_order = self._topological_sort()

        for act_id in topo_order:
            activity = self.activities[act_id]

            if not activity.predecessors:
                activity.ES = 0
            else:
                activity.ES = max(
                    self.activities[pred_id].EF
                    for pred_id in activity.predecessors
                )

            activity.EF = activity.ES + activity.duration

        project_duration = max(act.EF for act in self.activities.values())
        logger.info(f"Forward pass complete. Project duration: {project_duration} {self.unit}")

        return project_duration

    def _backward_pass(self, project_duration: float) -> None:
        """
        Calculate Latest Start (LS) and Latest Finish (LF) times.

        Backward pass algorithm:
        - For activities with no successors: LF = project_duration
        - For other activities: LF = min(LS of all successors)
        - LS = LF - Duration

        Args:
            project_duration: Total project duration from forward pass
        """
        topo_order = self._topological_sort()

        # Process in reverse topological order
        for act_id in reversed(topo_order):
            activity = self.activities[act_id]

            if not self.graph[act_id]:  # No successors
                activity.LF = project_duration
            else:
                activity.LF = min(
                    self.activities[succ_id].LS
                    for succ_id in self.graph[act_id]
                )

            activity.LS = activity.LF - activity.duration

        logger.info("Backward pass complete")

    def _calculate_slack(self) -> None:
        """
        Calculate slack (float) for each activity.

        Slack = LF - EF = LS - ES

        Activities with slack = 0 are on the critical path.
        """
        for activity in self.activities.values():
            activity.slack = activity.LF - activity.EF
            activity.critical = abs(activity.slack) < 1e-9  # Handle floating point

    def _identify_critical_path(self) -> List[str]:
        """
        Identify the critical path (sequence of activities with slack = 0).

        Returns:
            List of activity IDs on the critical path in order
        """
        critical_activities = [
            act_id for act_id, act in self.activities.items()
            if act.critical
        ]

        # Sort critical activities in dependency order
        return [act_id for act_id in self._topological_sort()
                if act_id in critical_activities]

    def _identify_bottlenecks(self) -> List[Dict]:
        """
        Identify bottlenecks: critical activities with multiple predecessors.

        Returns:
            List of bottleneck activity info
        """
        bottlenecks = []

        for act_id, activity in self.activities.items():
            if activity.critical and len(activity.predecessors) > 1:
                critical_preds = [
                    pred_id for pred_id in activity.predecessors
                    if self.activities[pred_id].critical
                ]

                if len(critical_preds) > 1:
                    bottlenecks.append({
                        'id': act_id,
                        'name': activity.name,
                        'critical_predecessors': critical_preds,
                        'risk': 'high'
                    })

        return bottlenecks

    def _optimization_opportunities(self) -> List[Dict]:
        """
        Identify optimization opportunities (activities with slack).

        Returns:
            List of optimization recommendations
        """
        opportunities = []

        for act_id, activity in self.activities.items():
            if not activity.critical and activity.slack > 0:
                opportunities.append({
                    'activity': act_id,
                    'name': activity.name,
                    'slack': round(activity.slack, 2),
                    'slack_unit': self.unit,
                    'recommendation': f"Can delay up to {activity.slack:.1f} {self.unit} without impacting project"
                })

        # Sort by slack (descending)
        opportunities.sort(key=lambda x: x['slack'], reverse=True)

        return opportunities

    def analyze(self) -> Dict:
        """
        Perform complete CPM analysis.

        Returns:
            Dict containing:
            - project_duration: Total project duration
            - activities: List of activities with ES/EF/LS/LF/slack
            - critical_path: List of critical activity IDs
            - bottlenecks: Critical activities with high risk
            - optimization_opportunities: Non-critical activities with slack

        Example:
            >>> result = analyzer.analyze()
            >>> print(f"Duration: {result['project_duration']} {result['unit']}")
            >>> print(f"Critical path: {result['critical_path']}")
        """
        try:
            # Step 1: Forward pass
            project_duration = self._forward_pass()

            # Step 2: Backward pass
            self._backward_pass(project_duration)

            # Step 3: Calculate slack
            self._calculate_slack()

            # Step 4: Identify critical path
            critical_path = self._identify_critical_path()

            # Step 5: Find bottlenecks
            bottlenecks = self._identify_bottlenecks()

            # Step 6: Optimization opportunities
            opportunities = self._optimization_opportunities()

            # Build result
            result = {
                'project_duration': round(project_duration, 2),
                'unit': self.unit,
                'activities': [
                    {
                        'id': act.id,
                        'name': act.name,
                        'duration': act.duration,
                        'predecessors': act.predecessors,  # Include for diagram generation
                        'ES': round(act.ES, 2),
                        'EF': round(act.EF, 2),
                        'LS': round(act.LS, 2),
                        'LF': round(act.LF, 2),
                        'slack': round(act.slack, 2),
                        'critical': act.critical
                    }
                    for act in self.activities.values()
                ],
                'critical_path': critical_path,
                'critical_path_duration': round(project_duration, 2),
                'bottlenecks': bottlenecks,
                'optimization_opportunities': opportunities[:10],  # Top 10
                'statistics': {
                    'total_activities': len(self.activities),
                    'critical_activities': len(critical_path),
                    'non_critical_activities': len(self.activities) - len(critical_path),
                    'average_slack': round(
                        sum(act.slack for act in self.activities.values() if not act.critical)
                        / max(1, len(self.activities) - len(critical_path)),
                        2
                    )
                }
            }

            logger.info(f"CPM analysis complete: {len(critical_path)}/{len(self.activities)} activities critical")
            return result

        except Exception as e:
            logger.error(f"CPM analysis failed: {e}")
            raise CalculationError(f"Analysis failed: {e}")


def analyze_critical_path(activities: List[Dict], unit: str = "days") -> Dict:
    """
    Convenience function to perform CPM analysis.

    Args:
        activities: List of activity dictionaries with id, name, duration, predecessors
        unit: Time unit for durations (days, weeks, sprints)

    Returns:
        Dict with complete CPM analysis results

    Raises:
        ValidationError: If input data is invalid
        CalculationError: If analysis fails

    Example:
        >>> activities = [
        ...     {"id": "A", "name": "Epic: Auth", "duration": 3, "predecessors": []},
        ...     {"id": "B", "name": "Epic: Dashboard", "duration": 2, "predecessors": ["A"]},
        ...     {"id": "C", "name": "Epic: Reports", "duration": 4, "predecessors": ["A"]},
        ...     {"id": "D", "name": "Epic: Integration", "duration": 1, "predecessors": ["B", "C"]}
        ... ]
        >>> result = analyze_critical_path(activities, unit="sprints")
        >>> print(json.dumps(result, indent=2))
    """
    analyzer = CriticalPathAnalyzer(activities, unit)
    return analyzer.analyze()


# Example usage and testing
if __name__ == "__main__":
    print("=" * 60)
    print("Critical Path Method (CPM) Analysis")
    print("=" * 60)

    # Example 1: Simple project with 4 epics
    print("\n📊 Example 1: Agile Project with 4 Epics")
    print("-" * 60)

    activities = [
        {
            "id": "A",
            "name": "Epic: Authentication System",
            "duration": 3,
            "predecessors": []
        },
        {
            "id": "B",
            "name": "Epic: User Dashboard",
            "duration": 2,
            "predecessors": ["A"]
        },
        {
            "id": "C",
            "name": "Epic: Reports Module",
            "duration": 4,
            "predecessors": ["A"]
        },
        {
            "id": "D",
            "name": "Epic: External Integration",
            "duration": 1,
            "predecessors": ["B", "C"]
        }
    ]

    try:
        result = analyze_critical_path(activities, unit="sprints")

        print(f"\n✅ Project Duration: {result['project_duration']} {result['unit']}")
        print(f"🔴 Critical Path: {' → '.join(result['critical_path'])}")
        print(f"📈 Critical Activities: {result['statistics']['critical_activities']}/{result['statistics']['total_activities']}")

        print("\n📋 Activity Details:")
        print(f"{'ID':<5} {'Name':<30} {'Dur':<5} {'ES':<5} {'EF':<5} {'LS':<5} {'LF':<5} {'Slack':<6} {'Crit?':<6}")
        print("-" * 80)
        for act in result['activities']:
            print(f"{act['id']:<5} {act['name']:<30} {act['duration']:<5.0f} "
                  f"{act['ES']:<5.0f} {act['EF']:<5.0f} {act['LS']:<5.0f} {act['LF']:<5.0f} "
                  f"{act['slack']:<6.1f} {'✓' if act['critical'] else '':<6}")

        if result['bottlenecks']:
            print("\n⚠️  Bottlenecks (High Risk):")
            for bn in result['bottlenecks']:
                print(f"   - {bn['name']} (ID: {bn['id']})")
                print(f"     Depends on: {', '.join(bn['critical_predecessors'])}")

        if result['optimization_opportunities']:
            print("\n💡 Optimization Opportunities (Top 3):")
            for opp in result['optimization_opportunities'][:3]:
                print(f"   - {opp['name']}: {opp['recommendation']}")

        # Example 2: Complex project
        print("\n\n📊 Example 2: Larger Project with Parallelization")
        print("-" * 60)

        complex_activities = [
            {"id": "INIT", "name": "Project Kickoff", "duration": 0.5, "predecessors": []},
            {"id": "REQ", "name": "Requirements Analysis", "duration": 2, "predecessors": ["INIT"]},
            {"id": "ARCH", "name": "Architecture Design", "duration": 3, "predecessors": ["REQ"]},
            {"id": "UI", "name": "UI/UX Design", "duration": 2, "predecessors": ["REQ"]},
            {"id": "BE-DEV", "name": "Backend Development", "duration": 5, "predecessors": ["ARCH"]},
            {"id": "FE-DEV", "name": "Frontend Development", "duration": 4, "predecessors": ["UI", "ARCH"]},
            {"id": "DB", "name": "Database Setup", "duration": 1, "predecessors": ["ARCH"]},
            {"id": "INT", "name": "Integration", "duration": 2, "predecessors": ["BE-DEV", "FE-DEV", "DB"]},
            {"id": "TEST", "name": "Testing", "duration": 3, "predecessors": ["INT"]},
            {"id": "DEPLOY", "name": "Deployment", "duration": 1, "predecessors": ["TEST"]}
        ]

        result2 = analyze_critical_path(complex_activities, unit="weeks")

        print(f"\n✅ Project Duration: {result2['project_duration']} {result2['unit']}")
        print(f"🔴 Critical Path: {' → '.join(result2['critical_path'])}")
        print(f"📊 Avg Slack (non-critical): {result2['statistics']['average_slack']} {result2['unit']}")

        print("\n💾 Full JSON Output:")
        print(json.dumps(result2, indent=2))

    except (ValidationError, CalculationError) as e:
        print(f"\n❌ Error: {e}")

    print("\n" + "=" * 60)
    print("Analysis Complete!")
    print("=" * 60)
