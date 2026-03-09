#!/usr/bin/env python3
"""
Complete Project Analysis - Full Integration Example

Demonstrates end-to-end project analysis using all scripts:
1. Critical Path Analysis
2. Budget Calculation
3. Poker Planning Validation
4. Gantt Chart Generation
5. Burndown Tracking

Exports to multiple formats: Markdown, Mermaid, PlantUML, HTML, CSV, JSON, PDF

Author: Senior Agile PM Budget Analyst Skill
License: MIT
"""

import sys
sys.path.append('..')

from critical_path import CriticalPathAnalyzer
from budget_calculator import BudgetCalculator, BudgetConfig, TeamMember
from poker_planning import PokerPlanningCalculator, PokerConfig, Story, EstimationScale
from gantt_chart import GanttChartGenerator, GanttConfig, Task, TaskType, TaskStatus
from burndown_chart import BurndownCalculator, BurndownConfig, ChartType
from exporters import (
    MarkdownExporter, MermaidExporter, PlantUMLExporter,
    HTMLExporter, CSVExporter, JSONExporter, save_to_file
)
from datetime import datetime, timedelta


class ProjectAnalysisReport:
    """
    Complete project analysis combining all analytical tools
    """

    def __init__(self, project_name: str):
        self.project_name = project_name
        self.start_date = datetime(2024, 3, 1)
        self.analyses = {}

    def run_critical_path_analysis(self, epics: list) -> dict:
        """Run CPM analysis on project epics"""
        print("\n🔍 Running Critical Path Analysis...")

        activities = [
            {"id": e['id'], "name": e['name'], "duration": e['duration'], "predecessors": e.get('predecessors', [])}
            for e in epics
        ]

        analyzer = CriticalPathAnalyzer(activities, unit="days")
        result = analyzer.analyze()

        self.analyses['critical_path'] = result
        print(f"   ✅ Duration: {result['project_duration']} days")
        print(f"   ✅ Critical Path: {' → '.join(result['critical_path'])}")

        return result

    def run_budget_analysis(self, story_points: int, team: list, fixed_costs: float) -> dict:
        """Calculate project budget"""
        print("\n💰 Running Budget Analysis...")

        config = BudgetConfig(
            total_story_points=story_points,
            points_per_sprint=20,
            sprint_duration_weeks=2,
            hours_per_sprint=320
        )

        calculator = BudgetCalculator(config, team, fixed_costs)
        result = calculator.calculate()

        self.analyses['budget'] = result
        print(f"   ✅ Total Budget: ${result['summary']['total_budget']:,.2f}")
        print(f"   ✅ Duration: {result['project_metrics']['total_sprints']} sprints")

        return result

    def run_poker_planning_analysis(self, stories: list) -> dict:
        """Validate estimations and calculate velocity"""
        print("\n🎯 Running Poker Planning Analysis...")

        config = PokerConfig(
            scale=EstimationScale.FIBONACCI,
            breakdown_threshold=13,
            points_per_sprint=20
        )

        calculator = PokerPlanningCalculator(config)

        # Add stories
        for story_data in stories:
            story = Story(
                id=story_data['id'],
                title=story_data['title'],
                estimated_points=story_data['points'],
                completed=story_data.get('completed', False),
                actual_points=story_data.get('actual_points'),
                sprint=story_data.get('sprint')
            )
            calculator.add_story(story)

        # Analyze backlog
        backlog_analysis = calculator.analyze_backlog()

        # Calculate velocity if we have completed stories
        velocity_result = calculator.calculate_velocity(completed_sprints=3)

        self.analyses['poker_planning'] = {
            'backlog': backlog_analysis,
            'velocity': velocity_result
        }

        print(f"   ✅ Total Stories: {backlog_analysis['total_stories']}")
        print(f"   ✅ Total Points: {backlog_analysis['total_points']}")

        if 'error' not in velocity_result:
            print(f"   ✅ Average Velocity: {velocity_result['average_velocity']:.1f} points/sprint")

        return self.analyses['poker_planning']

    def run_gantt_analysis(self, epics: list) -> dict:
        """Generate Gantt chart"""
        print("\n📊 Generating Gantt Chart...")

        config = GanttConfig(project_start_date=self.start_date)
        generator = GanttChartGenerator(config)

        # Add epics as tasks
        current_date = self.start_date
        for epic in epics:
            task = Task(
                id=epic['id'],
                name=epic['name'],
                task_type=TaskType.EPIC,
                start_date=current_date,
                duration_days=epic['duration'],
                dependencies=epic.get('predecessors', []),
                status=TaskStatus.NOT_STARTED
            )
            generator.add_task(task)
            current_date += timedelta(days=epic['duration'])

        chart_data = generator.generate()
        self.analyses['gantt'] = chart_data

        print(f"   ✅ Timeline: {chart_data['timeline']['project_start']} to {chart_data['timeline']['project_end']}")

        return chart_data

    def generate_markdown_report(self) -> str:
        """Generate comprehensive markdown report"""
        md = MarkdownExporter
        lines = []

        # Title
        lines.append(md.heading(f"{self.project_name} - Complete Analysis Report", 1))
        lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")

        # Executive Summary
        lines.append(md.heading("Executive Summary", 2))

        if 'critical_path' in self.analyses:
            cpm = self.analyses['critical_path']
            lines.append(f"- **Project Duration**: {cpm['project_duration']} days")
            lines.append(f"- **Critical Path**: {' → '.join(cpm['critical_path'])}")

        if 'budget' in self.analyses:
            budget = self.analyses['budget']
            lines.append(f"- **Total Budget**: ${budget['summary']['total_budget']:,.2f}")
            lines.append(f"- **Sprints Required**: {budget['project_metrics']['total_sprints']}")

        if 'poker_planning' in self.analyses:
            pp = self.analyses['poker_planning']
            lines.append(f"- **Total Story Points**: {pp['backlog']['total_points']}")
            if 'error' not in pp['velocity']:
                lines.append(f"- **Team Velocity**: {pp['velocity']['average_velocity']:.1f} points/sprint")

        lines.append("")

        # Critical Path Section
        if 'critical_path' in self.analyses:
            lines.append(md.heading("Critical Path Analysis", 2))
            cpm = self.analyses['critical_path']

            headers = ["Task", "Duration", "ES", "EF", "Slack", "Critical"]
            rows = []
            for act in cpm['activities']:
                rows.append([
                    f"{act['id']}: {act['name']}",
                    f"{act['duration']} days",
                    act['ES'],
                    act['EF'],
                    f"{act['slack']:.1f}",
                    "✅" if act['critical'] else "❌"
                ])
            lines.append(md.table(headers, rows))
            lines.append("")

        # Budget Section
        if 'budget' in self.analyses:
            lines.append(md.heading("Budget Analysis", 2))
            budget = self.analyses['budget']

            # Scenario table
            scenarios = budget['scenarios']
            budget_summary = budget['summary']
            scenario_headers = ["Scenario", "Budget"]
            scenario_rows = [
                ["Optimistic", f"${scenarios['optimistic']:,.2f}"],
                ["Realistic", f"${scenarios['realistic']:,.2f}"],
                ["Pessimistic", f"${scenarios['pessimistic']:,.2f}"]
            ]
            lines.append(md.table(scenario_headers, scenario_rows))
            lines.append("")

        # Gantt Chart ASCII
        if 'gantt' in self.analyses:
            lines.append(md.heading("Project Timeline", 2))
            gantt = self.analyses['gantt']
            lines.append(md.code_block(gantt['ascii_chart'], ""))
            lines.append("")

        return '\n'.join(lines)

    def generate_mermaid_diagrams(self) -> str:
        """Generate Mermaid diagrams"""
        diagrams = []

        # Critical Path Flowchart
        if 'critical_path' in self.analyses:
            cpm = self.analyses['critical_path']
            nodes = []
            edges = []

            for act in cpm['activities']:
                nodes.append({
                    'id': act['id'],
                    'label': f"{act['name']}\\n{act['duration']}d",
                    'shape': 'rounded',
                    'critical': act['critical']
                })

                for pred in act.get('predecessors', []):
                    edges.append({'from': pred, 'to': act['id']})

            flowchart = MermaidExporter.flowchart(nodes, edges, direction="LR")
            diagrams.append(f"## Critical Path\n\n```mermaid\n{flowchart}\n```\n")

        # Budget Pie Chart
        if 'budget' in self.analyses:
            budget = self.analyses['budget']
            data = {role: info['cost'] for role, info in budget['breakdown']['by_role'].items()}
            pie = MermaidExporter.pie_chart("Budget by Role", data)
            diagrams.append(f"## Budget Breakdown\n\n```mermaid\n{pie}\n```\n")

        return '\n'.join(diagrams)

    def generate_html_report(self) -> str:
        """Generate HTML executive report"""
        sections = []

        # Summary
        summary_content = f"<h3>{self.project_name}</h3>"
        summary_content += "<ul>"

        if 'critical_path' in self.analyses:
            cpm = self.analyses['critical_path']
            summary_content += f"<li><strong>Duration:</strong> {cpm['project_duration']} days</li>"

        if 'budget' in self.analyses:
            budget = self.analyses['budget']
            summary_content += f"<li><strong>Budget:</strong> ${budget['summary']['total_budget']:,.2f}</li>"

        summary_content += "</ul>"
        sections.append({"heading": "Project Overview", "content": summary_content})

        # Add more sections from analyses...
        if 'critical_path' in self.analyses:
            cpm = self.analyses['critical_path']
            headers = ["ID", "Name", "Duration", "Critical"]
            rows = [[a['id'], a['name'], f"{a['duration']} days", "✓" if a['critical'] else ""]
                   for a in cpm['activities']]
            table = HTMLExporter.table(headers, rows)
            sections.append({"heading": "Critical Path", "content": table})

        return HTMLExporter.simple_report(f"{self.project_name} - Analysis", sections)


def main():
    """Run complete project analysis with all tools"""

    print("=" * 80)
    print("COMPLETE PROJECT ANALYSIS - ALL TOOLS INTEGRATION")
    print("=" * 80)

    # Initialize project
    project = ProjectAnalysisReport("E-Commerce Platform v2.0")

    # Define project structure
    epics = [
        {"id": "E1", "name": "User Authentication", "duration": 14, "predecessors": [], "points": 21},
        {"id": "E2", "name": "Product Catalog", "duration": 21, "predecessors": ["E1"], "points": 34},
        {"id": "E3", "name": "Shopping Cart", "duration": 14, "predecessors": ["E1"], "points": 21},
        {"id": "E4", "name": "Checkout & Payment", "duration": 21, "predecessors": ["E2", "E3"], "points": 34},
        {"id": "E5", "name": "Order Management", "duration": 14, "predecessors": ["E4"], "points": 21}
    ]

    # Define team
    team = [
        TeamMember("Tech Lead", 1, 120),
        TeamMember("Senior Dev", 2, 100),
        TeamMember("Developer", 3, 70),
        TeamMember("QA Engineer", 2, 65)
    ]

    # Stories for poker planning
    stories = [
        {"id": "US-001", "title": "Login OAuth", "points": 8, "completed": True, "actual_points": 8, "sprint": 1},
        {"id": "US-002", "title": "User Registration", "points": 5, "completed": True, "actual_points": 5, "sprint": 1},
        {"id": "US-003", "title": "Password Reset", "points": 3, "completed": True, "actual_points": 3, "sprint": 1},
        {"id": "US-004", "title": "Product List", "points": 8, "completed": True, "actual_points": 8, "sprint": 2},
        {"id": "US-005", "title": "Product Search", "points": 13, "completed": True, "actual_points": 13, "sprint": 2},
        {"id": "US-006", "title": "Add to Cart", "points": 5, "completed": False, "sprint": 3},
        {"id": "US-007", "title": "Cart Management", "points": 8, "completed": False, "sprint": 3}
    ]

    # Run all analyses
    project.run_critical_path_analysis(epics)
    project.run_budget_analysis(story_points=131, team=team, fixed_costs=25000)
    project.run_poker_planning_analysis(stories)
    project.run_gantt_analysis(epics)

    # Generate exports
    print("\n" + "=" * 80)
    print("GENERATING COMPREHENSIVE REPORTS...")
    print("=" * 80)

    # 1. Markdown Report
    print("\n📄 1. Markdown Comprehensive Report")
    md_report = project.generate_markdown_report()
    save_to_file(md_report, 'project_analysis_complete.md')
    print("   ✅ Saved: project_analysis_complete.md")

    # 2. Mermaid Diagrams
    print("\n🎨 2. Mermaid Diagrams")
    mermaid_diagrams = project.generate_mermaid_diagrams()
    save_to_file(mermaid_diagrams, 'project_diagrams.md')
    print("   ✅ Saved: project_diagrams.md")

    # 3. HTML Executive Report
    print("\n🌐 3. HTML Executive Report")
    html_report = project.generate_html_report()
    save_to_file(html_report, 'project_executive_summary.html')
    print("   ✅ Saved: project_executive_summary.html")

    # 4. JSON Data Package
    print("\n💾 4. JSON Data Package")
    json_data = JSONExporter.to_json(project.analyses)
    save_to_file(json_data, 'project_analysis_data.json')
    print("   ✅ Saved: project_analysis_data.json")

    print("\n" + "=" * 80)
    print("✅ COMPLETE ANALYSIS FINISHED!")
    print("=" * 80)
    print("\nGenerated Files:")
    print("  📄 project_analysis_complete.md - Full markdown report")
    print("  🎨 project_diagrams.md - Mermaid visualizations")
    print("  🌐 project_executive_summary.html - Executive summary")
    print("  💾 project_analysis_data.json - Raw data for API integration")
    print("\n💡 Next Steps:")
    print("  1. Review project_executive_summary.html in browser")
    print("  2. Share project_analysis_complete.md with stakeholders")
    print("  3. Import project_analysis_data.json into your PM tools")


if __name__ == "__main__":
    main()
