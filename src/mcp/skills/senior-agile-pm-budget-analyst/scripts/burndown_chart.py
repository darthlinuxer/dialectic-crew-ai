#!/usr/bin/env python3
"""
Burndown/Burnup Chart Calculator

Generates sprint and release burndown/burnup charts for Agile tracking:
- Sprint burndown (daily progress)
- Release burndown (sprint-level progress)
- Burnup charts with scope tracking
- Forecast and trend analysis
- Progress metrics and health indicators

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


class ChartType(Enum):
    """Chart type enumeration"""
    BURNDOWN = "burndown"
    BURNUP = "burnup"


class TimeUnit(Enum):
    """Time unit for chart"""
    DAYS = "days"
    SPRINTS = "sprints"


@dataclass
class DataPoint:
    """Represents a single data point in the chart"""
    date: datetime
    remaining_points: float
    completed_points: float
    total_scope: float
    ideal_remaining: Optional[float] = None

    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage"""
        if self.total_scope == 0:
            return 0.0
        return (self.completed_points / self.total_scope) * 100


@dataclass
class SprintData:
    """Sprint-specific data"""
    sprint_number: int
    start_date: datetime
    end_date: datetime
    committed_points: float
    completed_points: float
    added_points: float = 0.0  # Scope changes mid-sprint
    removed_points: float = 0.0

    @property
    def actual_completed(self) -> float:
        """Actual completion considering scope changes"""
        return self.completed_points

    @property
    def final_scope(self) -> float:
        """Final scope after changes"""
        return self.committed_points + self.added_points - self.removed_points

    @property
    def completion_rate(self) -> float:
        """Completion rate as percentage"""
        if self.final_scope == 0:
            return 0.0
        return (self.completed_points / self.final_scope) * 100


@dataclass
class BurndownConfig:
    """Configuration for burndown chart"""
    chart_type: ChartType = ChartType.BURNDOWN
    time_unit: TimeUnit = TimeUnit.DAYS
    sprint_duration_days: int = 14
    work_days_per_week: int = 5
    show_weekends: bool = False
    include_forecast: bool = True
    ascii_chart_height: int = 20
    ascii_chart_width: int = 80

    def validate(self) -> None:
        """Validate configuration"""
        if self.sprint_duration_days <= 0:
            raise ValidationError("sprint_duration_days must be positive")

        if not (1 <= self.work_days_per_week <= 7):
            raise ValidationError("work_days_per_week must be between 1 and 7")


class BurndownCalculator:
    """
    Burndown/Burnup Chart Calculator

    Tracks and analyzes sprint/release progress:
    - Daily tracking of remaining/completed work
    - Ideal burndown line calculation
    - Trend analysis and forecasting
    - Scope change tracking
    - Health indicators

    Example:
        config = BurndownConfig(
            chart_type=ChartType.BURNDOWN,
            sprint_duration_days=14
        )

        calculator = BurndownCalculator(
            config=config,
            start_date=datetime(2024, 3, 1),
            initial_scope=50
        )

        # Add daily progress
        calculator.add_data_point(
            date=datetime(2024, 3, 2),
            completed_points=5
        )

        # Generate chart
        chart_data = calculator.generate()
    """

    def __init__(
        self,
        config: BurndownConfig,
        start_date: datetime,
        initial_scope: float,
        end_date: Optional[datetime] = None
    ):
        """
        Initialize calculator

        Args:
            config: BurndownConfig instance
            start_date: Project/sprint start date
            initial_scope: Initial story points
            end_date: Project/sprint end date (calculated if not provided)

        Raises:
            ValidationError: If configuration is invalid
        """
        config.validate()
        self.config = config
        self.start_date = start_date
        self.initial_scope = initial_scope
        self.current_scope = initial_scope

        if end_date is None:
            self.end_date = start_date + timedelta(days=config.sprint_duration_days)
        else:
            self.end_date = end_date

        self.data_points: List[DataPoint] = []
        self.scope_changes: List[Tuple[datetime, float, str]] = []  # (date, change, reason)

        # Add initial data point
        initial_point = DataPoint(
            date=start_date,
            remaining_points=initial_scope,
            completed_points=0,
            total_scope=initial_scope,
            ideal_remaining=initial_scope
        )
        self.data_points.append(initial_point)

        logger.info(f"BurndownCalculator initialized: {initial_scope} points, "
                   f"{start_date.date()} to {self.end_date.date()}")

    def _is_work_day(self, date: datetime) -> bool:
        """Check if date is a working day"""
        if self.config.show_weekends:
            return True
        return date.weekday() < 5  # Monday = 0, Friday = 4

    def _calculate_work_days(self, start: datetime, end: datetime) -> int:
        """Calculate number of working days between dates"""
        days = 0
        current = start
        while current <= end:
            if self._is_work_day(current):
                days += 1
            current += timedelta(days=1)
        return days

    def add_data_point(
        self,
        date: datetime,
        completed_points: float,
        scope_change: float = 0.0,
        scope_change_reason: str = ""
    ) -> None:
        """
        Add a progress data point

        Args:
            date: Date of the data point
            completed_points: Cumulative completed story points
            scope_change: Points added (positive) or removed (negative)
            scope_change_reason: Reason for scope change
        """
        if date < self.start_date:
            raise ValidationError("Data point date cannot be before start date")

        # Update scope if changed
        if scope_change != 0:
            self.current_scope += scope_change
            self.scope_changes.append((date, scope_change, scope_change_reason))
            logger.info(f"Scope change on {date.date()}: {scope_change:+.1f} points - {scope_change_reason}")

        # Calculate remaining points
        remaining = self.current_scope - completed_points

        # Calculate ideal remaining
        total_work_days = self._calculate_work_days(self.start_date, self.end_date)
        elapsed_work_days = self._calculate_work_days(self.start_date, date)

        if total_work_days > 0:
            ideal_remaining = self.current_scope * (1 - elapsed_work_days / total_work_days)
        else:
            ideal_remaining = 0

        data_point = DataPoint(
            date=date,
            remaining_points=max(0, remaining),
            completed_points=completed_points,
            total_scope=self.current_scope,
            ideal_remaining=ideal_remaining
        )

        self.data_points.append(data_point)
        logger.debug(f"Added data point: {date.date()} - Completed: {completed_points}, "
                    f"Remaining: {remaining:.1f}")

    def get_latest_point(self) -> Optional[DataPoint]:
        """Get the most recent data point"""
        return self.data_points[-1] if self.data_points else None

    def calculate_velocity(self) -> float:
        """
        Calculate current velocity (points per day)

        Returns:
            Average velocity based on recent progress
        """
        if len(self.data_points) < 2:
            return 0.0

        # Use last few days for velocity calculation
        recent_points = self.data_points[-min(5, len(self.data_points)):]

        first_point = recent_points[0]
        last_point = recent_points[-1]

        days_elapsed = self._calculate_work_days(first_point.date, last_point.date)

        if days_elapsed == 0:
            return 0.0

        points_completed = last_point.completed_points - first_point.completed_points
        velocity = points_completed / days_elapsed

        return velocity

    def forecast_completion(self) -> Dict:
        """
        Forecast when work will be completed

        Returns:
            Dictionary with forecast details
        """
        latest = self.get_latest_point()
        if not latest:
            return {"error": "No data points available"}

        velocity = self.calculate_velocity()

        if velocity <= 0:
            return {
                "error": "Cannot forecast: velocity is zero or negative",
                "velocity": velocity
            }

        remaining = latest.remaining_points
        days_to_complete = remaining / velocity

        forecast_date = latest.date + timedelta(days=int(days_to_complete))

        # Calculate days ahead or behind schedule
        scheduled_end = self.end_date
        days_delta = (forecast_date - scheduled_end).days

        forecast = {
            "current_velocity": round(velocity, 2),
            "remaining_points": remaining,
            "forecast_completion_date": forecast_date.strftime("%Y-%m-%d"),
            "scheduled_end_date": scheduled_end.strftime("%Y-%m-%d"),
            "days_delta": days_delta,
            "status": "On Track" if abs(days_delta) <= 2 else
                     ("Ahead of Schedule" if days_delta < 0 else "Behind Schedule"),
            "confidence": "Low" if len(self.data_points) < 5 else "Medium" if len(self.data_points) < 10 else "High"
        }

        return forecast

    def calculate_trend(self) -> Dict:
        """
        Calculate trend analysis

        Returns:
            Dictionary with trend metrics
        """
        if len(self.data_points) < 3:
            return {"error": "Insufficient data for trend analysis (need at least 3 points)"}

        # Compare actual vs ideal progress
        actual_rates = []
        ideal_rates = []

        for i in range(1, len(self.data_points)):
            prev = self.data_points[i-1]
            curr = self.data_points[i]

            days = self._calculate_work_days(prev.date, curr.date)
            if days > 0:
                actual_rate = (prev.remaining_points - curr.remaining_points) / days
                ideal_rate = (prev.ideal_remaining - curr.ideal_remaining) / days if prev.ideal_remaining and curr.ideal_remaining else 0

                actual_rates.append(actual_rate)
                ideal_rates.append(ideal_rate)

        if not actual_rates:
            return {"error": "Unable to calculate rates"}

        avg_actual_rate = sum(actual_rates) / len(actual_rates)
        avg_ideal_rate = sum(ideal_rates) / len(ideal_rates) if ideal_rates else 0

        # Calculate variance
        variance = avg_actual_rate - avg_ideal_rate if avg_ideal_rate > 0 else 0
        variance_percent = (variance / avg_ideal_rate * 100) if avg_ideal_rate > 0 else 0

        trend = {
            "average_actual_burndown_rate": round(avg_actual_rate, 2),
            "average_ideal_burndown_rate": round(avg_ideal_rate, 2),
            "variance": round(variance, 2),
            "variance_percent": round(variance_percent, 1),
            "trend": "Faster than planned" if variance > 0 else
                    ("Slower than planned" if variance < 0 else "On pace"),
            "data_points_analyzed": len(actual_rates)
        }

        return trend

    def analyze_health(self) -> Dict:
        """
        Analyze sprint/release health

        Returns:
            Dictionary with health indicators
        """
        latest = self.get_latest_point()
        if not latest:
            return {"error": "No data available"}

        forecast = self.forecast_completion()
        trend = self.calculate_trend()

        # Calculate progress metrics
        elapsed_time = (latest.date - self.start_date).days
        total_time = (self.end_date - self.start_date).days
        time_elapsed_percent = (elapsed_time / total_time * 100) if total_time > 0 else 0

        work_completed_percent = latest.completion_percentage

        # Health status determination
        if "error" in forecast:
            status = "Unknown"
            color = "⚪"
        elif work_completed_percent >= time_elapsed_percent + 10:
            status = "Healthy"
            color = "🟢"
        elif work_completed_percent >= time_elapsed_percent - 10:
            status = "At Risk"
            color = "🟡"
        else:
            status = "Critical"
            color = "🔴"

        health = {
            "status": status,
            "color": color,
            "time_elapsed_percent": round(time_elapsed_percent, 1),
            "work_completed_percent": round(work_completed_percent, 1),
            "performance_index": round(work_completed_percent / time_elapsed_percent, 2)
                                if time_elapsed_percent > 0 else 0,
            "scope_changes": len(self.scope_changes),
            "total_scope_change": sum(change for _, change, _ in self.scope_changes),
            "forecast": forecast if "error" not in forecast else None,
            "trend": trend if "error" not in trend else None
        }

        return health

    def generate_ascii_chart(self) -> str:
        """
        Generate ASCII representation of chart

        Returns:
            ASCII string representation
        """
        if len(self.data_points) < 2:
            return "Insufficient data for chart (need at least 2 points)"

        height = self.config.ascii_chart_height
        width = self.config.ascii_chart_width

        # Get data range
        max_points = max(dp.total_scope for dp in self.data_points)
        total_days = (self.end_date - self.start_date).days

        # Initialize chart grid
        grid = [[' ' for _ in range(width)] for _ in range(height)]

        # Draw axes
        for y in range(height):
            grid[y][0] = '│'
        for x in range(width):
            grid[height-1][x] = '─'
        grid[height-1][0] = '└'

        # Plot ideal line
        for x in range(1, width):
            progress = x / width
            ideal_y = height - 2 - int((1 - progress) * (height - 2))
            if 0 <= ideal_y < height - 1:
                grid[ideal_y][x] = '·'

        # Plot actual line
        for dp in self.data_points:
            days_from_start = (dp.date - self.start_date).days
            x = int((days_from_start / total_days) * (width - 1)) + 1

            if self.config.chart_type == ChartType.BURNDOWN:
                value = dp.remaining_points
            else:  # BURNUP
                value = dp.completed_points

            y = height - 2 - int((value / max_points) * (height - 2))

            if 0 <= y < height - 1 and 1 <= x < width:
                grid[y][x] = '●'

        # Convert grid to string
        lines = [''.join(row) for row in grid]

        # Add labels
        chart_type_label = "BURNDOWN" if self.config.chart_type == ChartType.BURNDOWN else "BURNUP"
        title = f"{chart_type_label} CHART"
        lines.insert(0, title.center(width))
        lines.insert(1, "=" * width)

        # Y-axis labels
        lines[2] = f"{int(max_points):>3}" + lines[2][3:]
        lines[height//2] = f"{int(max_points/2):>3}" + lines[height//2][3:]
        lines[height] = "  0" + lines[height][3:]

        # X-axis label
        lines.append(f"Day 0" + " " * (width - 15) + f"Day {total_days}")

        # Legend
        lines.append("")
        lines.append("Legend: ● = Actual   · = Ideal")

        return '\n'.join(lines)

    def generate(self) -> Dict:
        """
        Generate complete chart data and analysis

        Returns:
            Dictionary with all chart data
        """
        if not self.data_points:
            return {"error": "No data points available"}

        # Get all metrics
        forecast = self.forecast_completion()
        trend = self.calculate_trend()
        health = self.analyze_health()
        ascii_chart = self.generate_ascii_chart()

        # Prepare data points for export
        data_points_export = [
            {
                "date": dp.date.strftime("%Y-%m-%d"),
                "remaining_points": dp.remaining_points,
                "completed_points": dp.completed_points,
                "total_scope": dp.total_scope,
                "ideal_remaining": dp.ideal_remaining,
                "completion_percent": round(dp.completion_percentage, 1)
            }
            for dp in self.data_points
        ]

        # Scope changes
        scope_changes_export = [
            {
                "date": date.strftime("%Y-%m-%d"),
                "change": change,
                "reason": reason
            }
            for date, change, reason in self.scope_changes
        ]

        chart_data = {
            "chart_type": self.config.chart_type.value,
            "start_date": self.start_date.strftime("%Y-%m-%d"),
            "end_date": self.end_date.strftime("%Y-%m-%d"),
            "initial_scope": self.initial_scope,
            "current_scope": self.current_scope,
            "data_points": data_points_export,
            "scope_changes": scope_changes_export,
            "forecast": forecast,
            "trend": trend,
            "health": health,
            "ascii_chart": ascii_chart
        }

        return chart_data


def main():
    """Example usage of BurndownCalculator"""

    print("=" * 80)
    print("BURNDOWN CHART CALCULATOR - Example Usage")
    print("=" * 80)

    # Example 1: Sprint Burndown
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Sprint Burndown Chart")
    print("=" * 80)

    config = BurndownConfig(
        chart_type=ChartType.BURNDOWN,
        sprint_duration_days=10,  # 2-week sprint (10 work days)
        work_days_per_week=5
    )

    sprint_start = datetime(2024, 3, 1)
    calculator = BurndownCalculator(
        config=config,
        start_date=sprint_start,
        initial_scope=50
    )

    # Simulate daily progress
    daily_progress = [
        (1, 5),    # Day 1: 5 points completed
        (2, 10),   # Day 2: 10 points total
        (3, 14),   # Day 3: 14 points total
        (4, 19),   # Day 4: 19 points
        (5, 24),   # Day 5: 24 points
        (6, 28),   # Day 6: 28 points
        (7, 33),   # Day 7: 33 points (scope change)
        (8, 38),   # Day 8: 38 points
        (9, 43),   # Day 9: 43 points
    ]

    for day, completed in daily_progress:
        date = sprint_start + timedelta(days=day)
        # Skip weekends
        if date.weekday() < 5:
            scope_change = 5 if day == 7 else 0  # Add scope on day 7
            reason = "New urgent story added" if scope_change > 0 else ""
            calculator.add_data_point(
                date=date,
                completed_points=completed,
                scope_change=scope_change,
                scope_change_reason=reason
            )

    # Generate chart
    chart_data = calculator.generate()

    print(f"\nSprint Information:")
    print(f"  Start Date: {chart_data['start_date']}")
    print(f"  End Date: {chart_data['end_date']}")
    print(f"  Initial Scope: {chart_data['initial_scope']} points")
    print(f"  Current Scope: {chart_data['current_scope']} points")
    print(f"  Data Points: {len(chart_data['data_points'])}")

    # Scope Changes
    if chart_data['scope_changes']:
        print(f"\nScope Changes:")
        for change in chart_data['scope_changes']:
            print(f"  {change['date']}: {change['change']:+.0f} points - {change['reason']}")

    # Forecast
    print(f"\nForecast:")
    forecast = chart_data['forecast']
    if 'error' not in forecast:
        print(f"  Current Velocity: {forecast['current_velocity']} points/day")
        print(f"  Remaining Points: {forecast['remaining_points']}")
        print(f"  Forecast Completion: {forecast['forecast_completion_date']}")
        print(f"  Scheduled End: {forecast['scheduled_end_date']}")
        print(f"  Days Delta: {forecast['days_delta']:+d} days")
        print(f"  Status: {forecast['status']}")
        print(f"  Confidence: {forecast['confidence']}")
    else:
        print(f"  {forecast['error']}")

    # Trend
    print(f"\nTrend Analysis:")
    trend = chart_data['trend']
    if 'error' not in trend:
        print(f"  Actual Burndown Rate: {trend['average_actual_burndown_rate']} points/day")
        print(f"  Ideal Burndown Rate: {trend['average_ideal_burndown_rate']} points/day")
        print(f"  Variance: {trend['variance']:+.2f} points/day ({trend['variance_percent']:+.1f}%)")
        print(f"  Trend: {trend['trend']}")
    else:
        print(f"  {trend['error']}")

    # Health
    print(f"\nSprint Health:")
    health = chart_data['health']
    print(f"  Status: {health['color']} {health['status']}")
    print(f"  Time Elapsed: {health['time_elapsed_percent']:.1f}%")
    print(f"  Work Completed: {health['work_completed_percent']:.1f}%")
    print(f"  Performance Index: {health['performance_index']:.2f}")
    print(f"  Scope Changes: {health['scope_changes']}")

    # ASCII Chart
    print(f"\n{chart_data['ascii_chart']}")

    # Example 2: Release Burnup
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Release Burnup Chart")
    print("=" * 80)

    config_burnup = BurndownConfig(
        chart_type=ChartType.BURNUP,
        time_unit=TimeUnit.SPRINTS,
        sprint_duration_days=14
    )

    release_start = datetime(2024, 1, 1)
    calculator_burnup = BurndownCalculator(
        config=config_burnup,
        start_date=release_start,
        initial_scope=200,
        end_date=release_start + timedelta(days=84)  # 6 sprints
    )

    # Simulate sprint-by-sprint progress
    sprint_progress = [
        (14, 28, 0),      # Sprint 1: 28 points
        (28, 54, 10),     # Sprint 2: 26 points + 10 scope change
        (42, 82, 0),      # Sprint 3: 28 points
        (56, 108, -5),    # Sprint 4: 26 points, 5 removed
        (70, 136, 15),    # Sprint 5: 28 points + 15 scope change
    ]

    for days, completed, scope_change in sprint_progress:
        date = release_start + timedelta(days=days)
        reason = ""
        if scope_change > 0:
            reason = f"Added {scope_change} points - new features"
        elif scope_change < 0:
            reason = f"Removed {abs(scope_change)} points - descoped"

        calculator_burnup.add_data_point(
            date=date,
            completed_points=completed,
            scope_change=scope_change,
            scope_change_reason=reason
        )

    chart_data_burnup = calculator_burnup.generate()

    print(f"\nRelease Information:")
    print(f"  Duration: {chart_data_burnup['start_date']} to {chart_data_burnup['end_date']}")
    print(f"  Initial Scope: {chart_data_burnup['initial_scope']} points")
    print(f"  Current Scope: {chart_data_burnup['current_scope']} points")
    print(f"  Scope Delta: {chart_data_burnup['current_scope'] - chart_data_burnup['initial_scope']:+.0f} points")

    print(f"\nProgress:")
    latest = chart_data_burnup['data_points'][-1]
    print(f"  Completed: {latest['completed_points']} points ({latest['completion_percent']:.1f}%)")
    print(f"  Remaining: {latest['remaining_points']} points")

    print(f"\nRelease Health: {chart_data_burnup['health']['color']} {chart_data_burnup['health']['status']}")

    print(f"\n{chart_data_burnup['ascii_chart']}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
