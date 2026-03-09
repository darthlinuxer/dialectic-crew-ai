#!/usr/bin/env python3
"""
Integration Tests for Analytical Scripts

These tests actually RUN the scripts and verify real outputs.
No mocks - we test the actual functionality and validate outputs.

Tests produce real files in tests/output/ for visual inspection.

Author: Senior Agile PM Budget Analyst Skill
License: MIT
"""

import sys
import os
sys.path.append('..')

import unittest
from datetime import datetime, timedelta
import json
import re

# Import all modules to test
from critical_path import CriticalPathAnalyzer, Activity
from budget_calculator import BudgetCalculator, BudgetConfig, TeamMember
from poker_planning import PokerPlanningCalculator, PokerConfig, Story, EstimationScale
from gantt_chart import GanttChartGenerator, GanttConfig, Task, TaskType, TaskStatus
from burndown_chart import BurndownCalculator, BurndownConfig, ChartType
from exporters import (
    MarkdownExporter, MermaidExporter, PlantUMLExporter,
    HTMLExporter, CSVExporter, JSONExporter, save_to_file
)


class IntegrationTestBase(unittest.TestCase):
    """Base class for integration tests"""

    @classmethod
    def setUpClass(cls):
        """Create output directory for test files"""
        cls.output_dir = os.path.join(os.path.dirname(__file__), 'output')
        os.makedirs(cls.output_dir, exist_ok=True)
        print(f"\n📁 Test outputs will be saved to: {cls.output_dir}")

    def save_output(self, content: str, filename: str) -> str:
        """Save test output to file"""
        filepath = os.path.join(self.output_dir, filename)
        save_to_file(content, filepath)
        return filepath

    def assertFileExists(self, filepath: str):
        """Assert file was created"""
        self.assertTrue(os.path.exists(filepath), f"File not created: {filepath}")

    def assertFileNotEmpty(self, filepath: str):
        """Assert file has content"""
        self.assertFileExists(filepath)
        size = os.path.getsize(filepath)
        self.assertGreater(size, 0, f"File is empty: {filepath}")

    def assertValidJSON(self, content: str):
        """Assert string is valid JSON"""
        try:
            json.loads(content)
        except json.JSONDecodeError as e:
            self.fail(f"Invalid JSON: {e}")

    def assertValidMarkdown(self, content: str):
        """Basic markdown validation"""
        # Should have at least one heading
        self.assertIn('#', content, "No markdown headings found")

    def assertValidMermaid(self, content: str):
        """Basic mermaid validation"""
        # Should have mermaid diagram type
        mermaid_types = ['flowchart', 'gantt', 'pie', 'xychart']
        has_type = any(t in content for t in mermaid_types)
        self.assertTrue(has_type, "No mermaid diagram type found")

    def assertValidHTML(self, content: str):
        """Basic HTML validation"""
        self.assertIn('<!DOCTYPE html>', content, "Missing DOCTYPE")
        self.assertIn('<html>', content, "Missing html tag")
        self.assertIn('</html>', content, "HTML not closed")


class TestCriticalPathIntegration(IntegrationTestBase):
    """Integration tests for Critical Path Analysis"""

    def setUp(self):
        """Set up test data"""
        self.activities = [
            {"id": "A", "name": "Requirements", "duration": 5, "predecessors": []},
            {"id": "B", "name": "Design", "duration": 8, "predecessors": ["A"]},
            {"id": "C", "name": "Procurement", "duration": 3, "predecessors": ["A"]},
            {"id": "D", "name": "Development", "duration": 10, "predecessors": ["B"]},
            {"id": "E", "name": "Testing", "duration": 5, "predecessors": ["D", "C"]},
            {"id": "F", "name": "Deployment", "duration": 2, "predecessors": ["E"]}
        ]

    def test_01_critical_path_analysis_runs(self):
        """Test CPM analysis executes successfully"""
        print("\n🔍 Testing Critical Path Analysis...")

        analyzer = CriticalPathAnalyzer(self.activities, unit="days")
        result = analyzer.analyze()

        # Validate result structure
        self.assertIn('project_duration', result)
        self.assertIn('critical_path', result)
        self.assertIn('activities', result)

        # Validate project duration is positive
        self.assertGreater(result['project_duration'], 0)

        # Validate critical path exists
        self.assertGreater(len(result['critical_path']), 0)

        print(f"   ✅ Project Duration: {result['project_duration']} days")
        print(f"   ✅ Critical Path: {' → '.join(result['critical_path'])}")

    def test_02_critical_path_json_export(self):
        """Test JSON export is valid"""
        print("\n💾 Testing CPM JSON Export...")

        analyzer = CriticalPathAnalyzer(self.activities)
        result = analyzer.analyze()

        json_output = JSONExporter.to_json(result)
        filepath = self.save_output(json_output, 'cpm_result.json')

        self.assertFileNotEmpty(filepath)
        self.assertValidJSON(json_output)

        print(f"   ✅ JSON saved: {filepath}")

    def test_03_critical_path_markdown_export(self):
        """Test Markdown export creates valid output"""
        print("\n📄 Testing CPM Markdown Export...")

        analyzer = CriticalPathAnalyzer(self.activities)
        result = analyzer.analyze()

        # Create markdown report
        md_lines = []
        md_lines.append(MarkdownExporter.heading("Critical Path Analysis", 1))
        md_lines.append(f"Duration: {result['project_duration']} days\n")

        headers = ["ID", "Name", "Duration", "ES", "EF", "Critical"]
        rows = [[a['id'], a['name'], a['duration'], a['ES'], a['EF'], "✅" if a['critical'] else "❌"]
                for a in result['activities']]
        md_lines.append(MarkdownExporter.table(headers, rows))

        md_output = '\n'.join(md_lines)
        filepath = self.save_output(md_output, 'cpm_report.md')

        self.assertFileNotEmpty(filepath)
        self.assertValidMarkdown(md_output)
        self.assertIn('Critical Path Analysis', md_output)

        print(f"   ✅ Markdown saved: {filepath}")

    def test_04_critical_path_mermaid_export(self):
        """Test Mermaid flowchart generation"""
        print("\n🎨 Testing CPM Mermaid Export...")

        analyzer = CriticalPathAnalyzer(self.activities)
        result = analyzer.analyze()

        # Create mermaid flowchart
        nodes = [{"id": a['id'], "label": a['name'], "critical": a['critical']}
                 for a in result['activities']]
        edges = [{"from": p, "to": a['id']}
                 for a in result['activities'] for p in a.get('predecessors', [])]

        mermaid = MermaidExporter.flowchart(nodes, edges, direction="LR")
        mermaid_output = f"```mermaid\n{mermaid}\n```"

        filepath = self.save_output(mermaid_output, 'cpm_flowchart.md')

        self.assertFileNotEmpty(filepath)
        self.assertValidMermaid(mermaid)
        self.assertIn('flowchart', mermaid)

        print(f"   ✅ Mermaid saved: {filepath}")

    def test_05_complex_project_with_dependencies(self):
        """Test complex project with multiple dependencies, parallel paths, and verify exports"""
        print("\n🔥 Testing Complex Project with Multiple Dependencies...")

        # Complex project: Enterprise Application Development
        complex_activities = [
            {"id": "A", "name": "Project Kickoff", "duration": 2, "predecessors": []},
            {"id": "B", "name": "Requirements Analysis", "duration": 5, "predecessors": ["A"]},
            {"id": "C", "name": "Architecture Design", "duration": 8, "predecessors": ["B"]},
            {"id": "D", "name": "Database Design", "duration": 5, "predecessors": ["B"]},
            {"id": "E", "name": "UI/UX Design", "duration": 6, "predecessors": ["B"]},
            {"id": "F", "name": "Backend Development", "duration": 15, "predecessors": ["C", "D"]},
            {"id": "G", "name": "Frontend Development", "duration": 12, "predecessors": ["C", "E"]},
            {"id": "H", "name": "API Integration", "duration": 5, "predecessors": ["F", "G"]},
            {"id": "I", "name": "Security Implementation", "duration": 7, "predecessors": ["F"]},
            {"id": "J", "name": "Unit Testing", "duration": 8, "predecessors": ["H", "I"]},
            {"id": "K", "name": "Integration Testing", "duration": 6, "predecessors": ["J"]},
            {"id": "L", "name": "UAT & Deployment", "duration": 4, "predecessors": ["K"]}
        ]

        analyzer = CriticalPathAnalyzer(complex_activities, unit="days")
        result = analyzer.analyze()

        # Validate critical path exists and has reasonable length
        self.assertGreater(len(result['critical_path']), 5, "Complex project should have long critical path")
        self.assertGreater(result['project_duration'], 40, "Complex project should take significant time")

        print(f"   ✅ Project Duration: {result['project_duration']} days")
        print(f"   ✅ Critical Path Length: {len(result['critical_path'])} activities")
        print(f"   ✅ Critical Path: {' → '.join(result['critical_path'])}")

        # Test Mermaid Flowchart with RED critical paths
        print("\n   🎨 Testing Mermaid Flowchart with Critical Path Coloring...")
        nodes = [{"id": a['id'], "label": a['name'], "critical": a['critical']}
                 for a in result['activities']]
        edges = [{"from": p, "to": a['id']}
                 for a in result['activities'] for p in a.get('predecessors', [])]

        # Verify edges were extracted correctly
        self.assertGreater(len(edges), 10, "Complex project should have many edges")
        print(f"   ✅ Extracted {len(edges)} edges from dependencies")

        # Generate Mermaid with default red critical path coloring
        mermaid = MermaidExporter.flowchart(nodes, edges, direction="TB")
        mermaid_output = f"```mermaid\n{mermaid}\n```"

        filepath = self.save_output(mermaid_output, 'cpm_complex_flowchart.md')

        # Validate Mermaid output structure
        self.assertFileNotEmpty(filepath)
        self.assertValidMermaid(mermaid)

        # CRITICAL: Verify edges are present in output
        self.assertIn('-->', mermaid, "Mermaid flowchart MUST contain edges (arrows)")
        edge_count = mermaid.count('-->')
        self.assertGreater(edge_count, 10, f"Expected many edges, found only {edge_count}")

        # Verify critical path styling is applied (red color by default)
        self.assertIn('classDef critical', mermaid, "Critical path styling must be defined")
        self.assertIn('#ff6b6b', mermaid, "Critical nodes should use red color by default")

        # Verify normal node styling is also present
        self.assertIn('classDef normal', mermaid, "Normal node styling must be defined")

        print(f"   ✅ Mermaid flowchart has {edge_count} edges (arrows)")
        print(f"   ✅ Critical path nodes styled in RED (#ff6b6b)")
        print(f"   ✅ Mermaid saved: {filepath}")

        # Test PlantUML Gantt Diagram
        print("\n   📊 Testing PlantUML Gantt with Critical Path...")

        tasks = []
        for a in result['activities']:
            task = {
                "id": a['id'],
                "name": a['name'],
                "duration": a['duration'],
                "dependencies": a.get('predecessors', []),
                "critical": a['critical']
            }
            tasks.append(task)

        plantuml = PlantUMLExporter.gantt_diagram(
            tasks,
            title="Complex Enterprise Application Development"
        )

        filepath = self.save_output(plantuml, 'cpm_complex_gantt.puml')

        # Validate PlantUML structure
        self.assertFileNotEmpty(filepath)
        self.assertIn('@startgantt', plantuml)
        self.assertIn('@endgantt', plantuml)

        # Verify all tasks are present
        for activity in complex_activities:
            self.assertIn(activity['name'], plantuml, f"Task {activity['name']} missing from Gantt")

        # Verify dependencies are represented
        self.assertIn('starts at', plantuml, "PlantUML Gantt should show dependencies")

        # Verify critical tasks are colored red
        self.assertIn('colored in Red', plantuml, "Critical tasks should be colored red")

        print(f"   ✅ PlantUML Gantt includes all {len(complex_activities)} tasks")
        print(f"   ✅ Dependencies properly represented")
        print(f"   ✅ Critical tasks colored RED")
        print(f"   ✅ PlantUML saved: {filepath}")

        # Generate comprehensive markdown report
        print("\n   📄 Generating Comprehensive Markdown Report...")

        md_lines = []
        md_lines.append(MarkdownExporter.heading("Complex Project Analysis", 1))
        md_lines.append(MarkdownExporter.heading("Executive Summary", 2))
        md_lines.append(f"- **Total Duration:** {result['project_duration']} days\n")
        md_lines.append(f"- **Total Activities:** {len(result['activities'])}\n")
        md_lines.append(f"- **Critical Path Length:** {len(result['critical_path'])} activities\n")
        md_lines.append(f"- **Critical Path:** {' → '.join(result['critical_path'])}\n\n")

        md_lines.append(MarkdownExporter.heading("Activity Details", 2))
        headers = ["ID", "Name", "Duration", "ES", "EF", "LS", "LF", "Slack", "Critical"]
        rows = []
        for a in result['activities']:
            rows.append([
                a['id'],
                a['name'],
                f"{a['duration']} days",
                a['ES'],
                a['EF'],
                a['LS'],
                a['LF'],
                a['slack'],
                "🔴 YES" if a['critical'] else "⚪ No"
            ])
        md_lines.append(MarkdownExporter.table(headers, rows))

        md_output = '\n'.join(md_lines)
        filepath = self.save_output(md_output, 'cpm_complex_report.md')

        self.assertFileNotEmpty(filepath)
        self.assertValidMarkdown(md_output)
        print(f"   ✅ Comprehensive report saved: {filepath}")

        print("\n   🎉 Complex project test PASSED - All exports verified!")


class TestBudgetIntegration(IntegrationTestBase):
    """Integration tests for Budget Calculator"""

    def setUp(self):
        """Set up test data"""
        self.team = [
            TeamMember("Tech Lead", 1, 120),
            TeamMember("Senior Dev", 2, 100),
            TeamMember("Developer", 3, 70),
            TeamMember("QA", 2, 65)
        ]

        self.config = BudgetConfig(
            total_story_points=100,
            points_per_sprint=20,
            sprint_duration_weeks=2,
            hours_per_sprint=320
        )

    def test_01_budget_calculation_runs(self):
        """Test budget calculation executes"""
        print("\n💰 Testing Budget Calculation...")

        calculator = BudgetCalculator(self.config, self.team, fixed_costs=10000)
        result = calculator.calculate()

        # Validate structure
        self.assertIn('summary', result)
        self.assertIn('breakdown', result)
        self.assertIn('scenarios', result)

        # Validate calculations
        summary = result['summary']
        self.assertGreater(summary['total_budget'], 0)
        self.assertGreater(summary['base_cost'], 0)

        print(f"   ✅ Total Budget: ${summary['total_budget']:,.2f}")
        print(f"   ✅ Base Cost: ${summary['base_cost']:,.2f}")

    def test_02_budget_scenario_analysis(self):
        """Test scenario analysis produces valid results"""
        print("\n📊 Testing Budget Scenarios...")

        calculator = BudgetCalculator(self.config, self.team, fixed_costs=10000)
        result = calculator.calculate()

        scenarios = result['scenarios']

        # Validate scenarios
        self.assertIn('optimistic', scenarios)
        self.assertIn('realistic', scenarios)
        self.assertIn('pessimistic', scenarios)

        # Validate ordering: optimistic < realistic < pessimistic
        self.assertLess(scenarios['optimistic']['total_budget'], scenarios['realistic']['total_budget'])
        self.assertLess(scenarios['realistic']['total_budget'], scenarios['pessimistic']['total_budget'])

        print(f"   ✅ Optimistic: ${scenarios['optimistic']['total_budget']:,.2f}")
        print(f"   ✅ Realistic: ${scenarios['realistic']['total_budget']:,.2f}")
        print(f"   ✅ Pessimistic: ${scenarios['pessimistic']['total_budget']:,.2f}")

    def test_03_budget_mermaid_pie_chart(self):
        """Test Mermaid pie chart generation"""
        print("\n🥧 Testing Budget Pie Chart...")

        calculator = BudgetCalculator(self.config, self.team, fixed_costs=10000)
        result = calculator.calculate()

        # Create pie chart from breakdown (extract numeric values only)
        breakdown = result['breakdown']
        data = {
            "Base Cost": breakdown['base_cost']['total'],
            "Overhead": breakdown['overhead']['total'],
            "Fixed Costs": breakdown['fixed_costs']['total'],
            "Contingency": breakdown['contingency']['total']
        }

        pie_chart = MermaidExporter.pie_chart("Budget Composition", data)
        output = f"```mermaid\n{pie_chart}\n```"

        filepath = self.save_output(output, 'budget_pie.md')

        self.assertFileNotEmpty(filepath)
        self.assertIn('pie', pie_chart)
        self.assertIn('title', pie_chart)

        print(f"   ✅ Pie chart saved: {filepath}")

    def test_04_budget_csv_export(self):
        """Test CSV export"""
        print("\n📈 Testing Budget CSV Export...")

        calculator = BudgetCalculator(self.config, self.team, fixed_costs=10000)
        result = calculator.calculate()

        # Export sprint breakdown to CSV
        sprint_data = result['by_sprint']

        csv_output = CSVExporter.dict_to_csv(sprint_data)
        filepath = self.save_output(csv_output, 'budget_by_sprint.csv')

        self.assertFileNotEmpty(filepath)
        self.assertIn('sprint', csv_output)
        self.assertIn('budget', csv_output)

        print(f"   ✅ CSV saved: {filepath}")


class TestPokerPlanningIntegration(IntegrationTestBase):
    """Integration tests for Poker Planning"""

    def setUp(self):
        """Set up test data"""
        self.config = PokerConfig(
            scale=EstimationScale.FIBONACCI,
            breakdown_threshold=13,
            points_per_sprint=20
        )

    def test_01_estimate_validation(self):
        """Test estimate validation"""
        print("\n🎯 Testing Poker Planning Validation...")

        calculator = PokerPlanningCalculator(self.config)

        # Test valid estimates
        valid, msg = calculator.validate_estimate(8)
        self.assertTrue(valid)
        print(f"   ✅ Valid estimate (8): {msg}")

        # Test invalid estimate
        valid, msg = calculator.validate_estimate(7)
        self.assertFalse(valid)
        print(f"   ✅ Invalid estimate (7): {msg}")

    def test_02_breakdown_recommendation(self):
        """Test story breakdown recommendation"""
        print("\n✂️ Testing Story Breakdown...")

        calculator = PokerPlanningCalculator(self.config)

        # Test story that should be broken down
        breakdown = calculator.recommend_breakdown(21)
        self.assertTrue(breakdown['should_breakdown'])
        self.assertGreater(len(breakdown['suggested_breakdown']), 0)

        print(f"   ✅ 21 points: {breakdown['reason']}")

        # Test story that doesn't need breakdown
        breakdown = calculator.recommend_breakdown(8)
        self.assertFalse(breakdown['should_breakdown'])

        print(f"   ✅ 8 points: {breakdown['reason']}")

    def test_03_velocity_calculation(self):
        """Test velocity calculation with real data"""
        print("\n🚀 Testing Velocity Calculation...")

        calculator = PokerPlanningCalculator(self.config)

        # Add completed stories
        stories = [
            Story("US-1", "Feature 1", estimated_points=8, actual_points=8, completed=True, sprint=1),
            Story("US-2", "Feature 2", estimated_points=5, actual_points=5, completed=True, sprint=1),
            Story("US-3", "Feature 3", estimated_points=13, actual_points=13, completed=True, sprint=2),
            Story("US-4", "Feature 4", estimated_points=8, actual_points=8, completed=True, sprint=2),
            Story("US-5", "Feature 5", estimated_points=5, actual_points=5, completed=True, sprint=3),
        ]

        for story in stories:
            calculator.add_story(story)

        velocity = calculator.calculate_velocity(completed_sprints=3)

        self.assertNotIn('error', velocity)
        self.assertIn('average_velocity', velocity)
        self.assertGreater(velocity['average_velocity'], 0)

        print(f"   ✅ Average Velocity: {velocity['average_velocity']:.1f} points/sprint")

    def test_04_backlog_analysis_json(self):
        """Test backlog analysis JSON export"""
        print("\n📋 Testing Backlog Analysis...")

        calculator = PokerPlanningCalculator(self.config)

        # Add various stories
        stories = [
            Story("US-1", "Small Story", estimated_points=3),
            Story("US-2", "Ideal Story", estimated_points=5),
            Story("US-3", "Large Story", estimated_points=21),
        ]

        for story in stories:
            calculator.add_story(story)

        analysis = calculator.analyze_backlog()

        # Export to JSON
        json_output = JSONExporter.to_json(analysis)
        filepath = self.save_output(json_output, 'backlog_analysis.json')

        self.assertFileNotEmpty(filepath)
        self.assertValidJSON(json_output)

        print(f"   ✅ Backlog analysis saved: {filepath}")


class TestGanttIntegration(IntegrationTestBase):
    """Integration tests for Gantt Chart"""

    def setUp(self):
        """Set up test data"""
        self.config = GanttConfig(project_start_date=datetime(2024, 3, 1))

    def test_01_gantt_generation(self):
        """Test Gantt chart generation"""
        print("\n📊 Testing Gantt Chart Generation...")

        generator = GanttChartGenerator(self.config)

        # Add tasks
        tasks = [
            Task("E1", "Epic 1", TaskType.EPIC, datetime(2024, 3, 1), 14, status=TaskStatus.COMPLETED),
            Task("E2", "Epic 2", TaskType.EPIC, datetime(2024, 3, 15), 21, dependencies=["E1"]),
            Task("E3", "Epic 3", TaskType.EPIC, datetime(2024, 4, 5), 14, dependencies=["E2"]),
        ]

        for task in tasks:
            generator.add_task(task)

        chart_data = generator.generate()

        # Validate structure
        self.assertIn('timeline', chart_data)
        self.assertIn('tasks', chart_data)
        self.assertIn('ascii_chart', chart_data)

        print(f"   ✅ Timeline: {chart_data['timeline']['project_start']} to {chart_data['timeline']['project_end']}")

    def test_02_gantt_ascii_output(self):
        """Test ASCII Gantt chart output"""
        print("\n🖼️ Testing ASCII Gantt...")

        generator = GanttChartGenerator(self.config)

        tasks = [
            Task("E1", "Authentication", TaskType.EPIC, datetime(2024, 3, 1), 14),
            Task("E2", "Dashboard", TaskType.EPIC, datetime(2024, 3, 15), 14),
        ]

        for task in tasks:
            generator.add_task(task)

        chart_data = generator.generate()
        ascii_chart = chart_data['ascii_chart']

        filepath = self.save_output(ascii_chart, 'gantt_ascii.txt')

        self.assertFileNotEmpty(filepath)
        self.assertIn('TASK', ascii_chart)
        self.assertIn('TIMELINE', ascii_chart)

        print(f"   ✅ ASCII chart saved: {filepath}")

    def test_03_gantt_mermaid_export(self):
        """Test Mermaid Gantt export with complex project and critical path"""
        print("\n📅 Testing Mermaid Gantt with Critical Path...")

        # Complex project with multiple phases
        complex_activities = [
            {"id": "A", "name": "Project Kickoff", "duration": 2, "predecessors": []},
            {"id": "B", "name": "Requirements Analysis", "duration": 5, "predecessors": ["A"]},
            {"id": "C", "name": "Architecture Design", "duration": 8, "predecessors": ["B"]},
            {"id": "D", "name": "Database Design", "duration": 5, "predecessors": ["B"]},
            {"id": "E", "name": "UI/UX Design", "duration": 6, "predecessors": ["B"]},
            {"id": "F", "name": "Backend Development", "duration": 15, "predecessors": ["C", "D"]},
            {"id": "G", "name": "Frontend Development", "duration": 12, "predecessors": ["C", "E"]},
            {"id": "H", "name": "API Integration", "duration": 5, "predecessors": ["F", "G"]},
            {"id": "I", "name": "Security Implementation", "duration": 7, "predecessors": ["F"]},
            {"id": "J", "name": "Unit Testing", "duration": 8, "predecessors": ["H", "I"]},
            {"id": "K", "name": "Integration Testing", "duration": 6, "predecessors": ["J"]},
            {"id": "L", "name": "UAT & Deployment", "duration": 4, "predecessors": ["K"]}
        ]

        # Run CPM analysis to identify critical path
        from datetime import datetime, timedelta
        analyzer = CriticalPathAnalyzer(complex_activities, unit="days")
        result = analyzer.analyze()

        # Create Gantt sections by project phase
        start_date = datetime(2024, 3, 1)

        # Calculate actual dates based on ES/EF from CPM
        tasks_by_phase = {
            "Planning Phase": ["A", "B", "C", "D", "E"],
            "Development Phase": ["F", "G", "H", "I"],
            "Testing Phase": ["J", "K", "L"]
        }

        sections = []
        for phase_name, task_ids in tasks_by_phase.items():
            phase_tasks = []
            for activity in result['activities']:
                if activity['id'] in task_ids:
                    task_start = start_date + timedelta(days=activity['ES'])
                    task_end = start_date + timedelta(days=activity['EF'])

                    # Critical path tasks use "crit" status, others use "active"
                    status = "crit" if activity['critical'] else "active"

                    phase_tasks.append({
                        "id": activity['id'],
                        "name": activity['name'],
                        "start": task_start.strftime("%Y-%m-%d"),
                        "end": task_end.strftime("%Y-%m-%d"),
                        "status": status
                    })

            if phase_tasks:
                sections.append({"name": phase_name, "tasks": phase_tasks})

        mermaid_gantt = MermaidExporter.gantt("Enterprise Application Development Timeline", sections)
        output = f"```mermaid\n{mermaid_gantt}\n```"

        filepath = self.save_output(output, 'gantt_mermaid.md')

        self.assertFileNotEmpty(filepath)
        self.assertIn('gantt', mermaid_gantt)

        # Verify all phases are present
        self.assertIn('Planning Phase', mermaid_gantt)
        self.assertIn('Development Phase', mermaid_gantt)
        self.assertIn('Testing Phase', mermaid_gantt)

        # Verify critical path is marked with "crit" status
        self.assertIn('crit', mermaid_gantt, "Critical path tasks should be marked with 'crit' status")

        # Count critical vs non-critical tasks
        crit_count = mermaid_gantt.count(':crit,')
        active_count = mermaid_gantt.count(':active,')

        print(f"   ✅ Critical path tasks: {crit_count}")
        print(f"   ✅ Non-critical tasks: {active_count}")
        print(f"   ✅ Total tasks: {crit_count + active_count}")
        print(f"   ✅ Phases: {len(sections)}")
        print(f"   ✅ Mermaid Gantt saved: {filepath}")


class TestBurndownIntegration(IntegrationTestBase):
    """Integration tests for Burndown Chart"""

    def setUp(self):
        """Set up test data"""
        self.config = BurndownConfig(
            chart_type=ChartType.BURNDOWN,
            sprint_duration_days=10
        )

    def test_01_burndown_tracking(self):
        """Test burndown tracking"""
        print("\n📉 Testing Burndown Tracking...")

        calculator = BurndownCalculator(
            self.config,
            start_date=datetime(2024, 3, 1),
            initial_scope=50
        )

        # Add daily progress
        for day in range(1, 6):
            calculator.add_data_point(
                date=datetime(2024, 3, 1) + timedelta(days=day),
                completed_points=day * 10
            )

        latest = calculator.get_latest_point()
        self.assertIsNotNone(latest)
        self.assertEqual(latest.completed_points, 50)

        print(f"   ✅ Latest: {latest.completed_points} points completed")

    def test_02_burndown_forecast(self):
        """Test forecast calculation"""
        print("\n🔮 Testing Burndown Forecast...")

        calculator = BurndownCalculator(
            self.config,
            start_date=datetime(2024, 3, 1),
            initial_scope=50
        )

        # Add progress data
        for day in range(1, 6):
            calculator.add_data_point(
                date=datetime(2024, 3, 1) + timedelta(days=day),
                completed_points=day * 5
            )

        forecast = calculator.forecast_completion()

        self.assertNotIn('error', forecast)
        self.assertIn('current_velocity', forecast)
        self.assertIn('status', forecast)

        print(f"   ✅ Velocity: {forecast['current_velocity']} points/day")
        print(f"   ✅ Status: {forecast['status']}")

    def test_03_burndown_ascii_chart(self):
        """Test ASCII chart generation"""
        print("\n📊 Testing Burndown ASCII Chart...")

        calculator = BurndownCalculator(
            self.config,
            start_date=datetime(2024, 3, 1),
            initial_scope=50
        )

        # Add progress
        for day in range(1, 8):
            calculator.add_data_point(
                date=datetime(2024, 3, 1) + timedelta(days=day),
                completed_points=day * 7
            )

        chart_data = calculator.generate()
        ascii_chart = chart_data['ascii_chart']

        filepath = self.save_output(ascii_chart, 'burndown_ascii.txt')

        self.assertFileNotEmpty(filepath)
        self.assertIn('BURNDOWN', ascii_chart)

        print(f"   ✅ ASCII chart saved: {filepath}")


class TestExportersIntegration(IntegrationTestBase):
    """Integration tests for Exporters module"""

    def test_01_markdown_table(self):
        """Test markdown table generation"""
        print("\n📝 Testing Markdown Table...")

        headers = ["Name", "Value", "Status"]
        rows = [
            ["Item 1", "100", "✅"],
            ["Item 2", "200", "❌"],
        ]

        table = MarkdownExporter.table(headers, rows)
        filepath = self.save_output(table, 'markdown_table.md')

        self.assertFileNotEmpty(filepath)
        self.assertIn('Name', table)
        self.assertIn('|', table)

        print(f"   ✅ Table saved: {filepath}")

    def test_02_html_report(self):
        """Test HTML report generation"""
        print("\n🌐 Testing HTML Report...")

        sections = [
            {"heading": "Summary", "content": "<p>Test content</p>"},
            {"heading": "Details", "content": "<p>More details</p>"}
        ]

        html = HTMLExporter.simple_report("Test Report", sections)
        filepath = self.save_output(html, 'test_report.html')

        self.assertFileNotEmpty(filepath)
        self.assertValidHTML(html)
        self.assertIn('Test Report', html)

        print(f"   ✅ HTML saved: {filepath}")

    def test_03_plantuml_activity(self):
        """Test PlantUML activity diagram"""
        print("\n🔷 Testing PlantUML Diagram...")

        activities = [
            {"id": "A", "name": "Start", "predecessors": [], "critical": False},
            {"id": "B", "name": "Process", "predecessors": ["A"], "critical": True},
        ]

        diagram = PlantUMLExporter.activity_diagram(activities, "Test Diagram")
        output = f"```plantuml\n{diagram}\n```"

        filepath = self.save_output(output, 'plantuml_diagram.puml')

        self.assertFileNotEmpty(filepath)
        self.assertIn('@startuml', diagram)
        self.assertIn('@enduml', diagram)

        print(f"   ✅ PlantUML saved: {filepath}")


def run_integration_tests():
    """Run all integration tests and generate report"""

    print("=" * 80)
    print("INTEGRATION TESTS - REAL OUTPUT VALIDATION")
    print("=" * 80)

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestCriticalPathIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestBudgetIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestPokerPlanningIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestGanttIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestBurndownIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestExportersIntegration))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Tests Run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    output_dir = os.path.join(os.path.dirname(__file__), 'output')
    print(f"\n📁 All test outputs saved to: {output_dir}")
    print("   You can visually inspect all generated files!")

    # List all generated files
    if os.path.exists(output_dir):
        files = sorted(os.listdir(output_dir))
        print(f"\n📄 Generated Files ({len(files)}):")
        for f in files:
            print(f"   - {f}")

    print("\n" + "=" * 80)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)
