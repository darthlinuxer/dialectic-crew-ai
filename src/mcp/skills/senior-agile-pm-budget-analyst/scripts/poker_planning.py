#!/usr/bin/env python3
"""
Poker Planning Calculator

Implements Agile/Scrum Poker Planning estimation logic:
- Validates Fibonacci sequence usage
- Recommends story breakdowns when threshold exceeded
- Calculates velocity and sprint estimates
- Provides statistical analysis of estimations

Author: Senior Agile PM Budget Analyst Skill
License: MIT
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from enum import Enum
import logging
from statistics import mean, median, stdev

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when validation fails"""
    pass


class CalculationError(Exception):
    """Raised when calculation fails"""
    pass


class EstimationScale(Enum):
    """Supported estimation scales"""
    FIBONACCI = "fibonacci"
    MODIFIED_FIBONACCI = "modified_fibonacci"
    T_SHIRT = "t_shirt"
    POWERS_OF_2 = "powers_of_2"


# Predefined estimation scales
ESTIMATION_SCALES = {
    EstimationScale.FIBONACCI: [1, 2, 3, 5, 8, 13, 21, 34, 55, 89],
    EstimationScale.MODIFIED_FIBONACCI: [0, 0.5, 1, 2, 3, 5, 8, 13, 20, 40, 100],
    EstimationScale.T_SHIRT: ["XS", "S", "M", "L", "XL", "XXL"],
    EstimationScale.POWERS_OF_2: [1, 2, 4, 8, 16, 32, 64]
}

# T-shirt to numeric mapping
T_SHIRT_TO_NUMERIC = {
    "XS": 1,
    "S": 2,
    "M": 3,
    "L": 5,
    "XL": 8,
    "XXL": 13
}


@dataclass
class Story:
    """Represents a User Story"""
    id: str
    title: str
    estimated_points: Optional[float] = None
    actual_points: Optional[float] = None  # After completion
    epic_id: Optional[str] = None
    sprint: Optional[int] = None
    completed: bool = False


@dataclass
class PlanningSession:
    """Represents a Poker Planning session"""
    session_id: str
    story_id: str
    story_title: str
    estimates: List[float] = field(default_factory=list)
    final_estimate: Optional[float] = None
    consensus_reached: bool = False
    rounds: int = 1

    def add_estimate(self, points: float) -> None:
        """Add an estimation vote"""
        self.estimates.append(points)

    def calculate_statistics(self) -> Dict:
        """Calculate statistical measures of estimates"""
        if not self.estimates:
            return {}

        return {
            "mean": mean(self.estimates),
            "median": median(self.estimates),
            "min": min(self.estimates),
            "max": max(self.estimates),
            "range": max(self.estimates) - min(self.estimates),
            "std_dev": stdev(self.estimates) if len(self.estimates) > 1 else 0.0,
            "variance_coefficient": (stdev(self.estimates) / mean(self.estimates) * 100)
                                   if len(self.estimates) > 1 and mean(self.estimates) > 0 else 0.0
        }


@dataclass
class PokerConfig:
    """Configuration for Poker Planning"""
    scale: EstimationScale = EstimationScale.FIBONACCI
    breakdown_threshold: float = 13  # Stories above this should be broken down
    points_per_sprint: float = 20  # Team velocity
    sprint_duration_weeks: int = 2
    ideal_story_size_min: float = 2  # Minimum recommended story size
    ideal_story_size_max: float = 8  # Maximum recommended story size
    consensus_variance_threshold: float = 30.0  # % - if variance coef > this, re-estimate

    def validate(self) -> None:
        """Validate configuration"""
        if self.breakdown_threshold <= 0:
            raise ValidationError(f"breakdown_threshold must be positive, got {self.breakdown_threshold}")

        if self.points_per_sprint <= 0:
            raise ValidationError(f"points_per_sprint must be positive, got {self.points_per_sprint}")

        if self.sprint_duration_weeks <= 0:
            raise ValidationError(f"sprint_duration_weeks must be positive, got {self.sprint_duration_weeks}")

        if self.ideal_story_size_min >= self.ideal_story_size_max:
            raise ValidationError(f"ideal_story_size_min ({self.ideal_story_size_min}) must be less than ideal_story_size_max ({self.ideal_story_size_max})")


class PokerPlanningCalculator:
    """
    Poker Planning Calculator

    Provides estimation validation, breakdown recommendations,
    velocity calculation, and sprint planning support.

    Example:
        config = PokerConfig(
            scale=EstimationScale.FIBONACCI,
            breakdown_threshold=13,
            points_per_sprint=20
        )

        calculator = PokerPlanningCalculator(config)

        # Validate estimation
        is_valid, msg = calculator.validate_estimate(8)

        # Analyze planning session
        session = PlanningSession("S1", "US-001", "Login Feature")
        session.estimates = [5, 8, 5, 8, 5]
        analysis = calculator.analyze_session(session)
    """

    def __init__(self, config: PokerConfig):
        """
        Initialize calculator with configuration

        Args:
            config: PokerConfig instance

        Raises:
            ValidationError: If configuration is invalid
        """
        config.validate()
        self.config = config
        self.stories: List[Story] = []
        self.sessions: List[PlanningSession] = []
        self.scale_values = ESTIMATION_SCALES[config.scale]

        logger.info(f"PokerPlanningCalculator initialized with {config.scale.value} scale")

    def validate_estimate(self, points: float) -> Tuple[bool, str]:
        """
        Validate if estimation follows the configured scale

        Args:
            points: Story points to validate

        Returns:
            Tuple of (is_valid, message)
        """
        if self.config.scale == EstimationScale.T_SHIRT:
            # Cannot validate numeric values for T-shirt scale
            return True, "T-shirt scale validation requires string values"

        if points in self.scale_values:
            return True, f"{points} is valid in {self.config.scale.value} scale"

        # Find closest valid values
        valid_nums = [v for v in self.scale_values if isinstance(v, (int, float))]
        closest = min(valid_nums, key=lambda x: abs(x - points))

        return False, f"{points} is not in {self.config.scale.value} scale. Closest valid value: {closest}"

    def recommend_breakdown(self, points: float) -> Dict:
        """
        Recommend if story should be broken down

        Args:
            points: Story points estimated

        Returns:
            Dictionary with recommendation details
        """
        should_break = points > self.config.breakdown_threshold

        recommendation = {
            "should_breakdown": should_break,
            "estimated_points": points,
            "threshold": self.config.breakdown_threshold,
            "reason": "",
            "suggested_breakdown": []
        }

        if should_break:
            recommendation["reason"] = (
                f"Story exceeds threshold of {self.config.breakdown_threshold} points. "
                f"Large stories have higher uncertainty and risk."
            )

            # Suggest breakdown into smaller stories
            num_stories = int(points / self.config.ideal_story_size_max) + 1
            avg_points = points / num_stories

            # Round to nearest valid scale value
            valid_nums = [v for v in self.scale_values if isinstance(v, (int, float))]
            suggested_size = min(valid_nums, key=lambda x: abs(x - avg_points))

            recommendation["suggested_breakdown"] = [
                f"Break into {num_stories} stories of approximately {suggested_size} points each",
                f"This brings each story within the ideal range of {self.config.ideal_story_size_min}-{self.config.ideal_story_size_max} points"
            ]
        else:
            recommendation["reason"] = "Story size is acceptable"

        return recommendation

    def analyze_session(self, session: PlanningSession) -> Dict:
        """
        Analyze a poker planning session

        Args:
            session: PlanningSession instance

        Returns:
            Dictionary with session analysis
        """
        if not session.estimates:
            return {
                "error": "No estimates provided in session"
            }

        stats = session.calculate_statistics()

        # Determine if consensus was reached
        variance_coef = stats.get("variance_coefficient", 0)
        consensus = variance_coef <= self.config.consensus_variance_threshold

        # Recommend final estimate (median is typically used in Scrum)
        recommended_estimate = stats["median"]

        # Find closest valid scale value
        valid_nums = [v for v in self.scale_values if isinstance(v, (int, float))]
        final_estimate = min(valid_nums, key=lambda x: abs(x - recommended_estimate))

        analysis = {
            "session_id": session.session_id,
            "story": {
                "id": session.story_id,
                "title": session.story_title
            },
            "statistics": stats,
            "consensus": {
                "reached": consensus,
                "variance_coefficient": variance_coef,
                "threshold": self.config.consensus_variance_threshold,
                "recommendation": "Consensus reached" if consensus else "Re-estimate recommended (high variance)"
            },
            "final_estimate": {
                "recommended": final_estimate,
                "basis": "median of estimates, rounded to nearest scale value"
            },
            "breakdown": self.recommend_breakdown(final_estimate)
        }

        return analysis

    def add_story(self, story: Story) -> None:
        """Add a story to the calculator"""
        self.stories.append(story)

    def calculate_velocity(self, completed_sprints: int = 3) -> Dict:
        """
        Calculate team velocity based on completed stories

        Args:
            completed_sprints: Number of recent sprints to consider (default: 3)

        Returns:
            Dictionary with velocity metrics
        """
        completed_stories = [s for s in self.stories if s.completed and s.actual_points is not None]

        if not completed_stories:
            return {
                "error": "No completed stories available for velocity calculation"
            }

        # Group by sprint
        sprint_points: Dict[int, List[float]] = {}
        for story in completed_stories:
            if story.sprint is not None:
                if story.sprint not in sprint_points:
                    sprint_points[story.sprint] = []
                sprint_points[story.sprint].append(story.actual_points)

        # Calculate points per sprint
        sprint_totals = {sprint: sum(points) for sprint, points in sprint_points.items()}

        # Consider only recent sprints
        recent_sprints = sorted(sprint_totals.keys())[-completed_sprints:]
        recent_velocities = [sprint_totals[s] for s in recent_sprints]

        if not recent_velocities:
            return {
                "error": "No sprint data available"
            }

        velocity_metrics = {
            "average_velocity": mean(recent_velocities),
            "median_velocity": median(recent_velocities),
            "min_velocity": min(recent_velocities),
            "max_velocity": max(recent_velocities),
            "std_dev": stdev(recent_velocities) if len(recent_velocities) > 1 else 0.0,
            "sprints_analyzed": len(recent_velocities),
            "sprint_details": {sprint: sprint_totals[sprint] for sprint in recent_sprints},
            "stability": "Stable" if (stdev(recent_velocities) if len(recent_velocities) > 1 else 0) < mean(recent_velocities) * 0.2 else "Unstable"
        }

        return velocity_metrics

    def estimate_completion(self, remaining_points: float, use_velocity: Optional[float] = None) -> Dict:
        """
        Estimate project completion timeline

        Args:
            remaining_points: Total story points remaining in backlog
            use_velocity: Override velocity (if None, calculate from completed stories)

        Returns:
            Dictionary with completion estimates
        """
        if use_velocity is None:
            velocity_data = self.calculate_velocity()
            if "error" in velocity_data:
                return velocity_data
            velocity = velocity_data["average_velocity"]
        else:
            velocity = use_velocity

        if velocity <= 0:
            raise CalculationError("Velocity must be positive")

        # Calculate different scenarios
        velocity_metrics = self.calculate_velocity() if use_velocity is None else None

        if velocity_metrics and "error" not in velocity_metrics:
            optimistic_velocity = velocity_metrics["max_velocity"]
            pessimistic_velocity = velocity_metrics["min_velocity"]
        else:
            # Use ±20% if no historical data
            optimistic_velocity = velocity * 1.2
            pessimistic_velocity = velocity * 0.8

        def calculate_scenario(points: float, vel: float) -> Dict:
            sprints = points / vel
            weeks = sprints * self.config.sprint_duration_weeks
            return {
                "sprints": round(sprints, 1),
                "weeks": round(weeks, 1),
                "months": round(weeks / 4.33, 1)
            }

        estimation = {
            "remaining_points": remaining_points,
            "velocity_used": velocity,
            "scenarios": {
                "optimistic": {
                    "velocity": optimistic_velocity,
                    "duration": calculate_scenario(remaining_points, optimistic_velocity),
                    "description": "Best case scenario with maximum historical velocity"
                },
                "realistic": {
                    "velocity": velocity,
                    "duration": calculate_scenario(remaining_points, velocity),
                    "description": "Most likely scenario with average velocity"
                },
                "pessimistic": {
                    "velocity": pessimistic_velocity,
                    "duration": calculate_scenario(remaining_points, pessimistic_velocity),
                    "description": "Worst case scenario with minimum historical velocity"
                }
            },
            "recommendation": f"Plan for {calculate_scenario(remaining_points, velocity)['sprints']} sprints "
                             f"({calculate_scenario(remaining_points, velocity)['weeks']} weeks) "
                             f"but communicate a range to stakeholders"
        }

        return estimation

    def analyze_backlog(self) -> Dict:
        """
        Analyze the entire backlog of stories

        Returns:
            Dictionary with backlog analysis
        """
        if not self.stories:
            return {
                "error": "No stories in backlog"
            }

        total_points = sum(s.estimated_points for s in self.stories if s.estimated_points is not None)
        completed_points = sum(s.actual_points for s in self.stories if s.completed and s.actual_points is not None)
        remaining_points = total_points - completed_points

        # Categorize stories by size
        size_distribution = {
            "small": [s for s in self.stories if s.estimated_points and s.estimated_points <= self.config.ideal_story_size_min],
            "ideal": [s for s in self.stories if s.estimated_points and self.config.ideal_story_size_min < s.estimated_points <= self.config.ideal_story_size_max],
            "large": [s for s in self.stories if s.estimated_points and self.config.ideal_story_size_max < s.estimated_points <= self.config.breakdown_threshold],
            "too_large": [s for s in self.stories if s.estimated_points and s.estimated_points > self.config.breakdown_threshold]
        }

        analysis = {
            "total_stories": len(self.stories),
            "total_points": total_points,
            "completed_points": completed_points,
            "remaining_points": remaining_points,
            "completion_percentage": (completed_points / total_points * 100) if total_points > 0 else 0,
            "size_distribution": {
                "small": {
                    "count": len(size_distribution["small"]),
                    "points": sum(s.estimated_points for s in size_distribution["small"]),
                    "percentage": len(size_distribution["small"]) / len(self.stories) * 100
                },
                "ideal": {
                    "count": len(size_distribution["ideal"]),
                    "points": sum(s.estimated_points for s in size_distribution["ideal"]),
                    "percentage": len(size_distribution["ideal"]) / len(self.stories) * 100
                },
                "large": {
                    "count": len(size_distribution["large"]),
                    "points": sum(s.estimated_points for s in size_distribution["large"]),
                    "percentage": len(size_distribution["large"]) / len(self.stories) * 100
                },
                "too_large": {
                    "count": len(size_distribution["too_large"]),
                    "points": sum(s.estimated_points for s in size_distribution["too_large"]),
                    "percentage": len(size_distribution["too_large"]) / len(self.stories) * 100,
                    "action_required": "These stories should be broken down",
                    "stories": [{"id": s.id, "title": s.title, "points": s.estimated_points}
                               for s in size_distribution["too_large"]]
                }
            },
            "health_check": {
                "ideal_distribution": len(size_distribution["ideal"]) / len(self.stories) * 100,
                "status": "Healthy" if len(size_distribution["too_large"]) == 0 else f"{len(size_distribution['too_large'])} stories need breakdown"
            }
        }

        return analysis

    def generate_sprint_plan(self, sprint_number: int, available_capacity: Optional[float] = None) -> Dict:
        """
        Generate a sprint plan by selecting stories from backlog

        Args:
            sprint_number: Sprint number to plan
            available_capacity: Override team capacity (if None, use config points_per_sprint)

        Returns:
            Dictionary with sprint plan
        """
        capacity = available_capacity if available_capacity is not None else self.config.points_per_sprint

        # Get unassigned stories sorted by priority (assuming order in list = priority)
        unassigned = [s for s in self.stories if not s.completed and not s.sprint]

        if not unassigned:
            return {
                "error": "No unassigned stories available for sprint planning"
            }

        # Simple greedy algorithm: select stories until capacity is reached
        selected_stories = []
        total_points = 0

        for story in unassigned:
            if story.estimated_points is None:
                continue

            if total_points + story.estimated_points <= capacity:
                selected_stories.append(story)
                total_points += story.estimated_points

            if total_points >= capacity * 0.9:  # Allow up to 90% capacity fill
                break

        sprint_plan = {
            "sprint_number": sprint_number,
            "capacity": capacity,
            "committed_points": total_points,
            "capacity_utilization": (total_points / capacity * 100) if capacity > 0 else 0,
            "stories": [
                {
                    "id": s.id,
                    "title": s.title,
                    "points": s.estimated_points,
                    "epic_id": s.epic_id
                }
                for s in selected_stories
            ],
            "recommendation": "Good capacity utilization" if 70 <= (total_points / capacity * 100) <= 90
                             else "Consider adjusting story selection"
        }

        return sprint_plan


def main():
    """Example usage of PokerPlanningCalculator"""

    print("=" * 80)
    print("POKER PLANNING CALCULATOR - Example Usage")
    print("=" * 80)

    # Example 1: Basic configuration and estimation validation
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Estimation Validation")
    print("=" * 80)

    config = PokerConfig(
        scale=EstimationScale.FIBONACCI,
        breakdown_threshold=13,
        points_per_sprint=20,
        sprint_duration_weeks=2
    )

    calculator = PokerPlanningCalculator(config)

    # Validate some estimates
    test_estimates = [5, 8, 13, 15, 21]
    for points in test_estimates:
        is_valid, message = calculator.validate_estimate(points)
        print(f"Points: {points:2} - Valid: {is_valid:5} - {message}")

    # Example 2: Planning Session Analysis
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Planning Session Analysis")
    print("=" * 80)

    session = PlanningSession(
        session_id="SESSION-001",
        story_id="US-001",
        story_title="User Login with OAuth"
    )

    # Simulate team estimates
    session.estimates = [5, 8, 5, 8, 5, 8]

    analysis = calculator.analyze_session(session)

    print(f"\nStory: {analysis['story']['id']} - {analysis['story']['title']}")
    print(f"\nEstimates: {session.estimates}")
    print(f"\nStatistics:")
    for key, value in analysis['statistics'].items():
        print(f"  {key:20}: {value:.2f}")

    print(f"\nConsensus:")
    print(f"  Reached: {analysis['consensus']['reached']}")
    print(f"  Variance Coefficient: {analysis['consensus']['variance_coefficient']:.2f}%")
    print(f"  Recommendation: {analysis['consensus']['recommendation']}")

    print(f"\nFinal Estimate: {analysis['final_estimate']['recommended']} points")
    print(f"  Basis: {analysis['final_estimate']['basis']}")

    # Example 3: Breakdown Recommendation
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Story Breakdown Recommendation")
    print("=" * 80)

    large_story = 21
    breakdown = calculator.recommend_breakdown(large_story)

    print(f"\nStory Points: {large_story}")
    print(f"Should Breakdown: {breakdown['should_breakdown']}")
    print(f"Reason: {breakdown['reason']}")
    if breakdown['suggested_breakdown']:
        print("\nSuggestions:")
        for suggestion in breakdown['suggested_breakdown']:
            print(f"  - {suggestion}")

    # Example 4: Velocity Calculation
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Velocity Calculation")
    print("=" * 80)

    # Add some completed stories
    completed_stories_data = [
        ("US-001", "Login", 5, 1),
        ("US-002", "Dashboard", 8, 1),
        ("US-003", "Profile", 5, 1),
        ("US-004", "Reports", 8, 2),
        ("US-005", "Export", 5, 2),
        ("US-006", "Settings", 3, 2),
        ("US-007", "Notifications", 5, 3),
        ("US-008", "Search", 8, 3),
        ("US-009", "Filters", 5, 3),
    ]

    for story_id, title, points, sprint in completed_stories_data:
        story = Story(
            id=story_id,
            title=title,
            estimated_points=points,
            actual_points=points,
            sprint=sprint,
            completed=True
        )
        calculator.add_story(story)

    velocity = calculator.calculate_velocity(completed_sprints=3)

    print(f"\nVelocity Metrics:")
    print(f"  Average Velocity: {velocity['average_velocity']:.1f} points/sprint")
    print(f"  Median Velocity: {velocity['median_velocity']:.1f} points/sprint")
    print(f"  Range: {velocity['min_velocity']:.1f} - {velocity['max_velocity']:.1f} points/sprint")
    print(f"  Standard Deviation: {velocity['std_dev']:.2f}")
    print(f"  Stability: {velocity['stability']}")

    print(f"\nSprint Details:")
    for sprint, points in velocity['sprint_details'].items():
        print(f"  Sprint {sprint}: {points} points")

    # Example 5: Completion Estimation
    print("\n" + "=" * 80)
    print("EXAMPLE 5: Project Completion Estimation")
    print("=" * 80)

    remaining_backlog = 89  # points
    estimation = calculator.estimate_completion(remaining_backlog)

    print(f"\nRemaining Points: {estimation['remaining_points']}")
    print(f"Velocity Used: {estimation['velocity_used']:.1f} points/sprint")

    print(f"\nScenarios:")
    for scenario_name, scenario_data in estimation['scenarios'].items():
        print(f"\n  {scenario_name.upper()}:")
        print(f"    Velocity: {scenario_data['velocity']:.1f} points/sprint")
        print(f"    Duration: {scenario_data['duration']['sprints']} sprints "
              f"({scenario_data['duration']['weeks']} weeks / "
              f"{scenario_data['duration']['months']} months)")
        print(f"    {scenario_data['description']}")

    print(f"\nRecommendation: {estimation['recommendation']}")

    # Example 6: Backlog Analysis
    print("\n" + "=" * 80)
    print("EXAMPLE 6: Backlog Analysis")
    print("=" * 80)

    # Add some unestimated stories
    new_stories = [
        ("US-010", "Integration API", 13, "EPIC-001"),
        ("US-011", "Error Handling", 3, "EPIC-001"),
        ("US-012", "Performance Optimization", 21, "EPIC-002"),
        ("US-013", "Unit Tests", 5, "EPIC-002"),
    ]

    for story_id, title, points, epic_id in new_stories:
        story = Story(
            id=story_id,
            title=title,
            estimated_points=points,
            epic_id=epic_id
        )
        calculator.add_story(story)

    backlog_analysis = calculator.analyze_backlog()

    print(f"\nBacklog Summary:")
    print(f"  Total Stories: {backlog_analysis['total_stories']}")
    print(f"  Total Points: {backlog_analysis['total_points']}")
    print(f"  Completed: {backlog_analysis['completed_points']} points "
          f"({backlog_analysis['completion_percentage']:.1f}%)")
    print(f"  Remaining: {backlog_analysis['remaining_points']} points")

    print(f"\nSize Distribution:")
    for size, data in backlog_analysis['size_distribution'].items():
        print(f"  {size.upper()}:")
        print(f"    Count: {data['count']} stories ({data['percentage']:.1f}%)")
        print(f"    Points: {data['points']}")
        if 'action_required' in data:
            print(f"    Action: {data['action_required']}")
            if data['stories']:
                print(f"    Stories needing breakdown:")
                for s in data['stories']:
                    print(f"      - {s['id']}: {s['title']} ({s['points']} points)")

    print(f"\nHealth Check:")
    print(f"  Ideal Distribution: {backlog_analysis['health_check']['ideal_distribution']:.1f}%")
    print(f"  Status: {backlog_analysis['health_check']['status']}")

    # Example 7: Sprint Planning
    print("\n" + "=" * 80)
    print("EXAMPLE 7: Sprint Planning")
    print("=" * 80)

    sprint_plan = calculator.generate_sprint_plan(sprint_number=4)

    print(f"\nSprint {sprint_plan['sprint_number']} Plan:")
    print(f"  Capacity: {sprint_plan['capacity']} points")
    print(f"  Committed: {sprint_plan['committed_points']} points")
    print(f"  Utilization: {sprint_plan['capacity_utilization']:.1f}%")

    print(f"\nSelected Stories:")
    for story in sprint_plan['stories']:
        print(f"  - {story['id']}: {story['title']} ({story['points']} points) [Epic: {story['epic_id']}]")

    print(f"\nRecommendation: {sprint_plan['recommendation']}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
