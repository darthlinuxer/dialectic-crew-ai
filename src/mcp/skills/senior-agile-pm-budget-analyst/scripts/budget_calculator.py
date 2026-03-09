"""
Module: budget_calculator.py
Purpose: Calculate detailed project budgets from Agile story points
Author: AI PM Assistant - senior-agile-pm-budget-analyst
Date: 2026-02-05

Calculates comprehensive project budgets using story point estimations,
team composition, and standard cost accounting practices. Includes
overhead, fixed costs, contingency reserves, and scenario analysis.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when input validation fails."""
    pass


class CalculationError(Exception):
    """Raised when calculations produce invalid results."""
    pass


@dataclass
class TeamMember:
    """Represents a team role with associated costs."""
    role: str
    count: int
    hourly_rate: float
    dedication_percent: float = 100.0  # % of time dedicated to project

    def __post_init__(self):
        """Validate team member data."""
        if self.count < 0:
            raise ValidationError(f"Count cannot be negative for role {self.role}")
        if self.hourly_rate < 0:
            raise ValidationError(f"Hourly rate cannot be negative for role {self.role}")
        if not (0 < self.dedication_percent <= 100):
            raise ValidationError(f"Dedication must be between 0 and 100% for role {self.role}")

    @property
    def effective_hourly_rate(self) -> float:
        """Calculate effective hourly rate considering dedication."""
        return self.hourly_rate * (self.dedication_percent / 100.0)


@dataclass
class BudgetConfig:
    """Configuration for budget calculations."""
    total_story_points: int
    points_per_sprint: int
    sprint_duration_weeks: int
    hours_per_sprint: int
    overhead_percentage: float = 0.20  # 20% default
    contingency_percentage: float = 0.15  # 15% default
    currency: str = "BRL"

    def __post_init__(self):
        """Validate configuration and normalize percentage inputs."""
        if self.total_story_points <= 0:
            raise ValidationError(f"total_story_points must be positive, got {self.total_story_points}")
        if self.points_per_sprint <= 0:
            raise ValidationError(f"points_per_sprint must be positive, got {self.points_per_sprint}")
        if self.sprint_duration_weeks <= 0:
            raise ValidationError(f"sprint_duration_weeks must be positive, got {self.sprint_duration_weeks}")
        if self.hours_per_sprint <= 0:
            raise ValidationError(f"hours_per_sprint must be positive, got {self.hours_per_sprint}")
        if self.overhead_percentage < 0:
            raise ValidationError(f"overhead_percentage cannot be negative, got {self.overhead_percentage}")
        if self.contingency_percentage < 0:
            raise ValidationError(f"contingency_percentage cannot be negative, got {self.contingency_percentage}")

        # Normalize percentages: accept both 0-100 (e.g., 20) and 0.0-1.0 (e.g., 0.20)
        if self.overhead_percentage > 1.0:
            self.overhead_percentage = self.overhead_percentage / 100.0
        if self.contingency_percentage > 1.0:
            self.contingency_percentage = self.contingency_percentage / 100.0

    @property
    def hours_per_point(self) -> float:
        """Calculate hours required per story point."""
        return self.hours_per_sprint / self.points_per_sprint

    @property
    def total_sprints(self) -> int:
        """Calculate total number of sprints needed."""
        import math
        return math.ceil(self.total_story_points / self.points_per_sprint)

    @property
    def total_hours(self) -> float:
        """Calculate total project hours."""
        return self.total_story_points * self.hours_per_point


def _round_currency(amount: float) -> float:
    """Round currency amount to 2 decimal places."""
    return float(Decimal(str(amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


class BudgetCalculator:
    """
    Calculate comprehensive project budget from story points.

    Uses standard cost accounting practices:
    1. Base Cost: Direct labor costs (story points × hours/point × hourly rates)
    2. Overhead: Indirect costs (management, facilities, admin)
    3. Fixed Costs: Non-variable costs (licenses, infrastructure, tools)
    4. Contingency: Risk reserve for uncertainties

    Example:
        >>> config = BudgetConfig(
        ...     total_story_points=89,
        ...     points_per_sprint=5,
        ...     sprint_duration_weeks=2,
        ...     hours_per_sprint=80
        ... )
        >>> team = [
        ...     {"role": "Senior Dev", "count": 2, "hourly_rate": 150},
        ...     {"role": "Developer", "count": 3, "hourly_rate": 100}
        ... ]
        >>> calculator = BudgetCalculator(config, team)
        >>> result = calculator.calculate()
        >>> print(result['summary']['total_budget'])
    """

    def __init__(
        self,
        config: BudgetConfig,
        team: List[Dict],
        fixed_costs: Optional[List[Dict]] = None
    ):
        """
        Initialize budget calculator.

        Args:
            config: Budget configuration with story points and sprint params
            team: List of team member dicts with role, count, hourly_rate
            fixed_costs: Optional list of fixed cost dicts with item, value, description

        Raises:
            ValidationError: If inputs are invalid
        """
        self.config = config
        # Convert team to TeamMember objects if they aren't already
        self.team_members = []
        for member in team:
            if isinstance(member, TeamMember):
                # Already a TeamMember object
                self.team_members.append(member)
            else:
                # Assume it's a dict and convert
                self.team_members.append(
                    TeamMember(
                        role=member['role'],
                        count=member['count'],
                        hourly_rate=member['hourly_rate'],
                        dedication_percent=member.get('dedication_percent', 100.0)
                    )
                )

        if not self.team_members:
            raise ValidationError("Team must have at least one member")

        # Handle fixed_costs - can be int/float or list of dicts
        if isinstance(fixed_costs, (int, float)):
            # Simple total value - convert to list format
            self.fixed_costs = [{"item": "Fixed Costs", "value": fixed_costs, "description": "Total fixed costs"}] if fixed_costs else []
        elif fixed_costs is None:
            self.fixed_costs = []
        else:
            # Assume it's a list of dicts
            self.fixed_costs = fixed_costs

        logger.info(f"Budget calculator initialized: {self.config.total_story_points} points, "
                   f"{len(self.team_members)} roles, {self.config.total_sprints} sprints")

    def _calculate_weighted_average_rate(self) -> float:
        """
        Calculate team's weighted average hourly rate.

        Weighted by number of team members in each role.

        Returns:
            Weighted average hourly rate
        """
        total_cost = sum(
            member.count * member.effective_hourly_rate
            for member in self.team_members
        )
        total_count = sum(member.count for member in self.team_members)

        if total_count == 0:
            raise CalculationError("Total team count is zero")

        return total_cost / total_count

    def _calculate_base_cost(self) -> Dict:
        """
        Calculate base cost (direct labor).

        Formula: Total Hours × Weighted Average Hourly Rate

        Returns:
            Dict with base cost breakdown by role
        """
        total_hours = self.config.total_hours
        weighted_avg_rate = self._calculate_weighted_average_rate()
        base_cost = total_hours * weighted_avg_rate

        # Cost breakdown by role
        by_role = {}
        for member in self.team_members:
            role_hours = total_hours * (
                member.count / sum(m.count for m in self.team_members)
            )
            role_cost = role_hours * member.effective_hourly_rate
            by_role[member.role] = {
                'count': member.count,
                'hourly_rate': member.hourly_rate,
                'dedication_percent': member.dedication_percent,
                'hours': _round_currency(role_hours),
                'cost': _round_currency(role_cost)
            }

        return {
            'total': _round_currency(base_cost),
            'hours': _round_currency(total_hours),
            'weighted_avg_rate': _round_currency(weighted_avg_rate),
            'by_role': by_role
        }

    def _calculate_overhead(self, base_cost: float) -> float:
        """
        Calculate overhead costs.

        Overhead includes management, facilities, admin, utilities, etc.
        Applied as percentage of base cost.

        Args:
            base_cost: Direct labor cost

        Returns:
            Overhead amount
        """
        return _round_currency(base_cost * self.config.overhead_percentage)

    def _calculate_fixed_costs_total(self) -> Dict:
        """
        Sum all fixed costs.

        Returns:
            Dict with total and breakdown
        """
        total = sum(item.get('value', 0) for item in self.fixed_costs)

        return {
            'total': _round_currency(total),
            'items': [
                {
                    'item': item['item'],
                    'value': _round_currency(item['value']),
                    'description': item.get('description', ''),
                    'frequency': item.get('frequency', 'one-time')
                }
                for item in self.fixed_costs
            ]
        }

    def _calculate_contingency(self, subtotal: float) -> float:
        """
        Calculate contingency reserve (risk reserve).

        Applied to subtotal (base + overhead + fixed costs) to account
        for uncertainties and risks.

        Args:
            subtotal: Base + Overhead + Fixed costs

        Returns:
            Contingency amount
        """
        return _round_currency(subtotal * self.config.contingency_percentage)

    def _calculate_by_sprint(self, total_budget: float) -> List[Dict]:
        """
        Break down budget by sprint.

        Assumes even distribution across sprints.

        Args:
            total_budget: Total project budget

        Returns:
            List of sprint budget dicts
        """
        sprints = []
        budget_per_sprint = total_budget / self.config.total_sprints
        points_per_sprint = self.config.points_per_sprint

        for sprint_num in range(1, self.config.total_sprints + 1):
            # Last sprint might have fewer points
            if sprint_num == self.config.total_sprints:
                remaining_points = (
                    self.config.total_story_points
                    - (points_per_sprint * (self.config.total_sprints - 1))
                )
                sprint_points = remaining_points
            else:
                sprint_points = points_per_sprint

            sprints.append({
                'sprint': sprint_num,
                'story_points': sprint_points,
                'budget': _round_currency(budget_per_sprint),
                'duration_weeks': self.config.sprint_duration_weeks
            })

        return sprints

    def _scenario_analysis(self, base_result: Dict) -> Dict:
        """
        Perform three-point estimation scenario analysis.

        Uses optimistic (-15%), realistic (baseline), pessimistic (+25%) scenarios.

        Args:
            base_result: Baseline budget calculation

        Returns:
            Dict with scenarios
        """
        baseline_points = self.config.total_story_points
        baseline_cost = base_result['summary']['total_budget']

        scenarios = {}

        # Optimistic: -15% story points (team more efficient than expected)
        opt_points = int(baseline_points * 0.85)
        opt_cost = baseline_cost * 0.85
        scenarios['optimistic'] = {
            'story_points': opt_points,
            'variance_percent': -15,
            'total_budget': _round_currency(opt_cost),
            'description': 'Team performs better than expected, fewer complexities'
        }

        # Realistic: baseline
        scenarios['realistic'] = {
            'story_points': baseline_points,
            'variance_percent': 0,
            'total_budget': baseline_cost,
            'description': 'Current estimates hold true'
        }

        # Pessimistic: +25% story points (unexpected complexities)
        pess_points = int(baseline_points * 1.25)
        pess_cost = baseline_cost * 1.25
        scenarios['pessimistic'] = {
            'story_points': pess_points,
            'variance_percent': 25,
            'total_budget': _round_currency(pess_cost),
            'description': 'Technical challenges, scope creep, learning curve'
        }

        return scenarios

    def calculate(self) -> Dict:
        """
        Calculate comprehensive project budget.

        Returns:
            Dict containing:
            - summary: Total budget and high-level breakdown
            - breakdown: Detailed cost breakdown by category
            - metrics: Per-point, per-sprint metrics
            - by_sprint: Budget distribution across sprints
            - scenarios: Optimistic/realistic/pessimistic projections

        Example:
            >>> result = calculator.calculate()
            >>> print(json.dumps(result['summary'], indent=2))
        """
        try:
            # Step 1: Calculate base cost (direct labor)
            base_cost_data = self._calculate_base_cost()
            base_cost = base_cost_data['total']

            # Step 2: Calculate overhead
            overhead_cost = self._calculate_overhead(base_cost)

            # Step 3: Sum fixed costs
            fixed_costs_data = self._calculate_fixed_costs_total()
            fixed_costs_total = fixed_costs_data['total']

            # Step 4: Calculate subtotal
            subtotal = base_cost + overhead_cost + fixed_costs_total

            # Step 5: Calculate contingency
            contingency_cost = self._calculate_contingency(subtotal)

            # Step 6: Total budget
            total_budget = subtotal + contingency_cost

            # Build result
            result = {
                'summary': {
                    'total_budget': _round_currency(total_budget),
                    'base_cost': _round_currency(base_cost),
                    'overhead_cost': _round_currency(overhead_cost),
                    'overhead_percentage': self.config.overhead_percentage * 100,
                    'fixed_costs': _round_currency(fixed_costs_total),
                    'contingency': _round_currency(contingency_cost),
                    'contingency_percentage': self.config.contingency_percentage * 100,
                    'currency': self.config.currency
                },
                'breakdown': {
                    'base_cost': base_cost_data,
                    'overhead': {
                        'total': _round_currency(overhead_cost),
                        'percentage': self.config.overhead_percentage * 100,
                        'description': 'Management, facilities, admin, utilities'
                    },
                    'fixed_costs': fixed_costs_data,
                    'contingency': {
                        'total': _round_currency(contingency_cost),
                        'percentage': self.config.contingency_percentage * 100,
                        'description': 'Risk reserve for uncertainties'
                    }
                },
                'metrics': {
                    'cost_per_point': _round_currency(total_budget / self.config.total_story_points),
                    'cost_per_sprint': _round_currency(total_budget / self.config.total_sprints),
                    'cost_per_hour': _round_currency(total_budget / self.config.total_hours),
                    'total_story_points': self.config.total_story_points,
                    'total_sprints': self.config.total_sprints,
                    'total_hours': _round_currency(self.config.total_hours),
                    'hours_per_point': _round_currency(self.config.hours_per_point)
                },
                'timeline': {
                    'total_sprints': self.config.total_sprints,
                    'sprint_duration_weeks': self.config.sprint_duration_weeks,
                    'total_weeks': self.config.total_sprints * self.config.sprint_duration_weeks,
                    'total_months': round(
                        (self.config.total_sprints * self.config.sprint_duration_weeks) / 4.33,
                        1
                    )
                }
            }

            # Add sprint breakdown
            result['by_sprint'] = self._calculate_by_sprint(total_budget)

            # Add scenario analysis
            result['scenarios'] = self._scenario_analysis(result)

            logger.info(f"Budget calculation complete: {self.config.currency} {total_budget:,.2f}")
            return result

        except Exception as e:
            logger.error(f"Budget calculation failed: {e}")
            raise CalculationError(f"Calculation failed: {e}")


def calculate_budget(
    total_story_points: int,
    points_per_sprint: int,
    sprint_duration_weeks: int,
    hours_per_sprint: int,
    team: List[Dict],
    fixed_costs: Optional[List[Dict]] = None,
    overhead_percentage: float = 0.20,
    contingency_percentage: float = 0.15,
    currency: str = "BRL"
) -> Dict:
    """
    Convenience function to calculate project budget.

    Args:
        total_story_points: Total story points for the project
        points_per_sprint: Story points capacity per sprint
        sprint_duration_weeks: Duration of each sprint in weeks
        hours_per_sprint: Available hours per sprint
        team: List of team member dicts
        fixed_costs: Optional list of fixed cost items
        overhead_percentage: Overhead as decimal (0.20 = 20%)
        contingency_percentage: Contingency as decimal (0.15 = 15%)
        currency: Currency code (BRL, USD, EUR, etc.)

    Returns:
        Dict with complete budget analysis

    Example:
        >>> result = calculate_budget(
        ...     total_story_points=89,
        ...     points_per_sprint=5,
        ...     sprint_duration_weeks=2,
        ...     hours_per_sprint=80,
        ...     team=[
        ...         {"role": "Senior Dev", "count": 2, "hourly_rate": 150},
        ...         {"role": "Developer", "count": 3, "hourly_rate": 100},
        ...         {"role": "QA", "count": 1, "hourly_rate": 80}
        ...     ],
        ...     fixed_costs=[
        ...         {"item": "AWS Infrastructure", "value": 15000, "frequency": "total"},
        ...         {"item": "Jira/Confluence Licenses", "value": 5000, "frequency": "total"},
        ...         {"item": "Design Tools", "value": 5000, "frequency": "total"}
        ...     ]
        ... )
        >>> print(f"Total Budget: {result['summary']['currency']} {result['summary']['total_budget']:,.2f}")
    """
    config = BudgetConfig(
        total_story_points=total_story_points,
        points_per_sprint=points_per_sprint,
        sprint_duration_weeks=sprint_duration_weeks,
        hours_per_sprint=hours_per_sprint,
        overhead_percentage=overhead_percentage,
        contingency_percentage=contingency_percentage,
        currency=currency
    )

    calculator = BudgetCalculator(config, team, fixed_costs)
    return calculator.calculate()


# Example usage and testing
if __name__ == "__main__":
    print("=" * 80)
    print("Agile Project Budget Calculator")
    print("=" * 80)

    # Example 1: E-commerce project
    print("\n💰 Example 1: E-commerce Platform Project")
    print("-" * 80)

    result = calculate_budget(
        total_story_points=89,
        points_per_sprint=5,
        sprint_duration_weeks=2,
        hours_per_sprint=80,
        team=[
            {"role": "Tech Lead", "count": 1, "hourly_rate": 180},
            {"role": "Senior Developer", "count": 2, "hourly_rate": 150},
            {"role": "Developer", "count": 3, "hourly_rate": 100},
            {"role": "QA Engineer", "count": 1, "hourly_rate": 80},
            {"role": "UX Designer", "count": 1, "hourly_rate": 90, "dedication_percent": 50}
        ],
        fixed_costs=[
            {"item": "AWS Infrastructure", "value": 15000, "description": "Servers, storage, CDN", "frequency": "project total"},
            {"item": "Software Licenses", "value": 8000, "description": "Jira, Confluence, monitoring tools", "frequency": "project total"},
            {"item": "Design Tools", "value": 2000, "description": "Figma, Adobe CC", "frequency": "project total"}
        ],
        overhead_percentage=0.20,
        contingency_percentage=0.15,
        currency="BRL"
    )

    # Print summary
    summary = result['summary']
    print(f"\n📊 Budget Summary:")
    print(f"   Total Budget: {summary['currency']} {summary['total_budget']:,.2f}")
    print(f"   Base Cost: {summary['currency']} {summary['base_cost']:,.2f}")
    print(f"   Overhead ({summary['overhead_percentage']:.0f}%): {summary['currency']} {summary['overhead_cost']:,.2f}")
    print(f"   Fixed Costs: {summary['currency']} {summary['fixed_costs']:,.2f}")
    print(f"   Contingency ({summary['contingency_percentage']:.0f}%): {summary['currency']} {summary['contingency']:,.2f}")

    # Print metrics
    metrics = result['metrics']
    print(f"\n📈 Key Metrics:")
    print(f"   Cost per Story Point: {summary['currency']} {metrics['cost_per_point']:,.2f}")
    print(f"   Cost per Sprint: {summary['currency']} {metrics['cost_per_sprint']:,.2f}")
    print(f"   Total Story Points: {metrics['total_story_points']}")
    print(f"   Total Sprints: {metrics['total_sprints']}")
    print(f"   Total Hours: {metrics['total_hours']:,.0f}")

    # Print timeline
    timeline = result['timeline']
    print(f"\n📅 Timeline:")
    print(f"   Duration: {timeline['total_sprints']} sprints = {timeline['total_weeks']} weeks = {timeline['total_months']} months")

    # Print team breakdown
    print(f"\n👥 Team Cost Breakdown:")
    for role, data in result['breakdown']['base_cost']['by_role'].items():
        print(f"   {role} (x{data['count']}): {summary['currency']} {data['cost']:,.2f} "
              f"[{data['hours']:,.0f}h @ {summary['currency']} {data['hourly_rate']}/h]")

    # Print scenarios
    print(f"\n🎯 Scenario Analysis:")
    for scenario_name, scenario in result['scenarios'].items():
        variance = f"+{scenario['variance_percent']}" if scenario['variance_percent'] > 0 else f"{scenario['variance_percent']}"
        print(f"   {scenario_name.capitalize()} ({variance}%): {summary['currency']} {scenario['total_budget']:,.2f}")
        print(f"      {scenario['description']}")

    # Print first 3 sprints
    print(f"\n🏃 Sprint Budget Allocation (first 3 sprints):")
    for sprint_data in result['by_sprint'][:3]:
        print(f"   Sprint {sprint_data['sprint']}: {sprint_data['story_points']} points → {summary['currency']} {sprint_data['budget']:,.2f}")

    # Full JSON output
    print("\n💾 Full JSON Output (truncated):")
    print(json.dumps({
        'summary': result['summary'],
        'metrics': result['metrics'],
        'timeline': result['timeline']
    }, indent=2))

    print("\n" + "=" * 80)
    print("✅ Budget calculation complete!")
    print("=" * 80)
